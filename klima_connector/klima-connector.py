#!/usr/bin/env python3

import time
import datetime
import paho.mqtt.client as mqtt
import logging
from logging.handlers import TimedRotatingFileHandler
import gzip
import os
from configparser import ConfigParser
import argparse

import aircon

######################################
#
#   V 1.0: 13.05.2024:  Initial Release
#   V 1.3: 25.06.2024:  Added on_disconnect to handle MQTT disconect events


# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the configuration file
config_file_path = os.path.join(script_dir, 'config.ini')

# Check if the config file exists
if not os.path.isfile(config_file_path):
    raise FileNotFoundError(f"The configuration file {config_file_path} was not found.")


#Read config.ini file
config_object = ConfigParser()
config_object.read(config_file_path)

general_Config = config_object["general"]
MQTT_Config = config_object["MQTT Broker Config"]

# set intervall for main loop
interval = int(general_Config["interval"] )

######################################
#   MQTT Config
######################################

client = mqtt.Client()
client.username_pw_set(username=MQTT_Config["user"], password=MQTT_Config["password"])

mqtt_prefix = MQTT_Config["mqtt_prefix"]

######################################
#   Inverter Config
######################################


Inverter_configs = config_object.items("Inverters")


class Inverter:
    def __init__(self, name, IP):
        self.name = name
        self.IP = IP
        self.power_status = None
        self.preset_temperatur = None
        self.operation_mode  = None
        self.airflow  = None
        self.auto_3d  = None
        self.wind_ud  = None
        self.wind_lr  = None


# Create a list of Inverter instances
inverters = [Inverter(name, IP) for name, IP in Inverter_configs]
    


######################################
#   Logging
######################################

log_path = general_Config["log_path"]

# Check if log_path is relative and, if so, make it absolute
if not os.path.isabs(log_path):
    log_path = os.path.join(script_dir, log_path)
        
try:
    os.makedirs(log_path)
    print("Logdir " + log_path + " created" )
      
except FileExistsError:
    pass
    

class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)

#get the root logger
rootlogger = logging.getLogger()
#set overall level to debug, default is warning for root logger
rootlogger.setLevel(logging.DEBUG)

#setup logging to file, rotating at midnight
filelog = logging.handlers.TimedRotatingFileHandler(log_path + general_Config["log_filename"], when='midnight', interval=1, encoding='utf-8')
filelog.setLevel(logging.DEBUG)
fileformatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
filelog.setFormatter(fileformatter)
filelog.rotator = GZipRotator()
rootlogger.addHandler(filelog)

#setup logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
console.setFormatter(formatter)
rootlogger.addHandler(console)

#get a logger for my script
logger = logging.getLogger(__name__)



######################################
#    Initialisierung
######################################

