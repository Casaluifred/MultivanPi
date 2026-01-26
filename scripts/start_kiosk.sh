<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MultivanPi Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;600;700;800;900&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        :root {
            --bg-color: #000000;
            --card-bg: rgba(25, 25, 25, 0.9);
            --accent-color: #00d4ff;
            --text-color: #ffffff;
            --success-color: #44ff44;
            --font-header: 4rem;      
            --font-clock: 4rem;       
            --font-date: 2rem;        
            --font-label: 2.5rem;
            --font-value: 8rem;
        }

        body {
            margin: 0; padding: 0; background-color: var(--bg-color); color: var(--text-color);
            font-family: 'Inter', sans-serif; overflow: hidden;
            width: 2560px; height: 1440px; transform: rotate(90deg); transform-origin: top left;
            position: absolute; top: 0; left: 1440px; display: flex; flex-direction: column;
        }

        .header { padding: 60px 100px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
        .header h2 { font-size: var(--font-header); margin: 0; letter-spacing: 2px; font-weight: 700; }
        .view-container { flex-grow: 1; position: relative; padding: 60px 100px; }
        .view { display: none; width: 100%; height: 100%; animation: fadeIn 0.4s ease-out; }
        .view.active { display: block; }

        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 50px; height: 100%; }

        .card { background: var(--card-bg); border-radius: 40px; padding: 60px; border: 1px solid rgba(255, 255, 255, 0.08); display: flex; flex-direction: column; justify-content: center; align-items: center; transition: all 0.2s ease; cursor: pointer; }
        .xtramp-box { border: 3px solid var(--accent-color); box-shadow: 0 0 40px rgba(0, 212, 255, 0.2); }
        .card-label { font-size: 2rem; opacity: 0.5; text-transform: uppercase; margin-bottom: 15px; }
        .card-value { font-size: 7rem; font-weight: 800; line-height: 1; }
        .unit { font-size: 3rem; opacity: 0.3; margin-left: 10px; }

        .victron-grid { display: grid; grid-template-columns: 2fr 1fr 1fr; grid-template-rows: repeat(2, 1fr); gap: 40px; height: 100%; }
        .detail-card { background: rgba(20, 20, 20, 0.8); border-radius: 40px; padding: 50px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; flex-direction: column; justify-content: space-between; }
        
        .home-btn { position: fixed; bottom: 60px; right: 60px; width: 120px; height: 120px; background: var(--card-bg); border: 2px solid var(--accent-color); border-radius: 30px; display: flex; justify-content: center; align-items: center; cursor: pointer; z-index: 1000; }
    </style>
</head>
<body>

    <div class="header">
        <div>
            <h2>MULTIVAN<span style="color: var(--accent-color); font-weight: 900;">PI</span></h2>
            <p id="system-status"><span style="width:18px;height:18px;background:var(--success-color);border-radius:50%;display:inline-block;margin-right:15px;"></span> SYSTEM ONLINE</p>
        </div>
        <div style="text-align: right;">
            <div id="clock" style="font-size: 4rem; font-weight: 300;">00:00</div>
            <div id="date" style="font-size: 2rem; opacity: 0.4;">--</div>
        </div>
    </div>

    <div class="view-container">
        <!-- HOME -->
        <section id="view-home" class="view active">
            <div class="grid">
                <div class="card xtramp-box" onclick="showView('victron')">
                    <i data-lucide="zap" size="100" color="#00d4ff"></i>
                    <div style="margin-top: 30px;">
                        <div class="card-label">Energie</div>
                        <div id="home-soc" style="font-size: 5rem; font-weight: 800;">--<span class="unit">%</span></div>
                    </div>
                </div>
                <div class="card" onclick="showView('climate')">
                    <i data-lucide="thermometer" size="100"></i>
                    <div style="margin-top: 30px;">
                        <div class="card-label">Klima</div>
                        <div class="card-value">22.4<span class="unit">°C</span></div>
                    </div>
                </div>
                <div class="card" onclick="showView('water')">
                    <i data-lucide="droplets" size="100"></i>
                    <div style="margin-top: 30px;">
                        <div class="card-label">Wasser</div>
                        <div class="card-value">85<span class="unit">%</span></div>
                    </div>
                </div>
                <div class="card" onclick="location.reload()">
                    <i data-lucide="refresh-cw" size="100" opacity="0.5"></i>
                    <div style="margin-top: 30px;"><div class="card-label">System</div><div style="font-size: 2.5rem; opacity: 0.5;">REFRESH</div></div>
                </div>
            </div>
        </section>

        <!-- VICTRON DETAIL -->
        <section id="view-victron" class="view">
            <div class="victron-grid">
                <div class="detail-card xtramp-box" style="grid-row: span 2;">
                    <div>
                        <div class="card-label">SmartShunt - Bord</div>
                        <div id="vic-soc" style="font-size: 12rem; font-weight: 900; color: var(--accent-color);">--<span class="unit" style="font-size: 5rem;">%</span></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 40px;">
                        <div><div class="card-label">Spannung</div><div id="vic-volt" style="font-size: 4rem; font-weight: 600;">--<span class="unit">V</span></div></div>
                        <div><div class="card-label">Strom</div><div id="vic-amp" style="font-size: 4rem; font-weight: 600;">--<span class="unit">A</span></div></div>
                    </div>
                </div>
                <div class="detail-card">
                    <div class="card-label">Solar (MPPT)</div>
                    <div id="vic-solar" style="font-size: 6rem; font-weight: 700; color: #ffcc00;">--<span class="unit">W</span></div>
                </div>
                <div class="detail-card">
                    <div class="card-label">Booster</div>
                    <div id="vic-booster" style="font-size: 6rem; font-weight: 700;">--<span class="unit">A</span></div>
                </div>
                <div class="detail-card" style="grid-column: span 2;">
                    <div class="card-label">Historie</div>
                    <div style="flex-grow: 1; display: flex; align-items: flex-end; gap: 10px;">
                        <div style="height: 40%; width: 15%; background: rgba(255,255,255,0.1); border-radius: 10px;"></div>
                        <div style="height: 85%; width: 15%; background: var(--accent-color); border-radius: 10px;"></div>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <div id="btn-home" class="home-btn" onclick="showView('home')" style="display: none;"><i data-lucide="home" size="60" color="#00d4ff"></i></div>

    <script>
        function showView(viewId) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById('view-' + viewId).classList.add('active');
            document.getElementById('btn-home').style.display = (viewId === 'home') ? 'none' : 'flex';
        }

        async function updateData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                
                // UI Update
                document.getElementById('home-soc').innerHTML = `${data.battery.soc}<span class="unit">%</span>`;
                document.getElementById('vic-soc').innerHTML = `${data.battery.soc}<span class="unit" style="font-size: 5rem;">%</span>`;
                document.getElementById('vic-volt').innerHTML = `${data.battery.voltage}<span class="unit">V</span>`;
                document.getElementById('vic-amp').innerHTML = `${data.battery.current}<span class="unit">A</span>`;
                document.getElementById('vic-solar').innerHTML = `${data.solar.power}<span class="unit">W</span>`;
            } catch (e) { console.log("Fehler beim Datenabruf"); }
        }

        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString('de-DE', {hour: '2-digit', minute:'2-digit'});
            document.getElementById('date').textContent = now.toLocaleDateString('de-DE', {weekday: 'long', day: 'numeric', month: 'long'});
        }

        setInterval(updateClock, 1000);
        setInterval(updateData, 2000); // Alle 2 Sek. neue Victron Daten
        updateClock();
        lucide.createIcons();
    </script>
</body>
</html>
