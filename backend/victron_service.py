import asyncio
import os
import json
import sys
import time
import uuid
import glob
import random
import struct
import platform
import math
import subprocess 
from aiohttp import web
from datetime import datetime
from bleak import BleakScanner, BleakClient

# =================================================================
# VERSIONIERUNG & DOKUMENTATION
# =================================================================
BACKEND_VERSION = "29.6 (EcoFlow Remain Time)" 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
INDEX_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "index.html"))
STATIC_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "static"))

# FIX 1: Zwinge Python, das /backend Verzeichnis fuer Imports zu nutzen
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# --- ECOFLOW CONTROLLER IMPORT ---
try:
    from ecoflow_controller import EcoFlowController
except ImportError as e:
    print(f"Warnung: ecoflow_controller.py nicht gefunden ({e}). EcoFlow-Funktionen sind deaktiviert.")
    EcoFlowController = None

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PRESSURE_HISTORY_FILE = os.path.join(BASE_DIR, "pressure_history.json")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration.json")

SERVER_SESSION_ID = str(uuid.uuid4())[:8]

# Globale Variablen
DEVICE_CONFIG = {}
ECOFLOW_CONFIG = {}
FRIDGE_CONFIG = {}
VEHICLE_CONFIG = {}
POWERQUEEN_CONFIG = {}
fridge_action_queue = asyncio.Queue()

def load_config():
    global DEVICE_CONFIG, ECOFLOW_CONFIG, FRIDGE_CONFIG, VEHICLE_CONFIG, POWERQUEEN_CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                full_config = json.load(f)
            DEVICE_CONFIG = full_config.get("victron", {})
            ECOFLOW_CONFIG = full_config.get("ecoflow", {})
            FRIDGE_CONFIG = full_config.get("fridge", {})
            VEHICLE_CONFIG = full_config.get("vehicle", {})
            POWERQUEEN_CONFIG = full_config.get("powerqueen", {})
            print(f"Konfiguration geladen: {len(DEVICE_CONFIG)} Victron Geräte.")
        except Exception as e:
            print(f"Fehler beim Laden der config.json: {e}")

load_config()

print(f"\n{'='*60}")
print(f"### MULTIVAN PI BACKEND v{BACKEND_VERSION} ###")
print(f"Status: Start-Sequencer Active")
print(f"Zeit: {datetime.now()}")
print(f"{'='*60}")

# =================================================================
# TREIBER IMPORTS
# =================================================================
SMBUS_AVAILABLE = False
SHARED_BUS = None
try:
    import smbus2 as smbus
    SHARED_BUS = smbus.SMBus(1)
    SMBUS_AVAILABLE = True
    print("I2C: Bus aktiv.")
except: 
    print("I2C: Fehler oder nicht vorhanden.")
    SHARED_BUS = None

BLE_AVAILABLE = False
try:
    from victron_ble.devices import BatterySense as BatterySenseParser
    from victron_ble.devices import SolarCharger as SolarChargerParser
    from victron_ble.devices import DcDcConverter as DcDcParser
    try: from victron_ble.devices import SmartShunt as SmartShuntParser
    except ImportError: from victron_ble.devices import BatteryMonitor as SmartShuntParser
    BLE_AVAILABLE = True
    print("BLE: Victron Bibliotheken geladen.")
except: pass

# =================================================================
# SYSTEM HELPER
# =================================================================
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(float(f.read()) / 1000, 1)
    except: return 0.0

def get_rtc_temp():
    try:
        paths = glob.glob("/sys/bus/i2c/devices/*-0068/hwmon/hwmon*/temp1_input")
        if paths:
            with open(paths[0], "r") as f:
                return round(float(f.read()) / 1000, 1)
    except: pass
    return 0.0

def get_wifi_ssid():
    try:
        ssid = subprocess.check_output(["iwgetid", "-r"]).decode("utf-8").strip()
        if ssid: return ssid
        return None
    except: return None

