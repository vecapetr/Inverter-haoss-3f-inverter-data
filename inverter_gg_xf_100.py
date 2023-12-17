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
tim = 1                                                  # serial timeout
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
msg13 = bytes.fromhex("47 50 44 41 54 30 0D") #GPDAT
msg14 = bytes.fromhex("43 50 52 3f 3f 0d")#CPR


#----------------------Mqtt publish-------------------------

def mqtt_publish():
    state_topic = "homeassistant/sensor/gg/state"
    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    publish.single(state_topic, payload, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    print('.......mqtt publish....... : ok in', current_time, end="\r")

#--------actual time--------------    

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
    hex_time = hex_time_comm.encode("utf-8").hex()
    msg_time = bytes.fromhex(hex_time)
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
		    print("INV "+str(inv+1)+" synchro not accepted",  end="\r")
    print(".......inverters in time.......                       ")
    time.sleep(5)
# --------------------------mqtt (HA)  sensor definition----------------
def create_sensor():
    ser = serial.Serial(ser_port_inv_3, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
    ser.write(msg11)
    response11 = ser.read(6)
    fw = float(response11[1:6])
    ser.close()

    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    msg          ={}
    config       = 1
    names        =["mode", "PV_string_voltage", "PV_charging_current",
		"PV_Today_generation", "out_current", "out_voltage",
		"out_frequency", "utility_voltage", "utility_frequency",
		"load_inverter", "battery_voltage", "battery_discharge_current",
		"charging_voltage", "charging_current", "charging_mode", "battery_capacity",
		"out_current_gop", "out_power", "PV_power","PV_current",
		"time_pub", "Total_generation", 'Today_Utility_consumption',
		"Total_Utility_consumption", "out_today_power", "out_total_power",
		"PV_Total_generation","battery_current", "internal_temperature"]

    ids          =["mode", "PV_string_voltage", "PV_charging_current",
		"PV_Today_generation", "out_current", "out_voltage",
		"out_frequency", "utility_voltage", "utility_frequency",
		"load_inverter", "battery_voltage", "battery_discharge_current",
		"charging_voltage", "charging_current", "charging_mode", "battery_capacity", 
		"out_current_gop", "out_power", "PV_power", "PV_current",
		"time_pub", "Total_generation", 'Today_Utility_consumption',
		"Total_Utility_consumption", "out_today_power", "out_total_power",
		"PV_Total_generation", "battery_current", "internal_temperature"]

    dev_cla      =["None", "voltage", "current",
		"energy", "current", "voltage",
		"frequency", "voltage", "frequency",
		"power_factor", "voltage", "current",
		"voltage", "current", "None", "battery",
		"current", "power", "power", "current",
		"None", "power", 'energy',
		"energy","energy","energy",
		"power", "current", "temperature"]

    stat_cla     =["None", "measurement", "measurement", 
		"total", "measurement", "measurement", 
		"measurement", "measurement", "measurement", 
		"measurement", "measurement", "measurement",
		"measurement", "measurement", "None", "measurement",
		"measurement", "measurement", "measurement", "measurement",
		"None", "measurement", "total",
		"total", "total", "total",
		"measurement", "measurement", "measurement"]

    unit_of_meas =["None", "V", "A",
		 "kWh", "A", "V",
		 "Hz", "V", "Hz",
		 "%", "V", "A",
		 "V", "A", "None", "%",
		 "A", "W", "W", "A",
		 "None", "kW", "kWh",
		 "kWh","kWh", "kWh",
		 "kW", "A", "°C"]

    # -----------------------define system sensors----------------------------
    b = 0
    print()
    print ("...define system sensors...")
    for inv in range(inverters):
	    for n in range(29):
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
		    b = b + 1.15
		    print(int(b), "%", end="\r")
		    time.sleep(1)
	    inv = inv + 1

    time.sleep(1)
    #-------------------------define individual sensors-------------------------
    b = 0
    print("...define individual sensors...")
    for inv in range(inverters):
	    for n in range(29):
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
		    b = b + 1.15
		    print(int(b), "%", end="\r")
		    time.sleep(1)
	    #inv = inv + 1
    print("...MQTT initialization completed...")

#------------------------------------------------------------------------
request = input("Def sensors?(y/n):")
#print(request)
if request == "y":
	    create_sensor()
request = input("Synchronize Date/Time?(y/n)")
if request == "y":
	    synchro_date()

#-----------------write---and---read---ser_port--------------------------
err = 0
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
	    print("...waiting for inverters data...        ", end="\r")
#	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
#	    ser.write(msg9)
#	    response9 = ser.read(10) #DATE
#	    if debug == 1 or debug == 2:
#		    print(response9)
#	    ser.close()

#	    time.sleep(0.5)

#	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
#	    ser.write(msg10)
#	    response10 = ser.read(10) #TIME
#	    if debug == 1 or debug == 2:
#		    print (response10)
#	    ser.close()
#	    time.sleep(0.5)
	
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg2)
	    response2 = ser.read(78) #GLINE
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
	    ser.write(msg6) #GOP
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

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = 1)
	    ser.write(msg8)
	    response8 = ser.read(150)
	    #print (response8)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg12)
	    response12 = ser.read(7)
	    #print (response12)
	    ser.close()

	    time.sleep(0.5)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg13)
	    response13 = ser.read(500) #GPDAT
	    #print (response13)
	    ser.close()

	    time.sleep(1)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg14)
	    response14 = ser.read(5)
	    #print (response14)
	    ser.close()

	    #print(response2[0:1], response3[0:1], response4[0:1], response5[0:1], response6[0:1], response7[0:1], response8[0:1], response12[0:1])
	    if response13[0:1] !=b'(' or response2[0:1] != b'(' or response3[0:1] != b'(' or response4[0:1] != b'(' or response5[0:1] != b'(' or response6[0:1] != b'(' or response7[0:1] != b'(' or response8[0:1] != b'(' or  response12[0:1] != b'B':
		    print()
		    print("...READ ERROR...")
		    err = err + 1
		    if err == 2:
			    print()
			    print("...READING FROM INVERTERS IMPOSSIBLE...")
			    exit()
		    print()
		    print (".... try new reading after 10s....", err)
		    time.sleep(10)
		    print(inv)
		    inv=0
		    continue
		
	    #print("reading")
	    #-------------------------result decoding-------------------
	    #GLINE
	    try:
		    utility_voltage = float(response2[1:6])
	    except:
		    utility_voltage = "N/A"
	    try:
	    	    utility_frequency = float(response2[7:12])
	    except:
		    utility_frequency = "N/A"
	    try:
	    	    utility_high_lost_voltage = float(response2[14:18])
	    except:
		    utility_high_lost_voltage = "N/A"
	    try:
		    utility_low_lost_voltage = float(response2[20:24])
	    except:
		    utility_low_lost_voltage ="N/A"
	    try:
		    utility_high_response_loss = float(response2[26:30])
	    except:
		    utility_high_response_loss = "N/A"
	    try:
		    utility_low_response_loss = float(response2[32:36])
	    except:
		    utility_low_response_loss = "N/A"
	    try:
		    utility_high_loss_freq = float(response2[38:42])
	    except:
		    utility_high_loss_freq = "N/A"
	    try:
		    utility_low_loss_freq = float(response2[44:48])
	    except:
		    utility_low_loss_freq = "N/A"
	    try:
		    load_inverter = int(response6[56:58])
	    except:
		    load_inverter = "N/A"
	    try:
		    utility_today_consumption = float(response2[60:64])/100
	    except:
		    utility_today_consumption = "N/A"
	    try:
		    utility_total_generation_exp = int(response2[66:70])
		    utility_total_generation_bas = int(response2[71:76])
		    utility_total_consumption = ((100000 * utility_total_generation_exp)+utility_total_generation_bas)/100
	    except:
		    utility_total_consumption = "N/A"
	    if debug == 1 or debug == 2:
		    print ("UTILITY VOLTAGE", utility_voltage, "V")
		    print ("UTILITY FREQUECY", utility_frequency, "Hz")
		    print ("PERCENTAGE LOAD", load_inverter, "%")
		    print ('TODAY GEN', utility_today_consumption, "kWh")
		    print ('TOTAL_GEN', utility_total_consumption, "kWh")
	    #GBAT
	    try:
		    battery_voltage = float(response4[1:6])
	    except:
		    battery_voltage ="N/A"

	    try:
		    battery_discharge_current = float(response4[8:13])
	    except:
		    battery_discharge_current = "N/A"
	    if debug == 1 or debug == 2:
		    print("gbat",response4)
		    print ("BATTERY VOLTAGE", battery_voltage, "V")
		    print ("BATTERY DISCHARGE CURRENT", battery_discharge_current, "A")
	    #GCHG 
	    try:
		    charging_voltage = float(response5[7:12])
	    except:
		    charging_voltage = "N/A"
	    try:
		    charging_current = float(response5[16:21])
	    except:
	    	    charging_current = "N/A"
	    try:
		    charging_modes = response5[81:82]
	    except:
		    charging_modes = "N/A"
	    if debug == 1 or debug == 2:
		    print("gchg",response5)
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
	    try:
		    out_voltage = float(response6[1:6])
	    except:
		    out_voltage = "N/A"
	    try:
		    out_frequency = float(response6[7:12])
	    except:
		    out_frequency = "N/A"
	    try:
		    out_current_gop = float(response6[14:19])
	    except:
		    out_current_gop = "N/A"
	    try:
		    out_power = int(response6[27:31])
		    #print(out_power)
	    except:
		    out_power = "N/A"
	    try:
		    out_load = int(response6[57:59])
	    except:
		    out_load = "N/A"
	    try:
		    out_today_power = int(response6[72:77])/100 #OK
	    except:
		    out_today_power = "N/A"
	    try:
		    out_total_power_exp = int(response6[78:83])
		    out_total_power_bas = int(response6[84:89])
		    out_total_power =  ((100000 * out_total_power_exp)+out_total_power_bas)/100
	    except:
		    out_total_power ="N/A"
	    if debug == 1 or debug == 2:
		    print("gop",response6)
		    print ("OUTPUT VOLTAGE", out_voltage, "V")
		    print ("OUTPUT FREQUENCY", out_frequency, "Hz")
		    print ("OUTPUT CURRENT GOP", out_current_gop, "A")
		    print ("OUTPUT ACTIVE POWER", out_power, "W")
		    print ("OUTPUT LOAD", out_load, "%")
		    print ("OUTPUT TODAY POWER", out_today_power, "kW/h")
		    print ("OUTPUT TOTAL POWER", out_total_power, "kW/h") 
	    #GINV
	    try:
		    out_current = float(response7[13:18])
	    except:
		    out_current = "N/A"
	    if debug == 1 or debug == 2:
		    print("ginv",response7)
		    print ("OUTPUT CURRENT GINV", out_current, "A")
	    #GPV
	    try:
		    pv_string_voltage = float(response8[1:6])
	    except:
		    pv_string_voltage = "N/A"
	    try:
		    pv_battery_voltage = float(response8[7:12])
	    except:
		    pv_battery_voltage = "N/A"
	    try:
		    pv_charging_current = float(response8[13:18])
	    except:
		    pv_charging_current = "N/A"
	    try:
		    pv_current = float(response8[19:24])
	    except:
		    pv_current = "N/A"
	    try:
		    pv_power = float(response8[25:30])
	    except:
		    pv_power = "N/A"
	    try:
		    pv_today_generation = float(response8[103:108])/100 #ok
	    except:
		    pv_today_generation = "N/A"
	    try:
		    pv_total_generation_exp = int(response8[109:114])
		    pv_total_generation_bas = int(response8[115:120])
		    pv_total_generation = ((100000 * pv_total_generation_exp)+pv_total_generation_bas)/100
	    except:
		    pv_total_generation = 0
	    if debug == 1 or debug == 2:
		    print("INV",inv+1)
		    print(response8)
		    print ("PV GENERATION TODAY", pv_today_generation, "kWh")
		    print ("PV GENERATION TOTAL", pv_total_generation, "kWh")
		    print ("PV CHARGING CURRENT", pv_charging_current, "A")
		    print ("PV POWER", pv_power, "W")
		    print ("STRING VOLTAGE", pv_string_voltage, "V")
		    print ("PV CURRENT", pv_current, "A")
	    #BL
	    try:
		    battery_capacity = int(response12[3:5])
	    except:
		    battery_capacity = "N/A"
	    if debug == 1 or debug == 2:
		    print ("BATTERY CAPACITY", battery_capacity, "%")
	    #GMOD
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
	    elif response3 ==b'':
		    gmod = ('Read Err')
	    if debug == 1 or debug == 2:
		    print (gmod)
	    #GPDAT0
