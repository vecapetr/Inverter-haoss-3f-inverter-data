#!/usr/bin/env python3
"""
DAEMON PRO STŘÍDAČE 4 A 5 (GRAND GLOW CAR CHARGER)
Samostatný skript pro monitoring střídačů 4 a 5 s MQTT autodiscovery
Synchronizace času 5-10 minut po půlnoci
"""

import serial
import time
import datetime
import json
import paho.mqtt.publish as publish
from paho.mqtt import client as mqtt_client
import sys
import os

# ==========================================
# --- 1. KONFIGURACE ---
# ==========================================

# MQTT nastavení
MQTT_username = 'inverter'
MQTT_password = 'Grand_Glow_03'
broker = "192.168.1.22"
MQTT_port = 1883

# NOVÝ SAMOSTATNÝ TOPIC PRO STŘÍDAČE 4 A 5
state_topic = "homeassistant/sensor/gg_car/state"

# Sériové porty pro střídače 4 a 5
ser_port_inv_4 = "/dev/ttyUSB4"
ser_port_inv_5 = "/dev/ttyUSB5"

# Sériová komunikace
ser_baudrate = 2400
tim = 1  # timeout

# Časovač
timer = 30

# Ladění (0=žádné, 1=základní, 2=detailní)
debug = 1

# ==========================================
# --- 2. PŘÍKAZY PRO KOMUNIKACI ---
# ==========================================

def build_command(cmd_str):
    """Vytvoří bytes příkaz z textového řetězce s CR na konci."""
    return (cmd_str + "\r").encode("utf-8")

# Základní příkazy
CMD_GLINE = build_command("GLINE")
CMD_GMOD = build_command("GMOD")
CMD_GBAT = build_command("GBAT")
CMD_GCHG = build_command("GCHG")
CMD_GOP = build_command("GOP")
CMD_GINV = build_command("GINV")
CMD_GPV = build_command("GPV")
CMD_BL = build_command("BL")
CMD_GPDAT0 = build_command("GPDAT0")
CMD_CPR = build_command("CPR??")
CMD_OPR = build_command("OPR??")
CMD_SVFW = build_command("SVFW")

def build_date_command():
    """Vytvoří příkaz pro nastavení data ve formátu DATEyymmdd\r."""
    now = datetime.datetime.now()
    date_str = now.strftime("%y%m%d")
    return build_command(f"DATE{date_str}")

def build_time_command():
    """Vytvoří příkaz pro nastavení času ve formátu TIMEhhmmss\r."""
    now = datetime.datetime.now()
    time_str = now.strftime("%H%M%S")
    return build_command(f"TIME{time_str}")

# ==========================================
# --- 3. DEFINICE SENZORŮ (dle 207.py) ---
# ==========================================

