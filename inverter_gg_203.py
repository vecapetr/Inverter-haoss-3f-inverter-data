#---- build 3f version --------candidate---testing---240820----
import serial
import logging
import time, datetime
import json
import sys
import binascii
import paho.mqtt.publish as publish
import random
from paho.mqtt import client as mqtt_client
from datetime import datetime
import math
import paho.mqtt.subscribe as subscribe
import os
import sys
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
timer = 30                                               # timer
debug = 0                                                # print all results and payload 0-stop, 1-data, 2-data+paylods

charging_mode_gg1 = "Constant Current"
charging_mode_gg2 = "Constant Current"
charging_mode_gg3 = "Constant Current"
boiler_power_rest1 = 0
boiler_power_rest2 = 0
boiler_power_rest3 = 0
pv_charging_current1 = 0
pv_charging_current2 = 0
pv_charging_current3 = 0
dec_boiler1 = 0
dec_boiler2 = 0
dec_boiler3 = 0
boiler_power_drive1 = 0
boiler_power_drive_state1 = "OFF"
battery_voltage_old1 = 0
boiler_power_float1 = 0
pv_current_gg1_old = 0
boiler_stop_counter1 = 0
boiler_power_drive_old1 = 0
boiler_power_drive_state_old1 = 0
float_count_1 = 0
float_count_2 = 0
float_count_3 = 0
boiler_power_rest_count1 = 0
boiler_power_drive2 = 0
boiler_power_drive_state2 = "OFF"
battery_voltage_old2 = 0
boiler_power_float2 = 0
pv_current_gg2_old = 0
boiler_stop_counter2 = 0
boiler_power_drive_old2 = 0
boiler_power_drive_state_old2 = 0
float_count2 = 0
boiler_power_rest_count2 = 0
boiler_power_drive3 = 0
boiler_power_drive_state3 = "OFF"
battery_voltage_old3 = 0
boiler_power_float3 = 0
pv_current_gg3_old = 0
boiler_stop_counter3 = 0
boiler_power_drive_old3 = 0
boiler_power_drive_state_old3 = 0
float_count3 = 0
boiler_power_rest_count3 = 0
boiler_on_off = "ON"
counter_start = 1
boiler_const = 35
boiler_power_pub_old1 = 0
boiler_power_pub_old2 = 0
boiler_power_pub_old3 = 0
counter_restart_boiler = 0
boiler_power = {}
boiler_counter_off = 0
boiler_counter_off_1 = 0
boiler_counter_off_2 = 0
boiler_counter_off_3 = 0

for inv in range(inverters):
    boiler_power[inv] = 0

#--------------boiler_power_drive_tab----------

#boiler_power_drive = ["0","91","101","109","114","119","125","129","133","137","140","144","149","152","156","161","166","170","176","182","190","202","255"]

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
msg14 = bytes.fromhex("43 50 52 3f 3f 0d")#CPR?
msg15 = bytes.fromhex("4f 50 52 3f 3f 0D")#opr?


#----------------------MQTT publish-------------------------
def mqtt_listen(boiler_on_off,grid_on_off):
    global boiler_counter_off
    global boiler_counter_off_1
    global boiler_counter_off_2
    global boiler_counter_off_3

    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    msg = subscribe.simple("homeassistant/hp01/write", client_id=client_id, qos=1, retained=True, hostname=broker, port=MQTT_port, auth=MQTT_auth)
    if msg.topic == "homeassistant/hp01/write":
        boiler_listen=str(msg.payload)
        if boiler_listen == b'boiler_ON':
            boiler_on_off = "ON"
        elif boiler_listen == b'boiler_OFF':
            boiler_on_off = "OFF"
        elif boiler_listen == b'soc_less':
            grid_on_off = "grid_ON"
        elif boiler_listen == b'soc_more':
            grid_on_off = "grid_OFF"
    return(boiler_on_off,grid_on_off)

def mqtt_publish():
    try:
        state_topic = "homeassistant/sensor/gg/state"
        MQTT_auth = None
        MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
        publish.single(state_topic, payload, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print('.......ALL DATA mqtt publish....... : ok in', current_time)
    except:
        print(".......Publish is not possible.......")

def mqtt_boiler_init():
    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_1/set"
    MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
    publish_data_boiler = {"brightness":"0","state":"OFF"}
    payload_boiler = json.dumps(publish_data_boiler)
    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_2/set"
    MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
    publish_data_boiler = {"brightness":"0","state":"OFF"}
    payload_boiler = json.dumps(publish_data_boiler)
    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_3/set"
    MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
    publish_data_boiler = {"brightness":"0","state":"OFF"}
    payload_boiler = json.dumps(publish_data_boiler)
    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
    print(".......boilers...initialise.......")

def grid_on():
    print(".......BYPASS ON........")
    hex_opr_comm1 = "OPR??\r"
    hex_opr1 = hex_opr_comm1.encode("utf-8").hex()
    msg_opr1 = bytes.fromhex(hex_opr1)
    hex_opr_comm = "OPR00\r"
    hex_opr = hex_opr_comm.encode("utf-8").hex()
    msg_opr = bytes.fromhex(hex_opr)

    if boiler_topic == "_1":
	    ser_port = (ser_port_inv_1)
	    inv=0
    elif boiler_topic == "_2":
	    ser_port = (ser_port_inv_2)
	    inv=1
    elif boiler_topic == "_3":
	    ser_port = (ser_port_inv_3)
	    inv=2
    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
    ser.write(msg_opr1)
    response_opr1 = ser.read(7)
    if response_opr1 == b'(00\r':
	    print(".......INV"+str(inv+1)+" OPR MODE WITHOUT CHANGE.......")
    elif not response_opr1 == b'(00\r':
	    print(".......MODE WILL CHANGE.......")
	    ser.write(msg_opr)
	    response_opr = ser.read(7)
	    if response_opr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" OPR command accepted")
                    print(".......OPR MODE GRID ONLY.......                 ")
	    elif not response_opr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" OPR command NOT accepted")
    ser.close()
    time.sleep(1)

