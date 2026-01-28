import asyncio
import os
import json
import sys
import time
import uuid
import math
import random
import platform
from aiohttp import web

# Versuche die Victron-Bibliothek und Parser-Module robust zu laden
BLE_AVAILABLE = False
try:
    from victron_ble.scanner import Scanner
    from victron_ble.devices import BatterySense as BatterySenseParser
    from victron_ble.devices import SolarCharger as SolarChargerParser
    try:
        from victron_ble.devices import SmartShunt as SmartShuntParser
    except ImportError:
        from victron_ble.devices import BatteryMonitor as SmartShuntParser
    BLE_AVAILABLE = True
    print("Victron-BLE Bibliothek erfolgreich geladen.")
except ImportError as e:
    BLE_AVAILABLE = False
    print(f"Information: Victron-BLE Bibliothek eingeschränkt: {e}")

# ADXL345: Versuche explizit SMBus2 zu laden
SMBUS_AVAILABLE = False
try:
    try:
        import smbus2 as smbus
    except ImportError:
        import smbus
    SMBUS_AVAILABLE = True
    print("I2C-Bus Bibliothek (smbus/smbus2) geladen.")
except ImportError:
    print("ACHTUNG: smbus/smbus2 nicht gefunden. ADXL345 läuft im SIMULATIONS-MODUS.")

# Absolute Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "index.html"))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration.json")

SERVER_SESSION_ID = str(uuid.uuid4())[:8]

# =================================================================
# SYSTEM STATS HELPER
# =================================================================
def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return round(float(f.read()) / 1000, 1)
    except:
        return 0.0

# =================================================================
# ADXL345 & LEVELING LOGIC
# =================================================================
class LevelingSensor:
    def __init__(self):
        self.bus = None
        self.simulated = not SMBUS_AVAILABLE
        self.offsets = {"roll": 0.0, "pitch": 0.0}
        self.load_calibration()
        
        self.address = 0x53
        if not self.simulated:
            try:
                self.bus = smbus.SMBus(1)
                self.bus.write_byte_data(self.address, 0x2D, 0x08) 
                self.bus.write_byte_data(self.address, 0x31, 0x08) 
                print("ADXL345 Sensor verbunden.")
            except Exception as e:
                print(f"ADXL345 Hardware-Fehler: {e}. Gehe in Simulations-Modus.")
                self.simulated = True

        self.history_roll = [0.0] * 20 
        self.history_pitch = [0.0] * 20

    def load_calibration(self):
        if os.path.exists(CALIBRATION_FILE):
            try:
                with open(CALIBRATION_FILE, 'r') as f:
                    self.offsets = json.load(f)
            except: pass

    def save_calibration(self, roll, pitch):
        new_roll_offset = self.offsets["roll"] + roll
        new_pitch_offset = self.offsets["pitch"] + pitch
        self.offsets["roll"] = new_roll_offset
        self.offsets["pitch"] = new_pitch_offset
        try:
            with open(CALIBRATION_FILE, 'w') as f:
                json.dump(self.offsets, f)
            self.history_roll = [new_roll_offset] * 20 
            return True
        except: return False

    def read_raw_data(self):
        if self.simulated:
            t = time.time()
            x = math.sin(t) * 20  
            y = math.cos(t * 0.5) * 20
            z = 250 
            return x, y, z
        try:
            data = self.bus.read_i2c_block_data(self.address, 0x32, 6)
            x = self.convert_to_g(data[0], data[1])
            y = self.convert_to_g(data[2], data[3])
            z = self.convert_to_g(data[4], data[5])
            return x, y, z
        except: return 0, 0, 0

    def convert_to_g(self, lsb, msb):
        val = (msb << 8) | lsb
        if val > 32767: val -= 65536
        return val

    def get_angles(self):
        x, y, z = self.read_raw_data()
        if x == 0 and y == 0 and z == 0: return 0.0, 0.0
        try:
            roll = math.atan2(y, z) * 57.2958
            pitch = math.atan2(-x, math.sqrt(y*y + z*z)) * 57.2958
        except: roll = 0; pitch = 0
            
        self.history_roll.pop(0); self.history_roll.append(roll)
        self.history_pitch.pop(0); self.history_pitch.append(pitch)
        
        avg_roll = sum(self.history_roll) / len(self.history_roll)
        avg_pitch = sum(self.history_pitch) / len(self.history_pitch)

        return round(avg_roll - self.offsets["roll"], 1), round(avg_pitch - self.offsets["pitch"], 1)

level_sensor = LevelingSensor()

# =================================================================
# GERÄTE-KONFIGURATION
# =================================================================
DEVICE_CONFIG = {
    "C0:65:47:F3:72:18": {"name": "SmartSense", "key": "7393782c8e60e541a5de2a28a091c681", "type": "sense"},
    "C7:74:47:93:3F:21": {"name": "SmartShunt Aufbau", "key": "b431407555a7a7e8a8c8c702560d5170", "type": "shunt_aufbau"},
    "MAC_SHUNT_STARTER": {"name": "SmartShunt Starter", "key": "KEY_SHUNT_STARTER", "type": "shunt_starter"},
    "E1:B5:C7:D7:9F:36": {"name": "SmartSolar MPPT", "key": "e2b509b595c2854127b4050f791c2d71", "type": "mppt"},
    "D7:CA:C9:74:A7:97": {"name": "Ladebooster", "key": "bee5991f9298392b75bf7c8a3677fa4d", "type": "booster"}
}

