# Inverter-haoss-3f-inverter-data
# soft is in python and working and tested on RPi 3 - Debian 11 - Cable PremiumCord USB2.0 to 4xRS232 (but in princip will working with all computers and different cables)
# My HAOSS running on VirtualBox on Mac Mini 2010 (450GB ssd, 8GB Ram)
# Read data from three inverters Grand Glow, (Voltronic clone but with new protocol commands)
# Software automatically define and create MQTT 20 variables x three inverters to Home assistant.
# place in directory modify variables (broker, port, user, passw - for MQTT, and usb rs232 device)
# install apprioriate library for python (serial, time, json, binascii, paho.mqtt.publish, etc) 
# in the moment is candidat version, my idea for future is grafana and influx (i must study more)