def grid_off():
    print(".......OPR_MODE_PV_BAT_UTI........")
    hex_opr_comm1 = "OPR??\r"
    hex_opr1 = hex_opr_comm1.encode("utf-8").hex()
    msg_opr1 = bytes.fromhex(hex_opr1)
    hex_opr_comm = "OPR02\r"
    hex_opr = hex_opr_comm.encode("utf-8").hex()
    msg_opr = bytes.fromhex(hex_opr)
    hex_cpr_comm1 = "CPR??\r"
    hex_cpr1 = hex_cpr_comm1.encode("utf-8").hex()
    msg_cpr1 = bytes.fromhex(hex_cpr1)
    hex_cpr_comm = "CPR03\r"
    hex_cpr = hex_cpr_comm.encode("utf-8").hex()
    msg_cpr = bytes.fromhex(hex_cpr)

    if boiler_topic == "_1":
	    ser_port = (ser_port_inv_1)
	    inv=0
    elif boiler_topic == "_2":
	    ser_port = (ser_port_inv_2)
	    inv=1
    elif boiler_topic == "_3":
	    ser_port = (ser_port_inv_3)
	    inv=2
    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
    response_opr = ser.read(7)
    ser.write(msg_opr1)
    response_opr1 = ser.read(7)
#    ser.close()
    time.sleep(1)
#    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
    ser.write(msg_cpr1)
    response_cpr1 = ser.read(7)
    if response_opr1 == b'(02\r':
	    print(".......INV"+str(inv+1)+" OPR MODE WITHOUT CHANGE.......")
    elif not response_opr1 == b'(02\r':
	    print(".......OPR MODE WILL CHANGE.......")
	    ser.write(msg_opr)
	    response_opr = ser.read(7)
	    if response_opr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" OPR command accepted")
                    print(".......OPR MODE PV-BAT-UTI.......                 ")
	    elif not response_opr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" OPR command NOT accepted")
    if response_cpr1 == b'(03\r':
	    print(".......INV"+str(inv+1)+" CPR MODE WITHOUT CHANGE.......")
    elif not response_cpr1 == b'(03\r':
	    print(".......CPR MODE WILL CHANGE.......")
	    ser.write(msg_cpr)
	    response_cpr = ser.read(7)
	    if response_cpr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" CPR command accepted")
                    print(".......CPR MODE PV-ONLY.......                 ")
	    elif not response_cpr == b'ACK\r':
                    print(".......INV"+str(inv+1)+" CPR command NOT accepted")
    ser.close()
    time.sleep(1)

def mqtt_boiler_publish():
    global boiler_on_off
    global grid_on_off
#    global boiler_const

    try:

        global boiler_counter_off
        global boiler_counter_off_1
        global boiler_counter_off_2
        global boiler_counter_off_3
        global counter_restart_boiler

        MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
        msg = subscribe.simple("homeassistant/hp01/write", client_id=client_id, qos=1, retained=True, hostname=broker, port=MQTT_port, auth=MQTT_auth)

        if msg.topic == "homeassistant/hp01/write":
            boiler_listen = msg.payload
            if boiler_listen == b'restart_inv_1':
                print(".......SYSTEM...RESTARTING.......")
                for t in range(10):
                    print("...next reading", 10 - 1 - t, "s...              ", end="\r")
                    time.sleep(1)
                os.execv('/usr/bin/python3',  [sys.argv[0], '/home/petr/fve/inverter/inverter_gg_203.py'])
            if boiler_listen == b'boiler_ON':
                boiler_on_off = "ON"
#                boiler_counter_off = 0
                boiler_counter_off_1 = 0
                boiler_counter_off_2 = 0
                boiler_counter_off_3 = 0
            elif boiler_listen == b'boiler_OFF':
                boiler_on_off = "OFF"
                counter_restart_boiler=250
            elif boiler_listen == b'boiler_FULL':
                boiler_on_off = "FULL"
            elif boiler_listen == b'soc_less':
                grid_on_off = "grid_ON"
                grid_on()
            elif boiler_listen == b'soc_more':
                grid_on_off = "grid_OFF"
                grid_off()
            elif boiler_listen == b'boiler_125' or boiler_listen == b'boiler_250':
#                boiler_on_off = "ON"
                MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
                for boiler_power_drive_down in range (1,26):

                    publish_data_boiler = {"brightness":boiler_power_drive1-(10*(boiler_power_drive_down)),"state":"ON"}
                    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_1/set"
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                    publish_data_boiler = {"brightness":boiler_power_drive2-(10*(boiler_power_drive_down)),"state":"ON"}
                    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_2/set"
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                    publish_data_boiler = {"brightness":boiler_power_drive3-(10*(boiler_power_drive_down)),"state":"ON"}
                    state_topic_boiler = "zigbee2mqtt/boiler_power_drive_3/set"
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)

                    time.sleep(0.5)

            elif not boiler_listen == b'soc_more' or not boiler_listen == b'soc_less' or not boiler_listen == b'boiler_OFF' or not boiler_listen == b'boiler_ON' or not boiler_listen == b'boiler_FULL' or not boiler_listen == b'boiler_125' or not boiler_listen == b'boiler_250':
                boiler_on_off = "OFF"
                boiler_counter_off = 0
    except:
        print(".......Listen...ERROR.......")
#    print(boiler_counter_off)
#    if boiler_counter_off == 0:
#        boiler_counter_off = 1
#        print(boiler_counter_off)

#        counter_restart_boiler=250

    try:
        if boiler_topic == "_1":
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            state_topic_boiler = "zigbee2mqtt/boiler_power_drive"+boiler_topic+"/set"
            MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
            publish_data_boiler = {"brightness":boiler_power_drive1,"state":boiler_power_drive_state1}
            payload_boiler = json.dumps(publish_data_boiler)
            if boiler_on_off == "OFF" and boiler_counter_off_1 == 0:
                boiler_counter_off_1 = 1
                publish_data_boiler = {"brightness":"0","state":"OFF"}
                payload_boiler = json.dumps(publish_data_boiler)
                publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                print(".......INV1...Boiler OFF..............")
            if charging_mode_gg1 == "Constant Current" or charging_mode_gg1 == "Stop Charging" or charging_mode_gg1 == "Floating" or charging_mode_gg1 == "Constant Voltage":