# Definice senzorů jako v 207.py
DEFINICE_SENZORU = [
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
    ("utility_frequency", "Utility Frequency", "Hz", "mdi:current-ac", "frequency", "measurement"),
    ("load_inverter", "Load Inverter", "%", "mdi:gauge", None, "measurement"),
    ("battery_voltage", "Battery Voltage", "V", "mdi:battery", "voltage", "measurement"),
    ("battery_discharge_current", "Battery Discharge Current", "A", "mdi:current-dc", "current", "measurement"),
    ("charging_voltage", "Charging Voltage", "V", "mdi:current-dc", "voltage", "measurement"),
    ("charging_current", "Charging Current", "A", "mdi:current-dc", "current", "measurement"),
    ("battery_capacity", "Battery Capacity", "%", "mdi:battery-charging", "battery", "measurement"),
    ("out_current_gop", "Output Current GOP", "A", "mdi:transmission-tower-export", "current", "measurement"),
    ("out_power", "Output Power", "W", "mdi:flash", "power", "measurement"),
    ("PV_power", "PV Power", "W", "mdi:solar-power-variant", "power", "measurement"),
    ("PV_current", "PV Current", "A", "mdi:current-dc", "current", "measurement"),
    ("time_pub", "Time Publish", None, "mdi:clock-outline", None, None),
    ("Total_generation", "Total Generation", "kWh", "mdi:solar-power", "energy", "total_increasing"),
    ("Today_Utility_consumption", "Today Utility Consumption", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
    ("Total_Utility_consumption", "Total Utility Consumption", "kWh", "mdi:transmission-tower", "energy", "total_increasing"),
    ("battery_current", "Battery Current", "A", "mdi:current-dc", "current", "measurement"),
    ("internal_temperature", "Internal Temperature", "°C", "mdi:thermometer", "temperature", "measurement"),
    ("mode_prior", "Mode Priority", None, "mdi:auto-mode", None, None),
    ("charging_mode_prior", "Charging Mode Priority", None, "mdi:auto-mode", None, None),
    ("mode_phase", "Mode Phase", None, "mdi:auto-mode", None, None),
    ("charger_power", "Charger Power", "A", "mdi:ev-plug-type2", "current", "measurement"),
    ("charging_mode", "Charging Mode", None, "mdi:battery-charging", None, None)
]

# ==========================================
# --- 4. MQTT FUNKCE (dle 207.py) ---
# ==========================================

def mqtt_publish(payload):
    """Odešle data na MQTT broker."""
    try:
        MQTT_auth = {'username': MQTT_username, 'password': MQTT_password}
        publish.single(state_topic, payload, hostname=broker, port=MQTT_port, 
                      auth=MQTT_auth, qos=0, retain=True)
        now = datetime.datetime.now()
        current_time = now.strftime("%H:%M:%S")
        if debug >= 1:
            print(f'📤 Data odeslána na MQTT: {current_time}')
        return True
    except Exception as e:
        print(f"❌ Chyba MQTT publish: {e}")
        return False


def create_discovery():
    """Vytvoří MQTT discovery entity podle vzoru 207.py (bez config_counter)."""
    print("\n🚀 Vytvářím MQTT discovery entity pro střídače 4 a 5...")
    print(f"   📨 State topic: {state_topic}")
    print(f"   🏷️  Název zařízení: Grand Glow Car Charger")
    
    MQTT_auth = {'username': MQTT_username, 'password': MQTT_password}
    
    # Střídače 4 a 5
    inverters = [4, 5]
    ser_ports = {4: ser_port_inv_4, 5: ser_port_inv_5}
    
    total_entities = 0
    
    for inv_id in inverters:
        ser_port = ser_ports[inv_id]
        
        # Získání FW verze
        try:
            ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                              stopbits=serial.STOPBITS_ONE, timeout=tim)
            ser.write(CMD_SVFW)
            response11 = ser.read(6)
            ser.close()
            if response11 and response11 != b"":
                fw = float(response11[1:6])
            else:
                fw = "unknown"
        except Exception as e:
            print(f"  ⚠️ Nelze přečíst FW verzi střídače {inv_id}: {e}")
            fw = "unknown"
        
        print(f"  📡 Střídač {inv_id}: FW verze {fw}")
        
        # Device info - jako v 207.py
        device_info = {
            "identifiers": [f"Grand_Glow_Car_Charger_{inv_id}"],
            "name": f"Grand Glow Car Charger {inv_id}",
            "model": "HFM PRO",
            "manufacturer": "Grand Glow",
            "sw_version": fw
        }
        
        # Vytvoření senzorů - stejný vzor jako v 207.py
        for key, name, unit, icon, dev_class, state_class in DEFINICE_SENZORU:
            full_key = f"gg_{inv_id}_{key}"
            config_topic = f"homeassistant/sensor/gg_car_{inv_id}_{key}/config"
            
            config_payload = {
                "name": f"Car Charger {inv_id} {name}",
                "state_topic": state_topic,
                "value_template": f"{{{{ value_json.{full_key} }}}}",
                "unique_id": f"gg_car_{inv_id}_{key}_sensor",
                "icon": icon,
                "device": device_info
            }
            
            if unit:
                config_payload["unit_of_measurement"] = unit
            if dev_class:
                config_payload["device_class"] = dev_class
            if state_class:
                config_payload["state_class"] = state_class
            
            try:
                publish.single(config_topic, payload=json.dumps(config_payload), 
                             hostname=broker, port=MQTT_port, auth=MQTT_auth, retain=True)
                if debug >= 2:
                    print(f"     ✅ {config_topic}")
                total_entities += 1
                time.sleep(0.02)
            except Exception as e:
                print(f"     ❌ Chyba při vytváření {config_topic}: {e}")
        
        print(f"  ✅ Střídač {inv_id}: Vytvořeno {len(DEFINICE_SENZORU)} senzorů")
    
    print(f"\n✅ Discovery dokončeno!")
    print(f"   📊 Vytvořeno {total_entities} entit (2 střídače × {len(DEFINICE_SENZORU)} senzorů)")
    print(f"   📨 State topic: {state_topic}")
    print(f"   🏷️  Zařízení: Grand Glow Car Charger")
    print(f"\n💡 Struktura entit:")
    print(f"   - gg_4_mode, gg_4_PV_power, ...")
    print(f"   - gg_5_mode, gg_5_PV_power, ...")
    return True


