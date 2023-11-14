#---- build 3f version --------candidate---testing---231110----
import serial
import logging
from logging.handlers import RotatingFileHandler
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
charging_mode = "ERROR"

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
    publish.single(state_topic, payload1, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    time.sleep(1)
    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    publish.single(state_topic, payload2, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    time.sleep(1)
    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    publish.single(state_topic, payload3, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    publish.single(state_topic, payload4, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print()
    print('...mqtt publish... : ok in', current_time, end="\r")

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
	    response_d = ser.read(5)
	    ser.close()
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg_time)
	    response_t = ser.read(5)
	    ser.close()
	    if response_t == "ACK\r" and response_d == "ACK\r":
    		    print("synchro accepted")

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
	     "out_current_gop", "out_power", "PV_power","PV_current"]

ids          =["mode", "PV_string_voltage", "PV_charging_current",
	     "today_generation", "out_current", "out_voltage",
	     "out_frequency", "utility_voltage", "utility_frequency",
	     "load_inverter", "battery_voltage", "battery_discharge_current",
	     "charging_voltage", "charging_current", "charging_mode", "battery_capacity", 
	     "out_current_gop", "out_power", "PV_power", "PV_current"]

dev_cla      =["None", "voltage", "current",
	      "power", "current", "voltage",
	      "frequency", "voltage", "frequency",
	      "power_factor", "voltage", "current",
	      "voltage", "current", "None", "battery",
	      "current", "power", "power", "current"]

stat_cla     =["None", "measurement", "measurement", 
	      "measurement", "measurement", "measurement", 
	      "measurement", "measurement", "measurement", 
	      "measurement", "measurement", "measurement",
	      "measurement", "measurement", "None", "measurement",
	      "measurement", "measurement", "measurement", "measurement"]

unit_of_meas =["None", "V", "A", "W", "A", "V", "Hz", "V", "Hz", "%", "V", "A", "V", "A", "None", "%", "A", "W", "W", "A"]

# -----------------------define system sensors----------------------------
b = 0
print()
print ("...define system sensors...")
for inv in range(inverters):
    for n in range(20):
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
	    b = b + 1.67
	    print(int(b), "%", end="\r")
	    time.sleep(1)
    inv = inv + 1

time.sleep(1)
#-------------------------define individual sensors-------------------------
b = 0
print("...define individual sensors...")
for inv in range(inverters):
	for n in range(20):
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
	    b = b + 1.67
	    print(int(b), "%", end="\r")
	    time.sleep(1)

print("...MQTT initialization completed...")

#-----------------write---and---read---ser_port--------------------------

loop = 29.3
while True:
	for inv in range(inverters):
	    if inv == 0:
		    ser_port = (ser_port_inv_1)
	    elif inv == 1:
		    ser_port = (ser_port_inv_2)
	    elif inv == 2:
		    ser_port = (ser_port_inv_3)
	    #ser_port["ser_ports"] = ser_ports[inv]
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
	    pv_generation_today = 10*float(response8[102:108])
	    #pv_generation_total = 
	    if debug == 1 or debug == 2:
		    print ("PV GENERATION TODAY", pv_generation_today, "W")
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


	    json_data = {'gg_'+str(inv+1)+'_PV_string_voltage': pv_string_voltage,
			'gg_'+str(inv+1)+'_PV_charging_current': pv_charging_current,
			'gg_'+str(inv+1)+'_today_generation': pv_generation_today,
			'gg_'+str(inv+1)+'_out_current': out_current,
			'gg_'+str(inv+1)+'_out_voltage': out_voltage,
			'gg_'+str(inv+1)+'_out_frequency': out_frequency,
			'gg_'+str(inv+1)+'_utility_voltage': utility_voltage,
			'gg_'+str(inv+1)+'_utility_frequency': utility_frequency,
			'gg_'+str(inv+1)+'_load_inverter': load_inverter,
			'gg_'+str(inv+1)+'_battery_voltage': battery_voltage,
			'gg_'+str(inv+1)+'_battery_discharge_current': battery_discharge_current,
			'gg_'+str(inv+1)+'_charging_voltage': charging_voltage,
			'gg_'+str(inv+1)+'_charging_current': charging_current,
			'gg_'+str(inv+1)+'_battery_capacity': battery_capacity,
			'gg_'+str(inv+1)+'_out_current_gop': out_current_gop,
			'gg_'+str(inv+1)+'_out_power': out_power,
			'gg_'+str(inv+1)+'_PV_power': pv_power,
			'gg_'+str(inv+1)+'_PV_current': pv_current
			}

	    if inv == 0:
		    payload1 = json.dumps(json_data)
		    gmod1 = gmod
		    charging_mode1 = charging_mode
	    elif inv == 1:
		    payload2 = json.dumps(json_data)
		    gmod2 = gmod
		    charging_mode2 = charging_mode
	    elif inv == 2:
		    payload3 = json.dumps(json_data)
		    gmod3 = gmod
		    charging_mode3 = charging_mode
	    loop = loop + 0.3
	    if loop > 30:
		    synchro_date()
		    loop = 1
	    inv = inv + 1
	json_data1 = {'gg_1_mode': gmod1,
		    'gg_2_mode': gmod2,
		    'gg_3_mode': gmod3,
		    'gg_1_charging_mode': charging_mode1,
		    'gg_2_charging_mode': charging_mode2,
		    'gg_3_charging_mode': charging_mode3
		    }
	payload4 = json.dumps(json_data1)
	if debug == 2:
	    print(payload1, payload2, payload3, payload4)
	mqtt_publish()
	print()
	for t in range(timer):
	    print(timer - 1 - t, "s                                                    ", end="\r")
	    time.sleep(1)

# -----------FINISH-----------