#                if current_time < "17:00:00": # and boiler_payload == "ON":# or over_power1 == 1:
                if boiler_on_off == "ON":
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print('.......INV1...mqtt boiler publish....... : ok in', current_time)
                    boiler_power_drive_old1 = boiler_power_drive1
                    boiler_power_drive_state_old1 = boiler_power_drive_state1
                    over_power1 = 0
                if boiler_on_off == "FULL": # or over_power1 == 1:
                    publish_data_boiler = {"brightness":"0","state":"OFF"}
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print(".......INV1...Boiler FULL..............")

    except:
        print(".......INV1...Publish_boiler is not possible.......")

    try:
        if boiler_topic == "_2":
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            state_topic_boiler = "zigbee2mqtt/boiler_power_drive"+boiler_topic+"/set"
            MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
            publish_data_boiler = {"brightness":boiler_power_drive2,"state":boiler_power_drive_state2}
            payload_boiler = json.dumps(publish_data_boiler)
            if boiler_on_off == "OFF" and boiler_counter_off_2 == 0:
                boiler_counter_off_2 = 1
                publish_data_boiler = {"brightness":"0","state":"OFF"}
                payload_boiler = json.dumps(publish_data_boiler)
                publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                print(".......INV2...Boiler OFF...........")
            if charging_mode_gg2 == "Constant Current" or charging_mode_gg2 == "Stop Charging" or charging_mode_gg2 == "Floating" or charging_mode_gg2 == "Constant Voltage":
                if boiler_on_off == "ON":
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print('.......INV2...mqtt boiler publish....... : ok in', current_time)
                    boiler_power_drive_old2 = boiler_power_drive2
                    boiler_power_drive_state_old2 = boiler_power_drive_state2
                    over_power2 = 0
                if boiler_on_off == "FULL": # or over_power2 == 1:
                    publish_data_boiler = {"brightness":"0","state":"OFF"}
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print(".......INV2...Boiler FULL...........")
    except:
        print(".......INV2...Publish_boiler is not possible.......")

    try:
        if boiler_topic == "_3":
            #print(boiler_power_drive3,boiler_power_drive_state3)
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            state_topic_boiler = "zigbee2mqtt/boiler_power_drive"+boiler_topic+"/set"
            MQTT_auth = { 'username': "mqtt-user", 'password': "MQTT-User" }
            publish_data_boiler = {"brightness":boiler_power_drive3,"state":boiler_power_drive_state3}
            payload_boiler = json.dumps(publish_data_boiler)
            if boiler_on_off == "OFF" and boiler_counter_off_3 == 0:
                boiler_counter_off_3 = 1
                publish_data_boiler = {"brightness":"0","state":"OFF"}
                payload_boiler = json.dumps(publish_data_boiler)
                publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                print(".......INV3...Boiler OFF..........")
            if charging_mode_gg3 == "Constant Current" or charging_mode_gg3 == "Stop Charging" or charging_mode_gg3 == "Floating" or charging_mode_gg3 == "Constant Voltage":
                if boiler_on_off == "ON":
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print('.......INV3...mqtt boiler publish....... : ok in', current_time)
                    boiler_power_drive_old3 = boiler_power_drive3
                    boiler_power_drive_state_old3 = boiler_power_drive_state3
                    over_power3 = 0
                if boiler_on_off == "FULL": # or over_power3 == 1:
                    publish_data_boiler = {"brightness":"0","state":"OFF"}
                    payload_boiler = json.dumps(publish_data_boiler)
                    publish.single(state_topic_boiler, payload_boiler, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
                    print(".......INV3...Boiler FULL..........")
    except:
        print(".......INV3...Publish_boiler is not possible.......")
    try:
        if boiler_counter_off_1 == 1 and boiler_counter_off_2 == 1 and boiler_counter_off_3 == 1:
            boiler_counter_off = 1
            boiler_counter_off_1 = 1
            boiler_counter_off_2 = 1
            boiler_counter_off_3 = 1
#            counter_restart_boiler=250

    except:
        boiler_counter_off_1=0
        boiler_counter_off_2=0
        boiler_counter_off_3=0
        boiler_counter_off=0
#        print(boiler_counter_off,boiler_counter_off_1,boiler_counter_off_2,boiler_counter_off_3)
        counter_restart_boiler=250
#    try:
#        print(boiler_counter_off,boiler_counter_off_1,boiler_counter_off_2,boiler_counter_off_3)

#    except:
#        print(".......CHYBA v COUNTER OFF.......")
        #ounter_restart_boiler=251
#    return boiler_on_off

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
	    ser.close()
	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg_time)
	    response_t = ser.read(7)
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
		"PV_Total_generation","battery_current", "internal_temperature",
		"mode_prior","charging_mode_prior","mode_phase",
		"boiler_power"]

    ids          =["mode", "PV_string_voltage", "PV_charging_current",
		"PV_Today_generation", "out_current", "out_voltage",
		"out_frequency", "utility_voltage", "utility_frequency",
		"load_inverter", "battery_voltage", "battery_discharge_current",
		"charging_voltage", "charging_current", "charging_mode", "battery_capacity", 
		"out_current_gop", "out_power", "PV_power", "PV_current",
		"time_pub", "Total_generation", 'Today_Utility_consumption',
		"Total_Utility_consumption", "out_today_power", "out_total_power",
		"PV_Total_generation", "battery_current", "internal_temperature",
		"mode_prior","charging_mode_prior","mode_phase",
		"boiler_power"]


    dev_cla      =["None", "voltage", "current",
		"energy", "current", "voltage",
		"frequency", "voltage", "frequency",
		"power_factor", "voltage", "current",
		"voltage", "current", "None", "battery",
		"current", "power", "power", "current",
		"None", "power", 'energy',
		"energy","energy","energy",
		"power", "current", "temperature",
		"None","None","None",
		"current"]

    stat_cla     =["None", "measurement", "measurement", 
		"total_increasing", "measurement", "measurement", 
		"measurement", "measurement", "measurement", 
		"measurement", "measurement", "measurement",
		"measurement", "measurement", "None", "measurement",
		"measurement", "measurement", "measurement", "measurement",
		"None", "measurement", "total_increasing",
		"total_increasing", "total_increasing", "total_increasing",
		"measurement", "measurement", "measurement",
		"None","None","None",
		"measurement"]

    unit_of_meas =["None", "V", "A",
		 "kWh", "A", "V",
		 "Hz", "V", "Hz",
		 "%", "V", "A",
		 "V", "A", "None", "%",
		 "A", "W", "W", "A",
		 "None", "kW", "kWh",
		 "kWh","kWh", "kWh",
		 "kW", "A", "°C",
		 "None","None","None",
		 "A"]

    icon  	=["mdi:auto-mode", "mdi:solar-panel", "mdi:solar-panel",
		 "mdi:solar-power", "mdi:transmission-tower-export", "mdi:transmission-tower-export",
		 "mdi:transmission-tower-export", "mdi:transmission-tower-import", "mdi:transmission-tower-import",
		 "mdi:meter-electric-outline", "mdi:battery", "mdi:current-dc",
		 "mdi:current-dc", "mdi:current-dc", "mdi:auto-mode", "mdi:battery-charging",
		 "mdi:transmission-tower-export", "mdi:transmission-tower-export", "mdi:solar-power", "mdi:transmission-tower-import",
		 "mdi:clock", "mdi:transmission-tower-export", "mdi:transmission-tower",
		 "mdi:transmission-tower-import","mdi:transmission-tower", "mdi:transmission-tower",
		 "mdi:solar-power", "mdi:current-dc", "mdi:thermometer-lines",
		 "mdi:auto-mode","mdi:auto-mode","mdi:auto-mode",
		 "mdi:water-boiler"]

    # -----------------------define system sensors----------------------------
    b = 0
    print()
    print ("...define system sensors...")
    for inv in range(inverters):
	    for n in range(33):
		    state_topic          = "homeassistant/sensor/gg/"+str(config)+"/config"
		    msg ["name"]         = "gg_"+str(inv+1)+"_"+names[n]
		    msg ["stat_t"]       = "homeassistant/sensor/gg/state"
		    msg ["icon"]         = icon[n]
		    msg ["uniq_id"]      = "gg_"+str(inv+1)+"_"+ids[n]
		    if dev_cla[n] != "None":
    			    msg ["dev_cla"]  = dev_cla[n]
		    if stat_cla[n] != "None":
    			    msg ["stat_cla"]  = stat_cla[n]
		    if unit_of_meas[n] != "None":
    			    msg ["unit_of_meas"] = unit_of_meas[n]
		    msg ["val_tpl"]      = "{{ value_json." +str(inv+1) +"_" + ids[n]+ "}}"
		    msg ["dev"]          = {"identifiers": ["gg_"+str(inv+1)], "manufacturer": "Grand Glow", "model": "HFM PRO","name": "Grand Glow "+str(inv+1), "sw_version": fw}
		    payload              = json.dumps(msg)
		    if debug == 2:
			    print(payload)
		    publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
		    msg                  ={}
		    config               = config +1
		    b = b + 0.99
		    print(int(b), "%", end="\r")
		    time.sleep(1)
	    inv = inv + 1

    time.sleep(1)
    #-------------------------define individual sensors-------------------------
    b = 0
    print("...define individual sensors...")
    for inv in range(inverters):
	    for n in range(33):
		    state_topic          = "homeassistant/sensor/gg/"+str(config)+"/config"
		    msg ["name"]         = "gg_"+str(inv+1)+"_"+names[n]
		    msg ["stat_t"]       = "homeassistant/sensor/gg/state"
		    msg ["icon"]         = icon[n]
		    msg ["uniq_id"]      = "gg_"+str(inv+1)+"_"+ids[n]
		    if dev_cla[n] != "None":
			    msg ["dev_cla"]  = dev_cla[n]
		    if stat_cla[n] != "None":
			    msg ["stat_cla"]  = stat_cla[n]                    
		    if unit_of_meas[n] != "None":
			    msg ["unit_of_meas"] = unit_of_meas[n]
		    msg ["val_tpl"]      = "{{ value_json.gg_"+str(inv+1)+"_" + ids[n]+ "}}"
		    msg ["dev"]          = {"identifiers": ["gg_"+str(inv+1)],"manufacturer": "Grand Glow","model": "HFM PRO","name": "Grand Glow "+str(inv+1),"sw_version": fw}
		    payload              = json.dumps(msg)
		    if debug == 2:
			    print(payload)
		    publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
		    msg                  ={}
		    config               = config +1
		    b = b + 0.99
		    print(int(b), "%", end="\r")
		    time.sleep(1)
	    #inv = inv + 1
    print("...MQTT initialization completed...")

