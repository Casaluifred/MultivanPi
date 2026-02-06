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
from bleak import BleakScanner

# =================================================================
# VERSIONIERUNG & DOKUMENTATION
# =================================================================
BACKEND_VERSION = "21.0 (Platinum Final)" 

# -----------------------------------------------------------------
# HARDWARE VERDRAHTUNG (DOKUMENTATION)
# -----------------------------------------------------------------
# 1. WAKE-UP TASTER (Edelstahl):
#    Funktion: Weckt den Raspberry Pi aus dem "Halt" (Shutdown) auf.
#    Verdrahtung:
#      - Pin A des Tasters  -> Raspberry Pi Pin 5 (GPIO 3 / SCL)
#      - Pin B des Tasters  -> Raspberry Pi Pin 6 (GND)
#    Hinweis:
#      Dies ist eine Hardware-Funktion des Broadcom-Chips.
#      Achtung: Nicht drücken, wenn der Pi AN ist (I2C Störung)!
#
# 2. SENSOREN (I2C):
#    - ADXL345 (Level): 0x53
#    - BME280 (Klima): 0x76
#    - DS3231 (RTC): 0x68
# -----------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
INDEX_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "index.html"))
STATIC_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "static"))

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
PRESSURE_HISTORY_FILE = os.path.join(BASE_DIR, "pressure_history.json")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration.json")

SERVER_SESSION_ID = str(uuid.uuid4())[:8]

# Globale Variablen
DEVICE_CONFIG = {}
ECOFLOW_CONFIG = {}

def load_config():
    global DEVICE_CONFIG, ECOFLOW_CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                full_config = json.load(f)
            DEVICE_CONFIG = full_config.get("victron", {})
            ECOFLOW_CONFIG = full_config.get("ecoflow", {})
            print(f"Konfiguration geladen: {len(DEVICE_CONFIG)} Victron Geräte.")
        except Exception as e:
            print(f"Fehler beim Laden der config.json: {e}")

load_config()

print(f"\n{'='*60}")
print(f"### MULTIVAN PI BACKEND v{BACKEND_VERSION} ###")
print(f"Status: ADXL345 Driver Active (With Smoothing)")
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

# --- ADXL345 (Leveling) MIT TIEFPASS ---
class LevelingSensor:
    def __init__(self, bus):
        self.bus = bus
        self.address = 0x53 
        self.offsets = {"roll": 0.0, "pitch": 0.0}
        self.working = False
        
        # Glättung
        self.last_roll = 0.0
        self.last_pitch = 0.0
        self.alpha = 0.1 
        
        if self.bus:
            try:
                dev_id = self.bus.read_byte_data(self.address, 0x00)
                if dev_id == 0xE5:
                    print(f"ADXL345: Gefunden auf 0x{self.address:02X}")
                    self.bus.write_byte_data(self.address, 0x2D, 0x08) # Measure
                    self.bus.write_byte_data(self.address, 0x31, 0x00) # +/- 2g
                    self.working = True
                    self.load_calibration()
            except: pass

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

    def read_axis(self, addr):
        try:
            low = self.bus.read_byte_data(self.address, addr)
            high = self.bus.read_byte_data(self.address, addr+1)
            val = (high << 8) | low
            if val > 32767: return val - 65536
            return val
        except: return 0

    def get_angles(self):
        if not self.working: return 0.0, 0.0
        try:
            x = self.read_axis(0x32)
            y = self.read_axis(0x34)
            z = self.read_axis(0x36)
            
            new_pitch = math.atan2(-x, math.sqrt(y*y + z*z)) * 180.0 / math.pi
            new_roll = math.atan2(y, z) * 180.0 / math.pi
            
            # Glättung
            self.last_roll = (new_roll * self.alpha) + (self.last_roll * (1.0 - self.alpha))
            self.last_pitch = (new_pitch * self.alpha) + (self.last_pitch * (1.0 - self.alpha))
            
            return round(self.last_roll - self.offsets["roll"], 1), round(self.last_pitch - self.offsets["pitch"], 1)
        except: return 0.0, 0.0

# --- BME280 ---
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
                self.bus.write_byte_data(self.address, 0xF4, 0x27)
                self.bus.write_byte_data(self.address, 0xF5, 0xA0)
                self.working = True
                print(f"BME280: Init OK auf 0x{self.address:02X}")
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
        self.base_dir = '/sys/bus/w1/devices/'; self.device_file = None; self._find()
    def _find(self):
        try: f = glob.glob(self.base_dir + '28*'); 
        except: pass; 
        if f: self.device_file = f[0] + '/w1_slave'
    def read(self):
        if not self.device_file: self._find(); return None
        try:
            with open(self.device_file, 'r') as f:
                l = f.readlines()
                if len(l)>0 and 'YES' in l[0]:
                    p = l[1].find('t='); 
                    if p!=-1: return float(l[1][p+2:])/1000.0
        except: return None

