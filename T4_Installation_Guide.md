# Phase 1 & 2: System- & Display-Installation (MultivanPi)
Diese Anleitung führt dich durch die komplette Einrichtung deines MultivanPi.
# 1. SD-Karte vorbereiten
Nutze den Raspberry Pi Imager (Version 2.0.6 oder neuer).

OS: Raspberry Pi OS Lite (64-bit)

Customization (Zahnrad): - Hostname: multivanpi

User: [Username]

Passwort: [Passwort]

SSH & RPi Connect: Aktiviert

# 2. Erster Start & Netzwerk
Verbinde den Pi per LAN oder richte das WLAN über das Terminal ein (siehe README).
# 3. Installation via GitHub
Führe das automatisierte Setup-Skript aus:

git clone [https://github.com/Casaluifred/MultivanPi.git](https://github.com/Casaluifred/MultivanPi.git)

cd MultivanPi

chmod +x setup.sh

./setup.sh



# 4. Finalisierung
Reboot: sudo reboot

Kiosk-Autostart: Trage /home/fred/multivanpi/scripts/start_kiosk.sh & in die Datei /home/fred/.config/openbox/autostart ein.


Dokumentation für MultivanPi.