def get_time():
    now = (datetime.datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    return now    

def on_connect(client, userdata, flags, rc):
    logger.debug("Connected to MQTT with result code " + str(rc))
    if rc == 0:
        logger.debug("Connected to MQTT successfully")
        client.connected_flag = True
        advertize_device()

        # Subscribing in on_connect() so that if connection is lost subscription will also be renewed
        client.subscribe(mqtt_prefix + "#")

    else:
        logger.error("Connect to MQTT failed with return code: " + str(rc))
        client.connected_flag = False
    

# Define the callback for disconnection
def on_disconnect(client, userdata, rc):
    logger.debug("Disconnected from MQTT with result code " + str(rc))
    client.connected_flag = False
    if rc != 0:
        print("Unexpected disconnection. Will attempt to reconnect.")
        client.reconnect_flag = True
            

# Define the callback for reconnection
def on_reconnect(client, userdata, rc):
    if rc == 0:
        logger.info("Successfully reconnected to MQTT")
        client.connected_flag = True
        client.reconnect_flag = False
    else:
        logger.error("Reconnect to MQTT failed with return code: " + str(rc))
        client.connected_flag = False
        client.reconnect_flag = True


def advertize_device():
    for inverter in inverters:
        logger.info("Found Inverter config " + inverter.name + " " + inverter.IP)
        client.publish(mqtt_prefix + inverter.name + "/name", inverter.name, 1, True)
        
    
           
def on_message(client, userdata, message):
     
    if "/set" in message.topic:
        logger.debug("Received MQTT Set message: " + str(message.topic) + ": " + str(message.payload.decode("utf-8")))
        
        topic_parts = message.topic.split("/")
        inverter_name = topic_parts[2]
        inverter_attribute = topic_parts[3]
        
        inverter = None
        
         # Check if Inverter Name exists
        found = False
        for inv in inverters:
            if inv.name == inverter_name:
                inverter = inv
                found = True
                break
                
        if not found:
            logger.error("Received MQTT Set message for Inverter Name " + inverter_name + " but the Name is not found in Config!")
            return
        
        args = init_args()
        
        # Set IP of received Inverter
        args.IP = inverter.IP
        
        
        ####################################
        #set received attribute
        ####################################
        
        if inverter_attribute == "power_status":
                
            if str(message.payload.decode("utf-8"))== "ON":
                logger.info("Set Power of " + inverter_name + " to ON ")
                args.on_off = True
                aircon.set_status(args)
            
            if str(message.payload.decode("utf-8"))== "OFF":
                logger.info("Set Power of " + inverter_name + " to OFF ")
                args.on_off = False
                aircon.set_status(args)
                        
        if inverter_attribute == "preset_temperatur":
            try:
                args.temperature = float(message.payload.decode("utf-8"))
            except:
                logger.error("Could not Convert received value to float")
                return
           
            logger.info("Set Preset Temperature of " + inverter_name + " to " +  str(message.payload.decode("utf-8")))
            aircon.set_status(args)
        
        if inverter_attribute == "airflow":
            try:
                if 0 <= int(message.payload.decode("utf-8")) <= 4:
                    args.airflow = int(message.payload.decode("utf-8"))
                else: 
                    logger.error("Airflow Value must be in Range 0-4")
                    return
            except:
                logger.error("Could not Convert received value to int value")
                return
            
            logger.info("Set Airflow of " + inverter_name + " to " +  str(message.payload.decode("utf-8")))
            aircon.set_status(args)
                                       
    
# Assign callback function to handle incoming messages
client.on_message = on_message

# Set the flags to False initially
client.connected_flag = False
client.reconnect_flag = False

# Assign the callbacks
client.on_connect = on_connect
client.on_disconnect = on_disconnect

# Configure the reconnection settings
client.reconnect_delay_set(min_delay=1, max_delay=120)

try:
    client.connect(MQTT_Config["broker_IP"], int(MQTT_Config["broker_port"]), 60)
except:
    logger.info("Could not connect to MQTT Broker")  
client.loop_start()


def bool2onoff(boolean_value):
    if boolean_value:
        return "ON"
    else:
        return "OFF"

def init_args():

    parser = argparse.ArgumentParser()
    
    # Just for lookup of arguments
	# 
	# on_off'  boolean
	# temperature', type=float)
	# airflow', type=int, choices=[0,1,2,3,4])
	# wind_ud', type=int, choices=[0,1,2,3,4])
	# wind_lr', type=int, choices=[0,1,2,3,4,5,6,7])

    args = parser.parse_args()
        
    args.temperature = None
    args.on_off = None
    args.airflow = None
    args.wind_ud = None
    args.wind_lr = None
    
    return args

######################################
#   Main Loop
######################################


def loop():
    while True:
        
        logger.debug("------- Loop Iteration Started ---------")
     
        args = init_args()

        # Check if MQTT reconnection is needed
        if client.reconnect_flag and not client.connected_flag:
            try:
                logger.info("Attempting to reconnect MQTT ...")
                client.reconnect()
            except Exception as e:
                logger.error(f"Reconnect attempt failed: {e}")

               
        ######################################
        #   Read Values from Inverter
        ######################################
        try:
            
            
            for inverter in inverters:
                logger.debug("------ Query Status of " + inverter.name + " " + inverter.IP)
                
                client.publish(mqtt_prefix + inverter.name + "/name", inverter.name, 1, True)
            
                args.IP = inverter.IP
            
                settings = aircon.get_status(args)
                
                logger.debug("Status: " + str(settings.on_off.value))
                logger.debug("Preset Temperature: " + str(settings.preset_temp.value))
                logger.debug("op_mode: " + str(settings.op_mode.value))
                logger.debug("airflow: " + str(settings.airflow.value))
                logger.debug("auto_3d: " + str(settings.entrust.value))
                logger.debug("wind_dir_ud: " + str(settings.wind_dir_ud.value))
                logger.debug("wind_dir_lr: " + str(settings.wind_dir_lr.value))
    
                ######################################
                #   MQTT publish
                ######################################
            
                client.publish(mqtt_prefix + inverter.name + "/" + "power_status", bool2onoff(bool(settings.on_off.value)), 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "preset_temperatur", settings.preset_temp.value, 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "operation_mode", settings.op_mode.value, 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "airflow", settings.airflow.value, 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "auto_3d", settings.entrust.value, 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "wind_ud", settings.wind_dir_ud.value, 0, False)
                client.publish(mqtt_prefix + inverter.name + "/" + "wind_lr", settings.wind_dir_lr.value, 0, False)
            
 
        except IOError:
            logger.error("Reading Inverter failed")  
            time.sleep(interval / 2)
        except:
            raise

        logger.debug("------- Loop Iteration Ended ---------")

        logger.debug("Sleep for " + str(interval) + "s")
        time.sleep(interval)

try:
    logger.info("╔═══════════════════════════════════════════════════════════════════╗")
    logger.info("║                                                                   ║")
    logger.info("║                Klimaanlagen Controller started                    ║")
    logger.info("║                                                                   ║")
    logger.info("╚═══════════════════════════════════════════════════════════════════╝")
    time.sleep(5)   #Wait 5 Seconds for MQTT to Connect and Pull Messages
    loop()
except:
    logger.info("------------ Client exited ------------")
    raise
    client.disconnect()
    client.loop_stop()
finally:
    logger.info("------------ Stopping client ------------")
    client.disconnect()
    client.loop_stop()