#------------------------------------------------------------------------
#request = input("Def sensors?(y/n):")
#print(request)
#if request == "y":
#	    create_sensor()
#request = input("Synchronize Date/Time?(y/n)")
#if request == "y":
#	    synchro_date()

#-----------------write---and---read---ser_port--------------------------
#default_set()

mqtt_boiler_init()

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

	    print(".......waiting for inverters data.......        ", end="\r")

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg2)
	    response2 = ser.read(78) #GLINE
	    #print(response2)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg3)
	    response3 = ser.read(5)
	    #print (response3)
	    gmod = "ERROR"
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg4)
	    response4 = ser.read(27)
	    #print (response4)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg5)
	    response5 = ser.read(110)
	    #print (response5)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg6) #GOP
	    response6 = ser.read(110)
	    #print (response6) 
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg7)
	    response7 = ser.read(20)
	    #print (response7)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg8)
	    response8 = ser.read(150)
	    #print (response8)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg12)
	    response12 = ser.read(7)
	    #print (response12)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg13)
	    response13 = ser.read(500) #GPDAT
	    #print (response13)
	    ser.close()

	    time.sleep(0.2)

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg14)
	    response14 = ser.read(5)
	    #print (response14)
	    ser.close()

	    ser = serial.Serial(ser_port, ser_baudrate, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout = tim)
	    ser.write(msg15)
	    response15 = ser.read(5)
	    # print (response15)
	    ser.close()

	    if response13[0:1] !=b'(' or response2[0:1] != b'(' or response3[0:1] != b'(' or response4[0:1] != b'(' or response5[0:1] != b'(' or response6[0:1] != b'(' or response7[0:1] != b'(' or response8[0:1] != b'(' or  response12[0:1] != b'B':
		    print()
		    print(".......READ ERROR.......")
		    err = err + 1
		    if err == 10:
			    print()
			    print(".......READING FROM INVERTERS IMPOSSIBLE.......")
			    exit()
		    print()
		    print ("........try new reading after 10s........", err)
		    time.sleep(10)
		    print(inv)
		    inv=0
		    err=0
		    continue
		
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
		    pv_charging_current = 0
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
		    battery_capacity = int(response12[2:5])
	    except:
		    battery_capacity = "N/A"
	    if debug == 1 or debug == 2:
		    print ("BATTERY CAPACITY", battery_capacity, "%")
	    #GMOD
	    if response3 == b'(B\r':
		    gmod = ('Battery mode')
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
	    try:
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
	    except:
	        print(".......Read Err Resp13.......")
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
	    elif chpr == 3:
		    oprior = "Read Error"

