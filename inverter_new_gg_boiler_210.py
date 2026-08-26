#!/usr/bin/env python3
"""
DAEMON PRO GRAND GLOW NEW S PODPOROU ZÁPISU OUTPUT PRIORITY A CHARGE PRIORITY
A AUTOMATICKOU SYNCHRONIZACÍ ČASU
"""

import time
import sys
import json
import select
import random
import uuid
import minimalmodbus
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import datetime

# ==========================================
# --- 1. LADĚNÍ A MULTI-INVERTOR ---
# ==========================================
DEBUG_LEVEL = 2
POCET_INVERTORU = 3

# --- PUBLIKOVÁNÍ BOJLERU ---
boiler_publish_start = "yes"

# --- OCHRANA PŘED PŘETÍŽENÍM ---
MAX_OUT_POWER_CRIT = 3500   # W - OKAMŽITÉ VYPNUTÍ

# --- KONFIGURACE BOJLERU ---
boiler_battery_start_voltage = 53.0
boiler_init_current = 3.5
boiler_const = 35

# --- REGULACE BOJLERU - JEDNOU ZA MINUTU ---
BOILER_REGULACE_INTERVAL = 60  # sekund

# --- KONTROLA ČASU - KAŽDÝCH 10 MINUT ---
MAX_CASOVA_ODYCHYLKA = 600  # 10 minut v sekundách
KONTROLA_CASU_INTERVAL = 600  # 10 minut v sekundách

# Mapování sériových portů a Modbus ID pro jednotlivé střídače
KONFIGURACE_STRIDACU = {
    1: {"port": "/dev/ttyUSB0", "slave_id": 1},
    2: {"port": "/dev/ttyUSB1", "slave_id": 1},  
    3: {"port": "/dev/ttyUSB2", "slave_id": 1}   
}

# --- 2. MQTT MOSQUITTO NASTAVENÍ ---
MQTT_username = 'inverter'
MQTT_password = 'Grand_Glow_03'
broker = "192.168.1.22"
MQTT_port = 1883

state_topic = "homeassistant/sensor/gg_new/state"
boiler_topic = "homeassistant/boiler/write"

LISTEN_CLIENT_ID = f"gg_boiler_listener_{uuid.uuid4().hex[:10]}"

# --- 3. KONFIGURACE VYTĚŽOVÁNÍ BOJLERU ---
gg_automatika_boileru = False
vynutit_okamzite_mereni = False

# ==========================================
# BOILER REGULACE - KAŽDÝ STŘÍDAČ MÁ VLASTNÍ HODNOTY
# ==========================================
boiler_power_nr = {1: 0, 2: 0, 3: 0}
boiler_power_rest = {1: 0, 2: 0, 3: 0}
boiler_power_rest1 = 0
boiler_power_rest2 = 0
boiler_power_rest3 = 0
boiler_power_rest_count = {1: 0, 2: 0, 3: 0}

dec_boiler1 = 0
dec_boiler2 = 0
dec_boiler3 = 0

minuly_proud = {1: 0, 2: 0, 3: 0}

# --- 4. FIXNÍ PŘEKLADOVÉ TABULKY HARDWARU ---
STAVY_OPERACE = {3: "UTILITY", 4: "BATTERY", 5: "UNKNOWN (5)"}

BATTERY_TYPE = {
    0: "Lead-acid",
    1: "Flooded",
    2: "NMC (Ternary Lithium)",
    3: "LiFePO4",
    4: "User-defined"
}

PRIORITA_VYSTUPU = {
    0: "UTI-PV-BAT",
    1: "PV-UTI-BAT",
    2: "PV-BAT-UTI",
    3: "GEN"
}

OUTPUT_PRIORITY_OPTIONS = {
    0: "UTI-PV-BAT",
    1: "PV-UTI-BAT",
    2: "PV-BAT-UTI",
    3: "GEN"
}

OUTPUT_PRIORITY_REVERSE = {
    "UTI-PV-BAT": 0,
    "PV-UTI-BAT": 1,
    "PV-BAT-UTI": 2,
    "GEN": 3
}

DEFAULT_OUTPUT_PRIORITY = "PV-BAT-UTI"
DEFAULT_CHARGE_PRIORITY = "Only PV"

PRIORITA_NABIJENI = {
    0: "PV/UTI",
    1: "Only PV",
    2: "PV First"
}

CHARGE_PRIORITY_REVERSE = {
    "PV/UTI": 0,
    "Only PV": 1,
    "PV First": 2
}

CHARGE_PRIORITY_OPTIONS = ["PV/UTI", "Only PV", "PV First"]

STAV_STROJE = {
    0: "Power on",
    1: "Initialization",
    2: "Standby mode",
    3: "Grid mode",
    4: "PV mode",
    5: "Battery mode",
    6: "Generator mode",
    7: "Fault mode",
    8: "Shutdown mode",
    9: "Factory mode",
    10: "Upgrade mode"
}

NABIJECI_STATUS = {
    0: "Stop Charging",
    1: "Const Volt/Const Curr",
    2: "Floating",
    3: "Equalization"
}

# --- 5. INICIALIZACE VŠECH MODBUS PORTŮ ---
instrumenty = {}

def inicializuj_instrumenty():
    global instrumenty
    instrumenty = {}
    print("🤖 Inicializuji připojení k solárním střídačům...")
    for i in range(1, POCET_INVERTORU + 1):
        cfg = KONFIGURACE_STRIDACU[i]
        try:
            instrument = minimalmodbus.Instrument(cfg["port"], cfg["slave_id"])
            instrument.serial.baudrate = 9600        
            instrument.serial.bytesize = 8
            instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
            instrument.serial.stopbits = 1
            instrument.serial.timeout = 2.0
            instrument.mode = minimalmodbus.MODE_RTU 
            instrumenty[i] = instrument
            print(f"  ➔ Invertor {i} úspěšně spojen na portu {cfg['port']}")
        except Exception as e:
            print(f"❌ KRIZOVÁ CHYBA: Nelze otevřít port pro Invertor {i}: {e}")
            sys.exit(1)

inicializuj_instrumenty()

# --- 6. FUNKCE PRO ČTENÍ A ZÁPIS DATA A ČASU ---
def precti_cas_stridace(inv_id, inst):
    try:
        year_ro = inst.read_register(864, functioncode=3)
        time.sleep(0.1)
        month_ro = inst.read_register(865, functioncode=3)
        time.sleep(0.1)
        day_ro = inst.read_register(866, functioncode=3)
        time.sleep(0.1)
        hour_ro = inst.read_register(867, functioncode=3)
        time.sleep(0.1)
        minute_ro = inst.read_register(868, functioncode=3)
        time.sleep(0.1)
        second_ro = inst.read_register(869, functioncode=3)
        time.sleep(0.1)
        
        return {
            "year": year_ro,
            "month": month_ro,
            "day": day_ro,
            "hour": hour_ro,
            "minute": minute_ro,
            "second": second_ro
        }
    except Exception as e:
        if DEBUG_LEVEL >= 2:
            print(f"❌ Chyba při čtení data a času ze střídače {inv_id}: {e}")
        return None

def zobraz_cas_stridace(inv_id, cas):
    if cas:
        print(f"  📅 Střídač {inv_id} - Datum/Čas: {cas['year']:04d}-{cas['month']:02d}-{cas['day']:02d} {cas['hour']:02d}:{cas['minute']:02d}:{cas['second']:02d}")

