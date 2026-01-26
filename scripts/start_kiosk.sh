#!/bin/bash

# 1. Umgebungsvariablen
export DISPLAY=:0
export XAUTHORITY=/home/fred/.Xauthority

PROJECT_DIR="/home/fred/MultivanPi"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python3"
SERVICE_SCRIPT="$PROJECT_DIR/backend/victron_service.py"
LOG_FILE="$PROJECT_DIR/service.log"

echo ">>> MultivanPi Kiosk: System-Start-Sequenz"

# 2. Alte Prozesse beenden
sudo fuser -k 3000/tcp > /dev/null 2>&1
pkill -9 -f chromium > /dev/null 2>&1
pkill -9 -f victron_service.py > /dev/null 2>&1
sleep 2

# 3. Backend starten (unbuffered Python für echtes Logging)
echo "Starte Backend..."
$PYTHON_BIN -u $SERVICE_SCRIPT > $LOG_FILE 2>&1 &

# 4. Warten auf Server (Wir erzwingen IPv4 bei curl)
echo -n "Warte auf API"
for i in {1..20}; do
    if curl -4 -s "http://127.0.0.1:3000" > /dev/null; then
        echo -e "\n[OK] Backend erreichbar!"
        break
    fi
    echo -n "."
    sleep 1
done

# 5. Grafik-Setup
xset s off
xset s noblank
xset -dpms
unclutter -idle 0.5 -root &

# Chromium-Locks radikal entfernen
rm -rf /home/fred/.config/chromium-kiosk/Singleton*

echo "Starte Chromium..."
# Wir nutzen die IP 127.0.0.1, das ist stabiler als 'localhost'
chromium --kiosk \
         --incognito \
         --no-first-run \
         --noerrdialogs \
         --disable-infobars \
         --window-size=1440,2560 \
         --window-position=0,0 \
         --force-device-scale-factor=1.0 \
         --user-data-dir=/home/fred/.config/chromium-kiosk \
         "http://127.0.0.1:3000"
