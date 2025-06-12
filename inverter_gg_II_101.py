#---- build 3f version --------candidate---testing---231117----
import serial
import time, datetime
import json
import binascii
import paho.mqtt.publish as publish
from paho.mqtt import client as mqtt_client
import paho.mqtt.subscribe as subscribe
from datetime import datetime
import math

import serial, time, sys, string
import os
import re
import crcmod
from binascii import unhexlify

pv_charge_cumulation = 0
sample = 0

#Commands with CRC cheats
#QPI            # Device protocol ID inquiry
#QID            # The device serial number inquiry
#QVFW           # Main CPU Firmware version inquiry
#nejde QVFW2          # Another CPU Firmware version inquiry
#QFLAG          # Device flag status inquiry
#QPIGS          # Device general status parameters inquiry
                # GridVoltage, GridFrequency, OutputVoltage, OutputFrequency, OutputApparentPower, OutputActivePower, OutputLoadPercent, BusVoltage, BatteryVoltage, BatteryChargingCurrent, BatteryCapacity, InverterHeatSinkTemperature, PV-InputCurrentForBattery, PV-InputVoltage, BatteryVoltageFromSCC, BatteryDischargeCurrent, DeviceStatus,
#QMOD           # Device mode inquiry P: PowerOnMode, S: StandbyMode, L: LineMode, B: BatteryMode, F: FaultMode, H: PowerSavingMode
#QPIWS          # Device warning status inquiry: Reserved, InverterFault, BusOver, BusUnder, BusSoftFail, LineFail, OPVShort, InverterVoltageTooLow, InverterVoltageTooHIGH, OverTemperature, FanLocked, BatteryVoltageHigh, BatteryLowAlarm, Reserved, ButteryUnderShutdown, Reserved, OverLoad, EEPROMFault, InverterSoftFail, SelfTestFail, OPDCVoltageOver, BatOpen, CurrentSensorFail, BatteryShort, PowerLimit, PVVoltageHigh, MPPTOverloadFault, MPPTOverloadWarning, BatteryTooLowToCharge, Reserved, Reserved
#QDI            # The default setting value information
#QMCHGCR        # Enquiry selectable value about max charging current
#QMUCHGCR       # Enquiry selectable value about max utility charging current
#QBOOT          # Enquiry DSP has bootstrap or not
#QOPM           # Enquiry output mode
#QPGS0          # Parallel information inquiry
                # TheParallelNumber, SerialNumber, WorkMode, FaultCode, GridVoltage, GridFrequency, OutputVoltage, OutputFrequency, OutputAparentPower, OutputActivePower, LoadPercentage, BatteryVoltage, BatteryChargingCurrent, BatteryCapacity, PV-InputVoltage, TotalChargingCurrent, Total-AC-OutputApparentPower, Total-AC-OutputActivePower, Total-AC-OutputPercentage, InverterStatus, OutputMode, ChargerSourcePriority, MaxChargeCurrent, MaxChargerRange, Max-AC-ChargerCurrent, PV-InputCurrentForBattery, BatteryDischargeCurrent
#PEXXX          # Setting some status enable
#PDXXX          # Setting some status disable
#PF             # Setting control parameter to default value
#FXX            # Setting device output rating frequency
#POP02          # set to SBU
#POP01          # set to Solar First
#POP00          # Set to UTILITY
#PBCVXX_X       # Set battery re-charge voltage
#PBDVXX_X       # Set battery re-discharge voltage
#PCP00          # Setting device charger priority: Utility First
#PCP01          # Setting device charger priority: Solar First
#PCP02          # Setting device charger priority: Solar and Utility
#PGRXX          # Setting device grid working range
#PBTXX          # Setting battery type
#PSDVXX_X       # Setting battery cut-off voltage
#PCVVXX_X       # Setting battery C.V. charging voltage
#PBFTXX_X       # Setting battery float charging voltage
#PPVOCKCX       # Setting PV OK condition
#PSPBX          # Setting solar power balance
#MCHGC0XX       # Setting max charging Current          M XX
#MUCHGC002      # Setting utility max charging current  0 02
#MUCHGC010      # Setting utility max charging current  0 10
#MUCHGC020      # Setting utility max charging current  0 20
#MUCHGC030      # Setting utility max charging current  0 30
#POPMMX         # Set output mode       M 0:single, 1: parrallel, 2: PH1, 3: PH2, 4: PH3



