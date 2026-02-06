#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}>>> MultivanPi: Starte automatische Installation${NC}"

# 1. System-Updates & Abhängigkeiten
echo -e "${GREEN}1. Installiere System-Abhängigkeiten...${NC}"
sudo apt update
sudo apt install -y python3-venv python3-pip chromium-browser xserver-xorg xinit openbox unclutter curl fuser bluetooth bluez

# 2. Python Virtual Environment
echo -e "${GREEN}2. Erstelle Virtual Environment...${NC}"
python3 -m venv /home/fred/MultivanPi/venv
source /home/fred/MultivanPi/venv/bin/activate

# 3. Python Module installieren
echo -e "${GREEN}3. Installiere Python-Module...${NC}"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install aiohttp victron-ble
fi

# 4. Verzeichnisse prüfen
echo -e "${GREEN}4. Prüfe Verzeichnisstruktur...${NC}"
mkdir -p ~/.config/openbox
mkdir -p scripts
mkdir -p backend

# 5. Berechtigungen setzen
echo -e "${GREEN}5. Setze Berechtigungen...${NC}"
chmod +x scripts/start_kiosk.sh

# 6. Autostart Konfiguration
echo -e "${GREEN}6. Konfiguriere Autostart (Openbox)...${NC}"
echo "/home/fred/MultivanPi/scripts/start_kiosk.sh &" > ~/.config/openbox/autostart

# 7. X11 Initialisierung
if [ ! -f "~/.xinitrc" ]; then
    echo "exec openbox-session" > ~/.xinitrc
fi

echo -e "${BLUE}>>> Installation abgeschlossen!${NC}"
echo "Bitte konfiguriere nun deine Victron-Keys in backend/victron_service.py"
echo "Danach kannst du das System mit 'sudo reboot' neu starten."
