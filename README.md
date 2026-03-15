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

4. ### EcoFlow Integration (ioBroker Pfade anpassen)

Da EcoFlow bei verschiedenen Modellen (Delta 2, Delta Pro, Delta 3 Plus etc.) die internen Bezeichnungen für die Sensordaten ändert, müssen die MQTT-Pfade im Python-Skript eventuell an dein spezifisches Modell angepasst werden. 

So findest du die richtigen Pfade für deine Powerstation:

1. Öffne die **ioBroker Weboberfläche** (standardmäßig unter `http://<IP-des-Pi>:8081`).
2. Wechsle oben in den Reiter **Objekte**.
3. Klappe den Baumbau auf: `ecoflow-mqtt.1` -> `[Deine_Seriennummer]`.
4. Suche in den Unterordnern (meist `DisplayPropertyUpload`, `bms_emsStatus` oder `pd`) nach den Live-Werten für deine Batterie. Typische Bezeichnungen sind:
   * **Eingangsleistung (Watt):** z. B. `powInSumW`, `pdWattsInSum` oder `totalInPwr`
   * **Ausgangsleistung (Watt):** z. B. `powOutSumW`, `pdWattsOutSum` oder `totalOutPwr`
   * **Verbleibende Entladezeit (Minuten):** z. B. `bmsDsgRemTime`
   * **Verbleibende Ladezeit (Minuten):** z. B. `bmsChgRemTime`
5. Klicke ganz rechts in der Zeile des jeweiligen Wertes auf das kleine Symbol **"Objekt-ID kopieren"**.

<div class="xtramp-box">
  <strong>Tipp zur Suche:</strong> Nutze das Suchfeld oben im Objekte-Reiter. Wenn du dort Begriffe wie <strong>watts</strong>, <strong>pwr</strong> oder <strong>remTime</strong> eingibst, filtert ioBroker den riesigen Baum und du findest die Datenpunkte in Sekundenschnelle. Schließe am besten kurz einen starken Verbraucher an, damit die Werte nicht auf 0 stehen und zweifelsfrei zu erkennen sind.
</div>

Öffne anschließend die Datei `backend/ecoflow_controller.py` in einem Editor und ersetze die Platzhalter im oberen Bereich (innerhalb der `__init__` Funktion) durch deine kopierten IDs:

```python
        # === HIER DEINE KOPIERTEN IDs EINTRAGEN ===
        self.dp_in = "ecoflow-mqtt.1.P351...DEINE_ID...powInSumW"
        self.dp_out = "ecoflow-mqtt.1.P351...DEINE_ID...powOutSumW"
        self.dp_remain_dsg = "ecoflow-mqtt.1.P351...DEINE_ID...bmsDsgRemTime"
        self.dp_remain_chg = "ecoflow-mqtt.1.P351...DEINE_ID...bmsChgRemTime"

© 2024-2026 Fred Fiedler