# =================================================================
# SENSOR KLASSEN
# =================================================================
class LevelingSensor:
    def __init__(self, bus):
        self.bus = bus
        self.sensor_type = None 
        self.address = None
        self.offsets = {"roll": 0.0, "pitch": 0.0}
        self.working = False
        
        self.last_roll = 0.0
        self.last_pitch = 0.0
        self.alpha = 0.1 

        if self.bus:
            for addr in [0x28, 0x29]:
                try:
                    if self.bus.read_byte_data(addr, 0x00) == 0xA0:
                        self.address = addr
                        self.sensor_type = 'BNO055'
                        break
                except: pass
            
            if not self.sensor_type:
                try:
                    if self.bus.read_byte_data(0x53, 0x00) == 0xE5:
                        self.address = 0x53
                        self.sensor_type = 'ADXL345'
                except: pass

            if self.sensor_type == 'BNO055':
                try:
                    self.bus.write_byte_data(self.address, 0x3D, 0x00)
                    time.sleep(0.05)
                    self.bus.write_byte_data(self.address, 0x3D, 0x08)
                    time.sleep(0.05)
                    self.working = True
                    print(f"BNO055 auf Adresse {hex(self.address)} im IMU-Modus initialisiert.")
                except: print("Fehler bei BNO055 Initialisierung.")
            
            elif self.sensor_type == 'ADXL345':
                try:
                    self.bus.write_byte_data(self.address, 0x2D, 0x08)
                    self.bus.write_byte_data(self.address, 0x31, 0x00)
                    self.working = True
                    print(f"ADXL345 auf Adresse {hex(self.address)} initialisiert (Fallback).")
                except: print("Fehler bei ADXL345 Initialisierung.")
            
            else:
                print("Kein Lagesensor am I2C Bus gefunden.")

            if self.working:
                self.load_calibration()

    def load_calibration(self):
        if os.path.exists(CALIBRATION_FILE):
            try:
                with open(CALIBRATION_FILE, 'r') as f:
                    data = json.load(f)
                    self.offsets["roll"] = data.get("roll_offset", 0.0)
                    self.offsets["pitch"] = data.get("pitch_offset", 0.0)
            except: pass

    def save_calibration(self, r, p):
        self.offsets["roll"] += r
        self.offsets["pitch"] += p
        try:
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump({"roll_offset": self.offsets["roll"], "pitch_offset": self.offsets["pitch"]}, f)
            return True
        except: return False

    def read_adxl_axis(self, addr):
        try:
            low = self.bus.read_byte_data(self.address, addr)
            high = self.bus.read_byte_data(self.address, addr+1)
            val = (high << 8) | low
            if val > 32767: return val - 65536
            return val
        except: return 0

    def get_angles(self):
        if not self.working: return 0.0, 0.0
        
        if self.sensor_type == 'BNO055':
            try:
                b = self.bus.read_i2c_block_data(self.address, 0x1C, 4)
                roll_raw = (b[1] << 8) | b[0]
                if roll_raw > 32767: roll_raw -= 65536
                pitch_raw = (b[3] << 8) | b[2]
                if pitch_raw > 32767: pitch_raw -= 65536
                return round((roll_raw / 16.0) - self.offsets["roll"], 1), round((pitch_raw / 16.0) - self.offsets["pitch"], 1)
            except: return 0.0, 0.0
            
        elif self.sensor_type == 'ADXL345':
            try:
                x = self.read_adxl_axis(0x32)
                y = self.read_adxl_axis(0x34)
                z = self.read_adxl_axis(0x36)
                
                new_pitch = math.atan2(-x, math.sqrt(y*y + z*z)) * 180.0 / math.pi
                new_roll = math.atan2(y, z) * 180.0 / math.pi
                
                self.last_roll = (new_roll * self.alpha) + (self.last_roll * (1.0 - self.alpha))
                self.last_pitch = (new_pitch * self.alpha) + (self.last_pitch * (1.0 - self.alpha))
                
                return round(self.last_roll - self.offsets["roll"], 1), round(self.last_pitch - self.offsets["pitch"], 1)
            except: return 0.0, 0.0

