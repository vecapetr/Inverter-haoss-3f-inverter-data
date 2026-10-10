#!/usr/bin/env python3
"""
EG.D HAN -> MQTT -> HA Discovery
Podporuje: energie (kWh), výkon (W), tarif, relé, odpojovač, timeprint
Kompatibilní s paho-mqtt >= 2.0 (Callback API v2)
"""
import sys
import time
import json
from datetime import datetime
from dataclasses import dataclass

import serial
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# ============ KONFIGURACE ============
PORT = "/dev/ttyUSB0"
BAUDRATE = 9600

MQTT_HOST = "192.168.1.22"
MQTT_PORT = 1883
MQTT_USER = "edg"
MQTT_PASS = "edg_1"

DEVICE_ID = "7d7f1d37359a485ca52ace13ee8d986c"
DEVICE_NAME = "EG.D Elektroměr"
DEVICE_MANUFACTURER = "EG.D"
DEVICE_MODEL = "HAN DLMS"

MQTT_PREFIX = "edg"
DISCOVERY_PREFIX = "homeassistant"

# ============ OBIS KONFIGURACE ============
OBIS_CONFIG = {
    # --- Energie (kWh) ---
    "1.8.0": {"key": "energy_import_kwh", "name": "EGD energie odběr celkem", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},
    "1.8.1": {"key": "energy_import_t1_kwh", "name": "EGD energie odběr T1", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},
    "1.8.2": {"key": "energy_import_t2_kwh", "name": "EGD energie odběr T2", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},
    "1.8.3": {"key": "energy_import_t3_kwh", "name": "EGD energie odběr T3", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},
    "1.8.4": {"key": "energy_import_t4_kwh", "name": "EGD energie odběr T4", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},
    "2.8.0": {"key": "energy_export_kwh", "name": "EGD energie dodávka celkem", "unit": "kWh", "scale": 0.001, "device_class": "energy", "state_class": "total_increasing"},

    # --- Výkon (W) ---
    "1.7.0": {"key": "power_import_w", "name": "EGD aktuální odběr", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "2.7.0": {"key": "power_export_w", "name": "EGD aktuální dodávka", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "21.7.0": {"key": "power_l1_w", "name": "EGD výkon L1", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "41.7.0": {"key": "power_l2_w", "name": "EGD výkon L2", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "61.7.0": {"key": "power_l3_w", "name": "EGD výkon L3", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "22.7.0": {"key": "power_export_l1_w", "name": "EGD dodávka L1", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "42.7.0": {"key": "power_export_l2_w", "name": "EGD dodávka L2", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "62.7.0": {"key": "power_export_l3_w", "name": "EGD dodávka L3", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},
    "17.0.0": {"key": "power_limiter_w", "name": "EGD hodnota omezovače", "unit": "W", "scale": 1, "device_class": "power", "state_class": "measurement"},

    # --- Tarif a stav (enum) ---
    "96.14.0": {"key": "tariff_code", "name": "EGD aktuální tarif kód", "unit": "", "scale": 1, "device_class": "", "state_class": ""},
    "96.13.0": {"key": "consumer_message", "name": "EGD zpráva zákazníkovi", "unit": "", "scale": 1, "device_class": "", "state_class": ""},
    "96.3.10": {"key": "disconnect_status", "name": "EGD odpojovač stav", "unit": "", "scale": 1, "device_class": "", "state_class": "", "enum_map": {0: "odpojeno", 1: "připojeno"}},

    # --- Relé ---
    "0-1:96.3.10.255": {"key": "relay_1_status", "name": "EGD relé 1 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},
    "0-2:96.3.10.255": {"key": "relay_2_status", "name": "EGD relé 2 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},
    "0-3:96.3.10.255": {"key": "relay_3_status", "name": "EGD relé 3 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},
    "0-4:96.3.10.255": {"key": "relay_4_status", "name": "EGD relé 4 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},
    "0-5:96.3.10.255": {"key": "relay_5_status", "name": "EGD relé 5 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},
    "0-6:96.3.10.255": {"key": "relay_6_status", "name": "EGD relé 6 stav", "enum_map": {0: "vypnuto", 1: "zapnuto"}},

    # --- Čas odeslání na MQTT (HH:MM) → timeprint ---
    "timeprint": {
        "key": "timeprint",
        "name": "EGD čas odeslání na MQTT",
        "unit": "",
        "scale": 1,
        "device_class": "",
        "state_class": "",
        "icon": "mdi:clock-check-outline",
        "is_timestamp": True,
    },
}
# ==========================================


@dataclass
class CosemObject:
    class_id: int
    logical_name: str
    full_obis: str
    attribute: int
    value: int


class CosemParser:
    def parse(self, data: bytes) -> list[CosemObject]:
        objects = []
        i = 0
        while i < len(data):
            if self._looks_like_register_value(data, i):
                class_id = int.from_bytes(data[i+2:i+4], "big")
                obis_raw = data[i+4:i+10]
                value = int.from_bytes(data[i+12:i+16], "big", signed=False)
                objects.append(CosemObject(
                    class_id=class_id,
                    logical_name=self._obis_short(obis_raw),
                    full_obis=self._obis_full(obis_raw),
                    attribute=2,
                    value=value,
                ))
                i += 16
                continue
            if self._looks_like_enum_value(data, i):
                class_id = int.from_bytes(data[i+2:i+4], "big")
                obis_raw = data[i+4:i+10]
                value = data[i+12]
                objects.append(CosemObject(
                    class_id=class_id,
                    logical_name=self._obis_short(obis_raw),
                    full_obis=self._obis_full(obis_raw),
                    attribute=3,
                    value=value,
                ))
                i += 13
                continue
            i += 1
        return objects

    def _looks_like_register_value(self, data: bytes, i: int) -> bool:
        return (
            i + 16 <= len(data)
            and data[i] == 0x02
            and data[i+1] == 0x02
            and int.from_bytes(data[i+2:i+4], "big") == 3
            and data[i+10] == 0x02
            and data[i+11] == 0x06
        )

    def _looks_like_enum_value(self, data: bytes, i: int) -> bool:
        if i + 13 > len(data):
            return False
        if data[i] != 0x02 or data[i+1] != 0x02:
            return False
        class_id = int.from_bytes(data[i+2:i+4], "big")
        if class_id not in (70, 71):
            return False
        return data[i+10] == 0x03 and data[i+11] == 0x16

    def _obis_short(self, raw: bytes) -> str:
        return f"{raw[2]}.{raw[3]}.{raw[4]}"

    def _obis_full(self, raw: bytes) -> str:
        return f"{raw[0]}-{raw[1]}:{raw[2]}.{raw[3]}.{raw[4]}.{raw[5]}"


def decode_objects(objects: list[CosemObject]) -> dict:
    """Dekóduje objekty podle OBIS_CONFIG (energie, výkon, enum)."""
    results = {}
    for obj in objects:
        mapping = OBIS_CONFIG.get(obj.full_obis) or OBIS_CONFIG.get(obj.logical_name)
        if not mapping:
            continue

        key = mapping["key"]
        value = obj.value

        if "enum_map" in mapping:
            enum_map = mapping["enum_map"]
            results[key] = {
                "name": mapping.get("name", key),
                "value": enum_map.get(value, str(value)),
                "is_enum": True,
                "unit": "",
                "obis": obj.logical_name,
            }
            continue

        scale = float(mapping.get("scale", 1))
        scaled_value = round(value * scale, 3)

        results[key] = {
            "name": mapping.get("name", key),
            "value": scaled_value,
            "is_enum": False,
            "unit": mapping.get("unit", ""),
            "device_class": mapping.get("device_class", ""),
            "state_class": mapping.get("state_class", ""),
            "obis": obj.logical_name,
        }

    return results


# ============ MQTT ============
def mqtt_connect() -> mqtt.Client:
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=DEVICE_ID,
    )
    client.username_pw_set(MQTT_USER, MQTT_PASS)

    def on_connect(c, userdata, flags, reason_code, properties=None):
        if reason_code == 0:
            print(f"✅ [{ts()}] MQTT připojeno k {MQTT_HOST} (client_id={DEVICE_ID})")
        else:
            print(f"❌ [{ts()}] MQTT chyba: rc={reason_code}")

    def on_disconnect(c, userdata, disconnect_flags, reason_code, properties=None):
        if reason_code != 0:
            print(f"⚠️  [{ts()}] MQTT odpojeno (rc={reason_code})")

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    time.sleep(0.5)
    return client


def publish_discovery(client: mqtt.Client):
    """Publikuje HA Discovery pro všechny OBIS z OBIS_CONFIG (s časem)."""
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    device_info = {
        "identifiers": [DEVICE_ID],
        "name": DEVICE_NAME,
        "manufacturer": DEVICE_MANUFACTURER,
        "model": DEVICE_MODEL,
    }

    print(f"  [{ts()}] Začínám Discovery ({len(OBIS_CONFIG)} OBIS)...")

    for obis, cfg in OBIS_CONFIG.items():
        key = cfg.get("key")
        if not key:
            continue

        unique_id = f"{DEVICE_ID}_{key}"
        state_topic = f"{MQTT_PREFIX}/{DEVICE_ID}/{key}/state"
        config_topic = f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/{key}/config"

        payload = {
            "name": cfg.get("name", key),
            "unique_id": unique_id,
            "state_topic": state_topic,
            "device": device_info,
            "availability_topic": f"{MQTT_PREFIX}/{DEVICE_ID}/status",
            "payload_available": "online",
            "payload_not_available": "offline",
        }

        payload["icon"] = cfg.get("icon", "mdi:flash")

        if "enum_map" in cfg:
            payload["icon"] = "mdi:information-outline"
        elif cfg.get("is_timestamp"):
            payload["icon"] = "mdi:clock-outline"
        else:
            unit = cfg.get("unit", "")
            if unit:
                payload["unit_of_measurement"] = unit
            if cfg.get("device_class"):
                payload["device_class"] = cfg["device_class"]
            if cfg.get("state_class"):
                payload["state_class"] = cfg["state_class"]

        client.publish(config_topic, json.dumps(payload), retain=True)
        print(f"  [{ts()}] 📡 Discovery: {key:30} → {config_topic}")

    client.publish(f"{MQTT_PREFIX}/{DEVICE_ID}/status", "online", retain=True)
    print(f"  [{ts()}] 📡 Status: {MQTT_PREFIX}/{DEVICE_ID}/status = online")
    print(f"  [{ts()}] ✅ Discovery publikováno pro {len(OBIS_CONFIG)} OBIS")


def publish_values(client: mqtt.Client, data: dict):
    """Publikuje hodnoty do MQTT s časem odeslání (timeprint)."""
    ts = lambda: datetime.now().strftime("%H:%M:%S")

    publish_time_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    publish_time_hhmm = datetime.now().strftime("%H:%M")

    print(f"  [{ts()}] Publikuji {len(data)} hodnot...")

    for key, info in data.items():
        topic = f"{MQTT_PREFIX}/{DEVICE_ID}/{key}/state"
        client.publish(topic, str(info["value"]), retain=True)
        print(f"  [{ts()}] 📤 {key:30} = {info['value']} → {topic}")

    # Čas odeslání na MQTT → entita "timeprint"
    time_topic = f"{MQTT_PREFIX}/{DEVICE_ID}/timeprint/state"
    client.publish(time_topic, publish_time_hhmm, retain=True)
    print(f"  [{ts()}] 📤 {'timeprint':30} = {publish_time_hhmm} → {time_topic}")

    payload = {
        "timeprint": publish_time_full,
        "values": {key: info["value"] for key, info in data.items()},
    }
    client.publish(
        f"{MQTT_PREFIX}/{DEVICE_ID}/all",
        json.dumps(payload),
        retain=True,
    )
    print(f"  [{ts()}] 📤 Souhrnný JSON → {MQTT_PREFIX}/{DEVICE_ID}/all")


# ============ SERIAL ============
def read_frame(ser, timeout=70):
    start = time.time()
    buffer = bytearray()
    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            buffer.extend(chunk)
            time.sleep(0.3)
            while ser.in_waiting:
                buffer.extend(ser.read(4096))
            if len(buffer) > 100:
                return bytes(buffer)
    return bytes(buffer) if buffer else None


# ============ REŽIMY ============
def run_discovery_and_exit():
    """Publikuje Discovery + hodnoty a skončí. Vše s časovou značkou."""
    ts = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"🔧 Režim: DISCOVERY (jednorázově) – {ts()}")
    print(f"Port: {PORT} @ {BAUDRATE} 8N1")
    print(f"MQTT: {MQTT_HOST} (user: {MQTT_USER})")
    print(f"MQTT prefix: {MQTT_PREFIX}")
    print()

    print(f"🔌 Připojuji MQTT... [{ts()}]")
    client = mqtt_connect()
    print(f"✅ MQTT připraveno [{ts()}]")
    print()

    print(f"📡 Publikuji HA Discovery... [{ts()}]")
    publish_discovery(client)
    print(f"✅ Discovery dokončeno [{ts()}]")
    print()

    parser = CosemParser()

    print(f"⏳ Čekám na první rámec z elektroměru (~60 s)... [{ts()}]")
    try:
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
            frame = read_frame(ser, timeout=90)
            if not frame:
                print(f"❌ Žádná data [{ts()}]")
                return

            objects = parser.parse(frame)
            data = decode_objects(objects)

            now_str = ts()
            print(f"✅ Přijat rámec: {len(frame)} bajtů, objektů: {len(objects)} [{now_str}]")

            if data:
                print(f"📊 Hodnoty [{now_str}]:")
                for key, info in sorted(data.items()):
                    unit = info.get("unit", "")
                    print(f"   [{now_str}] {key:30} = {info['value']} {unit}")

                print(f"📤 Publikuji hodnoty do MQTT... [{ts()}]")
                publish_values(client, data)
                print(f"✅ Publikováno [{ts()}]")
            else:
                print(f"⚠️  Žádné cílové OBIS [{now_str}]")
                if objects:
                    for obj in objects[:15]:
                        print(f"   [{now_str}] {obj.logical_name} = {obj.value}")

    finally:
        print(f"🔌 Odpojuji MQTT... [{ts()}]")
        client.loop_stop()
        client.disconnect()
        print(f"🔚 Discovery režim dokončen [{ts()}]")


def run_forever():
    ts = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"🔁 Režim: CONTINUOUS – {ts()}")
    print(f"Port: {PORT} @ {BAUDRATE} 8N1")
    print(f"MQTT: {MQTT_HOST} (user: {MQTT_USER})")
    print(f"MQTT prefix: {MQTT_PREFIX}")
    print()

    print(f"🔌 Připojuji MQTT... [{ts()}]")
    client = mqtt_connect()
    print(f"✅ MQTT připraveno [{ts()}]")
    print()

    print(f"📡 Publikuji HA Discovery... [{ts()}]")
    publish_discovery(client)
    print(f"✅ Discovery dokončeno [{ts()}]")
    print()

    parser = CosemParser()

    try:
        with serial.Serial(PORT, BAUDRATE, timeout=1) as ser:
            while True:
                frame = read_frame(ser)
                if not frame:
                    print(f"[{ts()}] ⏳ Timeout – čekám na data...")
                    continue

                objects = parser.parse(frame)
                data = decode_objects(objects)

                now_str = ts()
                print(f"\n[{now_str}] 📨 Rámec: {len(frame)} bajtů, objektů: {len(objects)}")

                if data:
                    for key, info in sorted(data.items()):
                        unit = info.get("unit", "")
                        print(f"   [{now_str}] {key:30} = {info['value']} {unit}")
                    publish_values(client, data)
                    print(f"   [{now_str}] ✅ Publikováno")
                else:
                    print(f"   [{now_str}] ⚠️  Žádné cílové OBIS")

    except KeyboardInterrupt:
        print(f"\n[{ts()}] 🛑 Přerušeno uživatelem")
    finally:
        client.publish(f"{MQTT_PREFIX}/{DEVICE_ID}/status", "offline", retain=True)
        print(f"[{ts()}] 📡 Status: offline")
        client.loop_stop()
        client.disconnect()


def main():
    if "--discovery" in sys.argv:
        run_discovery_and_exit()
    else:
        run_forever()


if __name__ == "__main__":
    main()

