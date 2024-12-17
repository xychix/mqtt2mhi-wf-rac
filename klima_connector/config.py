"""Local configuration"""
import os
import socket
from configparser import ConfigParser
import getpass

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the path to the configuration file
config_file_path = os.path.join(script_dir, 'config/config.ini')

# Check if the config file exists
if not os.path.isfile(config_file_path):
    raise FileNotFoundError(f"The configuration file {config_file_path} was not found.")

#Read config.ini file
config_object = ConfigParser()
config_object.read(config_file_path)
general_Config = config_object["general"]

MY_DEVICE_ID = socket.gethostname()
#MY_OPERATOR_ID = getpass.getuser()
MY_OPERATOR_ID = general_Config["operator_id"]

TIMEZONE='UTC'
if os.path.exists('/etc/timezone'):
    with open('/etc/timezone', 'r', encoding='utf-8') as f:
        TIMEZONE=f.read().strip()
