#!/bin/bash

# ==========================================
# MULTIVAN PI - KIOSK START SCRIPT v2.1
# ==========================================
# 
# Nach änderungen ausführen:
# chmod +x ~/MultivanPi/scripts/start_kiosk.sh
# sudo chown fred:fred ~/MultivanPi/scripts/start_kiosk.sh
# ==========================================

# 1. Umgebungsvariablen setzen
export DISPLAY=:0
export XAUTHORITY=/home/fred/.Xauthority
export FONTCONFIG_PATH=/etc/fonts

# Projekt-Pfade definieren
PROJECT_DIR="/home/fred/MultivanPi"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python3"
SERVICE_SCRIPT="$PROJECT_DIR/backend/victron_service.py"
LOG_FILE="$PROJECT_DIR/service.log"

# Visuelles Feedback (Hintergrund grau setzen)
xsetroot -solid "#333333" 2>/dev/null

# Logging aktivieren (Ausgabe in Datei und Konsole)
exec > >(tee -a "$LOG_FILE") 2>&1

echo ">>> $(date): Startversuch MultivanPi"

# 2. Alte Prozesse sauber beenden
echo "Beende alte Prozesse..."
sudo fuser -k 3000/tcp > /dev/null 2>&1
sudo pkill -f chromium > /dev/null 2>&1
sudo pkill -f victron_service.py > /dev/null 2>&1
sleep 2

# 3. Backend starten (MIT SUDO!)
if [ -f "$SERVICE_SCRIPT" ]; then
    echo "Starte Backend..."
    # -u für unbuffered Output (wichtig für Logs)
    sudo $PYTHON_BIN -u "$SERVICE_SCRIPT" &
else
    echo "FEHLER: Backend-Script nicht gefunden: $SERVICE_SCRIPT"
    exit 1
fi

# 4. Warten auf Server (Healthcheck)
echo -n "Warte auf API..."
SUCCESS=false
for i in {1..30}; do
    # Prüft ob der Webserver auf Port 3000 antwortet
    if curl -s -o /dev/null "http://127.0.0.1:3000/api/data"; then
        echo " OK!"
        SUCCESS=true
        break
    fi
    echo -n "."
    sleep 1
done

if [ "$SUCCESS" = false ]; then
    echo " WARNUNG: Backend reagiert nicht schnell genug. Starte Browser trotzdem..."
fi

# 5. Grafik-Setup & Energiesparen (NEU: 15 Min Auto-Off)
xset s off          # Bildschirmschoner aus
xset -dpms          # Reset
xset +dpms          # Power Management AN
xset dpms 900 900 900  # Standby/Suspend/Off nach 900s (15 Min)

# Mauszeiger ausblenden
unclutter -idle 0.1 -root &

# Browser-Daten bereinigen (verhindert "Restore Session" Popups)
mkdir -p /home/fred/.config/chromium-kiosk
rm -rf /home/fred/.config/chromium-kiosk/Singleton*
rm -rf /home/fred/.config/chromium-kiosk/SingletonLock
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' ~/.config/chromium-kiosk/Default/Preferences
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' ~/.config/chromium-kiosk/Default/Preferences

# 6. Browser finden
if command -v chromium &> /dev/null; then
    CHROME_BIN="chromium"
elif command -v chromium-browser &> /dev/null; then
    CHROME_BIN="chromium-browser"
else
    echo "FEHLER: Kein Chromium Browser gefunden."
    exit 1
fi

echo "Starte Browser: $CHROME_BIN"

# 7. Browser starten (Endlosschleife für Absturz-Schutz)
while true; do
    $CHROME_BIN --kiosk \
      --noerrdialogs \
      --disable-infobars \
      --disable-gpu \
      --disable-software-rasterizer \
      --disable-features=TranslateUI \
      --check-for-update-interval=31536000 \
      --user-data-dir="/home/fred/.config/chromium-kiosk" \
      "http://127.0.0.1:3000"
      
    echo "Browser beendet. Neustart in 2s..."
    sleep 2
done