class BME280:
    def __init__(self, bus):
        self.bus = bus; self.address = 0x76; self.cal = {}; self.working = False
        if self.bus:
            try:
                id = self.bus.read_byte_data(0x76, 0xD0)
                if id in [0x60, 0x58]: self.address = 0x76
                else: self.address = 0x77
                self._load_calibration()
                self.bus.write_byte_data(self.address, 0xF2, 0x01)
                self.bus.write_byte_data(self.address, 0xF5, 0x90) 
                self.bus.write_byte_data(self.address, 0xF4, 0x27)
                self.working = True
            except: pass

    def _load_calibration(self):
        try:
            b = self.bus.read_i2c_block_data(self.address, 0x88, 24)
            self.cal['T1'] = struct.unpack('<H', bytes(b[0:2]))[0]; self.cal['T2'] = struct.unpack('<h', bytes(b[2:4]))[0]; self.cal['T3'] = struct.unpack('<h', bytes(b[4:6]))[0]
            self.cal['P1'] = struct.unpack('<H', bytes(b[6:8]))[0]; self.cal['P2'] = struct.unpack('<h', bytes(b[8:10]))[0]; self.cal['P3'] = struct.unpack('<h', bytes(b[10:12]))[0]; self.cal['P4'] = struct.unpack('<h', bytes(b[12:14]))[0]; self.cal['P5'] = struct.unpack('<h', bytes(b[14:16]))[0]; self.cal['P6'] = struct.unpack('<h', bytes(b[16:18]))[0]; self.cal['P7'] = struct.unpack('<h', bytes(b[18:20]))[0]; self.cal['P8'] = struct.unpack('<h', bytes(b[20:22]))[0]; self.cal['P9'] = struct.unpack('<h', bytes(b[22:24]))[0]
            h1 = self.bus.read_byte_data(self.address, 0xA1); h_data = self.bus.read_i2c_block_data(self.address, 0xE1, 7)
            self.cal['H1'] = h1; self.cal['H2'] = struct.unpack('<h', bytes(h_data[0:2]))[0]; self.cal['H3'] = h_data[2]
            e4 = h_data[3]; e5 = h_data[4]; e6 = h_data[5]; self.cal['H4'] = (e4 << 4) | (e5 & 0x0F); 
            if self.cal['H4'] > 2047: self.cal['H4'] -= 4096
            self.cal['H5'] = (e6 << 4) | (e5 >> 4); 
            if self.cal['H5'] > 2047: self.cal['H5'] -= 4096
            self.cal['H6'] = struct.unpack('<b', bytes([h_data[6]]))[0]
        except: self.working = False

    def read_data(self):
        if not self.working: return None
        try:
            d = self.bus.read_i2c_block_data(self.address, 0xF7, 8)
            t_r = (d[3]<<12)|(d[4]<<4)|(d[5]>>4); p_r = (d[0]<<12)|(d[1]<<4)|(d[2]>>4); h_r = (d[6]<<8)|d[7]
            v1 = (t_r/16384.0 - self.cal['T1']/1024.0)*self.cal['T2']; v2 = ((t_r/131072.0 - self.cal['T1']/8192.0)**2)*self.cal['T3']; t_f = v1 + v2; temp = t_f / 5120.0
            v1 = (t_f/2.0) - 64000.0; v2 = v1 * v1 * self.cal['P6'] / 32768.0; v2 = v2 + v1 * self.cal['P5'] * 2.0; v2 = (v2/4.0)+(self.cal['P4']*65536.0); v1 = (self.cal['P3'] * v1 * v1 / 524288.0 + self.cal['P2'] * v1) / 524288.0; v1 = (1.0 + v1 / 32768.0)*self.cal['P1']
            if v1 == 0: press = 0
            else: p = 1048576.0 - p_r; p = ((p - v2/4096.0) * 6250.0) / v1; v1 = self.cal['P9'] * p * p / 2147483648.0; v2 = p * self.cal['P8'] / 32768.0; press = (p + (v1 + v2 + self.cal['P7']) / 16.0) / 100.0
            h = t_f - 76800.0; h = (h_r - (self.cal['H4']*64.0 + self.cal['H5']/16384.0 * h)) * (self.cal['H2']/65536.0 * (1.0 + self.cal['H6']/67108864.0 * h * (1.0 + self.cal['H3']/67108864.0 * h))); h = h * (1.0 - self.cal['H1']*h/524288.0); hum = max(0, min(100, h))
            return round(temp, 1), round(press, 1), round(hum, 1)
        except: return None

class DS18B20:
    def __init__(self):
        self.base_dir = '/sys/bus/w1/devices/'
        self.device_file = None
        self.error_reported = False
        self._find()

    def _find(self):
        try:
            folders = glob.glob(self.base_dir + '28*')
            if folders: 
                self.device_file = folders[0] + '/w1_slave'
                if self.error_reported:
                    print(f"DS18B20: Sensor Hardware wieder gefunden -> {self.device_file}")
                else:
                    print(f"DS18B20: Sensor Hardware gefunden -> {self.device_file}")
                self.error_reported = False
            else:
                self.device_file = None
                if not self.error_reported:
                    print("DS18B20 [FEHLER]: Kein 1-Wire Sensor gefunden! Pruefe Kabel, Pullup-Widerstand (4.7k) und raspi-config.")
                    self.error_reported = True
        except Exception as e:
            print(f"DS18B20 [SYS-FEHLER]: {e}")

    def read(self):
        if not self.device_file or not os.path.exists(self.device_file):
            self._find()
            if not self.device_file:
                return None

        try:
            with open(self.device_file, 'r') as f:
                lines = f.readlines()
                if len(lines) > 0 and 'YES' in lines[0]:
                    pos = lines[1].find('t=')
                    if pos != -1: 
                        return float(lines[1][pos+2:])/1000.0
                else:
                    if not self.error_reported:
                        print("DS18B20 [WARNUNG]: Sensor antwortet, aber Signal ist fehlerhaft (CRC NO).")
                        self.error_reported = True
        except Exception as e:
            print(f"DS18B20 [LESE-FEHLER]: {e}")
            self.device_file = None 
        return None

