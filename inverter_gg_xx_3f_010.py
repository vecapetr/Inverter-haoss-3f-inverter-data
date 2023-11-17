#---- build 3f version --------candidate---testing---231117----
import serial
import logging
#from logging.handlers import RotatingFileHandler
import time, datetime
import json
import sys
import binascii
import paho.mqtt.publish as publish
import random
from paho.mqtt import client as mqtt_client
from datetime import datetime


# ---------------------------variables initialization---------- 
inverters             = 3                                # amount of inverter/s (max 9)
MQTT_username         = 'inverter'                       # your MQTT username
MQTT_password         = 'Grand_Glow_03'                  # your MQTT password
broker = "192.168.1.22"                                  # MQTT Broker
MQTT_port = 1883                                         # MQTT port
state_topic = "homeassistant/sensor/gg/state"            # MQTT topic
client_id = 'c67350b3bd694128b12d8f77a18e5aa4'           # HA client id

ser_port_inv_1 = "/dev/ttyUSB0"                          # usb device inv 1
ser_port_inv_2 = "/dev/ttyUSB1"                          # usb device inv 2
ser_port_inv_3 = "/dev/ttyUSB3"                          # usb device inv 3

ser_baudrate = 2400                                      # serial baudrate
tim = 0.5                                                # serial timeout
timer = 60                                               # timer
debug = 0                                                # print all results and payload 0-stop, 1-data, 2-data+paylods
charging_mode = "N/A"

#------------------commands--------------------

msg1 = bytes.fromhex("46 0D") #F
msg2 = bytes.fromhex("47 4c 49 4e 45 0D") #GLINE
msg3 = bytes.fromhex("47 4D 4F 44 0D") #GMOD
msg4 = bytes.fromhex("47 42 41 54 0D") #GBAT
msg5 = bytes.fromhex("47 43 48 47 0D") #GCHG
msg6 = bytes.fromhex("47 4f 50 0D") #GOP
msg7 = bytes.fromhex("47 49 4e 56 0D") #GINV
msg8 = bytes.fromhex("47 50 56 0D") #GPV
msg9 = bytes.fromhex("44 41 54 45 3f 3f 3f 3f 3f 3f 0D") #DATE
msg10 = bytes.fromhex("54 49 4d 45 3f 3f 3f 3f 3f 3f 0D") #TIME
msg11 = bytes.fromhex("53 56 46 57 0D") #SVFW
msg12 = bytes.fromhex("42 4C 0D") #BL
#----------------------Mqtt publish-------------------------

def mqtt_publish():
    state_topic = "homeassistant/sensor/gg/state"
    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    publish.single(state_topic, payload, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print()
    print('...mqtt publish... : ok in', current_time, end="\r")
    
def actual_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    
#--------synchro date time -------------------

def synchro_date():
    now = datetime.now()
    current_time = now.strftime("%H%M%S")
    current_date = now.strftime("%y%m%d")
    hex_date_comm = "DATE"+current_date+"\r"
    hex_date = hex_date_comm.encode("utf-8").hex()
    msg_date = bytes.fromhex(hex_date)
    hex_time_comm = "TIME"+current_time+"\r"
    hex_time = hex_date_comm.encode("utf-8").hex()
    msg_time = bytes.fromhex(hex_date)
    for inv in range(inverters):
	    if inv == 0:
		    ser_port = (ser_port_inv_1)
	    elif inv == 1:
		    ser_port = (ser_port_inv_2)
	    elif inv == 2:
		    ser_port = (ser_port_inv_3)
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg_date)
	    response_d = ser.read(7)
	    #print(response_d)
	    ser.close()
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg_time)
	    response_t = ser.read(7)
	    #print(response_t)
	    ser.close()
	    if not response_t == b'ACK\r' and not response_d == b'ACK\r':
		    print()
		    print("INV "+str(inv+1)+"synchro non accepted")

# --------------------------mqtt (HA)  sensor definition----------------