def synchronizuj_cas(inv_id, inst):
    try:
        now = datetime.datetime.now()
        
        rok = now.year % 100
        mesic = now.month
        den = now.day
        hodina = now.hour
        minuta = now.minute
        sekunda = now.second
        
        if DEBUG_LEVEL >= 2:
            print(f"  ⏰ Synchronizuji čas na střídači {inv_id}: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        inst.write_register(4105, 0x0001, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16692, sekunda, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16693, minuta, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16694, hodina, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16695, den, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16696, mesic, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(16697, rok, functioncode=0x10)
        time.sleep(0.2)
        
        inst.write_register(4105, 0x0000, functioncode=0x10)
        time.sleep(0.2)
        
        if DEBUG_LEVEL >= 2:
            print(f"  ✅ Synchronizace času na střídači {inv_id} dokončena!")
        
        return True
        
    except Exception as e:
        print(f"❌ Chyba při synchronizaci času na střídači {inv_id}: {e}")
        return False

def zkontroluj_a_synchronizuj_cas(inv_id, inst):
    try:
        cas = precti_cas_stridace(inv_id, inst)
        if not cas:
            return False
        
        now = datetime.datetime.now()
        
        try:
            cas_stridace = datetime.datetime(
                year=2000 + cas['year'],
                month=cas['month'],
                day=cas['day'],
                hour=cas['hour'],
                minute=cas['minute'],
                second=cas['second']
            )
        except ValueError:
            if DEBUG_LEVEL >= 2:
                print(f"  ⚠️ [STŘÍDAČ {inv_id}] Neplatné datum na střídači - provádím synchronizaci")
            synchronizuj_cas(inv_id, inst)
            return True
        
        rozdil = abs((now - cas_stridace).total_seconds())
        
        if rozdil > MAX_CASOVA_ODYCHYLKA:
            if DEBUG_LEVEL >= 2:
                print(f"  ⚠️ [STŘÍDAČ {inv_id}] Časová odchylka: {rozdil/60:.1f} minut - provádím synchronizaci")
            synchronizuj_cas(inv_id, inst)
            return True
        else:
            if DEBUG_LEVEL >= 2:
                print(f"  ✅ [STŘÍDAČ {inv_id}] Čas v pořádku (odchylka {rozdil/60:.1f} min)")
            return False
            
    except Exception as e:
        print(f"  ❌ [STŘÍDAČ {inv_id}] Chyba při kontrole času: {e}")
        return False

# --- 7. FUNKCE PRO ZÁPIS PRIORIT ---
def zapis_output_priority(inv_id, hodnota):
    global instrumenty
    
    if inv_id not in instrumenty:
        print(f"❌ Střídač {inv_id} neexistuje")
        return False
    
    inst = instrumenty[inv_id]
    
    if hodnota not in [0, 1, 2, 3]:
        print(f"❌ Neplatná hodnota Output Priority: {hodnota}")
        return False
    
    try:
        print(f"   🔑 Admin přihlášení na střídač {inv_id}...")
        inst.write_register(0x100A, 0x0001, functioncode=0x10)
        time.sleep(0.3)
        inst.write_register(0x100B, 0x0010, functioncode=0x10)
        time.sleep(0.3)
        inst.write_register(0x100C, 0x1C1A, functioncode=0x10)
        time.sleep(0.3)
        print(f"   ✅ Admin přihlášen")
        
        print(f"   ✏️  Zapisuji Output Priority: {hodnota} ({OUTPUT_PRIORITY_OPTIONS.get(hodnota, 'UNKNOWN')})")
        inst.write_register(16642, hodnota, functioncode=0x10)
        time.sleep(0.5)
        print(f"   ✅ Zápis proveden")
        
        print(f"   🔍 Ověřuji zápis...")
        overeni = inst.read_register(322, functioncode=3)
        time.sleep(0.2)
        
        if overeni == hodnota:
            print(f"   ✅ Ověření OK: {PRIORITA_VYSTUPU.get(overeni, 'UNKNOWN')}")
        else:
            print(f"   ⚠️ Ověření selhalo: zapsáno {hodnota}, přečteno {overeni}")
            return False
        
        print(f"   🔑 Odhlašuji Admin...")
        inst.write_register(0x100A, 0x0000, functioncode=0x10)
        time.sleep(0.3)
        print(f"   ✅ Admin odhlášen")
        
        return True
    except Exception as e:
        print(f"   ❌ Chyba při zápisu na střídač {inv_id}: {e}")
        return False

def zapis_charge_priority(inv_id, hodnota):
    global instrumenty
    
    if inv_id not in instrumenty:
        print(f"❌ Střídač {inv_id} neexistuje")
        return False
    
    inst = instrumenty[inv_id]
    
    if hodnota not in [0, 1, 2]:
        print(f"❌ Neplatná hodnota Charge Priority: {hodnota}")
        return False
    
    try:
        print(f"   🔑 Admin přihlášení na střídač {inv_id}...")
        inst.write_register(0x100A, 0x0001, functioncode=0x10)
        time.sleep(0.3)
        inst.write_register(0x100B, 0x0010, functioncode=0x10)
        time.sleep(0.3)
        inst.write_register(0x100C, 0x1C1A, functioncode=0x10)
        time.sleep(0.3)
        print(f"   ✅ Admin přihlášen")
        
        charge_text = {0: "PV/UTI", 1: "Only PV", 2: "PV First"}.get(hodnota, "UNKNOWN")
        print(f"   ✏️  Zapisuji Charge Priority: {hodnota} ({charge_text})")
        inst.write_register(16644, hodnota, functioncode=0x10)
        time.sleep(0.5)
        print(f"   ✅ Zápis proveden")
        
        print(f"   🔍 Ověřuji zápis...")
        overeni = inst.read_register(323, functioncode=3)
        time.sleep(0.2)
        
        if overeni == hodnota:
            print(f"   ✅ Ověření OK: {PRIORITA_NABIJENI.get(overeni, 'UNKNOWN')}")
        else:
            print(f"   ⚠️ Ověření selhalo: zapsáno {hodnota}, přečteno {overeni}")
            return False
        
        print(f"   🔑 Odhlašuji Admin...")
        inst.write_register(0x100A, 0x0000, functioncode=0x10)
        time.sleep(0.3)
        print(f"   ✅ Admin odhlášen")
        
        return True
    except Exception as e:
        print(f"   ❌ Chyba při zápisu na střídač {inv_id}: {e}")
        return False

# ==========================================
# FUNKCE PRO KONTROLU PRIORIT (POUZE KONTROLA, ZÁPIS JEN PŘI POTŘEBĚ)
# ==========================================

def kontrola_a_nastav_priority():
    print("\n" + "=" * 60)
    print("🔍 KONTROLA PRIORIT NA VŠECHNY STŘÍDAČE")
    print("=" * 60)
    
    output_hodnota = OUTPUT_PRIORITY_REVERSE["PV-BAT-UTI"]
    charge_hodnota = CHARGE_PRIORITY_REVERSE["Only PV"]
    
    vsechny_ok = True
    je_treba_zapis = False
    
    for inv_id, inst in instrumenty.items():
        print(f"\n📝 Kontroluji střídač {inv_id}...")
        
        try:
            op_raw = inst.read_register(322, functioncode=3)
            time.sleep(0.2)
            cp_raw = inst.read_register(323, functioncode=3)
            time.sleep(0.2)
            
            op_text = PRIORITA_VYSTUPU.get(op_raw, f"UNKNOWN({op_raw})")
            cp_text = PRIORITA_NABIJENI.get(cp_raw, f"UNKNOWN({cp_raw})")
            
            print(f"   Aktuální: Output={op_text}, Charge={cp_text}")
            
            if op_raw != output_hodnota:
                print(f"   ⚠️ Output Priority není PV-BAT-UTI ({op_text}) - nastavuji...")
                if zapis_output_priority(inv_id, output_hodnota):
                    print(f"   ✅ Output Priority nastavena na PV-BAT-UTI")
                    je_treba_zapis = True
                else:
                    print(f"   ❌ Output Priority se nepodařilo nastavit!")
                    vsechny_ok = False
            else:
                print(f"   ✅ Output Priority OK: PV-BAT-UTI")
            
            time.sleep(0.5)
            
            if cp_raw != charge_hodnota:
                print(f"   ⚠️ Charge Priority není Only PV ({cp_text}) - nastavuji...")
                if zapis_charge_priority(inv_id, charge_hodnota):
                    print(f"   ✅ Charge Priority nastavena na Only PV")
                    je_treba_zapis = True
                else:
                    print(f"   ❌ Charge Priority se nepodařilo nastavit!")
                    vsechny_ok = False
            else:
                print(f"   ✅ Charge Priority OK: Only PV")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"   ❌ Chyba při kontrole střídače {inv_id}: {e}")
            vsechny_ok = False
    
    print("\n" + "=" * 60)
    if vsechny_ok and not je_treba_zapis:
        print("✅ VŠECHNY priority jsou správně nastaveny! (žádný zápis nebyl potřeba)")
    elif vsechny_ok and je_treba_zapis:
        print("✅ VŠECHNY priority byly opraveny a jsou nyní správně!")
    else:
        print("⚠️ NĚKTERÉ priority se nepodařilo nastavit!")
    print("=" * 60)

# ==========================================
# SPOLEČNÉ FUNKCE PRO VŠECHNY STŘÍDAČE
# ==========================================