class ClimateModule:
    def __init__(self, bus):
        self.bme = BME280(bus)
        self.ds18 = DS18B20()
        self.data = {"temp_in": 0, "pressure": 0, "humidity": 0, "temp_out": 0.0}
        self.history = []
        self.last_save = 0
        self.load()

    def load(self):
        if os.path.exists(PRESSURE_HISTORY_FILE):
            try:
                with open(PRESSURE_HISTORY_FILE, 'r') as f: 
                    self.history = json.load(f)
            except: 
                self.history = []

    def save(self):
        try:
            with open(PRESSURE_HISTORY_FILE, 'w') as f: 
                json.dump(self.history, f)
        except: pass

    def update(self):
        d = self.bme.read_data()
        if d:
            temp, press, hum = d
            self.data["temp_in"] = temp
            self.data["pressure"] = press
            self.data["humidity"] = hum

        do = self.ds18.read()
        if do is not None: 
            self.data["temp_out"] = round(do, 1)
            
        if time.time() - self.last_save > 600:
            if self.data["pressure"] > 0:
                self.history.append({"ts": int(time.time()), "val": self.data["pressure"]})
                if len(self.history) > 450: 
                    self.history.pop(0)
                self.save()
                self.last_save = time.time()

    def get_trend(self):
        if len(self.history) < 18: return "stabil"
        diff = self.history[-1]["val"] - self.history[-18]["val"]
        if diff > 1.0: return "steigend"
        if diff < -1.0: return "fallend"
        return "stabil"

    def get_data(self):
        d = self.data.copy()
        d["pressure_trend"] = self.get_trend()
        d["pressure_history"] = self.history
        return d

class SharedState:
    def __init__(self):
        self.data = {
            "sys_backend_version": BACKEND_VERSION,
            "aufbau_soc": 42.0, "aufbau_volt": 0.0, "aufbau_amp": 0.0,
            "solar_watt": 0, "mppt_charge_amp": 0.0, 
            "starter_volt": 0.0, "starter_soc": None, "booster_amp": "Offline",
            "sense_temp": 0.0, "sense_volt": 0.0,
            "sense_last": "Suche...", "shunt_aufbau_last": "Suche...",
            "solar_last": "Suche...", "booster_last": "Suche...", "shunt_starter_last": "Suche...",
            "level_roll": 0.0, "level_pitch": 0.0,
            "session": SERVER_SESSION_ID,
            "sys_python": sys.version.split()[0], "sys_platform": platform.platform(),
            "sys_cpu_temp": 0.0, "sys_rtc_temp": 0.0, "sys_ssid": None,
            
            "sense_packets": 0,
            
            "fridge_connected": False, "temp_fridge": 0, "fridge_target": 0, 
            "fridge_voltage": 0.0, "fridge_mode": "ECO", "fridge_locked": True,
            "fridge_protection": "H",
            "fridge_power": False,
            "veh_wheelbase": VEHICLE_CONFIG.get("wheelbase", 2920), 
            "veh_track": VEHICLE_CONFIG.get("track_width", 1560),
            
            "pq_soc": 0, "pq_temp": 0.0,

            # EcoFlow Werte
            "ecoflow_soc": 0, 
            "ecoflow_in": 0, 
            "ecoflow_out": 0,
            "ecoflow_remain": 0, 
            "ecoflow_connected": False,
            "ecoflow_ac_on": False, 
            "ecoflow_dc_on": False, 
            "ecoflow_usb_on": False
        }
        self.last_seen = {}

    def update_victron(self, key, val, status_key):
        self.data[key] = val
        self.data[status_key] = time.strftime("%H:%M:%S")
        self.last_seen[status_key] = time.time()

    def check_timeouts(self):
        now = time.time()
        timeout = 120
        keys = [
            ("shunt_aufbau_last", "aufbau_soc"), 
            ("sense_last", "sense_temp"), 
            ("solar_last", "solar_watt"),
            ("booster_last", "booster_amp")
        ]
        for status_key, data_key in keys:
            if now - self.last_seen.get(status_key, 0) > timeout:
                if self.data.get(status_key) != "Suche...":
                    self.data[status_key] = "Suche..."
                    if data_key == "booster_amp":
                        self.data[data_key] = "Offline"
                        