#--------------boiler drive------------------

	    if charging_modes == b'0': #stop charging not enought power
		    boiler_power[inv] = 0
	    elif charging_modes == b'1' or charging_modes ==  b'2':
		    if pv_charging_current > 3.5: #constant current or constant voltage enought power
			    boiler_power[inv] = pv_charging_current - 3.5
	    elif charging_modes == b'3' and pv_charging_current > 0: #float add power
		    boiler_power[inv] = boiler_power[inv]+1
	    elif charging_modes == b'3' and pv_charging_current == 0:
		    boiler_power[inv] = boiler_power[inv]-1
		    if boiler_power[inv] < 0:
			    boiler_power[inv] = 0
	    boiler_power_pub = round(boiler_power[inv],1)
	    if inv == 0:
		    boiler_power_nr_gg1 = round(boiler_power[0],1)
		    pv_charging_current_nr_gg1 = round(pv_charging_current,1)
		    gmod_gg1 = gmod
		    charging_mode_gg1 = charging_mode
		    pv_current_gg1 = pv_current
		    battery_voltage_gg1 = battery_voltage
		    out_power_gg1 = out_power
	    if inv == 1:
		    boiler_power_nr_gg2 = round(boiler_power[1],1)
		    pv_charging_current_nr_gg2 = round(pv_charging_current,1)
		    gmod_gg2 = gmod
		    charging_mode_gg2 = charging_mode
		    pv_current_gg2 = pv_current
		    battery_voltage_gg2 = battery_voltage
		    out_power_gg2 = out_power
	    if inv == 2:
		    boiler_power_nr_gg3 = round(boiler_power[2],1)
		    pv_charging_current_nr_gg3 = round(pv_charging_current,1)
		    gmod_gg3 = gmod
		    charging_mode_gg3 = charging_mode
		    pv_current_gg3 = pv_current
		    battery_voltage_gg3 = battery_voltage
		    out_power_gg3 = out_power


#-------------------------json serialize-------------------

	    now = datetime.now()
	    time_print = now.strftime("D %d:%m T %H:%M")
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
	    publish_data ['gg_'+str(inv+1)+'_mode_prior'] = oprior
	    publish_data ['gg_'+str(inv+1)+'_mode_phase'] = par_mode
	    publish_data ['gg_'+str(inv+1)+'_charging_mode_prior'] = chprior
	    publish_data ['gg_'+str(inv+1)+'_boiler_power'] = boiler_power_pub
	    loop = loop + (inverters/10)
	    if loop > 50:
		    float_counter = 0
	    if loop > 300:
		    synchro_date()
		    loop = 1
		    boiler_power_rest1 = 0
		    boiler_power_drive1 = 0
		    dec_boiler1 = 0
		    boiler_power_rest2 = 0
		    boiler_power_drive2 = 0
		    dec_boiler2 = 0
		    boiler_power_rest3 = 0
		    boiler_power_drive3 = 0
		    dec_boiler3 = 0
#		    mqtt_boiler_publish()
	    inv = inv + 1
	payload = json.dumps(publish_data)
	mqtt_publish()
	battery_mode = "Off"
#--------------max load check-----------------------
	if out_power_gg1 > 3900:
	    print(".......INV 1 Power more than 3900 W.......")
	    over_power1 = 1
	    boiler_power_rest1 = 0
	    dec_boiler1 = 0
	    boiler_power_drive1 = 0
	    boiler_topic = "_1"
	    mqtt_boiler_publish()
	over_power1 = 0

	if out_power_gg2 > 3900:
	    print(".......INV 2 Power more than 3900 W.......")
	    over_power2 = 1
	    boiler_power_rest2 = 0
	    dec_boiler2 = 0
	    boiler_power_drive2 = 0
	    boiler_topic = "_2"
	    mqtt_boiler_publish()
	over_power2 = 0

	if out_power_gg3 > 3900:
	    print(".......INV 3 Power more than 3900 W.......")
	    over_power3 = 1
	    boiler_power_rest3 = 0
	    dec_boiler3 = 0
	    boiler_power_drive3 = 0
	    boiler_topic = "_3"
	    mqtt_boiler_publish()
	over_power3 = 0
#------------main boiler calc--------------------------


#------------boiler 1---------------------------------
#	print(boiler_const)
	if charging_mode_gg1 == "Constant Current":
		    boiler_power_float1 = 0
	if gmod_gg1 == "Battery mode" and gmod_gg2 == "Battery mode" and gmod_gg3 == "Battery mode" and battery_voltage_gg2 >= 52.5:
	    battery_mode = "On"
#	    print(".......Battery mode ON............")
	if battery_mode == "Off":
	    print(".......Battery mode OFF............")
	    boiler_power_rest1 = 0
	    dec_boiler1 = 0
	    boiler_power_drive1 = 0
	    float_count1 = 0
	    boiler_topic = "_1"
	    mqtt_boiler_publish()
	if boiler_power_rest1 == 0 and charging_mode_gg1 == "Constant Current" and battery_mode == "On":
	    boiler_power_rest_count1 = boiler_power_rest_count1 + 1
	    print(".......INV1...new boiler calculation.......")
	    if pv_charging_current_nr_gg1 < 3.5 and battery_mode == "On":
		    boiler_power_nr1 = 0
	    if pv_charging_current_nr_gg1 > 3.5 and battery_mode == "On":
		    boiler_power_nr1 = pv_charging_current_nr_gg1 - 3.5
#	    if pv_charging_current_nr_gg1 > 4.5 and battery_mode == "On":
#		    boiler_power_nr1 = pv_charging_current_nr_gg1 - 4.5
#	    if pv_charging_current_nr_gg1 > 5.5 and battery_mode == "On":
#		    boiler_power_nr1 = pv_charging_current_nr_gg1 - 5.5
#	    if pv_charging_current_nr_gg1 > 6.5 and battery_mode == "On":
#		    boiler_power_nr1 = pv_charging_current_nr_gg1 - 6.5
	    boiler_power_drive1 = int((boiler_const*boiler_power_nr1)+0)
	    boiler_power_drive_state1 = "ON"
#		    if boiler_power_drive1 < 25:
#			    boiler_power_drive_state1 = "OFF"
	    if boiler_power_drive1 > 130:
		    boiler_power_drive1 = 130
	    boiler_topic = "_1"
	    mqtt_boiler_publish()
	    boiler_power_rest1 = round(boiler_power_nr1,1)
	    pv_current_gg1_old = 0
#	    print("tu som rest 0", boiler_power_drive1,boiler_power_drive_state1,boiler_power_nr1,boiler_power_rest1)
	elif boiler_power_rest1 > 0.1 and battery_mode == "On" and charging_mode_gg1 == "Constant Current":
