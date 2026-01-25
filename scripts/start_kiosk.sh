#!/bin/bash

# Mauszeiger verstecken
unclutter -idle 0.1 -root &

# Bildschirmschoner und Energiesparmodus deaktivieren
xset s off
xset s noblank
xset -dpms

# Chromium im Kiosk-Modus starten
# Da wir per xrandr gedreht haben, ist die Auflösung nun 2560x1440
chromium --kiosk --noerrdialogs --disable-infobars --window-size=2560,1440 --window-position=0,0 http://localhost:3000
