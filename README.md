<img width="1058" height="652" alt="786915942_28672629139008113_3610977814371326377_n" src="https://github.com/user-attachments/assets/3d25e038-763a-4455-866a-8a1a80db141f" />
<img width="1600" height="1200" alt="774130635_28508790975391931_1624228225670826984_n" src="https://github.com/user-attachments/assets/c2bce9a9-f56b-4479-8286-f2a5d5adad02" />
<img width="442" height="296" alt="772793226_28508757072061988_4876872832214903256_n" src="https://github.com/user-attachments/assets/cc00f33f-6d37-4966-be33-3a05b3f6c3a3" />  
<N/>
#
#New version sw inverter_new_gg_boiler_210.py for Grand Glow HFM 5500 inverter but also function for EASUN EASUN Isolar SMS 6.5KP
# python3 inverter_new_gg_boiler_210.py --datetime    synchro time
# python3 inverter_new_gg_boiler_210.py --discovery autodiscovery all entities to HA
# python3 inverter_new_gg_boiler_210.py 


# Inverter-haoss-3f-inverter-data
# soft is in python and working and tested on RPi 3 - Debian 11 - Cable PremiumCord USB2.0 to 4xRS232 (but in princip will working with all computers and different cables)
# My HAOSS running on VirtualBox on Mac Mini 2010 (450GB ssd, 8GB Ram)
# Read data from three inverters Grand Glow, (Voltronic clone but with new protocol commands)
# Software automatically define and create MQTT 22 variables x three inverters to Home assistant.
# place in directory modify variables (broker, port, user, passw - for MQTT, and usb rs232 device)
# install apprioriate library for python (serial, time, json, binascii, paho.mqtt.publish, etc) 
# in the moment is new version, my idea for future is grafana and influx (i must study more)
# last version inverter_gg_xx_203.py read data from 1 - 9 inverters and check inverters values and control 3phase loading to boilers with driving by zigbee controlers 0-10V and SSR modules
# last version inverter_gg_xf_101.py some functionality bugs changed to better stability
#