#	    print("tu som rest vetsi jak 0")
	    boiler_power_rest_count1 = boiler_power_rest_count1 + 1
	    boiler_power_nr1 = pv_charging_current_nr_gg1 + boiler_power_rest1
	    if pv_charging_current_nr_gg1 <= 0 or battery_voltage < battery_voltage_old:
		    dec_boiler1 = dec_boiler1 - 2
		    if dec_boiler1 < 0:
			    dec_boiler1 = 0
			    print(".......INV1...power ZERO............  ")
		    elif dec_boiler1 > 0:
			    print(".......INV1...power decrease........  ")
	    elif pv_charging_current_nr_gg1 > 0 and battery_voltage >= battery_voltage_old:
		    dec_boiler1 = dec_boiler1 + 2
		    if dec_boiler1 > 255:
			    dec_boiler1 = 255
			    print(".......INV1...power MAX.............  ")
		    if dec_boiler1 < 255:
			    print(".......INV1...power increase........  ")
	    if boiler_power_nr1 >= 3.1:
		    boiler_power_nr1 = 3.1
	    pv_current_gg1_old = 0
	    boiler_power_drive1 = int((boiler_const*boiler_power_nr1)+dec_boiler1)
	    boiler_power_drive_state1 = "ON"
	    if boiler_power_rest_count1 < 3:
		    if boiler_power_drive1 > 160:
			    boiler_power_drive1 = 160
	    if boiler_power_drive1 < 17:
		    boiler_power_drive_state1 = "OFF"
	    if boiler_power_drive1 > 255:
		    boiler_power_drive1 = 255
	    boiler_topic = "_1"
	    mqtt_boiler_publish()
#	    print("tu som rest vetsi nez 0", boiler_power_drive1,boiler_power_drive_state1)

	    boiler_power_rest1 = round(boiler_power_nr1,1)
	if gmod_gg1 == "Utility mode":
	    dec_boiler1 = 0
	    boiler_power_drive1 = 0
	    boiler_power_rest1 = 0
	    pv_current_gg1_old = 0
	    float_count1 = 0
	    battery_voltage_old = 0
	    boiler_power_float1 = 0
	    pv_current_gg1_old = 0
	    boiler_stop_counter1 = 0
	    print(".......INV1...Utility mode............")
	if not charging_mode_gg1 == "Stop Charging":
	    boiler_stop_counter1 = 0
	if charging_mode_gg1 == "Stop Charging":
	    boiler_stop_counter1 = boiler_stop_counter1 + 1
	    if boiler_stop_counter1 > 5:
		    boiler_power_drive1 = 0
		    boiler_stop_counter1 = 0
		    boiler_power_rest1 = 0
		    boiler_power_rest_count1 = 0
	    boiler_power_drive1 = boiler_power_drive1 - 10
	    float_count1 = 0
	    if boiler_power_drive1 < 0:
		    boiler_power_drive1 = 0
	    print(".......INV1...Boiler Stop..........")
	    boiler_topic = "_1"
	    mqtt_boiler_publish()
#	if charging_mode_gg1 == "Floating" or charging_mode_gg1 == "Constant Voltage":
#	    print(".......INV1...Floating - Constant Voltage.......")
#	    mqtt_boiler_publish()
	battery_voltage_old=battery_voltage
	if charging_mode_gg1 == "Floating" or charging_mode_gg1 == "Constant Voltage":
	    print(".......INV1...Floating - Constant Voltage.......",float_count_1+1,"read","Drive",boiler_power_drive1,"pv current",pv_current_gg1,"pv current old",pv_current_gg1_old)
	    if float_count_1 == 0:
		    boiler_power_float1 = 1
		    boiler_power_drive1 = 130
		    boiler_power_drive_state1 = "ON"
		    boiler_topic = "_1"
		    mqtt_boiler_publish()
		    pv_current_gg1_old = pv_current_gg1
	    float_count_1 = float_count_1 + 1
	    if float_count_1 > 2:
		    float_count_1 = 0
		    if boiler_power_float1 == 1:
			    if pv_current_gg1 >= pv_current_gg1_old:
				    boiler_power_drive1 = boiler_power_drive1 + 2
				    boiler_power_drive_state1 = "ON"
				    if boiler_power_drive1 > 255:
					    boiler_power_drive1 = 255
				    boiler_topic = "_1"
				    mqtt_boiler_publish()
				    pv_current_gg1_old = pv_current_gg1
#				    time.sleep(30)
			    elif pv_current_gg1 < pv_current_gg1_old:
				    boiler_power_drive1 = boiler_power_drive1 - 2
				    boiler_power_drive_state1 = "ON"
				    boiler_topic = "_1"
				    pv_current_gg1_old = pv_current_gg1
				    if boiler_power_drive1 < 0:
					    boiler_power_drive1 = 0
					    float_count = 0
#					    boiler_power_float1 = 0
				    mqtt_boiler_publish()


#				    time.sleep(30)
#		    if boiler_power_float1 == 0:
#			    boiler_power_float1 = 1
#			    boiler_power_drive1 = 119
#			    boiler_power_drive_state1 = "ON"
#			    boiler_topic = "_1"
#			    mqtt_boiler_publish()
#			    pv_current_gg1_old = pv_current_gg1
#			    time.sleep(30)
#------------------end boiler 1--------------------------------
#------------boiler 2---------------------------------
	if charging_mode_gg2 == "Constant Current":
		    boiler_power_float2 = 0
	if gmod_gg1 == "Battery mode" and gmod_gg2 == "Battery mode" and gmod_gg3 == "Battery mode" and battery_voltage_gg2 >= 52.5:
	    battery_mode = "On"
#	    print(".......Battery mode ON............")
	if battery_mode == "Off":
	    print(".......Battery mode OFF............")
	    boiler_power_rest2 = 0
	    dec_boiler2 = 0
	    boiler_power_drive2 = 0
	    float_count2 = 0
	    boiler_topic = "_2"
	    mqtt_boiler_publish()
	if boiler_power_rest2 == 0 and charging_mode_gg2 == "Constant Current" and battery_mode == "On":
	    boiler_power_rest_count2 = boiler_power_rest_count2 + 1
	    print(".......INV2...new boiler calculation.......")
	    if pv_charging_current_nr_gg2 < 3.5 and battery_mode == "On":
		    boiler_power_nr2 = 0
	    if pv_charging_current_nr_gg2 > 3.5 and battery_mode == "On":
		    boiler_power_nr2 = pv_charging_current_nr_gg2 - 3.5
#	    if pv_charging_current_nr_gg2 > 4.5 and battery_mode == "On":
#		    boiler_power_nr2 = pv_charging_current_nr_gg2 - 4.5
#	    if pv_charging_current_nr_gg2 > 5.5 and battery_mode == "On":
#		    boiler_power_nr2 = pv_charging_current_nr_gg2 - 5.5
#	    if pv_charging_current_nr_gg2 > 6.5 and battery_mode == "On":
#		    boiler_power_nr2 = pv_charging_current_nr_gg2 - 6.5
	    boiler_power_drive2 = int((boiler_const*boiler_power_nr2)+0)
	    boiler_power_drive_state2 = "ON"
