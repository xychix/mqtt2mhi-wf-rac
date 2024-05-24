# Top

A simple Python MQTT Connector for Mitsubishi WF RAC AirCon

Based on theawesomestrob/mitsubishi-wf-rac an similar to my heidelberg-wallbox-connector

Values are published to MQTT and are easy integratable into openHAB and other Smart Home Systems.

### Currently the follwing Values from the Inverters are published to MQTT

- power_status
- preset_temperatur
- operation_mode
- airflow
- auto_3d
- wind_ud
- wind_lr

### Currently the follwing Values are read from MQTT and will be send to the Invertes

- power_status
- preset_temperatur
- airflow

### requirements

- Linux System running Linux and Python3 in the same network as MHI WF RAC Inverters
- fixed IP for the Inverters (can't be configured on the inverter, so must be set in DHCP Server (FritzBox, Wifi-Router etc.) )
- Mitsubishi Heavy Industrie Inverters with WF RAC Wifi, (Smart M-Air App compatible)

### Setup

- set fixed IPs for AC Inverters
- register all inverters with `python3 ./aircon.py register <IP of Inverter>`
- edit the config.ini file
- test `./klima-connector.py`
- create a systemctl to run the ./klima-connector.py as a service
