#!/bin/bash

# Farben für die Ausgabe
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   MultivanPi - Automatischer Installer v2.5        ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. System aktualisieren und Pakete installieren
echo -e "${GREEN}[1/8] Installiere System-Abhängigkeiten...${NC}"
sudo apt update
# chromium-browser heißt auf neueren Systemen oft nur 'chromium'
sudo apt install -y python3-venv python3-pip chromium-browser xserver-xorg xinit openbox unclutter curl fuser bluetooth bluez i2c-tools python3-smbus || sudo apt install -y python3-venv python3-pip chromium xserver-xorg xinit openbox unclutter curl fuser bluetooth bluez i2c-tools python3-smbus

# 2. Ordnerstruktur erstellen
echo -e "${GREEN}[2/8] Erstelle Ordnerstruktur...${NC}"
mkdir -p backend
mkdir -p scripts
mkdir -p static
mkdir -p ~/.config/openbox

# 3. Python Umgebung einrichten
echo -e "${GREEN}[3/8] Richte Python Virtual Environment ein...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installiere Python-Bibliotheken..."
pip install --upgrade pip
# Wir installieren alles, was für Victron, EcoFlow und Sensoren nötig ist
pip install aiohttp victron-ble smbus2 bleak

# 4. Offline-Assets herunterladen (Icons & Charts)
echo -e "${GREEN}[4/8] Lade Offline-Dateien (Icons & Charts)...${NC}"
# Lucide Icons
wget -q https://unpkg.com/lucide@latest/dist/umd/lucide.min.js -O static/lucide.min.js
# Chart.js für Diagramme
wget -q https://cdn.jsdelivr.net/npm/chart.js -O static/chart.min.js

if [ -f "static/lucide.min.js" ]; then
    echo " -> Icons erfolgreich geladen."
else
    echo -e "${YELLOW} -> Warnung: Icon-Download fehlgeschlagen. Internet prüfen!${NC}"
fi

# 5. Konfiguration vorbereiten (Sicherheit!)
echo -e "${GREEN}[5/8] Erstelle Konfiguration...${NC}"
# Wenn noch keine echte Config existiert, erstelle eine aus dem Beispiel
if [ ! -f "backend/config.json" ]; then
    if [ -f "backend/config.example.json" ]; then
        echo " -> Kopiere Beispiel-Konfiguration..."
        cp backend/config.example.json backend/config.json
        echo -e "${YELLOW} -> WICHTIG: Bitte trage später deine Keys in backend/config.json ein!${NC}"
    else
        echo " -> Erstelle leere Konfigurations-Vorlage..."
        # Fallback, falls example fehlt
        echo '{ "victron": {}, "ecoflow": {} }' > backend/config.json
    fi
else
    echo " -> Bestehende Konfiguration gefunden. Wird nicht überschrieben."
fi

# 6. Hardware aktivieren (I2C für Sensoren)
echo -e "${GREEN}[6/8] Aktiviere I2C Bus...${NC}"
# Aktiviert I2C non-interaktiv
sudo raspi-config nonint do_i2c 0

# 7. Autostart einrichten (Plan B: .bash_profile -> startx)
echo -e "${GREEN}[7/8] Richte Autostart ein...${NC}"

# .bash_profile für automatischen Grafik-Start
if ! grep -q "startx" ~/.bash_profile; then
    echo 'if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then exec startx; fi' >> ~/.bash_profile
fi

# .xinitrc für Openbox
echo "exec openbox-session" > ~/.xinitrc

# Openbox Autostart für unser Kiosk-Skript
echo "/home/$USER/MultivanPi/scripts/start_kiosk.sh &" > ~/.config/openbox/autostart

# Konsole Autologin aktivieren (damit .bash_profile greift)
sudo raspi-config nonint do_boot_behaviour B2

# 8. Berechtigungen und Abschluss
echo -e "${GREEN}[8/8] Setze Berechtigungen...${NC}"
chmod +x scripts/start_kiosk.sh
# Erlaubt Python Zugriff auf Bluetooth ohne sudo
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f venv/bin/python3)

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   Installation abgeschlossen!                      ${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "1. Bearbeite ${YELLOW}backend/config.json${NC} und füge deine Keys ein."
echo -e "2. Starte neu mit ${YELLOW}sudo reboot${NC}"