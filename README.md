# MultivanPi

**Raspberry-Pi-Dashboard für den VW T4 Camper: Victron-Energie, Klima, Kühlbox und digitale Wasserwaage auf einem Touchscreen.**

Statt für jedes Gerät eine eigene App zu öffnen, zeigt der MultivanPi alle wichtigen Daten des Campers auf einem fest verbauten Bildschirm, sofort beim Einsteigen und ohne Handy.

📖 **Ausführliche Projektbeschreibung und Bauanleitung:** [xtramp.de/multivanpi-projektbeschreibung](https://www.xtramp.de/multivanpi-projektbeschreibung/)

<!-- Screenshot des Dashboards hier einfügen, z. B.: ![MultivanPi Dashboard](docs/dashboard.jpg) -->

> **English summary:** MultivanPi is a Raspberry Pi based dashboard for a VW T4 campervan. It monitors Victron devices via Bluetooth LE, shows indoor/outdoor climate and a 3-day pressure trend, controls a Vevor/Alpicool compressor fridge and works as a digital spirit level that tells you how many centimetres to raise each wheel. Documentation is in German; a detailed build log is available at [xtramp.de](https://www.xtramp.de/multivanpi-projektbeschreibung/).

**Aktuelle Version:** 4.8

---

## Funktionen

- **Energie:** Victron SmartShunt, MPPT-Solarregler und Orion-Tr Smart Ladebooster per Bluetooth LE (passives Scannen, die VictronConnect-App funktioniert parallel)
- **EcoFlow:** Ein- und Ausgangsleistung sowie Restlaufzeit der Powerstation (über ioBroker, siehe unten)
- **Klima:** Innenklima, Luftdruck und Außentemperatur, Luftdruck-Trend über 3 Tage
- **Wasserwaage:** Neigung des Fahrzeugs mit Angabe in Zentimetern pro Rad
- **Kühlbox:** Steuerung einer Vevor/Alpicool-Kompressorkühlbox per Bluetooth
- **Automatik:** Watchdog schaltet die Kühlbox bei niedrigem Batterie-Ladezustand ab
- **Stromsparen:** Display wird komplett abgeschaltet und per Fingertipp geweckt
- **Backup:** Tägliche Sicherung von Konfiguration und Messdaten auf USB-Stick

## Hardware & Anschlüsse

| Komponente | Anschluss | Aufgabe |
|---|---|---|
| Raspberry Pi 4B (4 GB) | – | Rechner |
| 5,5" AMOLED-Touchscreen | HDMI / USB | Anzeige |
| BME280 | I2C (GPIO 2/3) | Innenklima & Luftdruck |
| ADXL345 | I2C (GPIO 2/3) | Wasserwaage |
| DS18B20 | 1-Wire (GPIO 4) | Außentemperatur, **4,7-kΩ-Pull-Up nötig** |
| DS3231 | I2C (GPIO 2/3) | Echtzeituhr |
| DC-DC-Wandler 12 V → 5 V (min. 3 A) | Aufbaubatterie | Stromversorgung |

> [!TIP]
> Statt des ADXL345 kann auch ein **GY-BNO055** (I2C, GPIO 2/3) verwendet werden. Er liefert stabilere Lagedaten.

> [!WARNING]
> Kein MPU6050 verwenden: Er nutzt die I2C-Adresse `0x68`, auf der meist schon die Echtzeituhr sitzt. Zeigt `i2cdetect -y 1` an dieser Stelle `UU`, ist die Adresse vom Kernel belegt.

## Voraussetzungen

- Raspberry Pi OS [Version eintragen] mit Openbox
- Python [Version eintragen, z. B. 3.13]
- [Abhängigkeiten eintragen, z. B. `pip install -r requirements.txt`]
- Für EcoFlow: ioBroker mit dem Adapter `ecoflow-mqtt`

## Installation

1. `scripts/download_assets.sh` ausführen.
2. `backend/config.json` anpassen.
3. `scripts/start_kiosk.sh` im Autostart (Openbox) hinterlegen.
4. Optional: EcoFlow einrichten (siehe nächster Abschnitt).

> [!CAUTION]
> Die `config.json` enthält Deine persönlichen Victron-Schlüssel. Sie gehört nicht in ein öffentliches Repository.

## EcoFlow-Integration (ioBroker-Pfade anpassen)

EcoFlow verwendet je nach Modell (Delta 2, Delta Pro, Delta 3 Plus usw.) unterschiedliche interne Bezeichnungen für die Sensordaten. Deshalb müssen die MQTT-Pfade im Python-Skript eventuell an Dein Modell angepasst werden.

So findest Du die richtigen Pfade für Deine Powerstation:

1. Öffne die **ioBroker-Weboberfläche** (standardmäßig unter `http://<IP-des-Pi>:8081`).
2. Wechsle oben in den Reiter **Objekte**.
3. Klappe den Baum auf: `ecoflow-mqtt.1` → `[Deine_Seriennummer]`.
4. Suche in den Unterordnern (meist `DisplayPropertyUpload`, `bms_emsStatus` oder `pd`) nach den Live-Werten Deiner Batterie. Typische Bezeichnungen sind:
   - **Eingangsleistung (Watt):** z. B. `powInSumW`, `pdWattsInSum` oder `totalInPwr`
   - **Ausgangsleistung (Watt):** z. B. `powOutSumW`, `pdWattsOutSum` oder `totalOutPwr`
   - **Verbleibende Entladezeit (Minuten):** z. B. `bmsDsgRemTime`
   - **Verbleibende Ladezeit (Minuten):** z. B. `bmsChgRemTime`
5. Klicke ganz rechts in der Zeile des jeweiligen Wertes auf das Symbol **„Objekt-ID kopieren“**.

> [!TIP]
> Nutze das Suchfeld oben im Reiter „Objekte“. Gibst Du dort Begriffe wie **watts**, **pwr** oder **remTime** ein, filtert ioBroker den Baum, und Du findest die Datenpunkte in Sekunden. Schließe am besten kurz einen starken Verbraucher an, damit die Werte nicht auf 0 stehen und eindeutig zu erkennen sind.

Öffne anschließend `backend/ecoflow_controller.py` und ersetze die Platzhalter in der Funktion `__init__` durch Deine kopierten IDs:

```python
# === HIER DEINE KOPIERTEN IDs EINTRAGEN ===
self.dp_in = "ecoflow-mqtt.1.P351...DEINE_ID...powInSumW"
self.dp_out = "ecoflow-mqtt.1.P351...DEINE_ID...powOutSumW"
self.dp_remain_dsg = "ecoflow-mqtt.1.P351...DEINE_ID...bmsDsgRemTime"
self.dp_remain_chg = "ecoflow-mqtt.1.P351...DEINE_ID...bmsChgRemTime"
```

## Bekannte Probleme

**Absturz bei Fehlercode 129 des Orion-Tr Smart:** Die Bibliothek `victron_ble` kennt den Code „Engine Shutdown + No Input“ nicht. Abhilfe: in `victron_ble/devices/base.py` den Wert `ENGINE_SHUTDOWN_AND_NO_INPUT = 129` ergänzen. Details im Blog unter [xtramp.de](https://www.xtramp.de/multivanpi-projektbeschreibung/).

**`org.bluez.Error.InProgress` beim Start:** Kühlbox und Victron-Scan kommen sich beim Verbindungsaufbau in die Quere. Der Victron-Scan pausiert deshalb beim Start für 8 Sekunden.

## Lizenz

GPL

© 2024–2026 Fred Fiedler · [xtramp.de](https://www.xtramp.de)