def zapis_output_priority_vsechny(hodnota):
    global instrumenty
    
    if hodnota not in [0, 1, 2, 3]:
        print(f"❌ Neplatná hodnota Output Priority: {hodnota}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🔄 ZAPISUJI OUTPUT PRIORITY NA VŠECHNY STŘÍDAČE: {OUTPUT_PRIORITY_OPTIONS.get(hodnota, 'UNKNOWN')}")
    print(f"{'='*60}")
    
    uspech = True
    for inv_id in instrumenty.keys():
        print(f"\n{'='*40}")
        print(f"📝 Zapisuji na střídač {inv_id}")
        print(f"{'='*40}")
        
        if not zapis_output_priority(inv_id, hodnota):
            uspech = False
            print(f"❌ Chyba na střídači {inv_id}")
        
        time.sleep(0.5)
    
    if uspech:
        print(f"\n✅ VŠECHNY střídače nastaveny na {OUTPUT_PRIORITY_OPTIONS.get(hodnota, 'UNKNOWN')}")
    else:
        print(f"\n⚠️ NĚKTERÉ střídače se nepodařilo nastavit!")
    
    return uspech

def zapis_charge_priority_vsechny(hodnota):
    global instrumenty
    
    charge_text = {0: "PV/UTI", 1: "Only PV", 2: "PV First"}.get(hodnota, "UNKNOWN")
    
    if hodnota not in [0, 1, 2]:
        print(f"❌ Neplatná hodnota Charge Priority: {hodnota}")
        return False
    
    print(f"\n{'='*60}")
    print(f"🔄 ZAPISUJI CHARGE PRIORITY NA VŠECHNY STŘÍDAČE: {charge_text}")
    print(f"{'='*60}")
    
    uspech = True
    for inv_id in instrumenty.keys():
        print(f"\n{'='*40}")
        print(f"📝 Zapisuji na střídač {inv_id}")
        print(f"{'='*40}")
        
        if not zapis_charge_priority(inv_id, hodnota):
            uspech = False
            print(f"❌ Chyba na střídači {inv_id}")
        
        time.sleep(0.5)
    
    if uspech:
        print(f"\n✅ VŠECHNY střídače nastaveny na {charge_text}")
    else:
        print(f"\n⚠️ NĚKTERÉ střídače se nepodařilo nastavit!")
    
    return uspech

# ==========================================
# BOILER PUBLIKOVÁNÍ NA MQTT
# ==========================================

def publikuj_boiler_mqtt(inv_id, drive_hodnota):
    auth_dict = {"username": MQTT_username, "password": MQTT_password}
    
    topic = f"zigbee2mqtt/boiler_power_drive_{inv_id}/set"
    
    if drive_hodnota < 0:
        drive_hodnota = 0
    elif drive_hodnota > 255:
        drive_hodnota = 255
    
    payload = {
        "state": "ON" if drive_hodnota > 0 else "OFF",
        "brightness": drive_hodnota
    }
    
    try:
        publish.single(topic, payload=json.dumps(payload), hostname=broker, port=MQTT_port, auth=auth_dict, retain=False)
        if DEBUG_LEVEL >= 2:
            print(f"  📤 [PUBLISH BOJLER {inv_id}] -> Topic: {topic}, Drive: {drive_hodnota}/255, State: {payload['state']}")
        return True
    except Exception as e:
        print(f"  ❌ [PUBLISH BOJLER {inv_id}] Chyba při publikování na MQTT: {e}")
        return False

# ==========================================
# BOILER REGULACE - DVOUFÁZOVÁ LOGIKA S DYNAMICKÝM BULK NAPĚTÍM
# ==========================================