# ---------------------------variables initialization---------- 
inverters             = 1                                # amount of inverter/s
MQTT_username         = 'inverter'                       # your MQTT username
MQTT_password         = 'Grand_Glow_03'                  # your MQTT password
broker = "192.168.1.22"                                  # MQTT Broker
MQTT_port = 1883                                         # MQTT port
state_topic = "homeassistant/sensor/gg/state"            # MQTT topic
client_id = 'c67350b3bd694128b12d8f77a18e5aa4'           # HA client id
debug = 1

#----------------------MQTT listaen------------------------
def mqtt_listen():
    print("listen")
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    msg = subscribe.simple("homeassistant/hp01/write", client_id=client_id, qos=0, retained=True, hostname=broker, port=MQTT_port, auth=MQTT_auth)
    if msg.topic == "homeassistant/hp01/write":
        print("payload" , msg.payload, end="\r")
        print()
#----------------------Mqtt publish-------------------------

def mqtt_publish():
    try:
        state_topic = "homeassistant/sensor/gg_II/state"
        MQTT_auth = None
        MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
        publish.single(state_topic, payload, hostname=broker, port=MQTT_port, auth=MQTT_auth, qos=0, retain=True)
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        print('.......mqtt publish....... : ok in', current_time)
    except:
        print(".......Publish is not possible.......")

# --------------------------mqtt (HA)  sensor definition----------------
def create_sensor():
    command = "QVFW" # firmware
    ser.open()
    ser.flushInput()            #flush input buffer, discarding all its contents
    ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
    xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
    command_a=command.encode('utf-8')
    command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
    command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
    command_c='\x0d'.encode('utf-8')
    command_crc = command_a + command_b + command_c
    ser.write(command_crc)
    response = ser.readline()
    ser.close()
    firmware = str(float(response[8:16]))
    fw = firmware.zfill(8)
    print ("FW",fw)

    MQTT_auth = None
    MQTT_auth = { 'username': MQTT_username, 'password': MQTT_password }
    msg          ={}
    config       = 1
    names        =["mode", "utility_voltage", "utility_frequency",
	"out_voltage", "out_frequency", "out_power",
	"out_load", "battery_voltage", "battery_charging_current",
	"battery_capacity", "heatsink_temperature", "pv_input_current",
	"pv_voltage", "battery_discharge_current", "time_pub",
	"aparent_power","charging_prior_mode","prior_mode",
	"pv_charging_power","charging_status","pv_charge_w_h"]



    ids          =["mode", "utility_voltage", "utility_frequency",
	"out_voltage", "out_frequency", "out_power",
	"out_load", "battery_voltage", "battery_charging_current",
	"battery_capacity", "heatsink_temperature", "pv_input_current",
	"pv_voltage", "battery_discharge_current", "time_pub",
	"aparent_power","charging_prior_mode","prior_mode",
	"pv_charging_power","charging_status","pv_charge_w_h"]


    dev_cla      =["None", "voltage", "frequency",
	"voltage", "frequency", "power",
	"power_factor", "voltage", "current",
	"battery", "temperature", "current",
	"voltage", "current", "None",
	"power","None","None",
	"power","None","energy"]

    stat_cla     =["None", "measurement", "measurement", 
	"measurement", "measurement","measurement",
	"measurement", "measurement", "measurement",
	"measurement", "measurement", "measurement",
	"measurement", "measurement", "None",
	"measurement","None","None",
	"measurement","None","total_increasing"]

    unit_of_meas =["None", "V", "Hz",
	 "V", "Hz", "W",
	 "%", "V", "A",
	 "%", "°C", "A",
	 "V", "A", "None",
	 "W","None","None",
	 "W","None","kWh"]

    icon  	=["mdi:auto-mode", "mdi:transmission-tower-import", "mdi:transmission-tower-import",
	 "mdi:transmission-tower-export", "mdi:transmission-tower-export", "mdi:transmission-tower-export",
	 "mdi:meter-electric-outline","mdi:battery","mdi:current-dc",
	 "mdi:battery", "mdi:thermometer-lines", "mdi:current-dc",
	 "mdi:solar-panel", "mdi:current-dc", "mdi:clock",
	 "mdi:transmission-tower","mdi:auto-mode","mdi:auto-mode",
	 "mdi:solar-panel","mdi:auto-mode","mdi:solar-power"]

    # -----------------------define system sensors----------------------------
    b = 0
    print()
    print ("...define system sensors...")
    for inv in range(inverters):
        for n in range(21):
            state_topic          = "homeassistant/sensor/gg_II/"+str(config)+"/config"
            msg ["name"]         = "gg_II_"+str(inv+1)+"_"+names[n]
            msg ["stat_t"]       = "homeassistant/sensor/gg_II/state"
            msg ["icon"]         = icon[n]
            msg ["uniq_id"]      = "gg_II_"+str(inv+1)+"_"+ids[n]
            if dev_cla[n] != "None":
                msg ["dev_cla"]  = dev_cla[n]
            if stat_cla[n] != "None":
                msg ["stat_cla"]  = stat_cla[n]
            if unit_of_meas[n] != "None":
                msg ["unit_of_meas"] = unit_of_meas[n]
            msg ["val_tpl"]      = "{{ value_json." +str(inv+1) +"_" + ids[n]+ "}}"
            msg ["dev"]          = {"identifiers": ["gg_II_"+str(inv+1)], "manufacturer": "Grand Glow", "model": "HFM II W","name": "Grand Glow II "+str(inv+1), "sw_version": fw}
            payload              = json.dumps(msg)
            if debug == 2:
                print(payload)
            publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
            msg                  ={}
            config               = config +1
            b = b + 5
            print(int(b), "%", end="\r")
            time.sleep(0.5)
        inv = inv + 1

    time.sleep(1)
    #-------------------------define individual sensors-------------------------
    b = 0
    print("...define individual sensors...")
    for inv in range(inverters):
        for n in range(21):
            state_topic          = "homeassistant/sensor/gg_II/"+str(config)+"/config"
            msg ["name"]         = "gg_II_"+str(inv+1)+"_"+names[n]
            msg ["stat_t"]       = "homeassistant/sensor/gg_II/state"
            msg ["icon"]         = icon[n]
            msg ["uniq_id"]      = "gg_II_"+str(inv+1)+"_"+ids[n]
            if dev_cla[n] != "None":
                msg ["dev_cla"]  = dev_cla[n]
            if stat_cla[n] != "None":
                msg ["stat_cla"]  = stat_cla[n]                    
            if unit_of_meas[n] != "None":
                msg ["unit_of_meas"] = unit_of_meas[n]
            msg ["val_tpl"]      = "{{ value_json.gg_II_"+str(inv+1)+"_" + ids[n]+ "}}"
            msg ["dev"]          = {"identifiers": ["gg_II_"+str(inv+1)],"manufacturer": "Grand Glow","model": "HFM II W","name": "Grand Glow II "+str(inv+1),"sw_version": fw}
            payload              = json.dumps(msg)
            if debug == 2:
                print(payload)
            publish.single(state_topic, payload, hostname=broker, port= MQTT_port, auth=MQTT_auth, qos=0, retain=True)
            msg                  ={}
            config               = config +1
            b = b + 5
            print(int(b), "%", end="\r")
            time.sleep(0.5)
        #inv = inv + 1
    print("...MQTT initialization completed...")

#------------------------------------------------------------------------

ser = serial.Serial()
ser.port = "/dev/ttyUSB4"
ser.baudrate = 2400
ser.bytesize = serial.EIGHTBITS     #number of bits per bytes
ser.parity = serial.PARITY_NONE     #set parity check: no parity
ser.stopbits = serial.STOPBITS_ONE  #number of stop bits
#ser.timeout = none                 #block read
ser.timeout = 1                     #non-block read
ser.xonxoff = False                 #disable software flow control
ser.rtscts = False                  #disable hardware (RTS/CTS) flow control
ser.dsrdtr = False                  #disable hardware (DSR/DTR) flow control
ser.writeTimeout = 2                #timeout for write



#------------------------------------------------------------------------
#request = input("Def sensors?(y/n):")
#print(request)
#if request == "y":
#	    create_sensor()

#--------actual time--------------    

def actual_time():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")

#-----------------write---and---read---ser_port--------------------------
#mqtt_boiler_publish()
err = 0
publish_data = {}
inv = 0
while True:
    actual_time()
    print(".......waiting for inverters data.......        ", end="\r")
    charging_status = "N/A"
    try:
        now=datetime.now()
        now_power=int(now.strftime("%S"))
        command = "QPIGS" # rating infos
        ser.open()
        ser.flushInput()            #flush input buffer, discarding all its contents
        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_a=command.encode('utf-8')
        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
        command_c='\x0d'.encode('utf-8')
        command_crc = command_a + command_b + command_c
        ser.write(command_crc)
        response = ser.readline()
        ser.close()
        print(response)
        utility_voltage = float(response[1:6])
        utility_frequency = float(response[7:10])
        out_voltage = float(response[12:17])
        out_frequency = float(response[18:22])
        out_power = int(response[28:33])
        aparent_power = int(response[23:27])
        out_load = int(response[33:36])
        battery_voltage = float(response[41:47])
        battery_charging_current = int(response[47:50])
        battery_capacity = int(response[51:55])
        heatsink_temperature = int(response[56:59])
        pv_input_current = float(response[60:65])
        pv_voltage = float(response[65:71])
        charging_voltage = float(response[72:76])
        battery_discharge_current = int(response[77:82])
        device_status_nr = int(response[88:91])
        pv_charging_power = int(response[99:104])
        charging_status_nr = int(response[104:107])
        charging_status = "N/A"
