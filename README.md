# MultivanPi v2.4

Zentrales Dashboard für den VW Multivan zur Überwachung von Victron Energiedaten, Klima und Fahrzeug-Nivellierung.

## Hardware & Anschlüsse
- **BME280**: I2C (GPIO 2/3) - Innenklima & Druck
- **ADXL345**: I2C (GPIO 2/3) - Wasserwaage
- **DS18B20**: 1-Wire (GPIO 4) - Außentemperatur (4.7k Pull-Up benötigt)
- **DS3231**: I2C (GPIO 2/3) - Echtzeituhr

## Installation
1. `scripts/download_assets.sh` ausführen.
2. `backend/config.json` anpassen.
3. `scripts/start_kiosk.sh` im Autostart (Openbox) hinterlegen.

© 2024-2026 Fred Fiedler
