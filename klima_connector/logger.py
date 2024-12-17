import logging
from logging.handlers import TimedRotatingFileHandler
from configparser import ConfigParser
import os
import gzip

class GZipRotator:
    def __call__(self, source, dest):
        os.rename(source, dest)
        f_in = open(dest, 'rb')
        f_out = gzip.open("%s.gz" % dest, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        os.remove(dest)


def setup_logger(general_config, script_dir):
    log_path = general_config["log_path"]
    if not os.path.isabs(log_path):
        log_path = os.path.join(script_dir, log_path)

    try:
        os.makedirs(log_path)
        print("Logdir {} created ".format(log_path))

    except FileExistsError:
        pass

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_log = logging.handlers.TimedRotatingFileHandler(log_path + general_config["log_filename"],
                                                         when='midnight', interval=1, encoding='utf-8')
    file_log.setLevel(logging.DEBUG)
    file_log.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    file_log.rotator = GZipRotator()
    root_logger.addHandler(file_log)

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s %(message)s'))
    root_logger.addHandler(console)

    return logging.getLogger(__name__)

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

app_logger = setup_logger(general_Config, script_dir)