def rizeni_vytazovani_boileru(inv_id, battery_current, out_power, avg_battery_voltage, all_in_battery_mode, pv_power, bulk_voltage):
    """
    Regulace boileru - dvě fáze:
    1. Nabíjení pod Bulk napětí - udržuje nabíjecí proud na 3.5A (PŮVODNÍ LOGIKA)
    2. Nad Bulk napětím - udržuje výkon na úrovni PV výkonu (NOVÁ LOGIKA)
    
    bulk_voltage: načteno z registru 16650 (Constant Voltage Point)
    """
    global boiler_power_rest, boiler_power_nr, gg_automatika_boileru
    global boiler_power_rest1, boiler_power_rest2, boiler_power_rest3
    global boiler_power_rest_count, dec_boiler1, dec_boiler2, dec_boiler3
    global minuly_proud
    
    # ==========================================
    # KONTROLA - je automatika zapnutá?
    # ==========================================
    if not gg_automatika_boileru:
        return

    # ==========================================
    # KONTROLA - všechny 3 musí být v BATTERY
    # ==========================================
    if not all_in_battery_mode:
        vynuluj_interni_fazi(inv_id)
        if boiler_publish_start.lower() == "yes":
            publikuj_boiler_mqtt(inv_id, 0)
        if DEBUG_LEVEL >= 2:
            print(f"  🔋 [STŘÍDAČ {inv_id}] nejsou všechny v BATTERY - boiler vypnut")
        return

    # ==========================================
    # KONTROLA NAPĚTÍ - průměr musí být nad 53V
    # ==========================================
    if avg_battery_voltage < boiler_battery_start_voltage:
        vynuluj_interni_fazi(inv_id)
        if boiler_publish_start.lower() == "yes":
            publikuj_boiler_mqtt(inv_id, 0)
        if DEBUG_LEVEL >= 2:
            print(f"  🔋 [STŘÍDAČ {inv_id}] napětí {avg_battery_voltage:.1f}V < {boiler_battery_start_voltage}V - boiler vypnut")
        return

    # ==========================================
    # KONTROLA PŘETÍŽENÍ - out_power
    # ==========================================
    if out_power > MAX_OUT_POWER_CRIT:
        vynuluj_interni_fazi(inv_id)
        if boiler_publish_start.lower() == "yes":
            publikuj_boiler_mqtt(inv_id, 0)
        if DEBUG_LEVEL >= 1:
            print(f"  🛑🛑🛑 [STŘÍDAČ {inv_id}] KRITICKÉ PŘETÍŽENÍ! out_power={out_power}W → BOJLER STOP!")
        return

    # ==========================================
    # NAČTENÍ HODNOT PRO TENTO STŘÍDAČ
    # ==========================================
    minuly_rest = boiler_power_rest[inv_id]
    minuly_proud_hodnota = minuly_proud[inv_id]
    
    if inv_id == 1:
        dec_boiler = dec_boiler1
    elif inv_id == 2:
        dec_boiler = dec_boiler2
    elif inv_id == 3:
        dec_boiler = dec_boiler3

    # ==========================================
    # ROZHODNUTÍ - KTERÝ REŽIM?
    # ==========================================
    # Bulk napětí načtené ze střídače (registr 16650)
    if bulk_voltage is None or bulk_voltage == 0:
        BULK_VOLTAGE = 57.0
        if DEBUG_LEVEL >= 2:
            print(f"  ⚠️ [STŘÍDAČ {inv_id}] Bulk napětí nenalezeno, použito výchozí: 57.0V")
    else:
        BULK_VOLTAGE = bulk_voltage
    
    # ==========================================
    # SCÉNÁŘ 1: Pod Bulk napětím - PŮVODNÍ LOGIKA
    # ==========================================
    if avg_battery_voltage < BULK_VOLTAGE:
        if DEBUG_LEVEL >= 2:
            print(f"  📊 [STŘÍDAČ {inv_id}] SCÉNÁŘ 1 (PROUD): {avg_battery_voltage:.1f}V < {BULK_VOLTAGE:.1f}V")
        
        # Kontrola proudu - pokud < 3.5A → NETOPÍME
        if battery_current < boiler_init_current:
            vynuluj_interni_fazi(inv_id)
            if boiler_publish_start.lower() == "yes":
                publikuj_boiler_mqtt(inv_id, 0)
            if DEBUG_LEVEL >= 2:
                if battery_current == 0:
                    print(f"  💤 [STŘÍDAČ {inv_id}] DISCHARGING nebo STOP - boiler vypnut")
                else:
                    print(f"  💤 [STŘÍDAČ {inv_id}] proud {battery_current:.1f}A < {boiler_init_current}A - boiler vypnut")
            return

        # PRVNÍ SPUŠTĚNÍ (rest == 0)
        if minuly_rest == 0:
            boiler_power_rest_count[inv_id] += 1
            
            rozdil = battery_current - boiler_init_current
            if rozdil < 0:
                rozdil = 0
            
            boiler_power_nr[inv_id] = rozdil
            
            aktualni_power_drive = int(boiler_const * boiler_power_nr[inv_id]) + 0
            
            if aktualni_power_drive > 130:
                aktualni_power_drive = 130
            
            if aktualni_power_drive < 0:
                aktualni_power_drive = 0
            if aktualni_power_drive > 255:
                aktualni_power_drive = 255
            
            boiler_power_rest[inv_id] = rozdil
            minuly_proud[inv_id] = battery_current
            
            if DEBUG_LEVEL >= 2:
                print(f"  🚀 [STŘÍDAČ {inv_id}] PRVNÍ SPUŠTĚNÍ: proud={battery_current:.1f}A, drive={aktualni_power_drive}")

        # BĚŽNÝ CHOD (rest > 0)
        else:
            boiler_power_rest_count[inv_id] += 1
            
            boiler_power_nr[inv_id] = battery_current + minuly_rest
            
            if boiler_power_nr[inv_id] >= 3.5:
                boiler_power_nr[inv_id] = 3.5
            
            # Regulace dec_boiler (+2/-2)
            if battery_current >= minuly_proud_hodnota:
                dec_boiler = dec_boiler + 2
                if dec_boiler > 255:
                    dec_boiler = 255
            else:
                dec_boiler = dec_boiler - 2
                if dec_boiler < 0:
                    dec_boiler = 0
            
            aktualni_power_drive = int(boiler_const * boiler_power_nr[inv_id]) + dec_boiler
            
            if aktualni_power_drive < 0:
                aktualni_power_drive = 0
            if aktualni_power_drive > 255:
                aktualni_power_drive = 255
            
            boiler_power_rest[inv_id] = boiler_power_nr[inv_id]
            minuly_proud[inv_id] = battery_current

        # ==========================================
        # KONTROLA COUNTERU - POUZE VE SCÉNÁŘI 1 (vynulování po ~3 hodinách)
        # ==========================================
        if boiler_power_rest_count[inv_id] > 180:
            if DEBUG_LEVEL >= 2:
                print(f"  🔄 [STŘÍDAČ {inv_id}] RESET po {boiler_power_rest_count[inv_id]} cyklech (~3 hodiny)")
            vynuluj_interni_fazi(inv_id)
            if boiler_publish_start.lower() == "yes":
                publikuj_boiler_mqtt(inv_id, 0)
            return

    # ==========================================
    # SCÉNÁŘ 2: Nad Bulk napětím - NOVÁ LOGIKA (PV regulace)
    # ==========================================
    else:
        if DEBUG_LEVEL >= 2:
            print(f"  📊 [STŘÍDAČ {inv_id}] SCÉNÁŘ 2 (PV): {avg_battery_voltage:.1f}V >= {BULK_VOLTAGE:.1f}V")
        
        # ==========================================
        # PRVNÍ VSTUP DO SCÉNÁŘE 2 - nastavíme drive na 255
        # ==========================================
        if minuly_rest == 0:
            if DEBUG_LEVEL >= 2:
                print(f"  🚀 [STŘÍDAČ {inv_id}] PŘECHOD DO PV REŽIMU - drive=255")
            
            boiler_power_rest[inv_id] = 1  # označení, že jsme v PV režimu
            boiler_power_nr[inv_id] = 0
            boiler_power_rest_count[inv_id] = 0  # vynulujeme counter při vstupu do PV režimu
            minuly_proud[inv_id] = battery_current
            
            # Nastavíme dec_boiler na počáteční hodnotu
            if pv_power > out_power:
                rozdil = min(pv_power - out_power, 255)
                dec_boiler = int(rozdil)
            else:
                dec_boiler = 100  # startovací hodnota
            
            if dec_boiler > 255:
                dec_boiler = 255
            if dec_boiler < 0:
                dec_boiler = 0
            
            aktualni_power_drive = dec_boiler
            
            if DEBUG_LEVEL >= 2:
                print(f"  📈 [STŘÍDAČ {inv_id}] PV={pv_power}W, out={out_power}W, dec_boiler={dec_boiler}")
            
        # ==========================================
        # BĚŽNÝ CHOD VE SCÉNÁŘI 2
        # ==========================================
        else:
            # VE SCÉNÁŘI 2 NENULUJEME COUNTER - jen inkrementujeme pro informaci
            boiler_power_rest_count[inv_id] += 1
            
            # Kontrola - pokud PV výkon >= out_power → přidáváme +2
            # pokud PV výkon < out_power → ubíráme -2
            if pv_power >= out_power:
                dec_boiler = dec_boiler + 2
                if dec_boiler > 255:
                    dec_boiler = 255
                if DEBUG_LEVEL >= 2:
                    print(f"  📈 [STŘÍDAČ {inv_id}] PV={pv_power}W >= out={out_power}W → +2 (dec={dec_boiler})")
            else:
                dec_boiler = dec_boiler - 2
                if dec_boiler < 0:
                    dec_boiler = 0
                if DEBUG_LEVEL >= 2:
                    print(f"  📉 [STŘÍDAČ {inv_id}] PV={pv_power}W < out={out_power}W → -2 (dec={dec_boiler})")
            
            # ==========================================
            # KONTROLA - pokud dec_boiler klesne na 0 → vypneme boiler
            # ==========================================
            if dec_boiler == 0:
                if DEBUG_LEVEL >= 2:
                    print(f"  🛑 [STŘÍDAČ {inv_id}] PV výkon nestačí (dec=0) - boiler vypnut")
                vynuluj_interni_fazi(inv_id)
                if boiler_publish_start.lower() == "yes":
                    publikuj_boiler_mqtt(inv_id, 0)
                return
            
            aktualni_power_drive = dec_boiler
            boiler_power_nr[inv_id] = dec_boiler / boiler_const
            boiler_power_rest[inv_id] = boiler_power_nr[inv_id]
            
            if DEBUG_LEVEL >= 2:
                print(f"  ✨ [STŘÍDAČ {inv_id}] PV režim: PV={pv_power}W, out={out_power}W, dec={dec_boiler}, drive={aktualni_power_drive}")
            
            # ==========================================
            # VE SCÉNÁŘI 2 NENULUJEME COUNTER - pouze informativní výpis
            # ==========================================
            if boiler_power_rest_count[inv_id] > 180:
                if DEBUG_LEVEL >= 2:
                    print(f"  📊 [STŘÍDAČ {inv_id}] PV režim - counter={boiler_power_rest_count[inv_id]} (nenuluje se)")

    # ==========================================
    # ULOŽENÍ dec_boiler PRO TENTO STŘÍDAČ
    # ==========================================
    if inv_id == 1:
        dec_boiler1 = dec_boiler
    elif inv_id == 2:
        dec_boiler2 = dec_boiler
    elif inv_id == 3:
        dec_boiler3 = dec_boiler

    # ==========================================
    # PUBLIKACE
    # ==========================================
    if aktualni_power_drive > 0:
        if boiler_publish_start.lower() == "yes":
            publikuj_boiler_mqtt(inv_id, aktualni_power_drive)
    else:
        vynuluj_interni_fazi(inv_id)
        if boiler_publish_start.lower() == "yes":
            publikuj_boiler_mqtt(inv_id, 0)

def vynuluj_interni_fazi(inv_id):
    global boiler_power_nr, boiler_power_rest
    global boiler_power_rest1, boiler_power_rest2, boiler_power_rest3
    global boiler_power_rest_count
    global dec_boiler1, dec_boiler2, dec_boiler3
    global minuly_proud
    
    if boiler_power_rest[inv_id] > 0 and DEBUG_LEVEL >= 2:
        print(f"  🛑 [STŘÍDAČ {inv_id}] Vynulováno (rest=0, power_nr=0)")
    
    boiler_power_nr[inv_id] = 0
    boiler_power_rest[inv_id] = 0
    boiler_power_rest_count[inv_id] = 0
    minuly_proud[inv_id] = 0
    
    if inv_id == 1:
        boiler_power_rest1 = 0
        dec_boiler1 = 0
    elif inv_id == 2:
        boiler_power_rest2 = 0
        dec_boiler2 = 0
    elif inv_id == 3:
        boiler_power_rest3 = 0
        dec_boiler3 = 0

# ==========================================
# DISCOVERY - SELECT ENTITY
# ==========================================

def generuj_spolecnou_output_select_entity():
    auth_dict = {"username": MQTT_username, "password": MQTT_password}
    
    device_info = {
        "identifiers": ["Grand_Glow_HF_NEW_5500_system"],
        "name": "Grand Glow New System",
        "model": "HFMII 5500",
        "manufacturer": "Grand Glow"
    }
    
    command_topic = "homeassistant/select/gg_output_priority/set"
    config_topic = "homeassistant/select/gg_output_priority/config"
    
    config_payload = {
        "name": "GG Output Priority (All Inverters)",
        "state_topic": state_topic,
        "value_template": "{{ value_json.gg_new_1_output_priority }}",
        "unique_id": "gg_output_priority_select_all",
        "icon": "mdi:auto-mode",
        "device": device_info,
        "options": ["UTI-PV-BAT", "PV-UTI-BAT", "PV-BAT-UTI", "GEN"],
        "command_topic": command_topic,
        "optimistic": False
    }
    
    try:
        publish.single(config_topic, payload=json.dumps(config_payload), hostname=broker, port=MQTT_port, auth=auth_dict, retain=True)
        print(f"   ✅ SPOLEČNÁ select entity pro Output Priority vytvořena")
        print(f"   📨 Command topic: {command_topic}")
        return True
    except Exception as e:
        print(f"   ❌ Chyba: {e}")
        return False

def generuj_spolecnou_charge_select_entity():
    auth_dict = {"username": MQTT_username, "password": MQTT_password}
    
    device_info = {
        "identifiers": ["Grand_Glow_HF_NEW_5500_system"],
        "name": "Grand Glow New System",
        "model": "HFMII 5500",
        "manufacturer": "Grand Glow"
    }
    
    command_topic = "homeassistant/select/gg_charge_priority/set"
    config_topic = "homeassistant/select/gg_charge_priority/config"
    
    config_payload = {
        "name": "GG Charge Priority (All Inverters)",
        "state_topic": state_topic,
        "value_template": "{{ value_json.gg_new_1_charger_priority }}",
        "unique_id": "gg_charge_priority_select_all",
        "icon": "mdi:battery-charging",
        "device": device_info,
        "options": ["PV/UTI", "Only PV", "PV First"],
        "command_topic": command_topic,
        "optimistic": False
    }
    
    try:
        publish.single(config_topic, payload=json.dumps(config_payload), hostname=broker, port=MQTT_port, auth=auth_dict, retain=True)
        print(f"   ✅ SPOLEČNÁ select entity pro Charge Priority vytvořena")
        print(f"   📨 Command topic: {command_topic}")
        return True
    except Exception as e:
        print(f"   ❌ Chyba: {e}")
        return False