state = SharedState()
climate_sensor = ClimateModule(SHARED_BUS)
leveling = LevelingSensor(SHARED_BUS)

# =================================================================
# KÜHLBOX TASK 
# =================================================================
async def vevor_fridge_task(state_obj):
    if not FRIDGE_CONFIG: 
        return
        
    mac = FRIDGE_CONFIG.get("mac")
    rx_uuid = FRIDGE_CONFIG.get("rx_uuid")
    tx_uuid = FRIDGE_CONFIG.get("tx_uuid")
    
    local_state = {
        "lock": 0x00, "power": 0x00, "mode": 0x00, 
        "battery": 0x00, "temp_target": 0
    }
    last_action_time = [0.0] 
    
    def build_command():
        temp_byte = local_state["temp_target"] & 0xFF
        payload = [
            0x11, 0x02, 
            local_state["lock"], local_state["power"], local_state["mode"], local_state["battery"], 
            temp_byte, 0x0c, 0xec, 0x02, 0x00, 0x00, 0x00, 0x00, 0xfd, 0x00, 0x04
        ]
        checksum = (sum(payload) - 8) & 0xFF
        return bytes([0xfe, 0xfe] + payload + [checksum])

    def notification_handler(sender, data):
        if time.time() - last_action_time[0] < 2.5: return
            
        if len(data) >= 12 and data[0] == 0xfe and data[1] == 0xfe:
            local_state["lock"] = data[4]
            local_state["power"] = data[5]
            local_state["mode"] = data[6]
            local_state["battery"] = data[7] 
            
            temp_target = data[8]
            if temp_target > 127: temp_target -= 256
            local_state["temp_target"] = temp_target
            
            state_obj.data["fridge_connected"] = True
            state_obj.data["fridge_power"] = True if data[5] == 1 else False
            state_obj.data["fridge_mode"] = "ECO" if data[6] == 1 else "MAX"
            state_obj.data["fridge_target"] = temp_target
            
            if data[7] == 0: state_obj.data["fridge_protection"] = "L"
            elif data[7] == 1: state_obj.data["fridge_protection"] = "M"
            else: state_obj.data["fridge_protection"] = "H"
            
            try:
                if len(data) >= 19:
                    temp_ist = struct.unpack_from('>b', data, 18)[0]
                    if -30 <= temp_ist <= 50: state_obj.data["temp_fridge"] = temp_ist
                if len(data) >= 22:
                    state_obj.data["fridge_voltage"] = float(f"{data[20]}.{data[21]}")
            except: pass

    async def ping_loop(client):
        while True:
            try:
                await client.write_gatt_char(tx_uuid, bytes.fromhex("fefe03010200"))
                await asyncio.sleep(3)
            except: break

    while True:
        try:
            print(f"Kühlbox: Verbinde zu {mac}...")
            async with BleakClient(mac, timeout=15.0) as client:
                print("Kühlbox: Verbunden! Abonniere Daten...")
                await client.start_notify(rx_uuid, notification_handler)
                ping_task = asyncio.create_task(ping_loop(client))
                
                while client.is_connected:
                    cmd_data = await fridge_action_queue.get()
                    action = cmd_data.get("action")
                    val = cmd_data.get("value")
                    
                    if action == "power": local_state["power"] = 1 if val == "on" else 0
                    elif action == "mode": local_state["mode"] = 1 if val == "eco" else 0
                    elif action == "temp": local_state["temp_target"] = int(val)
                    elif action == "protection":
                        if val == "L": local_state["battery"] = 0
                        elif val == "M": local_state["battery"] = 1
                        elif val == "H": local_state["battery"] = 2
                    
                    local_state["lock"] = 0x00
                    await client.write_gatt_char(tx_uuid, build_command())
                    last_action_time[0] = time.time()
                    fridge_action_queue.task_done()
                        
        except Exception as e:
            print(f"Kühlbox Verbindung abgebrochen: {e}")
            state_obj.data["fridge_connected"] = False
            await asyncio.sleep(20) 