#	    if boiler_power_drive2 < 25:
#		    boiler_power_drive_state2 = "OFF"
	    if boiler_power_drive2 > 130:
		    boiler_power_drive2 = 130
	    boiler_topic = "_2"
	    mqtt_boiler_publish()
	    boiler_power_rest2 = round(boiler_power_nr2,1)
	    pv_current_gg2_old = 0
	elif boiler_power_rest2 > 0.1 and battery_mode == "On" and charging_mode_gg2 == "Constant Current":
	    boiler_power_rest_count2 = boiler_power_rest_count2 + 1
	    boiler_power_nr2 = pv_charging_current_nr_gg2 + boiler_power_rest2
	    if pv_charging_current_nr_gg2 <= 0 or battery_voltage < battery_voltage_old:
		    dec_boiler2 = dec_boiler2 - 2
		    if dec_boiler2 < 0:
			    dec_boiler2 = 0
			    print(".......INV2...power ZERO............  ")
		    elif dec_boiler2 > 0:
			    print(".......INV2...power decrease........  ")
	    elif pv_charging_current_nr_gg2 > 0 and battery_voltage >= battery_voltage_old:
		    dec_boiler2 = dec_boiler2 + 2
		    if dec_boiler2 > 255:
			    dec_boiler2 = 255
			    print(".......INV2...power MAX............   ")
		    elif dec_boiler2 < 255:
			    print(".......INV2...power increase.......   ")
	    if boiler_power_nr2 >= 3.1:
		    boiler_power_nr2 = 3.1
	    pv_current_gg2_old = 0
	    boiler_power_drive2 = int((boiler_const*boiler_power_nr2)+dec_boiler2)
	    boiler_power_drive_state2 = "ON"
	    if boiler_power_rest_count2 < 3:
		    if boiler_power_drive2 > 160:
			    boiler_power_drive2 = 160
	    if boiler_power_drive2 < 25:
		    boiler_power_drive_state2 = "OFF"
	    if boiler_power_drive2 > 255:
		    boiler_power_drive2 = 255
	    boiler_topic = "_2"
	    mqtt_boiler_publish()
	    boiler_power_rest2 = round(boiler_power_nr2,1)
	if gmod_gg2 == "Utility mode":
	    dec_boiler2 = 0
	    boiler_power_drive2 = 0
	    boiler_power_rest2 = 0
	    pv_current_gg2_old = 0
	    float_count2 = 0
	    battery_voltage_old = 0
	    boiler_power_float2 = 0
	    pv_current_gg2_old = 0
	    boiler_stop_counter2 = 0
	    print(".......INV2...Utility mode............")
	if not charging_mode_gg2 == "Stop Charging":
	    boiler_stop_counter2 = 0
	if charging_mode_gg2 == "Stop Charging":
	    boiler_stop_counter2 = boiler_stop_counter2 + 1
	    if boiler_stop_counter2 > 5:
		    boiler_power_drive2 = 0
		    boiler_stop_counter2 = 0
		    boiler_power_rest2 = 0
		    boiler_power_rest_count2 = 0
	    boiler_power_drive2 = boiler_power_drive2 - 10
	    float_count2 = 0
	    if boiler_power_drive2 < 0:
		    boiler_power_drive2 = 0
	    print(".......INV2...Boiler Stop..........")
	    boiler_topic = "_2"
	    mqtt_boiler_publish()
	if charging_mode_gg2 == "Floating" or charging_mode_gg2 == "Constant Voltage":
	    print(".......INV2...Floating - Constant Voltage.......",float_count_2+1,"read","Drive",boiler_power_drive2,"pv current",pv_current_gg2,"pv current old",pv_current_gg2_old)
	    if float_count_2 == 0:
		    boiler_power_float2 = 1
		    boiler_power_drive2 = 130
		    boiler_power_drive_state2 = "ON"
		    boiler_topic = "_2"
		    mqtt_boiler_publish()
		    pv_current_gg2_old = pv_current_gg2
	    float_count_2 = float_count_2 + 1
	    if float_count_2 > 2:
		    float_count_2 = 0
		    print(".......INV2...Floating - Constant Voltage.......")
		    if boiler_power_float2 == 1:
			    if pv_current_gg2 >= pv_current_gg2_old:
				    boiler_power_drive2 = boiler_power_drive2 + 2
				    boiler_power_drive_state2 = "ON"
				    if boiler_power_drive2 > 255:
					    boiler_power_drive2 = 255
				    boiler_topic = "_1"
				    mqtt_boiler_publish()
				    pv_current_gg2_old = pv_current_gg2
#				    time.sleep(30)
			    elif pv_current_gg2 < pv_current_gg2_old:
				    boiler_power_drive2 = boiler_power_drive2 - 2
				    boiler_power_drive_state2 = "ON"
				    boiler_topic = "_1"
				    pv_current_gg2_old = pv_current_gg2
				    if boiler_power_drive2 < 0:
					    boiler_power_drive2 = 0
					    float_count_2 = 0
#					    boiler_power_float2 = 0
				    mqtt_boiler_publish()
#	    mqtt_boiler_publish()
	battery_voltage_old=battery_voltage
#------------------end boiler 2--------------------------------
#------------boiler 3---------------------------------
	if charging_mode_gg3 == "Constant Current":
		    boiler_power_float3 = 0
	if gmod_gg1 == "Battery mode" and gmod_gg2 == "Battery mode" and gmod_gg3 == "Battery mode" and battery_voltage_gg2 >= 52.5:
	    battery_mode = "On"
#	    print(".......Battery mode ON............")
	if battery_mode == "Off":
	    print(".......Battery mode OFF............")
	    boiler_power_rest3 = 0
	    dec_boiler3 = 0
	    boiler_power_drive3 = 0
	    float_count3 = 0
	    boiler_topic = "_3"
	    mqtt_boiler_publish()
	if boiler_power_rest3 == 0 and charging_mode_gg3 == "Constant Current" and battery_mode == "On":
	    boiler_power_rest_count3 = boiler_power_rest_count3 + 1
	    print(".......INV3...new boiler calculation.......")
	    if pv_charging_current_nr_gg3 < 3.5 and battery_mode == "On":
		    boiler_power_nr3 = 0
	    if pv_charging_current_nr_gg3 > 3.5 and battery_mode == "On":
		    boiler_power_nr3 = pv_charging_current_nr_gg3 - 3.5
