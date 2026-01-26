#!/bin/bash

# 1. Umgebungsvariablen setzen
export DISPLAY=:0

# 2. PROJEKT-VERZEICHNIS
# Wir wechseln in dein Verzeichnis, damit der Server die index.html findet
cd /home/fred/MultivanPi

# 3. WEBSERVER STARTEN (Falls er noch nicht läuft)
# Wir starten den Python-Server im Hintergrund (&). 
# 'nohup' und die Umleitung nach /dev/null sorgen dafür, dass er stabil läuft.
if ! pgrep -f "python3 -m http.server 3000" > /dev/null; then
    nohup python3 -m http.server 3000 > /dev/null 2>&1 &
    sleep 2 # Kurze Pause, damit der Server bereit ist
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
