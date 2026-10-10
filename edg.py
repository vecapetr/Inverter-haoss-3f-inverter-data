#!/usr/bin/env python3
"""
Čtení dat z HAN portu elektroměru (DLMS/COSEM)
Oblast: EG.D, elektroměr Kaifa MA309 apod.
Hardware: Raspberry Pi + USB-RS485 (/dev/ttyUSB0)
Parametry: 9600 8N1
"""

import serial
import binascii
from datetime import datetime

# ============ KONFIGURACE ============
PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
# OBIS kódy dle oficiálního schématu EG.D
TARGET_OBIS = {
    "1.8.2": "VT (Vysoký tarif)",
    "1.8.3": "NT (Nízký tarif)",
    "2.8.0": "Dodávka do sítě",
}
# =====================================


def extract_value_from_frame(frame, obis_bytes):
    """
    Najde v DLMS rámci zadaný OBIS a přečte za ním 4bajtovou hodnotu.
    """
    idx = frame.find(obis_bytes)
    if idx == -1:
        return None

    # Za OBIS (6 bajtů) obvykle následuje 4bajtové číslo (big-endian uint32)
    value_start = idx + 6

    if value_start + 4 > len(frame):
        return None

    value_bytes = frame[value_start:value_start + 4]
    value = int.from_bytes(value_bytes, byteorder='big')

    # Filtr nesmyslných hodnot (např. části hlavičky rámce)
    if value > 100_000_000:  # 100 000 MWh je nesmysl
        return None

    return value


def parse_dlms_frame(frame):
    """Projde rámec a vrátí slovník {OBIS: hodnota}"""
    results = {}

    # Bajtové vzory OBIS (A-B:C.D.E:FF)
    obis_patterns = {
        "1.8.2": bytes.fromhex("0108020000ff"),
        "1.8.3": bytes.fromhex("0108030000ff"),
        "2.8.0": bytes.fromhex("0208000000ff"),
    }

    for obis_str, pattern in obis_patterns.items():
        value = extract_value_from_frame(frame, pattern)

        # Zkusit i variantu bez posledního FF (některé elektroměry)
        if value is None:
            alt_pattern = pattern[:4]
            value = extract_value_from_frame(frame, alt_pattern)

        if value is not None:
            results[obis_str] = value

    return results


def read_frame(ser):
    """
    Přečte jeden kompletní HDLC rámec.
    Rámec začíná i končí bajtem 0x7E.
    """
    buffer = bytearray()
    start_found = False
    timeout_count = 0

    while timeout_count < 100:  # max ~10 s čekání
        byte = ser.read(1)
        if not byte:
            timeout_count += 1
            continue

        timeout_count = 0

        if byte == b'\x7e':
            if start_found:
                return bytes(buffer)  # konec rámce
            else:
                start_found = True
                buffer = bytearray()
        elif start_found:
            buffer.extend(byte)

    return None


def main():
    print(f"[{datetime.now()}] Otevírám {PORT} @ {BAUDRATE} 8N1...")

    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
    except serial.SerialException as e:
        print(f"CHYBA: Nelze otevřít port – {e}")
        print("Zkontroluj: existuje zařízení? Má uživatel právo? (sudo / dialout)")
        return

    print(f"[{datetime.now()}] Čekám na data z elektroměru (interval ~60 s)...")
    print("-" * 50)

    try:
        while True:
            frame = read_frame(ser)

            if frame is None or len(frame) < 10:
                continue

            data = parse_dlms_frame(frame)

            if data:
                print(f"\n[{datetime.now()}] Přijat rámec (délka: {len(frame)} B)")
                for obis, value in sorted(data.items()):
                    name = TARGET_OBIS.get(obis, obis)
                    # Elektroměr obvykle ukládá v Wh, převedeme na kWh
                    print(f"  {obis} {name}: {value / 1000.0:.3f} kWh")
            else:
                # Debug výpis, pokud se nepodařilo rozpoznat OBIS
                hex_preview = binascii.hexlify(frame[:80]).decode()
                print(f"[{datetime.now()}] Rámec nepřečten: {hex_preview}...")

    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Přerušeno uživatelem")
    finally:
        ser.close()
        print("Port uzavřen")


if __name__ == "__main__":
    main()
