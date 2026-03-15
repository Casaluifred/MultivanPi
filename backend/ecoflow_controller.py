import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EcoFlowController:
    def __init__(self, host="127.0.0.1", port=8087, serial="P351ZEH4PGBL0776"):
        self.base_url = f"http://{host}:{port}"
        self.serial = serial
        
        self.dp_soc = f"ecoflow-mqtt.1.{self.serial}.DisplayPropertyUpload.cmsBattSoc"
        self.dp_ac = f"ecoflow-mqtt.1.{self.serial}.setDp3.cfgAcOutOpen"
        self.dp_12v = f"ecoflow-mqtt.1.{self.serial}.setDp3.cfgDc12vOutOpen"
        self.dp_usb = f"ecoflow-mqtt.1.{self.serial}.setDp3.cfgUsbOpen"
        self.dp_in = f"ecoflow-mqtt.1.{self.serial}.DisplayPropertyUpload.powInSumW"
        self.dp_out = f"ecoflow-mqtt.1.{self.serial}.DisplayPropertyUpload.powOutSumW"

    def _lese_wert(self, datenpunkt):
        url = f"{self.base_url}/get/{datenpunkt}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            daten = response.json()
            return daten.get("val")
        except requests.exceptions.RequestException as e:
            logging.debug(f"Fehler beim Lesen von {datenpunkt}: {e}")
            return None

    def _schalte_wert(self, datenpunkt, zustand: bool):
        val_str = "true" if zustand else "false"
        url = f"{self.base_url}/set/{datenpunkt}?value={val_str}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            logging.info(f"EcoFlow Befehl gesendet: {datenpunkt.split('.')[-1]} -> {val_str}")
            return True
        except requests.exceptions.RequestException as e:
            logging.error(f"Fehler beim Schalten von {datenpunkt}: {e}")
            return False

    def get_soc(self):
        val = self._lese_wert(self.dp_soc)
        if val is not None: return float(val)
        return None

    def get_total_in(self):
        val = self._lese_wert(self.dp_in)
        if val is not None: return int(float(val))
        return 0

    def get_total_out(self):
        val = self._lese_wert(self.dp_out)
        if val is not None: return int(float(val))
        return 0

    def get_remain_time(self):
        # Sucht automatisch in Lade- und Entladezeiten.
        # Sobald ein Wert ueber 0 gefunden wird, wird er zurueckgegeben.
        pfade = [
            f"ecoflow-mqtt.1.{self.serial}.bms_emsStatus.bmsDsgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.bms_emsStatus.bmsChgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.bmsMaster.bmsDsgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.bmsMaster.bmsChgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.DisplayPropertyUpload.bmsDsgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.DisplayPropertyUpload.bmsChgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.bms_emsStatus.chgRemTime",
            f"ecoflow-mqtt.1.{self.serial}.bms_emsStatus.dsgRemTime"
        ]
        
        for p in pfade:
            val = self._lese_wert(p)
            if val is not None:
                try:
                    # Falls ioBroker einen formatierten String wie "5122 min" liefert
                    if isinstance(val, str):
                        val_clean = ''.join(filter(str.isdigit, val))
                        if val_clean and int(val_clean) > 0:
                            return int(val_clean)
                    elif int(float(val)) > 0:
                        return int(float(val))
                except:
                    pass
        
        # Gebe 0 zurueck, wenn Batterie ruht (bewirkt "-- verbleibend" im Dashboard)
        return 0

    def get_ac_status(self):
        val = self._lese_wert(self.dp_ac)
        return bool(val)

    def set_ac(self, zustand: bool):
        return self._schalte_wert(self.dp_ac, zustand)

    def get_12v_status(self):
        val = self._lese_wert(self.dp_12v)
        return bool(val)

    def set_12v(self, zustand: bool):
        return self._schalte_wert(self.dp_12v, zustand)

    def get_usb_status(self):
        val = self._lese_wert(self.dp_usb)
        return bool(val)

    def set_usb(self, zustand: bool):
        return self._schalte_wert(self.dp_usb, zustand)