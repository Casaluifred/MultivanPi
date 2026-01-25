#!/bin/bash

# MultivanPi Setup Skript
# Zielsystem: Raspberry Pi OS (Lite) 64-bit
# Autor: fred

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}>>> Starte MultivanPi Setup...${NC}"

# 1. System Update
echo -e "${GREEN}1. Aktualisiere Systempakete...${NC}"
sudo apt update && sudo apt upgrade -y

# 2. Installation der Basis-Abhängigkeiten
echo -e "${GREEN}2. Installiere Basis-Tools (Git, Python, Pip)...${NC}"
sudo apt install -y git python3 python3-pip python3-venv python3-full curl build-essential

# 3. Installation der Kiosk-Umgebung (Grafik & Browser)
echo -e "${GREEN}3. Installiere Kiosk-Komponenten (X11, Openbox, Chromium)...${NC}"

# Suche nach dem verfügbaren Chromium-Paket
if apt-cache show chromium > /dev/null 2>&1; then
    CHROME_PKG="chromium"
elif apt-cache show chromium-browser > /dev/null 2>&1; then
    CHROME_PKG="chromium-browser"
else
    echo -e "${RED}Fehler: Weder 'chromium' noch 'chromium-browser' wurden in den Paketquellen gefunden!${NC}"
    exit 1
fi

echo -e "${BLUE}Nutze Paket: $CHROME_PKG${NC}"
sudo apt install -y xserver-xorg x11-xserver-utils xinit openbox $CHROME_PKG unclutter

# 4. Installation von Node.js (LTS)
echo -e "${GREEN}4. Installiere Node.js & NPM...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
else
    echo "Node.js ist bereits installiert."
fi

# 5. Benutzer-Berechtigungen setzen (OBD-II & Sensoren)
echo -e "${GREEN}5. Setze Berechtigungen für User 'fred'...${NC}"
sudo usermod -aG dialout,gpio $USER
echo "Berechtigungen für dialout und gpio hinzugefügt."

# 6. Projekt-Struktur & Python Virtual Environment
echo -e "${GREEN}6. Bereite Python-Umgebung vor...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    # Falls eine requirements.txt existiert:
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    deactivate
fi

# 7. Openbox Konfiguration vorbereiten
echo -e "${GREEN}7. Konfiguriere Autostart...${NC}"
mkdir -p ~/.config/openbox
if [ ! -f "$HOME/.config/openbox/autostart" ]; then
    echo "Erstelle neue Openbox Autostart Datei..."
    echo "# MultivanPi Autostart" > ~/.config/openbox/autostart
    echo "exec /home/fred/MultivanPi/scripts/start_kiosk.sh &" >> ~/.config/openbox/autostart
fi

# 8. Ausführrechte für Skripte sicherstellen
if [ -f "scripts/start_kiosk.sh" ]; then
    chmod +x scripts/start_kiosk.sh
fi

echo -e "${BLUE}>>> Setup abgeschlossen!${NC}"
echo -e "Bitte führe jetzt noch ${GREEN}sudo raspi-config${NC} aus, um:"
echo -e "1. Unter 'Advanced Options' -> 'Wayland' auf 'X11' zu wechseln."
echo -e "2. Unter 'System Options' -> 'Boot / Auto Login' auf 'Console Autologin' zu stellen."
echo -e ""
echo -e "Danach das System mit ${GREEN}sudo reboot${NC} neu starten."