#		    print("gpdat0",response13)
	    if response13[1:2]==b"":
		    communication = "Read Err"
	    elif int(response13[1:2])==0:
		    communication = "Communication Abnormality Present"
	    elif int(response13[1:2])==1:
		    communication = "Communication Data are Valid"
	    if debug == 1 or debug == 2:
		    print(communication)
	    if response13[3:4]==b"":
		    oper_status = "Read Err"
	    elif int(response13[3:4])==0:
		    oper_status = "Power Up Mode"
	    elif int(response13[3:4])==1:
		    oper_status = "Shutdown Mode"
	    elif int(response13[3:4])==2:
		    oper_status = "Fault Mode"
	    elif int(response13[3:4])==3:
		    oper_status = "Standby Mode"
	    elif int(response13[3:4])==4:
		    oper_status = "Mains Mode"
	    elif int(response13[3:4])==5:
		    oper_status = "Battery Mode"
	    elif int(response13[3:4])==6:
		    oper_status = "Test Mode"
	    if debug == 1 or debug == 2:
		    print(oper_status)
	    if response13[10:11]==b"":
		    par_mode = "Read Err"
	    elif int(response13[10:11])==0:
		    par_mode = "Single Mode"
	    elif int(response13[10:11])==1:
		    par_mode = "Single Phase Parallel Mode"
	    elif int(response13[10:11])==2:
		    par_mode = "R-Phase Parallel Mode"
	    elif int(response13[8:9])==3:
		    par_mode = "S-Phase Parallel Mode"
	    elif int(response13[8:9])==4:
		    par_mode = "T-Phase Parallel Mode"
	    if debug == 1 or debug == 2:
		    print(par_mode)
	    try:
		    inverter_voltage = float(response13[15:20])
	    except:
		    inverter_voltage = "N/A"
	    try:
		    inverter_freq = float(response13[21:26])
	    except:
		    inverter_freq = "N/A"
	    try:
		    mains_voltage = float(response13[27:32])
	    except:
	    	    mains_voltage = "N/A"
	    try:
		    mains_freq = float(response13[33:38])
	    except:
		    mains_freq = "N/A"
	    try:
		    output_voltage = float(response13[39:44])
	    except:
		    output_voltage = "N/A"
	    try:
		    output_freq = float(response13[45:50])
	    except:
		    output_freq = "N/A"
	    try:
		    output_current = float(response13[51:56])
	    except:
		    output_current = "N/A"
	    try:
		    battery_voltage_1 = float(response13[57:61])
	    except:
		    battery_voltage_1 = "N/A"
	    try:
		    battery_current =  float(response13[62:67])
	    except:
		    battery_current = "N/A"
	    try:
		    active_power = float(response13[77:81])
	    except:
		    active_power = "N/A"
	    try:
		    battery_capacity_1 = float(response13[82:85])
	    except:
		    battery_capacity_1 = "N/A"
	    try:
		    internal_temperature = float(response13[102:107])
	    except:
		    internal_temperature = "N/A"
	    if debug == 1 or debug == 2:
		    print("Inverter voltage",inverter_voltage,"V")
		    print("Inverter Frequency", inverter_freq, "Hz")
		    print("Mains Voltage", mains_voltage, "V")
		    print("Mains Frequency", mains_freq, "Hz")
		    print("Output Voltage", output_voltage, "V")
		    print("Output Frequency", output_freq, "Hz")
		    print("Output Current", output_current, "A")
		    print("Battery Voltage", battery_voltage_1, "V")
		    print("Battery Current", battery_current, "A")
		    print("Active Power", active_power, "W")
		    print("Battery Capacity", battery_capacity_1, "%")
		    print("Internal Temperature", internal_temperature, "°C")
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
	    elif chpr == 5:
		    chprior = "Read Error"

	    #print("Charging Priority Inverter",str(inv+1),chprior,"              ")