#	    if pv_charging_current_nr_gg3 > 4.5 and battery_mode == "On":
#		    boiler_power_nr3 = pv_charging_current_nr_gg3 - 4.5
#	    if pv_charging_current_nr_gg3 > 5.5 and battery_mode == "On":
#		    boiler_power_nr3 = pv_charging_current_nr_gg3 - 5.5
#	    if pv_charging_current_nr_gg3 > 6.5 and battery_mode == "On":
#		    boiler_power_nr3 = pv_charging_current_nr_gg3 - 6.5
	    boiler_power_drive3 = int((boiler_const*boiler_power_nr3)+0)
	    boiler_power_drive_state3 = "ON"
#	    if boiler_power_drive3 < 25:
#			    boiler_power_drive_state3 = "OFF"
	    if boiler_power_drive3 > 130:
		    boiler_power_drive3 = 130
	    boiler_topic = "_3"
	    mqtt_boiler_publish()
	    boiler_power_rest3 = round(boiler_power_nr3,1)
	    pv_current_gg3_old = 0
	elif boiler_power_rest3 > 0.1 and battery_mode == "On" and charging_mode_gg3 == "Constant Current":
	    boiler_power_rest_count3 = boiler_power_rest_count3 + 1
	    boiler_power_nr3 = pv_charging_current_nr_gg3 + boiler_power_rest3
	    if pv_charging_current_nr_gg3 <= 0 or battery_voltage < battery_voltage_old:
		    dec_boiler3 = dec_boiler3 - 2
		    if dec_boiler3 < 0:
			    dec_boiler3 = 0
			    print(".......INV3...power ZERO............  ")
		    elif dec_boiler3 > 0:
			    print(".......INV3...power decrease........  ")
	    elif pv_charging_current_nr_gg3 > 0 and battery_voltage >= battery_voltage_old:
		    dec_boiler3 = dec_boiler3 + 2
		    if dec_boiler3 > 255:
			    dec_boiler3 = 255
			    print(".......INV3...power MAX.............  ")
		    elif dec_boiler3 < 255:
			    print(".......INV3...power increase........  ")
	    if boiler_power_nr3 >= 3.1:
		    boiler_power_nr3 = 3.1
	    pv_current_gg3_old = 0
	    boiler_power_drive3 = int((boiler_const*boiler_power_nr3)+dec_boiler3)
	    boiler_power_drive_state3 = "ON"
	    if boiler_power_rest_count3 < 3:
		    if boiler_power_drive3 > 160:
			    boiler_power_drive3 = 160
	    if boiler_power_drive3 < 25:
		    boiler_power_drive_state3 = "OFF"
	    if boiler_power_drive3 > 255:
		    boiler_power_drive3 = 255
	    boiler_topic = "_3"
	    mqtt_boiler_publish()
	    boiler_power_rest3 = round(boiler_power_nr3,1)
	if gmod_gg3 == "Utility mode":
	    dec_boiler3 = 0
	    boiler_power_drive3 = 0
	    boiler_power_rest3 = 0
	    pv_current_gg3_old = 0
	    float_count3 = 0
	    battery_voltage_old = 0
	    boiler_power_float3 = 0
	    pv_current_gg3_old = 0
	    boiler_stop_counter3 = 0
	    print(".......INV3...Utility mode............")
	if not charging_mode_gg3 == "Stop Charging":
	    boiler_stop_counter3 = 0
	if charging_mode_gg3 == "Stop Charging":
	    boiler_stop_counter3 = boiler_stop_counter3 + 1
	    if boiler_stop_counter3 > 5:
		    boiler_power_drive3 = 0
		    boiler_stop_counter3 = 0
		    boiler_power_rest3 = 0
		    boiler_power_rest_count3 = 0
	    boiler_power_drive3 = boiler_power_drive3 - 10
	    float_count3 = 0
	    if boiler_power_drive3 < 0:
		    boiler_power_drive3 = 0
	    print(".......INV3...Boiler Stop..........")
	    boiler_topic = "_3"
	    mqtt_boiler_publish()
	if charging_mode_gg3 == "Floating" or charging_mode_gg3 == "Constant Voltage":
	    print(".......INV3...Floating - Constant Voltage.......",float_count_3+1,"read","Drive",boiler_power_drive3,"pv current",pv_current_gg3,"pv current old",pv_current_gg3_old)
	    if float_count_3 == 0:
		    boiler_power_float3 = 1
		    boiler_power_drive3 = 130
		    boiler_power_drive_state3 = "ON"
		    boiler_topic = "_3"
		    mqtt_boiler_publish()
		    pv_current_gg3_old = pv_current_gg3
	    float_count_3 = float_count_3 + 1
	    if float_count_3 > 2:
		    float_count_3 = 0
		    if boiler_power_float3 == 1:
			    if pv_current_gg3 >= pv_current_gg3_old:
				    boiler_power_drive3 = boiler_power_drive3 + 2
				    boiler_power_drive_state3 = "ON"
				    if boiler_power_drive3 > 255:
					    boiler_power_drive3 = 255
				    boiler_topic = "_3"
				    mqtt_boiler_publish()
				    pv_current_gg3_old = pv_current_gg3
#				    time.sleep(30)
			    elif pv_current_gg3 < pv_current_gg3_old:
				    boiler_power_drive3 = boiler_power_drive3 - 2
				    boiler_power_drive_state3 = "ON"
				    boiler_topic = "_3"
				    pv_current_gg3_old = pv_current_gg3
				    if boiler_power_drive3 < 0:
					    boiler_power_drive3 = 0
					    float_count_3 = 0
#					    boiler_power_float3 = 0
				    mqtt_boiler_publish()
#	    mqtt_boiler_publish()
	battery_voltage_old=battery_voltage
	print()
	print()

#------------------end boiler 3--------------------------------
#------------------end main boiler calc-------------------------
	counter_restart_boiler = counter_restart_boiler + 1
	print(".......Boiler Counter",251-counter_restart_boiler)
	if counter_restart_boiler > 251:
	    boiler_power_rest1 = 0
	    boiler_power_rest2 = 0
	    boiler_power_rest3 = 0
	    counter_restart_boiler = 0

	    print(".......Boiler...Counter...Restart.......")
	if debug == 2:
	    print(payload)
#	for t in range(10):
#	    print(".......next reading", 10 - 1 - t, "s.......              ", end="\r")
#	    time.sleep(0.1)


# -----------FINISH-----------

print("all done")




