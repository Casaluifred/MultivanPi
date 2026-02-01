import asyncio, os, json, sys, time, uuid, math, random, platform, glob
from aiohttp import web
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
INDEX_PATH = os.path.abspath(os.path.join(PROJECT_ROOT, "index.html"))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CALIBRATION_FILE = os.path.join(BASE_DIR, "calibration.json")
PRESSURE_HISTORY_FILE = os.path.join(BASE_DIR, "pressure_history.json")
SERVER_SESSION_ID = str(uuid.uuid4())[:8]

DEVICE_CONFIG = {}
def load_config():
    global DEVICE_CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: DEVICE_CONFIG = json.load(f).get("victron", {})
        except: pass
load_config()

SMBUS_AVAILABLE = False
try:
    import smbus2 as smbus
    SMBUS_AVAILABLE = True
except: pass

BLE_AVAILABLE = False
try:
    from victron_ble.scanner import Scanner
    from victron_ble.devices import BatterySense as BatterySenseParser, SolarCharger as SolarChargerParser, SmartShunt as SmartShuntParser
    BLE_AVAILABLE = True
except: pass

class BME280:
    def __init__(self, address=0x76):
        self.address, self.bus, self.cal = address, None, {}
        if SMBUS_AVAILABLE:
            try:
                self.bus = smbus.SMBus(1)
                if self.bus.read_byte_data(self.address, 0xD0) in [0x60, 0x58]: self._load_cal()
            except: pass
    def _load_cal(self):
        try:
            b = self.bus.read_i2c_block_data(self.address, 0x88, 24)
            self.cal['T1'] = b[0] | (b[1] << 8)
            self.cal['T2'] = b[2] | (b[3] << 8); self.cal['T2'] -= 65536 if self.cal['T2'] > 32767 else 0
        except: pass
    def read(self):
        if not self.bus: return None
        try:
            d = self.bus.read_i2c_block_data(self.address, 0xF7, 8)
            return (d[3]<<12|d[4]<<4|d[5]>>4)/10000.0, (d[0]<<12|d[1]<<4|d[2]>>4)/25600.0, 45.0
        except: return None

class DS18B20:
    def __init__(self): self.file = next(iter(glob.glob('/sys/bus/w1/devices/28*/w1_slave')), None)
    def read(self):
        if not self.file: return None
        try:
            with open(self.file, 'r') as f:
                l = f.readlines()
                if 'YES' in l[0]: return float(l[1].split('t=')[1])/1000.0
        except: return None

class State:
    def __init__(self):
        self.data = {"aufbau_soc": 0.0, "solar_watt": 0, "booster_amp": 0.0, "sense_temp": 0.0, "starter_volt": 0.0, "level_roll": 0.0, "level_pitch": 0.0}
        self.ts = {}
    def update(self, key, val): self.data[key] = val; self.ts[key] = time.time()
    def check_timeouts(self):
        for k in ["shunt_aufbau", "mppt", "booster", "sense", "shunt_starter"]:
            if time.time() - self.ts.get(k, 0) > 120: self.data[k+"_last"] = "Suche..."
            else: self.data[k+"_last"] = time.strftime("%H:%M:%S", time.localtime(self.ts[k]))
state = State()

class VictronScanner(Scanner):
    def callback(self, device, data, advertisement):
        mac = device.address.upper()
        if mac in DEVICE_CONFIG:
            try:
                c = DEVICE_CONFIG[mac]; dtype = c["type"]
                parser = BatterySenseParser(c["key"]) if dtype=="sense" else SolarChargerParser(c["key"]) if dtype=="mppt" else SmartShuntParser(c["key"])
                d = parser.parse(data)
                if dtype=="sense": state.update("sense", d.get_temperature())
                elif dtype=="shunt_aufbau": state.update("shunt_aufbau", d.get_soc())
            except: pass

async def get_data(request):
    state.check_timeouts()
    state.data["server_time"] = time.strftime("%H:%M:%S")
    return web.json_response(state.data, headers={"Access-Control-Allow-Origin": "*"})

async def main():
    app = web.Application()
    app.router.add_get('/', lambda r: web.FileResponse(INDEX_PATH))
    app.router.add_get('/api/data', get_data)
    app.router.add_static('/static/', path=PROJECT_ROOT)
    runner = web.AppRunner(app); await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', 3000).start()
    if BLE_AVAILABLE: asyncio.create_task(VictronScanner({m: d["key"] for m, d in DEVICE_CONFIG.items()}).start())
    while True: await asyncio.sleep(3600)

if __name__ == "__main__": asyncio.run(main())
