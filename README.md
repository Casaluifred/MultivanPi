# MultivanPi
Ein zentrales Kontrollpanel für den VW T4 Multivan Camper auf Basis eines Raspberry Pi 4 und einem 5.5" 2K Touch-Display.
Features
Victron Integration: Überwachung von Solar (MPPT), Starterbatterie (SmartShunt) und Versorgerbatterie (LiFePO4) via Bluetooth LE.
Leveling Tool: Digitale Wasserwaage zur perfekten Ausrichtung des Fahrzeugs beim Parken.
Klima-Monitoring: Anzeige von Innen- und Außentemperatur sowie Luftfeuchtigkeit.
Smart Button: Physischer Edelstahl-Taster mit LED-Feedback (Pulsieren im Standby, PWM-gedimmt).
Fernzugriff: Sicherer Zugriff von unterwegs via Tailscale und Raspberry Pi Connect.
Hardware-Stack
Raspberry Pi 4 (4GB)
Waveshare 5.5" 2K LCD (1440x2560)
Victron SmartShunt & Smart Battery Sense
Edelstahl Vandalismus-Taster (16mm)
MeanWell DC-DC Wandler (12V -> 5V isoliert)
Installation
Um das System auf einem frischen Raspberry Pi OS Lite (64-bit) zu installieren, nutze das integrierte Setup-Skript:
# Repository klonen
git clone [https://github.com/Casaluifred/MultivanPi.git](https://github.com/Casaluifred/MultivanPi.git)
cd MultivanPi

# Installer starten
chmod +x setup.sh
./setup.sh


Projektstruktur
/backend: Python (FastAPI) für Victron BLE und MQTT.
/frontend: React Dashboard (Tailwind CSS).
/scripts: System-Skripte für Kiosk-Mode und Power-Management.
/docs: Bauanleitungen und Gehäuse-Designs (3D-Druck).
Lizenz
Dieses Projekt steht unter der Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) Lizenz.
Details findest du in der Datei LICENSE.
Erstellt von fred für den MultivanPi.
