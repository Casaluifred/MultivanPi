#!/bin/bash

# 1. Umgebungsvariablen setzen
export DISPLAY=:0

# 2. PROJEKT-VERZEICHNIS
cd /home/fred/MultivanPi

# 3. WEBSERVER & VICTRON SERVICE STARTEN
# WICHTIG: Wir nutzen jetzt das Python aus der virtuellen Umgebung (venv)
if ! pgrep -f "backend/victron_service.py" > /dev/null; then
    nohup /home/fred/MultivanPi/venv/bin/python3 backend/victron_service.py > /dev/null 2>&1 &
    sleep 4
fi

# 4. Kurze Pause für die Hardware-Initialisierung
sleep 4

# 5. TOUCH-ROTATION
TOUCH_DEVICE=$(xinput list --name-only | grep -iE "touch|point|waveshare|hid" | head -n 1)
if [ -n "$TOUCH_DEVICE" ]; then
    xinput set-prop "$TOUCH_DEVICE" "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1
fi

# 6. Mauszeiger verstecken
unclutter -idle 0.1 -root &

# 7. Bildschirmschoner und Energiesparmodus deaktivieren
xset s off
xset s noblank
xset -dpms

# 8. Chromium im Vollbild starten
chromium --kiosk \
         --no-first-run \
         --noerrdialogs \
         --disable-infobars \
         --start-maximized \
         --window-size=1440,2560 \
         --window-position=0,0 \
         --force-device-scale-factor=1.0 \
         --ignore-certificate-errors \
         --disable-restore-session-state \
         --ozone-platform=x11 \
         --user-data-dir=/home/fred/.config/chromium-kiosk \
         http://localhost:3000
