"""This module contains helper functions that have to do with the config 
file, like validation and currency support"""

import json
import sys
from .validations import validate_config


def read_config() -> dict:
    print('====================================== \n Starting up DEMA BACKTESTING \n======================================')
    # Try opening the config file.
    try:
        with open('config.json', 'r') as configfile:
            data = configfile.read()
    except FileNotFoundError:
        print("[ERROR] no config file found.")
        raise SystemExit
    except:
        print("[ERROR] something went wrong parsing config file.",
              sys.exc_info()[0])
        raise SystemExit

    config = json.loads(data)

    return config


def print_pairs(config_json):
    coins = ''
    for i in config_json['pairs']:
        coins += str(i) + ' '
    print("[INFO] Watching pairs: %s" % coins)

    