#        print (device_status_nr)
        if device_status_nr == 0:
            charging_status = "Stop Charging"
        elif device_status_nr == 110:
            charging_status = "PV Solar Charging"
        elif device_status_nr == 101:
            charging_status = "Utility Charging"
        elif device_status_nr == 111:
            charging_status = "Sol + Uti Charging"
#        if charging_status_nr == 1:
#            charging_status = "Floating"


        if debug == 1 or debug == 2:
            print ("grid voltage", utility_voltage, "V")
            print ("grid frequency", utility_frequency, "Hz")
            print ("ac out voltage", out_voltage, "V")
            print ("ac out frequency", out_frequency, "Hz")
            print ("ac out power", out_power, "W")
            print ("aparent power", aparent_power, "W")
            print ("out load", out_load, "%")
            print ("battery voltage", battery_voltage,"V")
            print ("battery charging current",battery_charging_current,"A")
            print ("battery capacity",battery_capacity,"%")
            print ("heatsink temperature",heatsink_temperature,"°C")
            print ("pv input current",pv_input_current,"A")
            print ("pv voltage", pv_voltage, "V")
            print ("charging voltage", charging_voltage, "V")
            print ("battery discharge current",battery_discharge_current,"A")
            print ("device status",device_status_nr)
            print ("pv_charging_power",pv_charging_power,"W")
            print ("charging_status",charging_status_nr)
            print ("charging_status",charging_status)
            print()


        command = "QMOD" # rating infos
        ser.open()
        ser.flushInput()            #flush input buffer, discarding all its contents
        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_a=command.encode('utf-8')
        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
        command_c='\x0d'.encode('utf-8')
        command_crc = command_a + command_b + command_c
        ser.write(command_crc)
        response = ser.readline()
        ser.close()
#        print(response)
        mode_nr = response[1:2]
        mode = "N/A"
        if mode_nr == b'P':
            mode = "Power On Mode"
        elif mode_nr == b"S":
            mode = "Standby Mode"
        elif mode_nr == b"L":
            mode = "Line Mode"
        elif mode_nr == b"B":
            mode = "Battery Mode"
        elif mode_nr == b"F":
            mode = "Fault Mode"
        elif mode_nr == b"H":
            mode = "Power saving Mode"
        elif mode_nr == b"D":
            mode = "Shutdown Mode"
        elif mode_nr == b"C":
            mode = "Charge Mode"
        elif mode_nr == b"Y":
            mode = "Bypass Mode"
        elif mode_nr == b"E":
            mode = "ECO Mode"
        if debug == 1 or debug == 2:
            print ("mode", mode)
            print()
#--------------pokusy--------------------

#        command = "QDI" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QFLAG" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QPIWS" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QSID" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QMN" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QID" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QPI" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

#        command = "QLT" # rating infos
#        ser.open()
#        ser.flushInput()            #flush input buffer, discarding all its contents
#        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
#        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
#        command_a=command.encode('utf-8')
#        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
#        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
#        command_c='\x0d'.encode('utf-8')
#        command_crc = command_a + command_b + command_c
#        ser.write(command_crc)
#        response = ser.readline()
#        ser.close()
#        print(command, response)

        command = "QPIRI" # rating infos
        ser.open()
        ser.flushInput()            #flush input buffer, discarding all its contents
        ser.flushOutput()           #flush output buffer, aborting current output and discard all that is in buffer
        xmodem_crc_func = crcmod.predefined.mkCrcFun('xmodem')
        command_a=command.encode('utf-8')
        command_b_0=hex(xmodem_crc_func(command_a)).replace('0x','',1)
        command_b=unhexlify(command_b_0.replace('0a','0b',1)) 
        command_c='\x0d'.encode('utf-8')
        command_crc = command_a + command_b + command_c
        ser.write(command_crc)
        response = ser.readline()
        ser.close()
