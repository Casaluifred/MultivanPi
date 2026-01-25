#!/bin/bash

# 1. Anzeige drehen
# Da KMS aus ist, probieren wir 'HDMI-1' und als Fallback 'default'
xrandr --output HDMI-1 --rotate right || xrandr --output default --rotate right

# 2. Mauszeiger nach 0.1 Sek. Inaktivität verstecken
unclutter -idle 0.1 -root &

# 3. Bildschirmschoner und Energiesparmodus aus
xset s off
xset s noblank
xset -dpms

# 4. Chromium im Kiosk-Modus starten
# Fenstergröße jetzt 2560x1440 (durch Drehung)
chromium --kiosk --noerrdialogs --disable-infobars --window-size=2560,1440 --window-position=0,0 http://localhost:3000