# ==========================================
# --- 5. SYNCHRONIZACE ČASU ---
# ==========================================

def synchronize_time(ser_port):
    """
    Synchronizuje datum a čas na střídači.
    Vrací True při úspěchu, False při chybě.
    """
    try:
        now = datetime.datetime.now()
        date_cmd = build_date_command()
        time_cmd = build_time_command()
        
        if debug >= 1:
            print(f"  ⏰ Synchronizuji čas: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Nastavení data
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(date_cmd)
        response_d = ser.read(7)
        ser.close()
        time.sleep(0.2)
        
        # Nastavení času
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(time_cmd)
        response_t = ser.read(7)
        ser.close()
        
        if response_t == b'ACK\r' and response_d == b'ACK\r':
            if debug >= 1:
                print(f"  ✅ Synchronizace času úspěšná")
            return True
        else:
            if debug >= 1:
                print(f"  ⚠️ Synchronizace času selhala (date: {response_d}, time: {response_t})")
            return False
            
    except Exception as e:
        print(f"  ❌ Chyba při synchronizaci času: {e}")
        return False


# ==========================================
# --- 6. ČTENÍ DAT ZE STŘÍDAČE ---
# ==========================================

def read_inverter_data(inv_num, ser_port):
    """Přečte data z jednoho střídače."""
    
    result = {}
    
    try:
        # GLINE
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GLINE)
        response2 = ser.read(78)
        ser.close()
        time.sleep(0.1)
        
        # GMOD
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GMOD)
        response3 = ser.read(5)
        ser.close()
        time.sleep(0.1)
        
        # GBAT
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GBAT)
        response4 = ser.read(27)
        ser.close()
        time.sleep(0.1)
        
        # GCHG
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GCHG)
        response5 = ser.read(110)
        ser.close()
        time.sleep(0.1)
        
        # GOP
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GOP)
        response6 = ser.read(110)
        ser.close()
        time.sleep(0.1)
        
        # GINV
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GINV)
        response7 = ser.read(20)
        ser.close()
        time.sleep(0.1)
        
        # GPV
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GPV)
        response8 = ser.read(150)
        ser.close()
        time.sleep(0.1)
        
        # BL
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_BL)
        response12 = ser.read(7)
        ser.close()
        time.sleep(0.1)
        
        # GPDAT0
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_GPDAT0)
        response13 = ser.read(500)
        ser.close()
        time.sleep(0.1)
        
        # CPR?
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_CPR)
        response14 = ser.read(5)
        ser.close()
        time.sleep(0.1)
        
        # OPR?
        ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, 
                          stopbits=serial.STOPBITS_ONE, timeout=tim)
        ser.write(CMD_OPR)
        response15 = ser.read(5)
        ser.close()
        
        # Kontrola chyb
        if (response13[0:1] != b'(' or response2[0:1] != b'(' or 
            response3[0:1] != b'(' or response4[0:1] != b'(' or 
            response5[0:1] != b'(' or response6[0:1] != b'(' or 
            response7[0:1] != b'(' or response8[0:1] != b'(' or 
            response12[0:1] != b'B'):
            if debug >= 1:
                print(f"  ❌ Chyba čtení střídače {inv_num} - neplatné odpovědi")
            return None
        
        # --- Dekódování dat ---
        
        # GLINE
        try:
            utility_voltage = float(response2[1:6])
        except:
            utility_voltage = 0
        try:
            utility_frequency = float(response2[7:12])
        except:
            utility_frequency = 0
        try:
            utility_today_consumption = float(response2[60:64]) / 100
        except:
            utility_today_consumption = 0
        try:
            utility_total_generation_exp = int(response2[66:70])
            utility_total_generation_bas = int(response2[71:76])
            utility_total_consumption = ((100000 * utility_total_generation_exp) + 
                                        utility_total_generation_bas) / 100
        except:
            utility_total_consumption = 0
        
        # GBAT
        try:
            battery_voltage = float(response4[1:6])
        except:
            battery_voltage = 0
        try:
            battery_discharge_current = float(response4[8:13])
        except:
            battery_discharge_current = 0
        
        # GCHG
        try:
            charging_voltage = float(response5[7:12])
        except:
            charging_voltage = 0
        try:
            charging_current = float(response5[16:21])
        except:
            charging_current = 0
        try:
            charging_modes = response5[81:82]
        except:
            charging_modes = b''
        
        if charging_modes == b'0':
            charging_mode = "Stop Charging"
        elif charging_modes == b'1':
            charging_mode = "Constant Current"
        elif charging_modes == b'2':
            charging_mode = "Constant Voltage"
        elif charging_modes == b'3':
            charging_mode = "Floating"
        else:
            charging_mode = "Unknown"
        
        # GOP
        try:
            out_voltage = float(response6[1:6])
        except:
            out_voltage = 0
        try:
            out_frequency = float(response6[7:12])
        except:
            out_frequency = 0
        try:
            out_current_gop = float(response6[14:19])
        except:
            out_current_gop = 0
        try:
            out_power = int(response6[27:31])
        except:
            out_power = 0
        try:
            out_load = int(response6[57:59])
        except:
            out_load = 0
        try:
            out_today_power = int(response6[72:77]) / 100
        except:
            out_today_power = 0
        try:
            out_total_power_exp = int(response6[78:83])
            out_total_power_bas = int(response6[84:89])
            out_total_power = ((100000 * out_total_power_exp) + out_total_power_bas) / 100
        except:
            out_total_power = 0
        
        # GINV
        try:
            out_current = float(response7[13:18])
        except:
            out_current = 0
        
        # GPV
        try:
            pv_string_voltage = float(response8[1:6])
        except:
            pv_string_voltage = 0
        try:
            pv_charging_current = float(response8[13:18])
        except:
            pv_charging_current = 0
        try:
            pv_current = float(response8[19:24])
        except:
            pv_current = 0
        try:
            pv_power = float(response8[25:30])
        except:
            pv_power = 0
        try:
            pv_today_generation = float(response8[103:108]) / 100
        except:
            pv_today_generation = 0
        try:
            pv_total_generation_exp = int(response8[109:114])
            pv_total_generation_bas = int(response8[115:120])
            pv_total_generation = ((100000 * pv_total_generation_exp) + 
                                  pv_total_generation_bas) / 100
        except:
            pv_total_generation = 0
        
        # BL
        try:
            battery_capacity = int(response12[2:5])
        except:
            battery_capacity = 0
        
        # GMOD
        if response3 == b'(B\r':
            gmod = 'Battery mode'
        elif response3 == b'(L\r':
            gmod = 'Utility mode'
        elif response3 == b'(P\r':
            gmod = 'Initial power-up mode'
        elif response3 == b'(S\r':
            gmod = 'Standby mode'
        elif response3 == b'(F\r':
            gmod = 'Failure mode'
        elif response3 == b'(D\r':
            gmod = 'Shutdown mode'
        elif response3 == b'(X\r':
            gmod = 'Test pattern'
        else:
            gmod = 'Unknown'
        
        # GPDAT0
        try:
            if response13[10:11] == b"":
                par_mode = "Single Mode"
            elif int(response13[10:11]) == 0:
                par_mode = "Single Mode"
            elif int(response13[10:11]) == 1:
                par_mode = "Single Phase Parallel Mode"
            elif int(response13[10:11]) == 2:
                par_mode = "R-Phase Parallel Mode"
            elif int(response13[8:9]) == 3:
                par_mode = "S-Phase Parallel Mode"
            elif int(response13[8:9]) == 4:
                par_mode = "T-Phase Parallel Mode"
            else:
                par_mode = "Unknown"
        except:
            par_mode = "Unknown"
        
        try:
            battery_current = float(response13[62:67])
        except:
            battery_current = 0
        try:
            internal_temperature = float(response13[102:107])
        except:
            internal_temperature = 0
        
        # CPR?
        try:
            chpr = int(response14[1:3])
        except:
            chpr = 5
        if chpr == 0:
            chprior = "Utility"
        elif chpr == 1:
            chprior = "PV first"
        elif chpr == 2:
            chprior = "Utility+PV"
        elif chpr == 3:
            chprior = "Only PV"
        else:
            chprior = "Read Error"
        
        # OPR?
        try:
            opr = int(response15[1:3])
        except:
            opr = 3
        if opr == 0:
            oprior = "Utility"
        elif opr == 1:
            oprior = "PV first"
        elif opr == 2:
            oprior = "PV-BAT-UTI"
        else:
            oprior = "Read Error"
        
        # --- Sestavení výsledku ---
        time_print = datetime.datetime.now().strftime("%H:%M")
        
        # charger_power - prozatím 0
        charger_power = 0
        
        result = {
            f"gg_{inv_num}_mode": gmod,
            f"gg_{inv_num}_PV_string_voltage": round(pv_string_voltage, 1),
            f"gg_{inv_num}_PV_charging_current": round(pv_charging_current, 2),
            f"gg_{inv_num}_PV_Today_generation": round(pv_today_generation, 2),
            f"gg_{inv_num}_PV_Total_generation": round(pv_total_generation, 2),
            f"gg_{inv_num}_out_current": round(out_current, 2),
            f"gg_{inv_num}_out_voltage": round(out_voltage, 1),
            f"gg_{inv_num}_out_frequency": round(out_frequency, 2),
            f"gg_{inv_num}_out_today_power": round(out_today_power, 2),
            f"gg_{inv_num}_out_total_power": round(out_total_power, 2),
            f"gg_{inv_num}_utility_voltage": round(utility_voltage, 1),
            f"gg_{inv_num}_utility_frequency": round(utility_frequency, 2),
            f"gg_{inv_num}_load_inverter": out_load,
            f"gg_{inv_num}_battery_voltage": round(battery_voltage, 1),
            f"gg_{inv_num}_battery_discharge_current": round(battery_discharge_current, 2),
            f"gg_{inv_num}_charging_voltage": round(charging_voltage, 1),
            f"gg_{inv_num}_charging_current": round(charging_current, 2),
            f"gg_{inv_num}_battery_capacity": battery_capacity,
            f"gg_{inv_num}_out_current_gop": round(out_current_gop, 2),
            f"gg_{inv_num}_out_power": int(out_power),
            f"gg_{inv_num}_PV_power": int(pv_power),
            f"gg_{inv_num}_PV_current": round(pv_current, 2),
            f"gg_{inv_num}_charging_mode": charging_mode,
            f"gg_{inv_num}_time_pub": time_print,
            f"gg_{inv_num}_Total_generation": round(pv_total_generation, 2),
            f"gg_{inv_num}_Today_Utility_consumption": round(utility_today_consumption, 2),
            f"gg_{inv_num}_Total_Utility_consumption": round(utility_total_consumption, 2),
            f"gg_{inv_num}_battery_current": round(battery_current, 2),
            f"gg_{inv_num}_internal_temperature": round(internal_temperature, 1),
            f"gg_{inv_num}_mode_prior": oprior,
            f"gg_{inv_num}_mode_phase": par_mode,
            f"gg_{inv_num}_charging_mode_prior": chprior,
            f"gg_{inv_num}_charger_power": round(charger_power, 1)
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Chyba při čtení střídače {inv_num}: {e}")
        return None


# ==========================================
# --- 7. HLAVNÍ SMYČKA ---
# ==========================================

def main():
    print("\n" + "=" * 60)
    print("🤖 DAEMON PRO STŘÍDAČE 4 A 5 (GRAND GLOW CAR CHARGER)")
    print("=" * 60)
    
    # Kontrola argumentů pro discovery
    if len(sys.argv) > 1 and sys.argv[1] == '--discovery':
        create_discovery()
        sys.exit(0)
    
    # Porty pro střídače 4 a 5
    inverters = {
        4: ser_port_inv_4,
        5: ser_port_inv_5
    }
    
    print(f"\n🌐 Spouštím monitoring střídačů 4 a 5...")
    print(f"   🏷️  Název zařízení: Grand Glow Car Charger")
    print(f"   📡 Střídač 4: {ser_port_inv_4}")
    print(f"   📡 Střídač 5: {ser_port_inv_5}")
    print(f"   🔄 Interval: {timer} sekund")
    print(f"   📨 MQTT state topic: {state_topic}")
    print(f"   ⏰ Synchronizace času: denně mezi 00:05 - 00:10")
    
    # Počáteční publikace
    publish_data_fail = {
        "gg_4_time_pub": "STARTING",
        "gg_5_time_pub": "STARTING",
        "status": "starting",
        "device": "Grand Glow Car Charger"
    }
    payload = json.dumps(publish_data_fail)
    mqtt_publish(payload)
    
    err_counter = 0
    last_sync_day = None
    sync_done_today = False
    
    while True:
        now = datetime.datetime.now()
        
        print(f"\n📊 Měření: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # --- Kontrola synchronizace času ---
        if now.hour == 0 and 5 <= now.minute <= 10:
            if not sync_done_today:
                print(f"\n⏰ Spouštím denní synchronizaci času ({now.strftime('%Y-%m-%d %H:%M:%S')})...")
                success = 0
                for inv_num, ser_port in inverters.items():
                    print(f"  📡 Synchronizuji střídač {inv_num}...")
                    if synchronize_time(ser_port):
                        success += 1
                    time.sleep(0.5)
                print(f"  ✅ Synchronizace dokončena: {success}/{len(inverters)} střídačů")
                sync_done_today = True
        else:
            if sync_done_today and now.hour == 0 and now.minute > 10:
                sync_done_today = False
            if now.day != last_sync_day:
                last_sync_day = now.day
                sync_done_today = False
        
        # --- Čtení dat ---
        all_data = {}
        success_count = 0
        
        for inv_num, ser_port in inverters.items():
            print(f"  🔍 Čtu střídač {inv_num}...")
            data = read_inverter_data(inv_num, ser_port)
            
            if data:
                all_data.update(data)
                success_count += 1
                if debug >= 1:
                    print(f"    ✅ Střídač {inv_num} - OK")
                err_counter = 0
            else:
                print(f"    ❌ Střídač {inv_num} - CHYBA ČTENÍ")
                err_counter += 1
                if err_counter >= 10:
                    print("❌ Příliš mnoho chyb čtení, restartuji...")
                    err_counter = 0
                    time.sleep(10)
            
            time.sleep(0.3)
        
        # --- Odeslání dat ---
        if all_data:
            all_data["sync_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
            all_data["status"] = "running"
            all_data["inverters_ok"] = success_count
            all_data["device"] = "Grand Glow Car Charger"
            payload = json.dumps(all_data)
            mqtt_publish(payload)
            if debug >= 1:
                print(f"  📤 Odesláno {len(all_data)} hodnot, {success_count}/{len(inverters)} střídačů OK")
        else:
            print("  ❌ Žádná data k odeslání")
            status_data = {
                "status": "error",
                "sync_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "inverters_ok": 0,
                "device": "Grand Glow Car Charger"
            }
            payload = json.dumps(status_data)
            mqtt_publish(payload)
        
        print(f"  ⏳ Čekám {timer} sekund...")
        time.sleep(timer)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Daemon ukončen uživatelem")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Neočekávaná chyba: {e}")
        sys.exit(1)