#        print(command, response)
        prior_mode_nr = int(response[74:75])
        prior_mode = "N/A"
        if prior_mode_nr == 0:
            prior_mode = "Utility First"
        elif prior_mode_nr == 1:
            prior_mode = "Solar First"
        elif prior_mode_nr == 2:
            prior_mode = "SBU First"
        charging_prior_mode_nr = int(response[76:77])
        charging_prior_mode = "N/A"
        if charging_prior_mode_nr == 0:
            charging_prior_mode = "Utility First"
        elif charging_prior_mode_nr == 1:
            charging_prior_mode = "Solar First"
        elif charging_prior_mode_nr == 2:
            charging_prior_mode = "Solar + Uti"
        elif charging_prior_mode_nr == 3:
            charging_prior_mode = "Only PV"
        if debug == 1 or debug == 2:
            print ("prior_mode", prior_mode)
            print ("charging_prior_mode", charging_prior_mode)
        pv_charging_power_in_time = round(float(pv_charging_power/2),4) #merí se dvakrát do minuty
        pv_charge_cumulation = round(pv_charging_power_in_time + pv_charge_cumulation,4)
        pv_charge_kw_h = round(pv_charge_cumulation/60000,4)
        print("pv_charge_w_h",pv_charge_kw_h,"kWh")
        pv_charge_w_h = round(pv_charge_kw_h,2)
    except:
        print(".......Reading problem.......")

#    stop()
#-------------------------json serialize-------------------

    try:
        now = datetime.now()
        time_print = now.strftime("D %d.%m. T %H:%M")
        publish_data ['gg_II_'+str(inv+1)+'_mode'] = mode
        publish_data ['gg_II_'+str(inv+1)+'_utility_voltage'] = utility_voltage
        publish_data ['gg_II_'+str(inv+1)+'_utility_frequency'] = utility_frequency
        publish_data ['gg_II_'+str(inv+1)+'_out_voltage'] = out_voltage
        publish_data ['gg_II_'+str(inv+1)+'_out_frequency'] = out_frequency
        publish_data ['gg_II_'+str(inv+1)+'_out_power'] = out_power
        publish_data ['gg_II_'+str(inv+1)+'_out_load'] = out_load
        publish_data ['gg_II_'+str(inv+1)+'_battery_voltage'] = battery_voltage
        publish_data ['gg_II_'+str(inv+1)+'_battery_charging_current'] = battery_charging_current
        publish_data ['gg_II_'+str(inv+1)+'_battery_capacity'] = battery_capacity
        publish_data ['gg_II_'+str(inv+1)+'_heatsink_temperature'] = heatsink_temperature
        publish_data ['gg_II_'+str(inv+1)+'_pv_input_current'] = pv_input_current
        publish_data ['gg_II_'+str(inv+1)+'_pv_voltage'] = pv_voltage
        publish_data ['gg_II_'+str(inv+1)+'_battery_discharge_current'] = battery_discharge_current
        publish_data ['gg_II_'+str(inv+1)+'_time_pub'] = time_print
        publish_data ['gg_II_'+str(inv+1)+'_aparent_power'] = aparent_power
        publish_data ['gg_II_'+str(inv+1)+'_prior_mode'] = prior_mode
        publish_data ['gg_II_'+str(inv+1)+'_charging_prior_mode'] = charging_prior_mode
        publish_data ['gg_II_'+str(inv+1)+'_charging_status'] = charging_status
        publish_data ['gg_II_'+str(inv+1)+'_pv_charging_power'] = pv_charging_power
        publish_data ['gg_II_'+str(inv+1)+'_pv_charge_w_h'] = pv_charge_w_h
        payload = json.dumps(publish_data)
        mqtt_publish()
    except:
        print("no data for publish")
        now = datetime.now()
        time_print = now.strftime("D %d.%m. T %H:%M")
        publish_data ['gg_II_'+str(inv+1)+'_time_pub'] = "NO DATA "+time_print
        payload = json.dumps(publish_data)
        mqtt_publish()

#    mqtt_listen()
        if debug == 2:
            print(payload)
    for t in range(26):
        print("...next reading", 26 - 1 - t, "s...              ", end="\r")
        time.sleep(1)
    print()
#    now = datetime.now()
#    now_1 = int(now.strftime("%S"))
#    time_power = now_power - now_1
#    sample = sample + 1
#    if sample == 11:
#        sample = 0
#        pv_charge_w_h = round(1.2*pv_charge_cumulation/1000,1) #prumer za deset mereni
#        payload = json.dumps(publish_data)
        #mqtt cumulation send
#        print("PV POWER",pv_charge_w_h,"kW/h")
    high_noon = now.strftime("%H:%M")
    print(high_noon)
    if high_noon == "00:00":
        pv_charge_cumulation = 0
        print(".......kumulace nulování.......")
#        print("PV POWER",pv_charge_w_h,"kW/h")
#    print ("kumulace",pv_charge_cumulation,"pv_charging_power_in_time",pv_charging_power_in_time,"W/s","sample",sample)
#    print()
