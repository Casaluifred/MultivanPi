# Phase 1 & 2: System- & Display-Installation (MultivanPi)
Diese Anleitung führt dich durch die komplette Einrichtung deines MultivanPi.
# 1. SD-Karte vorbereiten
Nutze den Raspberry Pi Imager (Version 2.0.6 oder neuer).
OS: Raspberry Pi OS Lite (64-bit)
Customization (Zahnrad):
Hostname: multivanpi
User: fred
SSH & RPi Connect: Aktiviert
Wichtig: Aktiviere das "Erste Einrichten überspringen" und setze das Passwort direkt.
# 2. Erster Start & System-Vorbereitung
Verbinde den Pi per LAN oder richte das WLAN ein. Bevor das Skript läuft, sollte das System aktuell sein:
sudo apt update && sudo apt upgrade -y


2.1 Grafik-Modus für Openbox (Wichtig!)
Da openbox für den Kiosk-Modus genutzt wird, muss der Pi auf das X11-Backend umgestellt werden (Standard ist oft Wayland):
sudo raspi-config aufrufen.
Unter Advanced Options -> Wayland auf X11 umstellen.
Unter System Options -> Boot / Auto Login auf Console Autologin oder Desktop Autologin stellen.
# 3. Display-Treiber (Optional)
Falls du ein spezielles Display (z.B. Waveshare) nutzt, installiere die Treiber vor dem Setup-Skript, um die korrekte Auflösung zu gewährleisten: (Beispiel für Waveshare DSI):
git clone [https://github.com/waveshare/LCD-show.git](https://github.com/waveshare/LCD-show.git)
cd LCD-show/
# Entsprechenden Befehl für dein Display ausführen


# 4. Installation via GitHub
Führe das automatisierte Setup-Skript aus, um alle Abhängigkeiten (Python, Webserver, Kiosk-Tools) zu installieren:
git clone [https://github.com/Casaluifred/MultivanPi.git](https://github.com/Casaluifred/MultivanPi.git)
cd MultivanPi
chmod +x setup.sh
./setup.sh


# 5. Finalisierung & Autostart
Reboot: sudo reboot
Kiosk-Autostart einrichten: Falls der Ordner nicht existiert: mkdir -p /home/fred/.config/openbox Erstelle oder bearbeite die Datei /home/fred/.config/openbox/autostart:
# Starte das Kiosk-Skript im Hintergrund
/home/fred/multivanpi/scripts/start_kiosk.sh &


# 6. Troubleshooting
Kein Bild? Prüfe in der /boot/firmware/config.txt (oder /boot/config.txt), ob die dtoverlay-Einträge für das Display korrekt sind.
Cursor sichtbar? Das Setup-Skript sollte unclutter installieren, um den Mauszeiger zu verstecken.
Dokumentation für MultivanPi.