# =================================================================
# GLOBALER DATENSPEICHER
# =================================================================
class SharedState:
    def __init__(self):
        self.data = {
            "aufbau_soc": 42.0, "aufbau_volt": 0.0, "aufbau_amp": 0.0,
            "solar_watt": 0, "starter_volt": 0.0, "booster_amp": 0.0, 
            "sense_temp": 0.0, "sense_last": "Suche...", "sense_packets": 0,
            "level_roll": 0.0, "level_pitch": 0.0,
            "session": SERVER_SESSION_ID,
            "server_time": "",
            # System Stats
            "sys_cpu_temp": 0.0,
            "sys_python": sys.version.split()[0],
            "sys_platform": platform.platform()
        }

    # Victron Processing (kurz gehalten da unverändert)
    def process_sense(self, decrypted):
        try:
            temp = decrypted.get_temperature()
            if temp is not None:
                self.data["sense_temp"] = temp
                self.data["sense_last"] = time.strftime("%H:%M:%S")
                self.data["sense_packets"] += 1
        except: pass
    def process_shunt_aufbau(self, decrypted):
        try:
            if decrypted.get_soc() is not None: self.data["aufbau_soc"] = decrypted.get_soc()
            if decrypted.get_voltage() is not None: self.data["aufbau_volt"] = decrypted.get_voltage()
            if decrypted.get_current() is not None: self.data["aufbau_amp"] = decrypted.get_current()
            self.data["sense_packets"] += 1
        except: pass
    def process_shunt_starter(self, decrypted):
        try:
            if decrypted.get_voltage() is not None: 
                self.data["starter_volt"] = decrypted.get_voltage()
                self.data["sense_packets"] += 1
        except: pass
    def process_mppt(self, decrypted):
        try:
            if decrypted.get_pv_power() is not None: 
                self.data["solar_watt"] = decrypted.get_pv_power()
                self.data["sense_packets"] += 1
        except: pass
    def process_booster(self, decrypted):
        try:
            if decrypted.get_current() is not None: 
                self.data["booster_amp"] = abs(decrypted.get_current())
                self.data["sense_packets"] += 1
        except: pass

state = SharedState()

class MyVictronScanner(Scanner):
    def __init__(self, config_dict):
        ble_config = {mac: dev["key"] for mac, dev in config_dict.items() if not mac.startswith("MAC_")}
        super().__init__(ble_config)
        self.parsers = {}
        for mac, dev in config_dict.items():
            if mac.startswith("MAC_"): continue
            t = dev["type"]
            try:
                if t == "sense": self.parsers[mac] = BatterySenseParser(dev["key"])
                elif t in ["shunt_aufbau", "shunt_starter", "booster"]: self.parsers[mac] = SmartShuntParser(dev["key"])
                elif t == "mppt": self.parsers[mac] = SolarChargerParser(dev["key"])
            except: pass
    def callback(self, device, data, advertisement):
        mac = device.address.upper().strip()
        if mac in self.parsers:
            try:
                decrypted = self.parsers[mac].parse(data)
                dev_type = DEVICE_CONFIG[mac]["type"]
                if dev_type == "sense": state.process_sense(decrypted)
                elif dev_type == "shunt_aufbau": state.process_shunt_aufbau(decrypted)
                elif dev_type == "shunt_starter": state.process_shunt_starter(decrypted)
                elif dev_type == "mppt": state.process_mppt(decrypted)
                elif dev_type == "booster": state.process_booster(decrypted)
            except: pass
        super().callback(device, data, advertisement)

async def get_data_api(request):
    roll, pitch = level_sensor.get_angles()
    state.data["level_roll"] = roll
    state.data["level_pitch"] = pitch
    state.data["server_time"] = time.strftime("%H:%M:%S")
    # Update CPU Temp on request
    state.data["sys_cpu_temp"] = get_cpu_temp()
    return web.json_response(state.data, headers={"Access-Control-Allow-Origin": "*"})

async def calibrate_api(request):
    roll, pitch = level_sensor.get_angles()
    success = level_sensor.save_calibration(roll, pitch)
    return web.json_response({"success": success}, headers={"Access-Control-Allow-Origin": "*"})

async def serve_dashboard(request):
    return web.FileResponse(INDEX_PATH) if os.path.exists(INDEX_PATH) else web.Response(text="index.html fehlt", status=404)

async def main():
    app = web.Application()
    app.router.add_get('/api/data', get_data_api)
    app.router.add_post('/api/calibrate', calibrate_api)
    app.router.add_get('/', serve_dashboard)
    app.router.add_static('/static/', path=PROJECT_ROOT) 
    
    runner = web.AppRunner(app)
    await runner.setup()
    web.TCPSite(runner, '0.0.0.0', 3000)
    await web.TCPSite(runner, '0.0.0.0', 3000).start()
    
    print(f"MultivanPi BACKEND LIVE (Session: {SERVER_SESSION_ID})")

    if BLE_AVAILABLE:
        scanner = MyVictronScanner(DEVICE_CONFIG)
        asyncio.create_task(scanner.start())
    
    while True: await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nBeendet.")