class ClimateModule:
    def __init__(self, bus):
        self.bme = BME280(bus); self.ds18 = DS18B20(); self.data = {"temp_in": 0, "pressure": 0, "humidity": 0, "temp_out": 0}
        self.history = []; self.last_save = 0; self.load()
    def load(self):
        if os.path.exists(PRESSURE_HISTORY_FILE):
            try:
                with open(PRESSURE_HISTORY_FILE, 'r') as f: self.history = json.load(f)
            except: pass
    def save(self):
        try:
            with open(PRESSURE_HISTORY_FILE, 'w') as f: json.dump(self.history, f)
        except: pass
    def update(self):
        d = self.bme.read_data()
        if d: self.data["temp_in"], self.data["pressure"], self.data["humidity"] = d
        do = self.ds18.read(); 
        if do: self.data["temp_out"] = do
        if time.time() - self.last_save > 600:
            if self.data["pressure"] > 0:
                self.history.append({"ts": int(time.time()), "val": self.data["pressure"]}); 
                if len(self.history) > 450: self.history.pop(0)
                self.save(); self.last_save = time.time()
    def get_trend(self):
        if len(self.history) < 18: return "stabil"
        diff = self.history[-1]["val"] - self.history[-18]["val"]
        if diff > 1.0: return "steigend"; 
        if diff < -1.0: return "fallend"
        return "stabil"
    def get_data(self):
        d = self.data.copy(); d["pressure_trend"] = self.get_trend(); d["pressure_history"] = self.history; return d

class EcoflowHandler:
    def __init__(self, config):
        self.data = {"soc": 0, "watts_in": 0, "watts_out": 0, "remain_mins": 0, "connected": False}
    async def update(self): pass
    def get_data(self): return self.data

class SharedState:
    def __init__(self):
        self.data = {
            "sys_backend_version": BACKEND_VERSION,
            "aufbau_soc": 42.0, "aufbau_volt": 0.0, "aufbau_amp": 0.0,
            "solar_watt": 0, "mppt_load_amp": 0.0, 
            "starter_volt": 0.0, "booster_amp": 0.0, 
            "sense_temp": 0.0, "sense_volt": 0.0,
            "sense_last": "Suche...", "shunt_aufbau_last": "Suche...",
            "solar_last": "Suche...", "booster_last": "Suche...", "shunt_starter_last": "Suche...",
            "level_roll": 0.0, "level_pitch": 0.0,
            "session": SERVER_SESSION_ID,
            "sys_python": sys.version.split()[0], "sys_platform": platform.platform(),
            "sys_cpu_temp": 0.0, "sys_rtc_temp": 0.0, "sys_ssid": None,
            "ecoflow_soc": 0, "sense_packets": 0,
            "fridge_connected": False, "temp_fridge": 0
        }
        self.last_seen = {}

    def update_victron(self, key, val, status_key):
        self.data[key] = val
        self.data[status_key] = time.strftime("%H:%M:%S")
        self.last_seen[status_key] = time.time()

    def check_timeouts(self):
        now = time.time()
        timeout = 120
        keys = [("shunt_aufbau_last", "aufbau_soc"), ("sense_last", "sense_temp"), ("solar_last", "solar_watt")]
        for status_key, data_key in keys:
            if now - self.last_seen.get(status_key, 0) > timeout:
                if self.data.get(status_key) != "Suche...":
                    self.data[status_key] = "Suche..."

state = SharedState()
ecoflow_handler = EcoflowHandler(ECOFLOW_CONFIG)
climate_sensor = ClimateModule(SHARED_BUS)
leveling = LevelingSensor(SHARED_BUS)

async def ble_scanner_task():
    print("Starte BLE Scanner Service...")
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
                        state.update_victron("solar_watt", d.get_pv_power(), "solar_last")
                        state.data["mppt_load_amp"] = d.get_load_current()
                    elif dtype == "booster": 
                        state.update_victron("booster_amp", 0.0, "booster_last")
                    elif dtype == "shunt_starter": 
                        state.update_victron("starter_volt", d.get_voltage(), "shunt_starter_last")
                    state.data["sense_packets"] += 1
            except: pass

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    while True: await asyncio.sleep(10)

async def get_data_api(request):
    try:
        climate_sensor.update()
        r, p = leveling.get_angles()
        state.data["level_roll"] = r
        state.data["level_pitch"] = p
        state.data.update(ecoflow_handler.get_data())
        state.data.update(climate_sensor.get_data())
        state.data["sys_cpu_temp"] = get_cpu_temp()
        state.data["sys_rtc_temp"] = get_rtc_temp()
        state.data["sys_ssid"] = get_wifi_ssid()
        state.check_timeouts()
        state.data["server_time"] = time.strftime("%H:%M:%S")
        return web.json_response(state.data, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def calibrate_level(request):
    try:
        r, p = leveling.get_angles()
        if leveling.save_calibration(r, p): return web.json_response({"status": "ok"})
        else: return web.json_response({"status": "save_error"})
    except: return web.json_response({"status": "error"})

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
    app.router.add_post('/api/level/calibrate', calibrate_level)
    app.router.add_post('/api/shutdown', shutdown_system)
    app.router.add_get('/', serve_dashboard)
    app.router.add_static('/static/', path=STATIC_PATH)
    
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 3000).start()
    print("Webserver läuft auf Port 3000")

    if BLE_AVAILABLE and DEVICE_CONFIG:
        asyncio.create_task(ble_scanner_task())
    
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass