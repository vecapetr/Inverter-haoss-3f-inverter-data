#!/usr/bin/env python3
"""
GRAND GLOW INVERTER READER - Clean version
Čte data z 1 střídače (INV 3) a publikuje je na MQTT
"""

import serial
import time
import datetime
import json
import paho.mqtt.publish as publish
import sys
import os

# ==========================================
# KONFIGURACE
# ==========================================

# Počet střídačů
POCET_INVERTORU = 1

# ČÍSLO STŘÍDAČE - bude použito pro entity (gg_3_*)
CISLO_STRIDACE = 3

# Mapování sériových portů pro jednotlivé střídače
# Klíč = číslo střídače (3), Hodnota = cesta k portu
KONFIGURACE_PORTU = {
    3: "/dev/ttyUSB3",
}

# Nastavení sériové komunikace
SER_BAUDRATE = 2400
SER_TIMEOUT = 1  # sekundy

# MQTT nastavení
MQTT_USERNAME = 'inverter'
MQTT_PASSWORD = 'Grand_Glow_03'
BROKER = "192.168.1.22"
MQTT_PORT = 1883
STATE_TOPIC = "homeassistant/sensor/gg/state"

# Debug úroveň: 0 = žádný, 1 = základní, 2 = detailní
DEBUG = 1

# ==========================================
# SYNCHRONIZACE DATUMU A ČASU
# ==========================================

def synchronizuj_cas(inv_id, ser_port):
    """
    Synchronizuje datum a čas na střídači podle systémového času.
    """
    try:
        now = datetime.datetime.now()
        
        # Příkazy pro synchronizaci
        # DATEYYMMDD\r
        date_str = now.strftime("DATE%y%m%d\r")
        msg_date = date_str.encode()
        
        # TIMEHHMMSS\r
        time_str = now.strftime("TIME%H%M%S\r")
        msg_time = time_str.encode()
        
        print(f"   ⏰ Synchronizuji střídač {inv_id}: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        ser = serial.Serial(ser_port, SER_BAUDRATE, parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE, timeout=SER_TIMEOUT)
        
        # Nastavení data
        ser.write(msg_date)
        response_d = ser.read(7)
        time.sleep(0.2)
        
        # Nastavení času
        ser.write(msg_time)
        response_t = ser.read(7)
        time.sleep(0.2)
        
        ser.close()
        
        if response_t == b'ACK\r' and response_d == b'ACK\r':
            print(f"   ✅ Střídač {inv_id} synchronizován")
            return True
        else:
            print(f"   ⚠️ Střídač {inv_id} - synchronizace selhala (D:{response_d}, T:{response_t})")
            return False
            
    except Exception as e:
        print(f"   ❌ Chyba při synchronizaci střídače {inv_id}: {e}")
        return False

def synchronizuj_cas_vsechny():
    """
    Provede synchronizaci času na VŠECHNY střídače.
    """
    print("\n" + "=" * 60)
    print("⏰ SPOUŠTÍM SYNCHRONIZACI ČASU NA VŠECHNY STŘÍDAČE")
    print("=" * 60)
    
    now = datetime.datetime.now()
    print(f"📅 Systémový čas: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    uspech = True
    for inv_id, ser_port in KONFIGURACE_PORTU.items():
        print(f"\n📝 Střídač {inv_id} na portu {ser_port}")
        if not synchronizuj_cas(inv_id, ser_port):
            uspech = False
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    if uspech:
        print("✅ VŠECHNY střídače byly úspěšně synchronizovány!")
    else:
        print("⚠️ NĚKTERÉ střídače se nepodařilo synchronizovat!")
    print("=" * 60)
    
    return uspech

# ==========================================
# MQTT PUBLIKACE
# ==========================================

def mqtt_publish(payload):
    """Publikuje data na MQTT."""
    try:
        auth = {'username': MQTT_USERNAME, 'password': MQTT_PASSWORD}
        publish.single(STATE_TOPIC, payload, hostname=BROKER, port=MQTT_PORT, auth=auth, qos=0, retain=True)
        if DEBUG >= 1:
            now = datetime.datetime.now()
            print(f'📤 Data publikována v {now.strftime("%H:%M:%S")}')
        return True
    except Exception as e:
        print(f"❌ Chyba při publikování MQTT: {e}")
        return False

# ==========================================
# ČTENÍ Z JEDNOHO STŘÍDAČE
# ==========================================

def precti_stridac(inv_id, ser_port):
    """
    Přečte data z jednoho střídače.
    Vrací slovník s naměřenými hodnotami.
    """
    
    # Příkazy pro komunikaci se střídačem
    msg_GLINE = bytes.fromhex("47 4c 49 4e 45 0D")  # GLINE
    msg_GMOD = bytes.fromhex("47 4d 4f 44 0D")      # GMOD
    msg_GBAT = bytes.fromhex("47 42 41 54 0D")      # GBAT
    msg_GCHG = bytes.fromhex("47 43 48 47 0D")      # GCHG
    msg_GOP = bytes.fromhex("47 4f 50 0D")          # GOP
    msg_GINV = bytes.fromhex("47 49 4e 56 0D")      # GINV
    msg_GPV = bytes.fromhex("47 50 56 0D")          # GPV
    msg_BL = bytes.fromhex("42 4c 0D")              # BL
    msg_GPDAT = bytes.fromhex("47 50 44 41 54 30 0D")  # GPDAT0
    msg_CPR = bytes.fromhex("43 50 52 3f 3f 0D")    # CPR?
    msg_OPR = bytes.fromhex("4f 50 52 3f 3f 0D")    # OPR?
    
    data = {}
    
    try:
        ser = serial.Serial(ser_port, SER_BAUDRATE, parity=serial.PARITY_NONE, 
                           stopbits=serial.STOPBITS_ONE, timeout=SER_TIMEOUT)
        
        # ------ GLINE ------
        ser.write(msg_GLINE)
        response = ser.read(78)
        if response and response[0:1] == b'(':
            try:
                data['utility_voltage'] = float(response[1:6])
                data['utility_frequency'] = float(response[7:12])
                data['utility_today_consumption'] = float(response[60:64]) / 100
                utility_total_exp = int(response[66:70])
                utility_total_bas = int(response[71:76])
                data['utility_total_consumption'] = ((100000 * utility_total_exp) + utility_total_bas) / 100
            except:
                data['utility_voltage'] = 0
                data['utility_frequency'] = 0
                data['utility_today_consumption'] = 0
                data['utility_total_consumption'] = 0
        else:
            data['utility_voltage'] = 0
            data['utility_frequency'] = 0
            data['utility_today_consumption'] = 0
            data['utility_total_consumption'] = 0
        
        time.sleep(0.1)
        
        # ------ GMOD ------
        ser.write(msg_GMOD)
        response = ser.read(5)
        if response == b'(B\r':
            data['mode'] = 'Battery mode'
        elif response == b'(L\r':
            data['mode'] = 'Utility mode'
        elif response == b'(P\r':
            data['mode'] = 'Initial power-up mode'
        elif response == b'(S\r':
            data['mode'] = 'Standby mode'
        elif response == b'(F\r':
            data['mode'] = 'Failure mode'
        elif response == b'(D\r':
            data['mode'] = 'Shutdown mode'
        elif response == b'(X\r':
            data['mode'] = 'Test pattern'
        else:
            data['mode'] = 'Read Err'
        
        time.sleep(0.1)
        
        # ------ GBAT ------
        ser.write(msg_GBAT)
        response = ser.read(27)
        if response and response[0:1] == b'(':
            try:
                data['battery_voltage'] = float(response[1:6])
                data['battery_discharge_current'] = float(response[8:13])
            except:
                data['battery_voltage'] = 0
                data['battery_discharge_current'] = 0
        else:
            data['battery_voltage'] = 0
            data['battery_discharge_current'] = 0
        
        time.sleep(0.1)
        
        # ------ GCHG ------
        ser.write(msg_GCHG)
        response = ser.read(110)
        if response and response[0:1] == b'(':
            try:
                data['charging_voltage'] = float(response[7:12])
                data['charging_current'] = float(response[16:21])
                charging_modes = response[81:82]
                
                if charging_modes == b'0':
                    data['charging_mode'] = "Stop Charging"
                elif charging_modes == b'1':
                    data['charging_mode'] = "Constant Current"
                elif charging_modes == b'2':
                    data['charging_mode'] = "Constant Voltage"
                elif charging_modes == b'3':
                    data['charging_mode'] = "Floating"
                else:
                    data['charging_mode'] = "Unknown"
            except:
                data['charging_voltage'] = 0
                data['charging_current'] = 0
                data['charging_mode'] = "Read Err"
        else:
            data['charging_voltage'] = 0
            data['charging_current'] = 0
            data['charging_mode'] = "Read Err"
        
        time.sleep(0.1)
        
        # ------ GOP ------
        ser.write(msg_GOP)
        response = ser.read(110)
        if response and response[0:1] == b'(':
            try:
                data['out_voltage'] = float(response[1:6])
                data['out_frequency'] = float(response[7:12])
                data['out_current_gop'] = float(response[14:19])
                data['out_power'] = int(response[27:31])
                data['out_load'] = int(response[57:59])
                data['out_today_power'] = int(response[72:77]) / 100
                out_total_exp = int(response[78:83])
                out_total_bas = int(response[84:89])
                data['out_total_power'] = ((100000 * out_total_exp) + out_total_bas) / 100
            except:
                data['out_voltage'] = 0
                data['out_frequency'] = 0
                data['out_current_gop'] = 0
                data['out_power'] = 0
                data['out_load'] = 0
                data['out_today_power'] = 0
                data['out_total_power'] = 0
        else:
            data['out_voltage'] = 0
            data['out_frequency'] = 0
            data['out_current_gop'] = 0
            data['out_power'] = 0
            data['out_load'] = 0
            data['out_today_power'] = 0
            data['out_total_power'] = 0
        
        time.sleep(0.1)
        
        # ------ GINV ------
        ser.write(msg_GINV)
        response = ser.read(20)
        if response and response[0:1] == b'(':
            try:
                data['out_current'] = float(response[13:18])
            except:
                data['out_current'] = 0
        else:
            data['out_current'] = 0
        
        time.sleep(0.1)
        
        # ------ GPV ------
        ser.write(msg_GPV)
        response = ser.read(150)
        if response and response[0:1] == b'(':
            try:
                data['pv_string_voltage'] = float(response[1:6])
                data['pv_charging_current'] = float(response[13:18])
                data['pv_current'] = float(response[19:24])
                data['pv_power'] = float(response[25:30])
                data['pv_today_generation'] = float(response[103:108]) / 100
                pv_total_exp = int(response[109:114])
                pv_total_bas = int(response[115:120])
                data['pv_total_generation'] = ((100000 * pv_total_exp) + pv_total_bas) / 100
            except:
                data['pv_string_voltage'] = 0
                data['pv_charging_current'] = 0
                data['pv_current'] = 0
                data['pv_power'] = 0
                data['pv_today_generation'] = 0
                data['pv_total_generation'] = 0
        else:
            data['pv_string_voltage'] = 0
            data['pv_charging_current'] = 0
            data['pv_current'] = 0
            data['pv_power'] = 0
            data['pv_today_generation'] = 0
            data['pv_total_generation'] = 0
        
        time.sleep(0.1)
        
        # ------ BL (Battery Level) ------
        ser.write(msg_BL)
        response = ser.read(7)
        if response and response[0:1] == b'B':
            try:
                data['battery_capacity'] = int(response[2:5])
            except:
                data['battery_capacity'] = 0
        else:
            data['battery_capacity'] = 0
        
        time.sleep(0.1)
        
        # ------ GPDAT0 ------
        ser.write(msg_GPDAT)
        response = ser.read(500)
        if response and response[0:1] == b'(':
            try:
                data['internal_temperature'] = float(response[102:107])
                data['battery_current'] = float(response[62:67])
                data['oper_status'] = int(response[3:4])
                data['par_mode'] = int(response[10:11])
            except:
                data['internal_temperature'] = 0
                data['battery_current'] = 0
                data['oper_status'] = 0
                data['par_mode'] = 0
        else:
            data['internal_temperature'] = 0
            data['battery_current'] = 0
            data['oper_status'] = 0
            data['par_mode'] = 0
        
        time.sleep(0.1)
        
        # ------ CPR? ------
        ser.write(msg_CPR)
        response = ser.read(5)
        if response and response[0:1] == b'(':
            try:
                chpr = int(response[1:3])
                if chpr == 0:
                    data['charging_mode_prior'] = "Utility"
                elif chpr == 1:
                    data['charging_mode_prior'] = "PV first"
                elif chpr == 2:
                    data['charging_mode_prior'] = "Utility+PV"
                elif chpr == 3:
                    data['charging_mode_prior'] = "Only PV"
                else:
                    data['charging_mode_prior'] = "Read Error"
            except:
                data['charging_mode_prior'] = "Read Error"
        else:
            data['charging_mode_prior'] = "Read Error"
        
        time.sleep(0.1)
        
        # ------ OPR? ------
        ser.write(msg_OPR)
        response = ser.read(5)
        if response and response[0:1] == b'(':
            try:
                opr = int(response[1:3])
                if opr == 0:
                    data['mode_prior'] = "Utility"
                elif opr == 1:
                    data['mode_prior'] = "PV first"
                elif opr == 2:
                    data['mode_prior'] = "PV-BAT-UTI"
                else:
                    data['mode_prior'] = "Read Error"
            except:
                data['mode_prior'] = "Read Error"
        else:
            data['mode_prior'] = "Read Error"
        
        ser.close()
        
        # Přidáme časové razítko
        now = datetime.datetime.now()
        data['time_pub'] = now.strftime("D %d:%m T %H:%M")
        
        return data
        
    except Exception as e:
        print(f"❌ Chyba při čtení střídače {inv_id}: {e}")
        return None

# ==========================================
# KONTROLA SYNCHRONIZACE ČASU
# ==========================================

def check_and_sync_time(last_sync_day):
    """
    Zkontroluje, zda je třeba provést synchronizaci času.
    Synchronizace probíhá vždy 5-10 minut po půlnoci (00:05 - 00:10).
    """
    now = datetime.datetime.now()
    current_day = now.day
    
    # Pokud je nový den a čas je mezi 00:05 a 00:10
    if current_day != last_sync_day and now.hour == 0 and now.minute >= 5 and now.minute < 10:
        print(f"\n📅 Nový den - provádím synchronizaci času ({now.strftime('%Y-%m-%d %H:%M:%S')})...")
        synchronizuj_cas_vsechny()
        return current_day
    
    return last_sync_day

# ==========================================
# HLAVNÍ SMYČKA
# ==========================================

def main():
    print("\n" + "=" * 60)
    print("🤖 GRAND GLOW INVERTER READER - INV 3")
    print("=" * 60)
    print(f"📌 Číslo střídače: {CISLO_STRIDACE} (entity: gg_{CISLO_STRIDACE}_*)")
    print(f"📌 Port: {KONFIGURACE_PORTU[CISLO_STRIDACE]}")
    print(f"📌 MQTT broker: {BROKER}:{MQTT_PORT}")
    print(f"📌 State topic: {STATE_TOPIC}")
    print(f"📌 Synchronizace času: denně v 00:05-00:10")
    print("=" * 60 + "\n")
    
    # Kontrola konfigurace
    for inv_id in KONFIGURACE_PORTU.keys():
        print(f"✅ Střídač {inv_id}: {KONFIGURACE_PORTU[inv_id]}")
    
    print("\n🚀 Spouštím čtení...")
    
    # Inicializace pro sledování dne
    last_sync_day = datetime.datetime.now().day
    
    # Hlavní smyčka
    while True:
        try:
            now = datetime.datetime.now()
            if DEBUG >= 1:
                print(f"\n📊 Čtení: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Kontrola synchronizace času
            last_sync_day = check_and_sync_time(last_sync_day)
            
            publish_data = {}
            
            for inv_id, ser_port in KONFIGURACE_PORTU.items():
                
                if DEBUG >= 1:
                    print(f"   📡 Čtu střídač {inv_id}...", end=" ")
                
                data = precti_stridac(inv_id, ser_port)
                
                if data:
                    if DEBUG >= 1:
                        print("✅")
                    
                    # Přidáme data do payloadu s prefixem gg_{inv_id}_
                    for key, value in data.items():
                        publish_data[f'gg_{inv_id}_{key}'] = value
                    
                    # Pro zpětnou kompatibilitu - původní názvy
                    if 'mode' in data:
                        publish_data[f'gg_{inv_id}_mode'] = data['mode']
                    if 'battery_capacity' in data:
                        publish_data[f'gg_{inv_id}_battery_capacity'] = data['battery_capacity']
                    if 'battery_voltage' in data:
                        publish_data[f'gg_{inv_id}_battery_voltage'] = data['battery_voltage']
                    if 'out_power' in data:
                        publish_data[f'gg_{inv_id}_out_power'] = data['out_power']
                    if 'pv_today_generation' in data:
                        publish_data[f'gg_{inv_id}_PV_Today_generation'] = data['pv_today_generation']
                    if 'pv_total_generation' in data:
                        publish_data[f'gg_{inv_id}_PV_Total_generation'] = data['pv_total_generation']
                    if 'pv_power' in data:
                        publish_data[f'gg_{inv_id}_PV_power'] = data['pv_power']
                    if 'pv_current' in data:
                        publish_data[f'gg_{inv_id}_PV_current'] = data['pv_current']
                    if 'pv_string_voltage' in data:
                        publish_data[f'gg_{inv_id}_PV_string_voltage'] = data['pv_string_voltage']
                    if 'pv_charging_current' in data:
                        publish_data[f'gg_{inv_id}_PV_charging_current'] = data['pv_charging_current']
                    if 'out_voltage' in data:
                        publish_data[f'gg_{inv_id}_out_voltage'] = data['out_voltage']
                    if 'out_current' in data:
                        publish_data[f'gg_{inv_id}_out_current'] = data['out_current']
                    if 'out_frequency' in data:
                        publish_data[f'gg_{inv_id}_out_frequency'] = data['out_frequency']
                    if 'out_today_power' in data:
                        publish_data[f'gg_{inv_id}_out_today_power'] = data['out_today_power']
                    if 'out_total_power' in data:
                        publish_data[f'gg_{inv_id}_out_total_power'] = data['out_total_power']
                    if 'utility_voltage' in data:
                        publish_data[f'gg_{inv_id}_utility_voltage'] = data['utility_voltage']
                    if 'utility_frequency' in data:
                        publish_data[f'gg_{inv_id}_utility_frequency'] = data['utility_frequency']
                    if 'charging_mode' in data:
                        publish_data[f'gg_{inv_id}_charging_mode'] = data['charging_mode']
                    if 'internal_temperature' in data:
                        publish_data[f'gg_{inv_id}_internal_temperature'] = data['internal_temperature']
                    if 'battery_current' in data:
                        publish_data[f'gg_{inv_id}_battery_current'] = data['battery_current']
                    if 'battery_discharge_current' in data:
                        publish_data[f'gg_{inv_id}_battery_discharge_current'] = data['battery_discharge_current']
                    if 'out_load' in data:
                        publish_data[f'gg_{inv_id}_load_inverter'] = data['out_load']
                    if 'utility_today_consumption' in data:
                        publish_data[f'gg_{inv_id}_Today_Utility_consumption'] = data['utility_today_consumption']
                    if 'utility_total_consumption' in data:
                        publish_data[f'gg_{inv_id}_Total_Utility_consumption'] = data['utility_total_consumption']
                    if 'charging_voltage' in data:
                        publish_data[f'gg_{inv_id}_charging_voltage'] = data['charging_voltage']
                    if 'charging_current' in data:
                        publish_data[f'gg_{inv_id}_charging_current'] = data['charging_current']
                    if 'mode_prior' in data:
                        publish_data[f'gg_{inv_id}_mode_prior'] = data['mode_prior']
                    if 'charging_mode_prior' in data:
                        publish_data[f'gg_{inv_id}_charging_mode_prior'] = data['charging_mode_prior']
                    if 'time_pub' in data:
                        publish_data[f'gg_{inv_id}_time_pub'] = data['time_pub']
                    if 'out_current_gop' in data:
                        publish_data[f'gg_{inv_id}_out_current_gop'] = data['out_current_gop']
                else:
                    if DEBUG >= 1:
                        print("❌")
                    # Pokud se nepodařilo přečíst, pošleme prázdné hodnoty
                    for key in ['mode', 'battery_voltage', 'out_power', 'pv_power', 'pv_current', 
                               'pv_string_voltage', 'pv_charging_current', 'out_voltage', 
                               'out_current', 'out_frequency', 'utility_voltage', 'utility_frequency',
                               'charging_mode', 'internal_temperature', 'battery_current',
                               'battery_discharge_current', 'load_inverter', 'battery_capacity',
                               'time_pub', 'out_current_gop', 'mode_prior', 'charging_mode_prior']:
                        if key == 'time_pub':
                            publish_data[f'gg_{inv_id}_{key}'] = now.strftime("D %d:%m T %H:%M")
                        elif key == 'mode_prior':
                            publish_data[f'gg_{inv_id}_{key}'] = "Read Error"
                        elif key == 'charging_mode_prior':
                            publish_data[f'gg_{inv_id}_{key}'] = "Read Error"
                        else:
                            publish_data[f'gg_{inv_id}_{key}'] = 0
            
            # Publikujeme data
            if publish_data:
                payload = json.dumps(publish_data)
                mqtt_publish(payload)
            
            # Čekáme před dalším čtením (30 sekund)
            for _ in range(30):
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n👋 Ukončuji...")
            break
        except Exception as e:
            print(f"❌ Chyba v hlavní smyčce: {e}")
            time.sleep(5)

# ==========================================
# DISCOVERY - VYTVOŘENÍ ENTIT V HOME ASSISTANT
# ==========================================

def create_discovery():
    """Vygeneruje MQTT discovery entity pro Home Assistant."""
    
    print("\n🚀 Vytvářím MQTT discovery entity pro střídač 3...")
    
    auth = {'username': MQTT_USERNAME, 'password': MQTT_PASSWORD}
    
    # Definice senzorů
    sensors = [
        ("mode", "Mode", None, "mdi:auto-mode", None, None),
        ("PV_string_voltage", "PV String Voltage", "V", "mdi:solar-panel", "voltage", "measurement"),
        ("PV_charging_current", "PV Charging Current", "A", "mdi:solar-panel", "current", "measurement"),
        ("PV_Today_generation", "PV Today Generation", "kWh", "mdi:solar-power", "energy", "total_increasing"),
        ("PV_Total_generation", "PV Total Generation", "kWh", "mdi:solar-panel-large", "energy", "total_increasing"),
        ("out_current", "Output Current", "A", "mdi:current-dc", "current", "measurement"),
        ("out_voltage", "Output Voltage", "V", "mdi:lightning-bolt", "voltage", "measurement"),
        ("out_frequency", "Output Frequency", "Hz", "mdi:current-ac", "frequency", "measurement"),
        ("out_today_power", "Output Today Power", "kWh", "mdi:flash", "energy", "total_increasing"),
        ("out_total_power", "Output Total Power", "kWh", "mdi:flash", "energy", "total_increasing"),
        ("utility_voltage", "Utility Voltage", "V", "mdi:transmission-tower", "voltage", "measurement"),
        ("utility_frequency", "Utility Frequency", "Hz", "mdi:transmission-tower", "frequency", "measurement"),
        ("load_inverter", "Load Inverter", "%", "mdi:gauge", None, "measurement"),
        ("battery_voltage", "Battery Voltage", "V", "mdi:battery", "voltage", "measurement"),
        ("battery_discharge_current", "Battery Discharge Current", "A", "mdi:current-dc", "current", "measurement"),
        ("charging_voltage", "Charging Voltage", "V", "mdi:battery-charging", "voltage", "measurement"),
        ("charging_current", "Charging Current", "A", "mdi:battery-charging", "current", "measurement"),
        ("battery_capacity", "Battery Capacity", "%", "mdi:battery-charging", "battery", "measurement"),
        ("out_current_gop", "Output Current GOP", "A", "mdi:current-dc", "current", "measurement"),
        ("out_power", "Output Power", "W", "mdi:flash", "power", "measurement"),
        ("PV_power", "PV Power", "W", "mdi:solar-power-variant", "power", "measurement"),
        ("PV_current", "PV Current", "A", "mdi:current-dc", "current", "measurement"),
        ("time_pub", "Time Published", None, "mdi:clock", None, None),
        ("Today_Utility_consumption", "Today Utility Consumption", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
        ("Total_Utility_consumption", "Total Utility Consumption", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
        ("battery_current", "Battery Current", "A", "mdi:current-dc", "current", "measurement"),
        ("internal_temperature", "Internal Temperature", "°C", "mdi:thermometer", "temperature", "measurement"),
        ("mode_prior", "Mode Priority", None, "mdi:auto-mode", None, None),
        ("charging_mode_prior", "Charging Mode Priority", None, "mdi:battery-charging", None, None),
        ("mode_phase", "Mode Phase", None, "mdi:auto-mode", None, None),
    ]
    
    config_counter = 1
    
    for inv_id, ser_port in KONFIGURACE_PORTU.items():
        
        # Zjistíme firmware
        fw = "unknown"
        try:
            ser = serial.Serial(ser_port, SER_BAUDRATE, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, timeout=1)
            msg_SVFW = bytes.fromhex("53 56 46 57 0D")
            ser.write(msg_SVFW)
            response = ser.read(6)
            if response and response[0:1] == b'(':
                fw = float(response[1:6])
            ser.close()
        except:
            pass
        
        device_info = {
            "identifiers": [f"gg_{inv_id}"],
            "manufacturer": "Grand Glow",
            "model": "HFM PRO",
            "name": f"Grand Glow {inv_id}",
            "sw_version": fw
        }
        
        print(f"\n📝 Vytvářím entity pro střídač {inv_id} (gg_{inv_id}_*):")
        
        for name, display_name, unit, icon, dev_class, state_class in sensors:
            state_topic = f"homeassistant/sensor/gg/{config_counter}/config"
            
            msg = {
                "name": f"gg_{inv_id}_{name}",
                "stat_t": STATE_TOPIC,
                "icon": icon,
                "uniq_id": f"gg_{inv_id}_{name}",
                "val_tpl": f"{{{{ value_json.gg_{inv_id}_{name} }}}}",
                "dev": device_info
            }
            
            if unit:
                msg["unit_of_meas"] = unit
            if dev_class:
                msg["dev_cla"] = dev_class
            if state_class:
                msg["stat_cla"] = state_class
            
            payload = json.dumps(msg)
            
            try:
                publish.single(state_topic, payload, hostname=BROKER, port=MQTT_PORT, auth=auth, qos=0, retain=True)
                print(f"   ✅ gg_{inv_id}_{name}")
                config_counter += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"   ❌ Chyba při vytváření gg_{inv_id}_{name}: {e}")
    
    print(f"\n✅ Discovery dokončeno! Vytvořeno {config_counter-1} entit pro střídač {CISLO_STRIDACE}.")

# ==========================================
# SPUŠTĚNÍ
# ==========================================

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--discovery':
            create_discovery()
            sys.exit(0)
        elif sys.argv[1] == '--datetime':
            print("\n" + "=" * 60)
            print("⏰ VYNUCENÁ SYNCHRONIZACE ČASU NA STŘÍDAČ")
            print("=" * 60)
            synchronizuj_cas_vsechny()
            sys.exit(0)
        else:
            print(f"❌ Neznámý argument: {sys.argv[1]}")
            print("Použití:")
            print("  python3 script.py           - Spustí čtení")
            print("  python3 script.py --discovery - Vygeneruje MQTT discovery")
            print("  python3 script.py --datetime   - Vynucená synchronizace času")
            sys.exit(1)
    
    main()



