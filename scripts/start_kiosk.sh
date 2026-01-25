#!/bin/bash

# Mauszeiger verstecken
unclutter -idle 0.1 -root &

# Bildschirmschoner und Energiesparmodus deaktivieren
xset s off
xset s noblank
xset -dpms

# Chromium im Kiosk-Modus starten
# --window-size und --window-position helfen beim Waveshare Display
chromium --kiosk --noerrdialogs --disable-infobars --window-size=1440,2560 --window-position=0,0 http://localhost:3000
