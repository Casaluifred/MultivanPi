#!/bin/bash

# Bildschirmschoner und Energiemanagement deaktivieren
xset s noblank
xset s off
xset -dpms

# Browser-Absturz-Meldungen unterdrücken
sed -i 's/"exited_cleanly":false/"exited_cleanly":true/' /home/fred/.config/chromium/Default/Preferences
sed -i 's/"exit_type":"Crashed"/"exit_type":"Normal"/' /home/fred/.config/chromium/Default/Preferences

# Chromium im Kiosk-Modus mit High-DPI Skalierung starten
chromium-browser \
    --force-device-scale-factor=2.5 \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --autoplay-policy=no-user-gesture-required \
    http://localhost:3000
