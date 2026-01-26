import asyncio
import os
import json
import sys
import time
import uuid
from aiohttp import web

# Versuche die Victron-Bibliothek und Parser-Module robust zu laden
BLE_AVAILABLE = False
try:
    from victron_ble.scanner import Scanner
    # Robuster Import: SmartShunt wird oft auch als BatteryMonitor behandelt oder 
    # befindet sich in einem Submodul, je nach Version der Bibliothek.
    from victron_ble.devices import BatterySense as BatterySenseParser
    from victron_ble.devices import SolarCharger as SolarChargerParser
    
    try:
        from victron_ble.devices import SmartShunt as SmartShuntParser
    except ImportError:
        # Fallback für ältere/neuere Versionen der Lib
        from victron_ble.devices import BatteryMonitor as SmartShuntParser
        
    BLE_AVAILABLE = True
    print("Victron-BLE Bibliothek erfolgreich geladen (mit SmartShunt-Fallback).")
except ImportError as e:
    BLE_AVAILABLE = False
    print(f"Information: Victron-BLE Bibliothek eingeschränkt: {e}")

# Absolute Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "index.html"))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

# Eindeutige ID für diese Sitzung
SERVER_SESSION_ID = str(uuid.uuid4())[:8]

# =================================================================
# GERÄTE-KONFIGURATION
# =================================================================
DEVICE_CONFIG = {
    "C0:65:47:F3:72:18": {
        "name": "SmartSense",
        "key": "7393782c8e60e541a5de2a28a091c681",
        "type": "sense"
    },
    "MAC_SHUNT_AUFBAU": {
        "name": "SmartShunt Aufbau",
        "key": "KEY_SHUNT_AUFBAU",
        "type": "shunt_aufbau"
    },
    "MAC_SHUNT_STARTER": {
        "name": "SmartShunt Starter",
        "key": "KEY_SHUNT_STARTER",
        "type": "shunt_starter"
    },
    "MAC_MPPT": {
        "name": "SmartSolar MPPT",
        "key": "KEY_MPPT",
        "type": "mppt"
    },
    "MAC_BOOSTER": {
        "name": "Ladebooster",
        "key": "KEY_BOOSTER",
        "type": "booster" 
    }
}

# =================================================================
# GLOBALER DATENSPEICHER (Shared State)
# =================================================================
class SharedState:
    def __init__(self):
        # Version 45.4-ID (Fix für SmartShunt Import)
        self.data = {
            "aufbau_soc": 42.0, 
            "aufbau_volt": 0.0,
            "aufbau_amp": 0.0,
            "solar_watt": 0,    
            "starter_volt": 0.0,
            "booster_amp": 0.0, 
            "sense_temp": 0.0,
            "sense_last": "Suche...",
            "sense_packets": 0,
            "session": SERVER_SESSION_ID,
            "server_time": ""
        }

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
            # Versuche verschiedene Methoden für SOC/Volt/Amp
            for attr in ["get_state_of_charge", "get_soc"]:
                if hasattr(decrypted, attr):
                    soc = getattr(decrypted, attr)()
                    if soc is not None: self.data["aufbau_soc"] = soc
            
            for attr in ["get_battery_voltage", "get_voltage"]:
                if hasattr(decrypted, attr):
                    volt = getattr(decrypted, attr)()
                    if volt is not None: self.data["aufbau_volt"] = volt
            
            for attr in ["get_battery_current", "get_current"]:
                if hasattr(decrypted, attr):
                    amp = getattr(decrypted, attr)()
                    if amp is not None: self.data["aufbau_amp"] = amp
            
            self.data["sense_packets"] += 1
        except: pass

    def process_shunt_starter(self, decrypted):
        try:
            for attr in ["get_battery_voltage", "get_voltage"]:
                if hasattr(decrypted, attr):
                    volt = getattr(decrypted, attr)()
                    if volt is not None: 
                        self.data["starter_volt"] = volt
                        self.data["sense_packets"] += 1
        except: pass

    def process_mppt(self, decrypted):
        try:
            watt = decrypted.get_pv_power()
            if watt is not None: 
                self.data["solar_watt"] = watt
                self.data["sense_packets"] += 1
        except: pass

    def process_booster(self, decrypted):
        try:
            for attr in ["get_battery_current", "get_current"]:
                if hasattr(decrypted, attr):
                    amp = getattr(decrypted, attr)()
                    if amp is not None: 
                        self.data["booster_amp"] = abs(amp)
                        self.data["sense_packets"] += 1
        except: pass

state = SharedState()

# =================================================================
# VICTRON SCANNER
# =================================================================
class MyVictronScanner(Scanner):
    def __init__(self, config_dict):
        ble_config = {mac: dev["key"] for mac, dev in config_dict.items() if not mac.startswith("MAC_")}
        super().__init__(ble_config)
        
        self.parsers = {}
        for mac, dev in config_dict.items():
            if mac.startswith("MAC_"): continue
            t = dev["type"]
            try:
                if t == "sense":
                    self.parsers[mac] = BatterySenseParser(dev["key"])
                elif t in ["shunt_aufbau", "shunt_starter", "booster"]:
                    self.parsers[mac] = SmartShuntParser(dev["key"])
                elif t == "mppt":
                    self.parsers[mac] = SolarChargerParser(dev["key"])
            except Exception as e:
                print(f"Fehler bei Parser {dev['name']}: {e}")

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

# =================================================================
# WEB SERVER
# =================================================================
async def get_data_api(request):
    state.data["server_time"] = time.strftime("%H:%M:%S")
    return web.json_response(state.data, headers={"Access-Control-Allow-Origin": "*"})

async def serve_dashboard(request):
    return web.FileResponse(INDEX_PATH) if os.path.exists(INDEX_PATH) else web.Response(text="index.html fehlt", status=404)

async def main():
    app = web.Application()
    app.router.add_get('/api/data', get_data_api)
    app.router.add_get('/', serve_dashboard)
    app.router.add_static('/static/', path=PROJECT_ROOT) 
    
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        site = web.TCPSite(runner, '0.0.0.0', 3000)
        await site.start()
        print(f"\n==========================================")
        print(f"MultivanPi BACKEND LIVE (Version 45.4-ID)")
        print(f"Session-ID: {SERVER_SESSION_ID}")
        print(f"==========================================\n")
        sys.stdout.flush()
    except Exception as e:
        print(f"Port Fehler: {e}")
        return

    if BLE_AVAILABLE:
        scanner = MyVictronScanner(DEVICE_CONFIG)
        asyncio.create_task(scanner.start())
    
    while True: await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nBeendet.")