ser = serial.Serial(ser_port_inv_1, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
ser.write(msg11)
response11 = ser.read(6)
fw = float(response11[1:6])
ser.close()

MQTT_auth = None
MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
msg          ={}
config       = 1
names        =["mode", "PV_string_voltage", "PV_charging_current",
	     "Today_generation", "out_current", "out_voltage",
	     "out_frequency", "utility_voltage", "utility_frequency",
	     "load_inverter", "battery_voltage", "battery_discharge_current",
	     "charging_voltage", "charging_current", "charging_mode", "battery_capacity",
	     "out_current_gop", "out_power", "PV_power","PV_current",
	     "time_pub", "Total_generation"]

ids          =["mode", "PV_string_voltage", "PV_charging_current",
	     "today_generation", "out_current", "out_voltage",
	     "out_frequency", "utility_voltage", "utility_frequency",
	     "load_inverter", "battery_voltage", "battery_discharge_current",
	     "charging_voltage", "charging_current", "charging_mode", "battery_capacity", 
	     "out_current_gop", "out_power", "PV_power", "PV_current",
	     "time_pub", "Total_generation"]

dev_cla      =["None", "voltage", "current",
	      "power", "current", "voltage",
	      "frequency", "voltage", "frequency",
	      "power_factor", "voltage", "current",
	      "voltage", "current", "None", "battery",
	      "current", "power", "power", "current",
	      "None", "power"]

stat_cla     =["None", "measurement", "measurement", 
	      "measurement", "measurement", "measurement", 
	      "measurement", "measurement", "measurement", 
	      "measurement", "measurement", "measurement",
	      "measurement", "measurement", "None", "measurement",
	      "measurement", "measurement", "measurement", "measurement",
	      "None", "measurement"]

unit_of_meas =["None", "V", "A", "W", "A", "V", "Hz", "V", "Hz", "%", "V", "A", "V", "A", "None", "%", "A", "W", "W", "A", "None", "kW"]

# -----------------------define system sensors----------------------------
b = 0
print()
print ("...define system sensors...")
for inv in range(inverters):
    for n in range(22):
	    state_topic          = "homeassistant/sensor/gg/"+str(config)+"/config"
	    msg ["name"]         = "gg_"+str(inv+1)+"_"+names[n]
	    msg ["stat_t"]       = "homeassistant/sensor/gg/state"
	    msg ["uniq_id"]      = "gg_"+str(inv+1)+"_"+ids[n]
	    if dev_cla[n] != "None":
    		msg ["dev_cla"]  = dev_cla[n]
	    if stat_cla[n] != "None":
    		msg ["stat_cla"]  = stat_cla[n]
	    if unit_of_meas[n] != "None":
    		msg ["unit_of_meas"] = unit_of_meas[n]
	    msg ["val_tpl"]      = "{{ value_json." +str(inv+1) +"_" + ids[n]+ "}}"
	    msg ["dev"]          = {"identifiers": ["gg_"+str(inv+1)], "manufacturer": "Grand Glow", "model": "HFM PRO","name": "Grand Glow", "sw_version": fw}
	    payload              = json.dumps(msg)
	    if debug == 2:
		    print(payload)
	    publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
	    msg                  ={}
	    config               = config +1
	    b = b + 1.51
	    print(int(b), "%", end="\r")
	    time.sleep(1)
    inv = inv + 1

time.sleep(1)
#-------------------------define individual sensors-------------------------
b = 0
print("...define individual sensors...")
for inv in range(inverters):
	for n in range(22):
	    state_topic          = "homeassistant/sensor/gg/"+str(config)+"/config"
	    msg ["name"]         = "gg_"+str(inv+1)+"_"+names[n]
	    msg ["stat_t"]       = "homeassistant/sensor/gg/state"
	    msg ["uniq_id"]      = "gg_"+str(inv+1)+"_"+ids[n]
	    if dev_cla[n] != "None":
		    msg ["dev_cla"]  = dev_cla[n]
	    if stat_cla[n] != "None":
		    msg ["stat_cla"]  = stat_cla[n]                    
	    if unit_of_meas[n] != "None":
		    msg ["unit_of_meas"] = unit_of_meas[n]
	    msg ["val_tpl"]      = "{{ value_json.gg_"+str(inv+1)+"_" + ids[n]+ "}}"
	    msg ["dev"]          = {"identifiers": ["gg_"+str(inv+1)],"manufacturer": "Grand Glow","model": "HFM PRO","name": "Grand Glow","sw_version": fw}
	    payload              = json.dumps(msg)
	    if debug == 2:
		    print(payload)
	    publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
	    msg                  ={}
	    config               = config +1
	    b = b + 1.51
	    print(int(b), "%", end="\r")
	    time.sleep(1)

print("...MQTT initialization completed...")

#-----------------write---and---read---ser_port--------------------------
publish_data = {}
loop = 29.3
while True:
	actual_time()
	for inv in range(inverters):
	    if inv == 0:
		    ser_port = (ser_port_inv_1)
	    elif inv == 1:
		    ser_port = (ser_port_inv_2)
	    elif inv == 2:
		    ser_port = (ser_port_inv_3)
	    elif inv == 3:
		    ser_port = (ser_port_inv_4)
	    elif inv == 4:
		    ser_port = (ser_port_inv_5)
	    elif inv == 5:
		    ser_port = (ser_port_inv_6)
	    elif inv == 6:
		    ser_port = (ser_port_inv_7)
	    elif inv == 7:
		    ser_port = (ser_port_inv_8)
	    elif inv == 8:
		    ser_port = (ser_port_inv_9)
	    print("...waiting for inverters data...",  end="\r")
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    #ser.write(msg1)
	    #response1 = ser.read(21)
	    #print (response1)
	    #ser.close()
	    #print (msg2)
	    ser.write(msg2)
	    response2 = ser.read(78)
	    #print(response2)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg3)
	    response3 = ser.read(5)
	    #print (response3)
	    gmod = "ERROR"
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg4)
	    response4 = ser.read(27)
	    #print (response4)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg5)
	    response5 = ser.read(110)
	    #print (response5)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg6)
	    response6 = ser.read(110)
	    #print (response6)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg7)
	    response7 = ser.read(20)
	    #print (response7)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg8)
	    response8 = ser.read(120)
	    #print (response8)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg12)
	    response12 = ser.read(7)
	    #print (response12)
	    ser.close()

	    time.sleep(0.5)

	#results
	#GLINE
	    utility_voltage = float(response2[1:6])
	    utility_frequency = float(response2[7:12])
	    utility_high_lost_voltage = float(response2[14:18])
	    utility_low_lost_voltage = float(response2[20:24])
	    load_inverter = int(response6[56:58])
	    if debug == 1 or debug == 2:
		    print()
		    print ("UTILITY VOLTAGE", utility_voltage, "V")
		    print ("UTILITY FREQUECY", utility_frequency, "Hz")
		    print ("PERCENTAGE LOAD", load_inverter, "%")
	#GBAT
	    battery_voltage = float(response4[1:6])
	    battery_discharge_current = float(response4[8:13])
	    if debug == 1 or debug == 2:
		    print ("BATTERY VOLTAGE", battery_voltage, "V")
		    print ("BATTERY DISCHARGE CURRENT", battery_discharge_current, "A")
	#GCHG 
	    charging_voltage = float(response5[7:12])
	    charging_current = float(response5[16:21])
	    charging_modes = response5[81:82]
	    if debug == 1 or debug == 2:
		    print("---", charging_modes,"-------")
	    if charging_modes == b'0':
		    charging_mode = "Stop Charging"
	    elif charging_modes == b'1':
		    charging_mode = "Constant Current"
	    elif charging_modes == b'2':
		    charging_mode = "Constant Voltage"
	    elif charging_modes == b'3':
		    charging_mode = "Floating"
	    if debug == 1 or debug == 2:
		    print(charging_mode)
		    print ("CHARGING VOLTAGE", charging_voltage, "V")
		    print ("CHARGING CURRENT", charging_current, "A")
	#GOP
	    out_voltage = float(response6[1:6])
	    out_frequency = float(response6[7:12])
	    out_current_gop = float(response6[14:19])
	    out_power = int(response6[27:31])
	    if debug == 1 or debug == 2:
		    print ("OUTPUT VOLTAGE", out_voltage, "V")
		    print ("OUTPUT FREQUENCY", out_frequency, "Hz")
		    print ("OUTPUT CURRENT GOP", out_current_gop, "A")
		    print ("OUTPUT ACTIVE POWER", out_power, "W")
	#GINV
	    out_current = float(response7[13:18])
	    if debug == 1 or debug == 2:
		    print ("OUTPUT CURRENT GINV", out_current, "A")
	#GPV
	    pv_string_voltage = float(response8[1:6])
	    pv_charging_current = float(response8[14:18])
	    pv_current = float(response8[20:24])
	    pv_power = float(response8[26:30])
	    pv_generation_today = 10*float(response8[104:108])
	    pv_total_generation_ext = response8[110:114]
	    pv_total_generation_bas = response8[116:120]
	    if pv_total_generation_ext == b'':
		    pv_total_generation_ext = 0
	    if pv_total_generation_bas == b'':
		    pv_total_generation_ext = 0
	    pv_total_generation = 0
	    #print(response8)
	    #pv_total_generation = (pv_total_generation_bas + (100000*pv_total_generation_ext))/1000
	    #print(pv_total_generation_ext, pv_total_generation_bas, pv_total_generation)

	    if debug == 1 or debug == 2:
		    print ("PV GENERATION TODAY", pv_generation_today, "W")
		    print ("PV GENERATION TOTAL", pv_total_generation, "kW")
		    print ("PV CHARGING CURRENT", pv_charging_current, "A")
		    print ("PV POWER", pv_power, "W")
		    print ("STRING VOLTAGE", pv_string_voltage, "V")
		    print ("PV CURRENT", pv_current, "A")
	#BL
	    battery_capacity = int(response12[3:5])
	    if debug == 1 or debug == 2:
		    print ("BATTERY CAPACITY", battery_capacity, "%")

	#prevod na vysledek GMOD

	    if response3 == b'(B\r':
		    gmod = ('Battery  mode')
	    elif response3 == b'(L\r':
		    gmod = ('Utility mode')
	    elif response3 == b'(P\r':
		    gmod = ('Initial power-up mode')
	    elif response3 == b'(S\r':
		    gmod = ('Standby mode')
	    elif response3 == b'(F\r':
		    gmod = ('Failure mode')
	    elif response3 == b'(D\r':
		    gmod = ('Shutdown mode')
	    elif response3 == b'(X\r':
		    gmod = ('Test patern')
	    if debug == 1 or debug == 2:
		    print (gmod)

	#serialize json
	    now = datetime.now()
	    time_print = now.strftime("DATE %Y:%m:%d TIME %H:%M")
	    publish_data ['gg_'+str(inv+1)+'_PV_string_voltage'] = pv_string_voltage
	    publish_data ['gg_'+str(inv+1)+'_PV_charging_current'] = pv_charging_current
	    publish_data ['gg_'+str(inv+1)+'_today_generation'] = pv_generation_today
	    publish_data ['gg_'+str(inv+1)+'_out_current'] = out_current
	    publish_data ['gg_'+str(inv+1)+'_out_voltage'] = out_voltage
	    publish_data ['gg_'+str(inv+1)+'_out_frequency'] = out_frequency
	    publish_data ['gg_'+str(inv+1)+'_utility_voltage'] = utility_voltage
	    publish_data ['gg_'+str(inv+1)+'_utility_frequency'] = utility_frequency
	    publish_data ['gg_'+str(inv+1)+'_load_inverter'] = load_inverter
	    publish_data ['gg_'+str(inv+1)+'_battery_voltage'] = battery_voltage
	    publish_data ['gg_'+str(inv+1)+'_battery_discharge_current'] = battery_discharge_current
	    publish_data ['gg_'+str(inv+1)+'_charging_voltage'] = charging_voltage
	    publish_data ['gg_'+str(inv+1)+'_charging_current'] = charging_current
	    publish_data ['gg_'+str(inv+1)+'_battery_capacity'] = battery_capacity
	    publish_data ['gg_'+str(inv+1)+'_out_current_gop'] = out_current_gop
	    publish_data ['gg_'+str(inv+1)+'_out_power'] = out_power
	    publish_data ['gg_'+str(inv+1)+'_PV_power'] = pv_power
	    publish_data ['gg_'+str(inv+1)+'_PV_current'] = pv_current
	    publish_data ['gg_'+str(inv+1)+'_mode'] = gmod
	    publish_data ['gg_'+str(inv+1)+'_charging_mode'] = charging_mode
	    publish_data ['gg_'+str(inv+1)+'_time_pub'] = time_print
	    publish_data ['gg_'+str(inv+1)+'_total_generation'] = pv_total_generation
	    loop = loop + (inverters/10)
	    if loop > 30:
		    synchro_date()
		    loop = 1
	    inv = inv + 1
	payload = json.dumps(publish_data)
	if debug == 2:
	    print(payload)
	mqtt_publish()
	print()
	for t in range(timer - 30):
	    print(timer - 1 - t, "s                                                    ", end="\r")
	    time.sleep(1)

# -----------FINISH-----------





