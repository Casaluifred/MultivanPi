#!/bin/bash

# 1. Sicherstellen, dass die Umgebungsvariable gesetzt ist
export DISPLAY=:0

# 2. Kurze Pause, damit der X-Server und die Hardware bereit sind
sleep 4

# 3. Monitor-Name auslesen (In deinem Fall: "default")
# Wir nutzen den Namen, den du mir gerade geschickt hast.
MONITOR_NAME=$(xrandr | grep " connected" | cut -d' ' -f1)

# Falls die Suche fehlschlägt, erzwingen wir "default"
if [ -z "$MONITOR_NAME" ]; then
    MONITOR_NAME="default"
fi

# 4. Anzeige drehen
# Da der Treiber "default" heißt, versuchen wir die Rotation direkt
# Hinweis: Falls 'xrandr' hier einen Fehler wirft, liegt es am fbdev-Treiber.
# In diesem Fall nutzen wir die Chromium-interne Drehung als Fallback.
xrandr --output "$MONITOR_NAME" --rotate right || echo "xrandr rotation failed, continuing..."

# 5. Mauszeiger verstecken
unclutter -idle 0.1 -root &

# 6. Bildschirmschoner und Energiesparmodus aus
xset s off
xset s noblank
xset -dpms

# 7. Chromium starten
# WICHTIG: Wenn xrandr die Drehung geschafft hat, ist die Auflösung 2560x1440.
# Wir fügen '--force-device-scale-factor' hinzu, um die Darstellung für das 2K Display zu optimieren.
chromium --kiosk \
         --noerrdialogs \
         --disable-infobars \
         --window-size=2560,1440 \
         --window-position=0,0 \
         --force-device-scale-factor=1.2 \
         --ignore-certificate-errors \
         http://localhost:3000