#-------------------------json serialize-------------------

	    now = datetime.now()
	    time_print = now.strftime("DATE %Y:%m:%d TIME %H:%M")
	    publish_data ['gg_'+str(inv+1)+'_PV_string_voltage'] = pv_string_voltage
	    publish_data ['gg_'+str(inv+1)+'_PV_charging_current'] = pv_charging_current
	    publish_data ['gg_'+str(inv+1)+'_PV_Today_generation'] = pv_today_generation
	    publish_data ['gg_'+str(inv+1)+'_PV_Total_generation'] = pv_total_generation
	    publish_data ['gg_'+str(inv+1)+'_out_current'] = out_current
	    publish_data ['gg_'+str(inv+1)+'_out_voltage'] = out_voltage
	    publish_data ['gg_'+str(inv+1)+'_out_frequency'] = out_frequency
	    publish_data ['gg_'+str(inv+1)+'_out_today_power'] = out_today_power
	    publish_data ['gg_'+str(inv+1)+'_out_total_power'] = out_total_power
	    publish_data ['gg_'+str(inv+1)+'_utility_voltage'] = utility_voltage
	    publish_data ['gg_'+str(inv+1)+'_utility_frequency'] = utility_frequency
	    publish_data ['gg_'+str(inv+1)+'_load_inverter'] = out_load
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
	    publish_data ['gg_'+str(inv+1)+'_Total_generation'] = pv_total_generation
	    publish_data ['gg_'+str(inv+1)+'_Today_Utility_consumption'] = utility_today_consumption
	    publish_data ['gg_'+str(inv+1)+'_Total_Utility_consumption'] = utility_total_consumption
	    publish_data ['gg_'+str(inv+1)+'_battery_current'] = battery_current
	    publish_data ['gg_'+str(inv+1)+'_internal_temperature'] = internal_temperature
	    loop = loop + (inverters/10)
	    if loop > 30:
		    synchro_date()
		    loop = 1
	    inv = inv + 1
	payload = json.dumps(publish_data)
	if debug == 2:
	    print(payload)
	mqtt_publish()
	time.sleep(5)
	range_timer = timer-35
	for t in range(range_timer):
	    print("...next reading", range_timer - 1 - t, "s...              ", end="\r")
	    time.sleep(1)

# -----------FINISH-----------

print("all done")