# =================================================================
# WATCHDOG TASK
# =================================================================
async def fridge_watchdog_task(state_obj):
    while True:
        await asyncio.sleep(180) 
        if not FRIDGE_CONFIG: continue
        auto_off_soc = FRIDGE_CONFIG.get("auto_off_soc", 0)
        
        if auto_off_soc > 0:
            current_soc = state_obj.data.get("aufbau_soc", 100.0)
            is_powered_on = state_obj.data.get("fridge_power", False)
            shunt_status = state_obj.data.get("shunt_aufbau_last", "Suche...")
            
            if shunt_status != "Suche..." and isinstance(current_soc, (int, float)):
                if current_soc <= auto_off_soc and is_powered_on:
                    print(f"!!! WATCHDOG !!! Batterie {current_soc}%. Abschaltung!")
                    await fridge_action_queue.put({"action": "power", "value": "off"})

# =================================================================
# POWERQUEEN BATTERIE TASK
# =================================================================
async def powerqueen_task(state_obj):
    if not POWERQUEEN_CONFIG:
        return
        
    mac = POWERQUEEN_CONFIG.get("mac")
    uart_uuid = POWERQUEEN_CONFIG.get("uart_uuid")
    ping_cmd_str = POWERQUEEN_CONFIG.get("ping_cmd")
    
    if not mac or not uart_uuid or not ping_cmd_str:
        print("PowerQueen: Unvollständige Config. Überspringe Task.")
        return
        
    ping_cmd = bytes.fromhex(ping_cmd_str)
    rx_buffer = bytearray()
    last_valid_temp = None

    def parse_pq_data(sender, data):
        nonlocal rx_buffer, last_valid_temp
        rx_buffer.extend(data)
        
        idx = rx_buffer.find(bytes.fromhex("000065019355aa"))
        
        if idx != -1:
            if len(rx_buffer) >= idx + 7 + 101:
                payload = rx_buffer[idx+7 : idx+7+101]
                
                try:
                    soc = struct.unpack_from(">H", payload, 82)[0]
                    t1 = struct.unpack_from(">b", payload, 42)[0]
                    t2 = struct.unpack_from(">b", payload, 45)[0]
                    t3 = struct.unpack_from(">b", payload, 47)[0]
                    
                    valid_temps = [t for t in (t1, t2, t3) if t != 0]
                    if valid_temps:
                        last_valid_temp = float(min(valid_temps))
                    
                    if last_valid_temp is not None:
                        state_obj.data["pq_soc"] = soc
                        state_obj.data["pq_temp"] = round(last_valid_temp, 1)
                except Exception:
                    pass
                    
                rx_buffer = rx_buffer[idx+7+101:]
        else:
            if len(rx_buffer) > 300:
                rx_buffer.clear()

    while True:
        try:
            print(f"PowerQueen: Verbinde zu {mac}...")
            async with BleakClient(mac, timeout=15.0) as client:
                print("PowerQueen: Verbunden!")
                await client.start_notify(uart_uuid, parse_pq_data)
                
                while client.is_connected:
                    await client.write_gatt_char(uart_uuid, ping_cmd)
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"PowerQueen: Verbindung abgerissen ({e}). Neuer Versuch in 10s...")
            await asyncio.sleep(10)

# =================================================================
# ECOFLOW IOBROKER TASK
# =================================================================
async def ecoflow_task(state_obj):
    if not ECOFLOW_CONFIG or not EcoFlowController:
        return
        
    sn = ECOFLOW_CONFIG.get("sn", "P351ZEH4PGBL0776")
    ctrl = EcoFlowController(serial=sn)
    print(f"EcoFlow: Hintergrund-Dienst gestartet für {sn}")
    
    while True:
        try:
            soc = await asyncio.to_thread(ctrl.get_soc)
            if soc is not None:
                state_obj.data["ecoflow_soc"] = soc
                state_obj.data["ecoflow_connected"] = True
                state_obj.data["ecoflow_ac_on"] = await asyncio.to_thread(ctrl.get_ac_status)
                state_obj.data["ecoflow_dc_on"] = await asyncio.to_thread(ctrl.get_12v_status)
                state_obj.data["ecoflow_usb_on"] = await asyncio.to_thread(ctrl.get_usb_status)
                
                if hasattr(ctrl, 'get_total_in'):
                    state_obj.data["ecoflow_in"] = await asyncio.to_thread(ctrl.get_total_in)
                if hasattr(ctrl, 'get_total_out'):
                    state_obj.data["ecoflow_out"] = await asyncio.to_thread(ctrl.get_total_out)
                
                # NEUER WERT: Verbleibende Zeit
                if hasattr(ctrl, 'get_remain_time'):
                    state_obj.data["ecoflow_remain"] = await asyncio.to_thread(ctrl.get_remain_time)
            else:
                state_obj.data["ecoflow_connected"] = False
        except Exception as e:
            print(f"EcoFlow Abfrage-Fehler: {e}")
            state_obj.data["ecoflow_connected"] = False
            
        await asyncio.sleep(15) 