# --- DEFINICE SENZORŮ ---
DEFINICE_SENZORU = [
    ("time_print", "Time Print", None, "mdi:clock-outline", None, None),
    ("operation_mode", "Operation Mode", None, "mdi:auto-mode", None, None),
    ("output_priority", "Output Priority", None, "mdi:auto-mode", None, None),
    ("charger_priority", "Charger Priority", None, "mdi:auto-mode", None, None),
    ("state_machine", "State Machine Status", None, "mdi:auto-mode", None, None),
    ("charging_status", "Charging Status", None, "mdi:battery-charging", None, None),
    ("battery_soc", "Battery SOC", "%", "mdi:battery", "battery", "measurement"),
    ("fan_speed", "Fan Speed", "%", "mdi:fan", None, "measurement"),
    ("utility_voltage", "Utility Voltage", "V", "mdi:transmission-tower", "voltage", "measurement"),
    ("utility_current", "Utility Current", "A", "mdi:current-dc", "current", "measurement"),
    ("utility_frequency", "Utility Frequency", "Hz", "mdi:current-ac", "frequency", "measurement"),
    ("utility_power", "Utility Power", "W", "mdi:flash", "power", "measurement"),
    ("grid_consumption_today", "Grid Consumption Today", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
    ("grid_consumption_total", "Grid Consumption Total", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
    ("output_voltage", "Output Voltage", "V", "mdi:lightning-bolt", "voltage", "measurement"),
    ("output_current", "Output Current", "A", "mdi:current-dc", "current", "measurement"),
    ("output_frequency", "Output Frequency", "Hz", "mdi:current-ac", "frequency", "measurement"),
    ("output_active_power", "Output Active Power", "W", "mdi:flash", "power", "measurement"),
    ("output_apparent_power", "Output Apparent Power", "VA", "mdi:flash", "power", "measurement"),
    ("output_load_percent", "Output Load Percent", "%", "mdi:gauge", None, "measurement"),
    ("output_energy_today", "Output Energy Today", "kWh", "mdi:flash", "energy", "total_increasing"),
    ("output_energy_total", "Output Energy Total", "kWh", "mdi:flash", "energy", "total_increasing"),
    ("battery_voltage", "Battery Voltage", "V", "mdi:battery", "voltage", "measurement"),
    ("battery_current", "Battery Current", "A", "mdi:current-dc", "current", "measurement"), 
    ("battery_state", "Battery State", None, "mdi:auto-mode", None, None),
    ("pv_voltage", "PV Voltage", "V", "mdi:solar-panel", "voltage", "measurement"),
    ("pv_current", "PV Current", "A", "mdi:current-dc", "current", "measurement"),
    ("pv_power", "PV Power", "W", "mdi:solar-power-variant", "power", "measurement"),
    ("pv_energy_today", "PV Energy Today", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    ("pv_energy_total", "PV Energy Total", "kWh", "mdi:solar-panel-large", "energy", "total_increasing"),
    ("temp_sink", "Sink Temperature", "°C", "mdi:thermometer", "temperature", "measurement")
]

def generuj_ha_entity():
    print(f"\n🚀 Odesílám MQTT Discovery definice...")
    print(f"📌 POČET STŘÍDAČŮ: {POCET_INVERTORU}")
    auth_dict = {"username": MQTT_username, "password": MQTT_password}
    
    try:
        for inv_id in range(1, POCET_INVERTORU + 1):
            device_info = {
                "identifiers": [f"Grand_Glow_HF_NEW_5500_inv_{inv_id}"],
                "name": f"Grand Glow New {inv_id}",
                "model": "HFMII 5500",
                "manufacturer": "Grand Glow"
            }

            for klic, nazev, jednotka, ikona, dev_class, state_class in DEFINICE_SENZORU:
                full_key = f"gg_new_{inv_id}_{klic}"
                config_topic = f"homeassistant/sensor/gg_inv_{inv_id}_{klic}/config"
                
                config_payload = {
                    "name": f"GG {inv_id} {nazev}",
                    "state_topic": state_topic,
                    "value_template": f"{{{{ value_json.{full_key} }}}}",
                    "unique_id": f"gg_new_{inv_id}_{klic}_sensor",
                    "icon": ikona,
                    "device": device_info
                }
                if jednotka: config_payload["unit_of_measurement"] = jednotka
                if dev_class: config_payload["device_class"] = dev_class
                if state_class: config_payload["state_class"] = state_class

                publish.single(config_topic, payload=json.dumps(config_payload), hostname=broker, port=MQTT_port, auth=auth_dict, retain=True)
                time.sleep(0.01)
        
        print("\n📋 Vytvářím SPOLEČNÉ select entity...")
        generuj_spolecnou_output_select_entity()
        generuj_spolecnou_charge_select_entity()
        
        print("\n📋 Kontroluji nastavení priorit...")
        kontrola_a_nastav_priority()
                
        print("\n✅ Discovery dokončeno.")
    except Exception as e:
        print(f"❌ Chyba při MQTT Discovery: {e}")

def odesli_na_mqtt(payload_dict):
    auth_dict = {"username": MQTT_username, "password": MQTT_password}
    try:
        json_data = json.dumps(payload_dict)
        publish.single(state_topic, payload=json_data, hostname=broker, port=MQTT_port, auth=auth_dict, retain=True)
        
        if DEBUG_LEVEL >= 1:
            print("📤 Data odeslána na MQTT broker.")
        if DEBUG_LEVEL == 3:
            print(f"📄 Surový JSON payload:\n{json_data}")
    except Exception as e:
        print(f"❌ Chyba odesílání dat na MQTT: {e}")

def mqtt_boiler_init():
    global boiler_power_rest1, boiler_power_rest2, boiler_power_rest3
    global boiler_power_rest, boiler_power_nr, boiler_power_rest_count
    global dec_boiler1, dec_boiler2, dec_boiler3
    global minuly_proud
    
    for i in range(1, 4):
        boiler_power_nr[i] = 0
        boiler_power_rest[i] = 0
        boiler_power_rest_count[i] = 0
        minuly_proud[i] = 0
    
    boiler_power_rest1 = 0
    boiler_power_rest2 = 0
    boiler_power_rest3 = 0
    dec_boiler1 = 0
    dec_boiler2 = 0
    dec_boiler3 = 0
        
    print(".......boilers_memory...initialise (DRY RUN).......")
    
    if boiler_publish_start.lower() == "yes":
        print("   📤 Posílám inicializační OFF na všechny boiler drivery...")
        for inv_id in range(1, 4):
            publikuj_boiler_mqtt(inv_id, 0)
            time.sleep(0.1)

def on_connect(client, userdata, flags, rc, properties=None):
    if DEBUG_LEVEL >= 2:
        print(f"📡 Poslechový klient připojen.")
    
    client.subscribe(boiler_topic)
    client.subscribe("homeassistant/select/gg_output_priority/set")
    client.subscribe("homeassistant/select/gg_charge_priority/set")
    
    if DEBUG_LEVEL >= 2:
        print(f"   📨 Přihlášen k: homeassistant/select/gg_output_priority/set")
        print(f"   📨 Přihlášen k: homeassistant/select/gg_charge_priority/set")

def on_message(client, userdata, msg):
    global gg_automatika_boileru, vynutit_okamzite_mereni
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8').strip()
        
        if topic == boiler_topic:
            if payload == "boiler_ON":
                gg_automatika_boileru = True
                if DEBUG_LEVEL >= 2:
                    print(f"⚙️ Automatika bojleru ZAPNUTA - všechny 3 fáze aktivní")
                vynutit_okamzite_mereni = True
                    
            elif payload == "boiler_OFF":
                gg_automatika_boileru = False
                if DEBUG_LEVEL >= 2:
                    print(f"⚙️ Automatika bojleru VYPNUTA - všechny 3 fáze vypnuty")
                mqtt_boiler_init()
                vynutit_okamzite_mereni = True
        
        elif topic == "homeassistant/select/gg_output_priority/set":
            if payload in OUTPUT_PRIORITY_REVERSE:
                hodnota = OUTPUT_PRIORITY_REVERSE[payload]
                print(f"\n📨 Požadavek na změnu Output Priority na VŠECH: {payload}")
                uspech = zapis_output_priority_vsechny(hodnota)
                if uspech:
                    print(f"   ✅ Output Priority změněna na {payload}")
                    vynutit_okamzite_mereni = True
                else:
                    print(f"   ❌ Zápis se nezdařil!")
            else:
                print(f"⚠️ Neznámá hodnota: {payload}")
        
        elif topic == "homeassistant/select/gg_charge_priority/set":
            if payload in CHARGE_PRIORITY_REVERSE:
                hodnota = CHARGE_PRIORITY_REVERSE[payload]
                print(f"\n📨 Požadavek na změnu Charge Priority na VŠECH: {payload}")
                uspech = zapis_charge_priority_vsechny(hodnota)
                if uspech:
                    print(f"   ✅ Charge Priority změněna na {payload}")
                    vynutit_okamzite_mereni = True
                else:
                    print(f"   ❌ Zápis se nezdařil!")
            else:
                print(f"⚠️ Neznámá hodnota: {payload}")
                
    except Exception as e:
        print(f"❌ Chyba při zpracování MQTT zprávy: {e}")

# ==========================================
# HLAVNÍ FUNKCE PRO ČTENÍ STŘÍDAČE S OPAKOVÁNÍM PŘI CHYBE
# ==========================================

def cti_jeden_stridac(inv_id, inst):
    pfx = f"gg_new_{inv_id}_"
    
    def read_register_with_retry(register, functioncode=3, retries=3, delay=0.5):
        for attempt in range(retries):
            try:
                return inst.read_register(register, functioncode=functioncode)
            except Exception as e:
                if "checksum" in str(e).lower() or "crc" in str(e).lower():
                    if DEBUG_LEVEL >= 2:
                        print(f"  ⚠️ [STŘÍDAČ {inv_id}] Checksum chyba na registru {register}, pokus {attempt+1}/{retries}")
                    time.sleep(delay)
                    if attempt == retries - 1:
                        raise
                else:
                    raise
        return None
    
    try:
        gg_time_string = time.strftime('%H:%M')
        
        # 66 - Operation Mode
        work_state_raw = read_register_with_retry(66, functioncode=3)
        time.sleep(0.1)
        
        # 80-83 - Utility
        utility_voltage_raw = read_register_with_retry(80, functioncode=3)
        time.sleep(0.1)
        utility_current_raw = read_register_with_retry(81, functioncode=3)
        time.sleep(0.1)
        utility_freq_raw = read_register_with_retry(82, functioncode=3)
        time.sleep(0.1)
        utility_power_raw = read_register_with_retry(83, functioncode=3)
        time.sleep(0.1)
        
        # 436 - Utility Power (Consumption Only)
        utility_power_w_raw = read_register_with_retry(436, functioncode=3)
        time.sleep(0.1)
        
        # 447-448 - Grid Consumption Today
        grid_consumption_today_H_raw = read_register_with_retry(447, functioncode=3)
        time.sleep(0.1)
        grid_consumption_today_L_raw = read_register_with_retry(448, functioncode=3)
        time.sleep(0.1)
        
        # 453-454 - Grid Consumption Total
        grid_consumption_total_H_raw = read_register_with_retry(453, functioncode=3)
        time.sleep(0.1)
        grid_consumption_total_L_raw = read_register_with_retry(454, functioncode=3)
        time.sleep(0.1)
        
        # 88-93 - Output
        output_voltage_raw = read_register_with_retry(88, functioncode=3)
        time.sleep(0.1)
        output_current_raw = read_register_with_retry(89, functioncode=3)
        time.sleep(0.1)
        output_freq_raw = read_register_with_retry(90, functioncode=3)
        time.sleep(0.1)
        output_active_power_raw = read_register_with_retry(91, functioncode=3)
        time.sleep(0.1)
        output_apparent_power_raw = read_register_with_retry(92, functioncode=3)
        time.sleep(0.1)
        output_load_raw = read_register_with_retry(93, functioncode=3)
        time.sleep(0.1)
        
        # 545-546 - Output Energy Today
        output_energy_today_H_raw = read_register_with_retry(545, functioncode=3)
        time.sleep(0.1)
        output_energy_today_L_raw = read_register_with_retry(546, functioncode=3)
        time.sleep(0.1)
        
        # 551-552 - Output Energy Total
        output_energy_total_H_raw = read_register_with_retry(551, functioncode=3)
        time.sleep(0.1)
        output_energy_total_L_raw = read_register_with_retry(552, functioncode=3)
        time.sleep(0.1)
        
        # 150-152 - PV
        pv_voltage_raw = read_register_with_retry(150, functioncode=3)
        time.sleep(0.1)
        pv_current_raw = read_register_with_retry(151, functioncode=3)
        time.sleep(0.1)
        pv_power_raw = read_register_with_retry(152, functioncode=3)
        time.sleep(0.1)
        
        # 615-616 - PV Energy Today
        pv_energy_today_H_raw = read_register_with_retry(615, functioncode=3)
        time.sleep(0.1)
        pv_energy_today_L_raw = read_register_with_retry(616, functioncode=3)
        time.sleep(0.1)
        
        # 621-622 - PV Energy Total
        pv_energy_total_H_raw = read_register_with_retry(621, functioncode=3)
        time.sleep(0.1)
        pv_energy_total_L_raw = read_register_with_retry(622, functioncode=3)
        time.sleep(0.1)
        
        # 128-129 - Battery
        battery_voltage_raw = read_register_with_retry(128, functioncode=3)
        time.sleep(0.1)
        battery_current_raw = read_register_with_retry(129, functioncode=3)
        time.sleep(0.1)
        
        # 338 - Battery SOC
        battery_soc_raw = read_register_with_retry(338, functioncode=3)
        time.sleep(0.1)
        
        # 374 - Charging Status
        charging_status_raw = read_register_with_retry(374, functioncode=3)
        time.sleep(0.1)
        
        # 800 - Fan Speed
        fan_speed_raw = read_register_with_retry(800, functioncode=3)
        time.sleep(0.1)
        
        # 817 - Temperature
        temp_sink_raw = read_register_with_retry(817, functioncode=3)
        time.sleep(0.1)
        
        # 322 - Output Priority
        output_priority_raw = read_register_with_retry(322, functioncode=3)
        time.sleep(0.1)
        
        # 323 - Charge Priority
        charger_priority_raw = read_register_with_retry(323, functioncode=3)
        time.sleep(0.1)
        
        # 324 - State Machine
        state_machine_raw = read_register_with_retry(324, functioncode=3)
        time.sleep(0.1)
        
        # 375-380 - Charging registers
        cv_voltage_raw = read_register_with_retry(375, functioncode=3)
        time.sleep(0.1)
        float_voltage_raw = read_register_with_retry(376, functioncode=3)
        time.sleep(0.1)
        cv_current_raw = read_register_with_retry(377, functioncode=3)
        time.sleep(0.1)
        float_current_raw = read_register_with_retry(378, functioncode=3)
        time.sleep(0.1)
        max_cc_time_raw = read_register_with_retry(379, functioncode=3)
        time.sleep(0.1)
        max_cv_time_raw = read_register_with_retry(380, functioncode=3)
        time.sleep(0.1)
        
        # 16647 - Battery Type
        battery_type_raw = read_register_with_retry(16647, functioncode=3)
        time.sleep(0.1)
        
        # 16650-16651 - Voltage settings
        cv_voltage_setting_raw = read_register_with_retry(16650, functioncode=3)
        time.sleep(0.1)
        float_voltage_setting_raw = read_register_with_retry(16651, functioncode=3)
        time.sleep(0.1)
        
        # 16645-16646 - Current settings
        grid_charge_current_raw = read_register_with_retry(16645, functioncode=3)
        time.sleep(0.1)
        max_charge_current_raw = read_register_with_retry(16646, functioncode=3)
        time.sleep(0.1)

        # ==========================================
        # PŘEVODY HODNOT
        # ==========================================
        text_output_priority = PRIORITA_VYSTUPU.get(output_priority_raw, "PV-BAT-UTI")
        text_charger_priority = PRIORITA_NABIJENI.get(charger_priority_raw, "Only PV")
        
        text_rezimu = STAVY_OPERACE.get(work_state_raw, f"UNKNOWN ({work_state_raw})")
        text_state_machine = STAV_STROJE.get(state_machine_raw, f"UNKNOWN ({state_machine_raw})")
        text_charging_status = NABIJECI_STATUS.get(charging_status_raw, f"UNKNOWN ({charging_status_raw})")
        text_battery_type = BATTERY_TYPE.get(battery_type_raw, f"UNKNOWN ({battery_type_raw})")
        
        battery_soc = battery_soc_raw
        fan_speed = fan_speed_raw
        temp_sink = temp_sink_raw / 10.0
        
        cv_voltage = cv_voltage_raw / 10.0
        float_voltage = float_voltage_raw / 10.0
        cv_current = cv_current_raw / 10.0
        float_current = float_current_raw / 10.0
        max_cc_time = max_cc_time_raw
        max_cv_time = max_cv_time_raw
        
        cv_voltage_setting = cv_voltage_setting_raw / 10.0
        float_voltage_setting = float_voltage_setting_raw / 10.0
        grid_charge_current = grid_charge_current_raw
        max_charge_current = max_charge_current_raw * 10
        
        utility_voltage = utility_voltage_raw / 10.0
        utility_freq    = utility_freq_raw / 100.0
        utility_power   = utility_power_raw
        utility_power_w = utility_power_w_raw * 10
        
        if utility_current_raw > 32767:
            utility_current = (65536 - utility_current_raw) / 100.0
        else:
            utility_current = utility_current_raw / 100.0
        
        grid_consumption_today = (grid_consumption_today_H_raw * 1000) + (grid_consumption_today_L_raw / 100.0)
        grid_consumption_total = (grid_consumption_total_H_raw * 1000) + (grid_consumption_total_L_raw / 100.0)
        
        output_voltage  = output_voltage_raw / 10.0
        output_current  = output_current_raw / 100.0  
        output_freq     = output_freq_raw / 100.0
        output_active_power = output_active_power_raw
        output_apparent_power = output_apparent_power_raw
        output_load     = output_load_raw / 10.0
        output_energy_today = (output_energy_today_H_raw * 1000) + (output_energy_today_L_raw / 100.0)
        output_energy_total = (output_energy_total_H_raw * 1000) + (output_energy_total_L_raw / 100.0)
        
        battery_voltage = battery_voltage_raw / 10.0
        
        # ==========================================
        # SPRÁVNÉ ZPRACOVÁNÍ PROUDU - ROZLIŠENÍ CHARGING / DISCHARGING
        # ==========================================
        if battery_current_raw > 32767:
            battery_current_calc = -((65536 - battery_current_raw) / 10.0)
            stav_baterie = "CHARGING"
            boiler_current = abs(battery_current_calc)
        else:
            battery_current_calc = battery_current_raw / 10.0
            if battery_current_calc > 0:
                stav_baterie = "DISCHARGING"
                boiler_current = 0
            else:
                stav_baterie = "STOP"
                boiler_current = 0
        
        pv_voltage = pv_voltage_raw / 10.0
        pv_power   = pv_power_raw
        if pv_current_raw > 32767:
            pv_current = (65536 - pv_current_raw) / 100.0
        else:
            pv_current = pv_current_raw / 100.0
        pv_energy_today = (pv_energy_today_H_raw * 1000) + (pv_energy_today_L_raw / 100.0)
        pv_energy_total = (pv_energy_total_H_raw * 1000) + (pv_energy_total_L_raw / 100.0)

        if DEBUG_LEVEL >= 2:
            print(f"\n--- DATA STŘÍDAČE {inv_id} [{gg_time_string}] ---")
            print(f"🔄 Operation Mode: [{text_rezimu}]")
            print(f"📋 Output Priority: [{text_output_priority}]")
            print(f"📋 Charge Priority: [{text_charger_priority}]")
            print(f"📋 State Machine: [{text_state_machine}]")
            print(f"🔋 Battery SOC: {battery_soc}%")
            print(f"🔋 Charging Status: [{text_charging_status}]")
            print(f"🌡️ Sink Temperature: {temp_sink:.1f}°C")
            print(f"🌀 Fan Speed: {fan_speed}%")
            print(f"🔌 Grid: {utility_voltage:.1f}V ({utility_current:.2f}A, {utility_power_w}W, {utility_freq:.2f}Hz)")
            print(f"⚡ Output: {output_voltage:.1f}V ({output_current:.2f}A, {output_active_power}W)")
            print(f"🔋 Bat: {battery_voltage:.1f}V ({battery_current_calc:.1f}A - {stav_baterie})")
            print(f"☀️ PV: {pv_voltage:.1f}V, {pv_current:.2f}A, {pv_power}W")
            print(f"⚙️ Bulk Voltage: {cv_voltage_setting:.1f}V")
            if stav_baterie == "CHARGING":
                print(f"  ✅ Nabíjení: {boiler_current:.1f}A k dispozici pro boiler")
            else:
                print(f"  ⛔ {stav_baterie}: boiler vypnut (proud={boiler_current:.1f}A)")

        # ==========================================
        # NÁVRATOVÉ HODNOTY - včetně bulk_voltage pro regulaci
        # ==========================================
        return {
            f"{pfx}time_print": gg_time_string,
            f"{pfx}operation_mode": text_rezimu,
            f"{pfx}output_priority": text_output_priority,
            f"{pfx}charger_priority": text_charger_priority,
            f"{pfx}state_machine": text_state_machine,
            f"{pfx}charging_status": text_charging_status,
            f"{pfx}battery_soc": battery_soc,
            f"{pfx}fan_speed": fan_speed,
            f"{pfx}utility_voltage": round(utility_voltage, 1),
            f"{pfx}utility_current": round(utility_current, 2),
            f"{pfx}utility_frequency": round(utility_freq, 2),
            f"{pfx}utility_power": int(utility_power_w),
            f"{pfx}grid_consumption_today": round(grid_consumption_today, 2),
            f"{pfx}grid_consumption_total": round(grid_consumption_total, 2),
            f"{pfx}output_voltage": round(output_voltage, 1),
            f"{pfx}output_current": round(output_current, 2),
            f"{pfx}output_frequency": round(output_freq, 2),
            f"{pfx}output_active_power": int(output_active_power),
            f"{pfx}output_apparent_power": int(output_apparent_power),
            f"{pfx}output_load_percent": round(output_load, 1),
            f"{pfx}output_energy_today": round(output_energy_today, 2),
            f"{pfx}output_energy_total": round(output_energy_total, 2),
            f"{pfx}battery_voltage": round(battery_voltage, 1),
            f"{pfx}battery_current": round(battery_current_calc, 1),
            f"{pfx}battery_state": stav_baterie,
            f"{pfx}pv_voltage": round(pv_voltage, 1),
            f"{pfx}pv_current": round(pv_current, 2),
            f"{pfx}pv_power": int(pv_power),
            f"{pfx}pv_energy_today": round(pv_energy_today, 2),
            f"{pfx}pv_energy_total": round(pv_energy_total, 2),
            f"{pfx}temp_sink": round(temp_sink, 1),
            f"{pfx}boiler_current": round(boiler_current, 1),
            f"{pfx}bulk_voltage": round(cv_voltage_setting, 1)  # Bulk napětí pro regulaci
        }
    except Exception as e:
        print(f"❌ Střídač {inv_id} chyba komunikace: {e}")
        return {}

# ==========================================
# --- HLAVNÍ SMYČKA ---
# ==========================================
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--discovery':
            generuj_ha_entity()
            sys.exit(0)
        elif sys.argv[1] == '--datetime':
            print("\n" + "=" * 60)
            print("⏰ VYNUCENÁ SYNCHRONIZACE ČASU NA VŠECHNY STŘÍDAČE")
            print("=" * 60)
            
            inicializuj_instrumenty()
            
            now = datetime.datetime.now()
            print(f"📅 Systémový čas: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            for inv_id, inst in instrumenty.items():
                print(f"\n📝 Synchronizuji střídač {inv_id}")
                synchronizuj_cas(inv_id, inst)
                cas = precti_cas_stridace(inv_id, inst)
                zobraz_cas_stridace(inv_id, cas)
                time.sleep(0.5)
            
            sys.exit(0)
        else:
            print(f"❌ Neznámý argument: {sys.argv[1]}")
            print("Použití:")
            print("  python3 script.py           - Spustí daemon")
            print("  python3 script.py --discovery - Vygeneruje MQTT discovery")
            print("  python3 script.py --datetime   - Vynucená synchronizace času")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("🤖 DAEMON MULTI-MONITORING GRAND GLOW NEW")
    print("=" * 60)
    print(f"\n⚙️  Počet střídačů: {POCET_INVERTORU}")
    print(f"⚙️  Default Output Priority: {DEFAULT_OUTPUT_PRIORITY}")
    print(f"⚙️  Default Charge Priority: {DEFAULT_CHARGE_PRIORITY}")
    print(f"⚙️  Boiler regulace: DVOUFÁZOVÁ LOGIKA")
    print(f"     - FÁZE 1 (pod Bulk napětím): UDRŽOVÁNÍ NABÍJECÍHO PROUDU NA 3.5A")
    print(f"     - FÁZE 2 (nad Bulk napětím): UDRŽOVÁNÍ VÝKONU PODLE PV VÝKONU")
    print(f"⚙️  Bulk napětí: čte se dynamicky ze střídače (registr 16650)")
    print(f"⚙️  Boiler publikování: {boiler_publish_start.upper()}")
    print(f"⚙️  Regulační interval: {BOILER_REGULACE_INTERVAL}s")
    print(f"⚙️  Regulační krok: +2/-2 k dec_boiler")
    print(f"⚙️  Vzorec FÁZE 1: drive = (35 * power_nr) + dec_boiler")
    print(f"⚙️  Vzorec FÁZE 2: drive = dec_boiler (PV regulace)")
    print(f"⚙️  OCHRANA PŘED PŘETÍŽENÍM: out_power > {MAX_OUT_POWER_CRIT}W → OKAMŽITÉ VYPNUTÍ")
    print(f"⚙️  RESET FÁZE 1: po 3 hodinách → nová inicializace")
    print(f"⚙️  RESET FÁZE 2: NENULUJE SE")
    print(f"⚙️  PAUZY MEZI ČTENÍM: 100ms pro stabilitu komunikace")
    print(f"⚙️  OPAKOVÁNÍ PŘI CHYBE: 3x s pauzou 0.5s")
    print(f"⚙️  CHARGING/DISCHARGING: boiler topí POUZE při nabíjení")
    print(f"⚙️  AUTOMATICKÁ KONTROLA PRIORIT: PV-BAT-UTI a Only PV")
    print(f"⚙️  KONTROLA ČASU: každých {KONTROLA_CASU_INTERVAL/60} minut")
    
    if boiler_publish_start.lower() == "yes":
        print(f"   📤 Topicy:")
        print(f"      - zigbee2mqtt/boiler_power_drive_1/set")
        print(f"      - zigbee2mqtt/boiler_power_drive_2/set")
        print(f"      - zigbee2mqtt/boiler_power_drive_3/set")
    
    print("\n⏰ Čtení data a času ze střídačů...")
    for inv_id, inst in instrumenty.items():
        cas = precti_cas_stridace(inv_id, inst)
        zobraz_cas_stridace(inv_id, cas)
    
    print("\n🔧 Kontroluji priority (PV-BAT-UTI a Only PV)...")
    kontrola_a_nastav_priority()
    
    print("\n🌐 Spouštím asynchronní poslech...")
    try:
        try: listener_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=LISTEN_CLIENT_ID)
        except AttributeError: listener_client = mqtt.Client(client_id=LISTEN_CLIENT_ID)
        listener_client.username_pw_set(MQTT_username, MQTT_password)
        listener_client.on_connect, listener_client.on_message = on_connect, on_message
        listener_client.connect(broker, MQTT_port, keepalive=60)
        listener_client.loop_start()  
    except Exception as e: print(f"⚠️ Nepodařilo se spustit poslech: {e}")

    print(f"\n🚀 Skenuji {POCET_INVERTORU} střídač(e) každých 30 sekund...")
    print(f"   🔥 Regulace boileru probíhá každých {BOILER_REGULACE_INTERVAL} sekund")
    print(f"   ⚡ FÁZE 1: udržet nabíjecí proud na 3.5A")
    print(f"   ⚡ FÁZE 2: udržet výkon podle PV výkonu")
    print(f"   ⚡ Pravidlo FÁZE 1: proud roste/stejný → +2, proud klesá → -2")
    print(f"   ⚡ Pravidlo FÁZE 2: PV >= out → +2, PV < out → -2")
    mqtt_boiler_init()
    
    last_sync_day = datetime.datetime.now().day
    last_time_check = time.time()
    last_boiler_regulace = time.time()
    
    battery_voltage_gg1 = 0
    battery_voltage_gg2 = 0
    battery_voltage_gg3 = 0
    gmod_gg1 = ""
    gmod_gg2 = ""
    gmod_gg3 = ""
    battery_voltage_gg_dia = 0
    all_in_battery_mode = False
    
    while True:
        if DEBUG_LEVEL >= 1: print(f"Měření: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        spolecny_balicek_dat = {}
        
        data_stridacu = {}
        for idx, inst in instrumenty.items():
            data = cti_jeden_stridac(idx, inst)
            data_stridacu[idx] = data
            if data:
                spolecny_balicek_dat.update(data)
            
            if idx == 1:
                battery_voltage_gg1 = data.get(f"gg_new_{idx}_battery_voltage", 0) if data else 0
                gmod_gg1 = data.get(f"gg_new_{idx}_operation_mode", "") if data else ""
            elif idx == 2:
                battery_voltage_gg2 = data.get(f"gg_new_{idx}_battery_voltage", 0) if data else 0
                gmod_gg2 = data.get(f"gg_new_{idx}_operation_mode", "") if data else ""
            elif idx == 3:
                battery_voltage_gg3 = data.get(f"gg_new_{idx}_battery_voltage", 0) if data else 0
                gmod_gg3 = data.get(f"gg_new_{idx}_operation_mode", "") if data else ""
        
        battery_voltage_gg_dia = (battery_voltage_gg1 + battery_voltage_gg2 + battery_voltage_gg3) / 3
        all_in_battery_mode = (gmod_gg1 == "BATTERY" and gmod_gg2 == "BATTERY" and gmod_gg3 == "BATTERY")
        
        now_time = time.time()
        if now_time - last_boiler_regulace >= BOILER_REGULACE_INTERVAL:
            if DEBUG_LEVEL >= 2:
                print(f"  🔥 SPOUŠTÍM REGULACI BOJLERU (interval {BOILER_REGULACE_INTERVAL}s)")
            
            for idx, inst in instrumenty.items():
                if idx in data_stridacu and data_stridacu[idx]:
                    d = data_stridacu[idx]
                    boiler_current = d.get(f"gg_new_{idx}_boiler_current", 0)
                    bulk_voltage = d.get(f"gg_new_{idx}_bulk_voltage", 57.0)
                    
                    rizeni_vytazovani_boileru(
                        idx,
                        boiler_current,
                        d.get(f"gg_new_{idx}_output_active_power", 0),
                        battery_voltage_gg_dia,
                        all_in_battery_mode,
                        d.get(f"gg_new_{idx}_pv_power", 0),
                        bulk_voltage
                    )
            
            last_boiler_regulace = now_time
        
        if spolecny_balicek_dat: odesli_na_mqtt(spolecny_balicek_dat)
        if DEBUG_LEVEL >= 2: print("-" * 60)
        
        if time.time() - last_time_check >= KONTROLA_CASU_INTERVAL:
            if DEBUG_LEVEL >= 1:
                print(f"\n⏰ Periodická kontrola času (každých {KONTROLA_CASU_INTERVAL/60} minut)...")
            
            for inv_id, inst in instrumenty.items():
                zkontroluj_a_synchronizuj_cas(inv_id, inst)
                time.sleep(0.3)
            
            last_time_check = time.time()
        
        now = datetime.datetime.now()
        if now.day != last_sync_day and now.hour == 0 and now.minute >= 5 and now.minute < 10:
            print(f"\n📅 Nový den - synchronizace času...")
            for inv_id, inst in instrumenty.items():
                synchronizuj_cas(inv_id, inst)
                cas = precti_cas_stridace(inv_id, inst)
                zobraz_cas_stridace(inv_id, cas)
            last_sync_day = now.day
        
        vynutit_okamzite_mereni = False
        for _ in range(300):
            if vynutit_okamzite_mereni:
                if DEBUG_LEVEL >= 2: print("⚡ Okamžitý sken!")
                break
            time.sleep(0.1)