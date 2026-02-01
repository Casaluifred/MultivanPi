import os

# Definition der Verzeichnisstruktur und Dateiinhalte
project_name = "MultivanPi"
base_path = os.path.join(os.path.expanduser("~"), project_name)

files = {
    "requirements.txt": """aiohttp
victron-ble
""",
    ".gitignore": """# Python
venv/
__pycache__/
*.py[cod]
*$py.class

# Sensible Daten
backend/config.json
backend/calibration.json
backend/pressure_history.json

# Logs
service.log
""",
    "README.md": """# MultivanPi v2.4

Zentrales Dashboard für den VW Multivan zur Überwachung von Victron Energiedaten, Klima und Fahrzeug-Nivellierung.

## Hardware & Anschlüsse
- **BME280**: I2C (GPIO 2/3) - Innenklima & Druck
- **ADXL345**: I2C (GPIO 2/3) - Wasserwaage
- **DS18B20**: 1-Wire (GPIO 4) - Außentemperatur (4.7k Pull-Up benötigt)
- **DS3231**: I2C (GPIO 2/3) - Echtzeituhr

## Installation
1. `scripts/download_assets.sh` ausführen.
2. `backend/config.json` anpassen.
3. `scripts/start_kiosk.sh` im Autostart (Openbox) hinterlegen.

© 2024-2026 Fred Fiedler
""",
    "index.html": r"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MultivanPi Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&display=swap" rel="stylesheet">
    <script src="/static/lucide.min.js"></script>
    <script src="/static/chart.min.js"></script>
    <style>
        :root {
            --bg-color: #000000; --card-bg: rgba(25, 25, 25, 0.95); --accent-color: #00d4ff;
            --text-color: #ffffff; --success-color: #44ff44; --warning-color: #ffcc00;
            --danger-color: #ff4444; --level-liquid: rgba(202, 255, 66, 0.15); 
            --level-border: rgba(202, 255, 66, 0.4); --level-bubble-core: rgba(202, 255, 66, 0.9);
        }
        body {
            margin: 0; padding: 0; background-color: var(--bg-color); color: var(--text-color);
            font-family: 'Inter', sans-serif; overflow: hidden;
            width: 2560px; height: 1440px; transform: rotate(90deg); transform-origin: top left;
            position: absolute; top: 0; left: 1440px; display: flex; flex-direction: column;
        }
        .header { padding: 60px 100px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .header h2 { font-size: 4rem; margin: 0; font-weight: 700; }
        #clock { font-size: 4rem; font-weight: 300; }
        .view-container { flex-grow: 1; padding: 60px 100px; position: relative; }
        .view { display: none; width: 100%; height: 100%; animation: fadeIn 0.3s ease; }
        .view.active { display: flex; flex-direction: column; }
        @keyframes fadeIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 50px; height: 100%; }
        .card { background: var(--card-bg); border-radius: 50px; padding: 40px; border: 4px solid var(--accent-color); transition: all 0.2s ease; cursor: pointer; text-align: center; }
        .card-layout { height: 100%; display: grid; grid-template-rows: 1fr auto 1fr; align-items: center; justify-items: center; }
        .large-icon { width: 180px !important; height: 180px !important; }
        .card-label { font-size: 2.2rem; opacity: 0.5; text-transform: uppercase; letter-spacing: 4px; }
        .val-home { font-size: 7rem; font-weight: 800; }
        .unit { font-size: 3rem; opacity: 0.3; margin-left: 10px; }
        .border-connected { border: 3px solid rgba(68, 255, 68, 0.4) !important; }
        .border-disconnected { border: 3px solid rgba(255, 204, 0, 0.5) !important; }
        .home-btn { position: fixed; bottom: 80px; right: 80px; width: 240px; height: 240px; background: var(--card-bg); border: 5px solid var(--accent-color); border-radius: 60px; display: none; justify-content: center; align-items: center; cursor: pointer; z-index: 1000; opacity: 0.7; }
        .home-btn svg { width: 192px !important; height: 192px !important; color: #fff; }
        .level-bar-container { background: #1e1e1e; border-radius: 40px; padding: 40px; margin-bottom: 40px; position: relative; border: 2px solid rgba(255,255,255,0.1); }
        .spirit-level { width: 80%; height: 140px; background: var(--level-liquid); border-radius: 70px; position: relative; overflow: hidden; border: 4px solid var(--level-border); }
        .bubble { width: 160px; height: 90px; background: radial-gradient(circle at 30% 30%, #fff, var(--level-bubble-core)); border-radius: 50px; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); transition: left 0.2s ease-out; }
    </style>
</head>
<body>
    <div class="header">
        <div><h2>MULTIVAN<span style="color: var(--accent-color);">PI</span></h2></div>
        <div id="clock">00:00</div>
    </div>
    <div class="view-container">
        <section id="view-home" class="view active">
            <div class="grid">
                <div class="card" id="card-energy" onclick="showView('victron')"><div class="card-layout"><div class="icon-box"><i data-lucide="zap" class="large-icon"></i></div><div class="card-label">Energie</div><div id="home-soc" class="val-home">--<span class="unit">%</span></div></div></div>
                <div class="card" onclick="showView('klima')"><div class="card-layout"><div class="icon-box"><i data-lucide="thermometer" class="large-icon"></i></div><div class="card-label">Klima</div><div id="home-temp" class="val-home">--<span class="unit">°C</span></div></div></div>
                <div class="card" onclick="showView('level')"><div class="card-layout"><div class="icon-box"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="large-icon"><rect x="1" y="8" width="22" height="8" rx="4" /><line x1="7" y1="8" x2="7" y2="16" /><line x1="17" y1="8" x2="17" y2="16" /><circle cx="12" cy="12" r="2" /></svg></div><div class="card-label">Ausrichten</div></div></div>
                <div class="card" onclick="location.reload()"><div class="card-layout"><div class="icon-box"><i data-lucide="refresh-cw" class="large-icon"></i></div><div class="card-label">System</div><div class="val-home">v2.4</div></div></div>
            </div>
        </section>
        <section id="view-victron" class="view">
            <div class="grid">
                <div id="card-vic-shunt" class="card"><div class="card-label">Aufbau</div><div id="vic-soc" class="val-home">--%</div><div id="vic-shunt-status">Suche...</div></div>
                <div id="card-vic-solar" class="card"><div class="card-label">Solar</div><div id="vic-solar" class="val-home">--W</div><div id="vic-solar-status">Suche...</div></div>
                <div id="card-vic-booster" class="card"><div class="card-label">Booster</div><div id="vic-booster" class="val-home">--A</div><div id="vic-booster-status">Suche...</div></div>
                <div id="card-vic-sense" class="card"><div class="card-label">Sense</div><div id="vic-sense" class="val-home">--°C</div><div id="vic-sense-status">Suche...</div></div>
            </div>
        </section>
        <section id="view-level" class="view">
            <div class="level-bar-container"><div class="card-label">Quer (Roll)</div><div class="spirit-level"><div id="bubble-roll" class="bubble"></div></div><div id="disp-roll" class="val-home">0.0°</div></div>
            <div class="level-bar-container"><div class="card-label">Längs (Pitch)</div><div class="spirit-level"><div id="bubble-pitch" class="bubble"></div></div><div id="disp-pitch" class="val-home">0.0°</div></div>
        </section>
    </div>
    <div id="btn-home" class="home-btn" onclick="showView('home')"><i data-lucide="home"></i></div>
    <script>
        function showView(id) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('view-' + id).classList.add('active');
            document.getElementById('btn-home').style.display = (id === 'home') ? 'none' : 'flex';
            lucide.createIcons();
        }
        function updateStatus(id, last) {
            const el = document.getElementById(id); if (!el) return;
            if (last && last !== "Suche...") { el.classList.add('border-connected'); el.classList.remove('border-disconnected'); }
            else { el.classList.add('border-disconnected'); el.classList.remove('border-connected'); }
        }
        async function fetchData() {
            try {
                const res = await fetch('/api/data'); const data = await res.json();
                document.getElementById('clock').innerText = data.server_time;
                document.getElementById('home-soc').innerHTML = data.aufbau_soc.toFixed(1) + '<span class="unit">%</span>';
                updateStatus('card-vic-shunt', data.shunt_aufbau_last);
                updateStatus('card-vic-solar', data.solar_last);
                updateStatus('card-vic-booster', data.booster_last);
                updateStatus('card-vic-sense', data.sense_last);
                document.getElementById('bubble-roll').style.left = (50 + (data.level_roll * 4)) + "%";
                document.getElementById('bubble-pitch').style.left = (50 + (data.level_pitch * 4)) + "%";
                document.getElementById('disp-roll').innerText = data.level_roll.toFixed(1) + "°";
                document.getElementById('disp-pitch').innerText = data.level_pitch.toFixed(1) + "°";
            } catch(e) {}
        }
        setInterval(fetchData, 1000);
        window.onload = () => { lucide.createIcons(); fetchData(); }
    </script>
</body>
</html>
""",
    "backend/config.json": """{
    "victron": {
        "C0:65:47:F3:72:18": {"name": "SmartSense", "key": "7393782c8e60e541a5de2a28a091c681", "type": "sense"},
        "C7:74:47:93:3F:21": {"name": "SmartShunt Aufbau", "key": "b431407555a7a7e8a8c8c702560d5170", "type": "shunt_aufbau"},
        "MAC_SHUNT_STARTER": {"name": "SmartShunt Starter", "key": "KEY_SHUNT_STARTER", "type": "shunt_starter"},
        "E1:B5:C7:D7:9F:36": {"name": "SmartSolar MPPT", "key": "e2b509b595c2854127b4050f791c2d71", "type": "mppt"},
        "D7:CA:C9:74:A7:97": {"name": "Ladebooster", "key": "bee5991f9298392b75bf7c8a3677fa4d", "type": "booster"}
    },
    "ecoflow": {
        "sn": "P351ZEH4PGBL0776",
        "access_key": "su1o8Q5w8WFAx1gaZFceCQPHZ5xRc8ac",
        "secret_key": "Roc4x4nwboDdDRSzdxRSb87Etb9LVQMX"
    }
}
""",
    "backend/victron_service.py": r"""import asyncio, os, json, sys, time, uuid, math, random, platform, glob
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
""",
    "scripts/start_kiosk.sh": """#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/fred/.Xauthority
PROJECT_DIR="/home/fred/MultivanPi"
sudo fuser -k 3000/tcp > /dev/null 2>&1
sudo $PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/backend/victron_service.py &
sleep 5
chromium-browser --kiosk --incognito --noerrdialogs --disable-infobars --window-size=1440,2560 "http://127.0.0.1:3000" &
""",
    "scripts/download_assets.sh": """#!/bin/bash
STATIC_DIR="/home/fred/MultivanPi/static"
mkdir -p "$STATIC_DIR"
curl -L -o "$STATIC_DIR/lucide.min.js" "https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"
curl -L -o "$STATIC_DIR/chart.min.js" "https://cdn.jsdelivr.net/npm/chart.js"
""",
    "scan_ble.py": """import asyncio
from bleak import BleakScanner
async def run():
    devices = await BleakScanner.discover(timeout=10.0)
    for d in devices: print(f"{d.address} | {d.name} | {d.rssi} dBm")
if __name__ == "__main__": asyncio.run(run())
"""
}

# Verzeichnisse erstellen
os.makedirs(os.path.join(base_path, "backend"), exist_ok=True)
os.makedirs(os.path.join(base_path, "scripts"), exist_ok=True)
os.makedirs(os.path.join(base_path, "static"), exist_ok=True)

# Dateien schreiben
for path, content in files.items():
    full_file_path = os.path.join(base_path, path)
    with open(full_file_path, "w", encoding="utf-8") as f:
        f.write(content)
    if path.endswith(".sh"):
        os.chmod(full_file_path, 0o755)

print(f"Projekt erfolgreich unter {base_path} erstellt.")