# =================================================================
# VICTRON BLE SCANNER LOGIK 
# =================================================================
async def ble_scanner_task():
    def callback(device, adv_data):
        mac = device.address.upper().strip()

        if mac in DEVICE_CONFIG:
            try:
                mfg_data = adv_data.manufacturer_data
                victron_bytes = mfg_data.get(737)
                if not victron_bytes: return 

                cfg = DEVICE_CONFIG[mac]; key = cfg["key"]; dtype = cfg["type"]
                parser = None

                if dtype == "mppt": parser = SolarChargerParser(key)
                elif dtype == "booster": parser = DcDcParser(key)
                elif dtype in ["shunt_starter", "shunt_aufbau"]: parser = SmartShuntParser(key)
                elif dtype == "sense": parser = BatterySenseParser(key)
                
                if parser:
                    d = parser.parse(victron_bytes)
                    if dtype == "sense":
                        state.update_victron("sense_temp", d.get_temperature(), "sense_last")
                        state.data["sense_volt"] = d.get_voltage()
                    elif dtype == "shunt_aufbau":
                        state.update_victron("aufbau_soc", d.get_soc(), "shunt_aufbau_last")
                        state.data["aufbau_volt"] = d.get_voltage()
                        state.data["aufbau_amp"] = d.get_current()
                    elif dtype == "mppt": 
                        state.update_victron("solar_watt", d.get_solar_power(), "solar_last")
                        charge_current = d.get_battery_charging_current()
                        if charge_current is None: charge_current = 0.0
                        state.data["mppt_charge_amp"] = charge_current
                    elif dtype == "booster":
                        try:
                            raw_val = d.get_charge_state()
                            status_text = str(raw_val).upper().split(".")[-1]
                            trans = {"OFF":"AUS","ON":"AN","BULK":"LADEN","ABSORPTION":"ABSORP.","FLOAT":"ERHALT.","STORAGE":"LAGERNG","FAULT":"FEHLER"}
                            state.update_victron("booster_amp", trans.get(status_text, status_text), "booster_last")
                        except: state.update_victron("booster_amp", "ERR", "booster_last")
                    elif dtype == "shunt_starter": 
                        soc = d.get_soc()
                        if soc is not None:
                            state.update_victron("starter_soc", soc, "shunt_starter_last")
                        else:
                            state.update_victron("starter_volt", d.get_voltage(), "shunt_starter_last")
                        state.data["starter_volt"] = d.get_voltage()
                    state.data["sense_packets"] += 1
            except Exception: pass

    scanner = BleakScanner(detection_callback=callback)
    
    # FIX 2: Absicherung, falls der Bluetooth-Chip beim Start noch durch die PowerQueen blockiert ist
    while True:
        try:
            await scanner.start()
            print("Victron Scanner erfolgreich gestartet!")
            break
        except Exception as e:
            print(f"Victron Scanner wartet auf freien Bluetooth-Chip ({e})... Neuer Versuch in 5s")
            await asyncio.sleep(5)
            
    while True: await asyncio.sleep(10)

# =================================================================
# API ENDPUNKTE
# =================================================================
async def api_fridge_control(request):
    try:
        data = await request.json()
        action = data.get("action") 
        value = data.get("value")
        await fridge_action_queue.put({"action": action, "value": value})
        return web.json_response({"status": "queued"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_ecoflow_switch(request):
    try:
        data = await request.json()
        switch_type = data.get("type") 
        new_state = data.get("state")  
        
        sn = ECOFLOW_CONFIG.get("sn", "P351ZEH4PGBL0776")
        if not EcoFlowController:
            return web.json_response({"error": "EcoFlow Controller not loaded"}, status=500)
            
        ctrl = EcoFlowController(serial=sn)
        success = False
        
        if switch_type == "ac":
            success = await asyncio.to_thread(ctrl.set_ac, new_state)
        elif switch_type == "dc":
            success = await asyncio.to_thread(ctrl.set_12v, new_state)
        elif switch_type == "usb":
            success = await asyncio.to_thread(ctrl.set_usb, new_state)
            
        if success:
            state.data[f"ecoflow_{switch_type}_on"] = new_state
            return web.json_response({"status": "ok"})
        else:
            return web.json_response({"status": "error"}, status=500)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def get_data_api(request):
    try:
        climate_sensor.update()
        r, p = leveling.get_angles()
        state.data["level_roll"] = r
        state.data["level_pitch"] = p
        
        state.data.update(climate_sensor.get_data())
        state.data["sys_cpu_temp"] = get_cpu_temp()
        state.data["sys_rtc_temp"] = get_rtc_temp()
        state.data["sys_ssid"] = get_wifi_ssid()
        
        state.data["auto_off_soc"] = FRIDGE_CONFIG.get("auto_off_soc", 0)
        
        state.check_timeouts()
        state.data["server_time"] = time.strftime("%H:%M:%S")
        return web.json_response(state.data, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
        
async def display_on(request):
    try:
        os.system("/usr/bin/vcgencmd display_power 1")
        os.system("echo 0 > /sys/class/backlight/rpi_backlight/bl_power 2>/dev/null")
        return web.json_response({"status": "on"})
    except: return web.json_response({"status": "error"})

async def display_off(request):
    try:
        os.system("/usr/bin/vcgencmd display_power 0")
        os.system("echo 1 > /sys/class/backlight/rpi_backlight/bl_power 2>/dev/null")
        return web.json_response({"status": "off"})
    except: return web.json_response({"status": "error"})
    
async def calibrate_level(request):
    try:
        await asyncio.sleep(0.05) 
        r, p = leveling.get_angles()
        if leveling.save_calibration(r, p):
            return web.json_response({"status": "ok"})
        else:
            return web.json_response({"status": "save_error"}, status=500)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

async def shutdown_system(request):
    try:
        os.system("sudo shutdown -h now")
        return web.json_response({"status": "shutdown_initiated"})
    except: return web.json_response({"status": "error"})

async def serve_dashboard(request):
    if os.path.exists(INDEX_PATH): return web.FileResponse(INDEX_PATH)
    return web.Response(text="Dashboard nicht gefunden", status=404)

async def main():
    app = web.Application()
    app.router.add_get('/api/data', get_data_api)
    app.router.add_post('/api/fridge/control', api_fridge_control)
    app.router.add_post('/api/ecoflow/switch', api_ecoflow_switch)
    app.router.add_post('/api/level/calibrate', calibrate_level)
    app.router.add_post('/api/shutdown', shutdown_system)
    app.router.add_post('/api/display/on', display_on)
    app.router.add_post('/api/display/off', display_off)
    app.router.add_get('/', serve_dashboard)
    app.router.add_static('/static/', path=STATIC_PATH)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 3000).start()
    print("Webserver läuft auf Port 3000")

    fridge_present = False
    if BLE_AVAILABLE and FRIDGE_CONFIG:
        fridge_mac = FRIDGE_CONFIG.get("mac", "").upper()
        print(f"Boot-Radar: Suche 5 Sekunden nach Kühlbox ({fridge_mac})...")
        try:
            devices = await BleakScanner.discover(timeout=5.0)
            for d in devices:
                if d.address.upper() == fridge_mac:
                    fridge_present = True
                    break
        except Exception as e:
            print(f"Fehler beim Boot-Radar: {e}")

    # SCHRITT 1: KÜHLBOX-DIENST
    if fridge_present:
        print("Kühlbox gefunden! Starte Verbindung und blockiere Victron-Scanner für 15 Sekunden...")
        asyncio.create_task(vevor_fridge_task(state))
        asyncio.create_task(fridge_watchdog_task(state))
        await asyncio.sleep(15) 
    elif FRIDGE_CONFIG:
        print("Kühlbox nicht in Reichweite. Sie wird für diese Sitzung übersprungen (keine Verzögerung).")

    # SCHRITT 2: POWERQUEEN-DIENST
    if POWERQUEEN_CONFIG:
        print("Starte PowerQueen-Dienst und blockiere weitere Starts für 10 Sekunden...")
        asyncio.create_task(powerqueen_task(state))
        await asyncio.sleep(10)

    # SCHRITT 3: ECOFLOW-DIENST
    if ECOFLOW_CONFIG:
        asyncio.create_task(ecoflow_task(state))

    # SCHRITT 4: VICTRON SCANNER
    if BLE_AVAILABLE and DEVICE_CONFIG:
        print("Starte Victron Scanner...")
        asyncio.create_task(ble_scanner_task())
    
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass