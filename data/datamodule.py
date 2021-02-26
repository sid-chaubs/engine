from collections import namedtuple

import numpy as np
import ccxt
import re
import json
import sys
from collections import defaultdict
from models.ohlcv import OHLCV
from models.ohlcv_encoder import OHLCVEncoder
from os import path
import os


# ======================================================================
# DataModule is responsible for downloading OHLCV data, preparing it
# and activating backtesting methods
#
# © 2021 DemaTrading.AI
# ======================================================================

msec = 1000
minute = 60 * msec
hour = 60 * minute
day = 24 * hour


class DataModule:
    exchange = None
    timeframe_calc = None

    backtesting_from = None
    backtesting_to = None

    history_data = {}

    def __init__(self, config, backtesting_module):
        print('[INFO] Starting DEMA Data-module...')
        self.config = config
        self.backtesting_module = backtesting_module
        self.config_timeframe_calc()
        self.load_exchange()

    def load_exchange(self) -> None:
        """
        Method checks for requested exchange existence
        checks for exchange OHLCV compatibility
        checks for timeframe support
        loads markets if no errors occur
        :return: None
        :rtype: None
        """
        print('[INFO] Connecting to exchange...')
        exchange_id = self.config['exchange']

        # Try to get exchange based on config param 'exchange'
        try:
            self.exchange = getattr(ccxt, exchange_id)
            self.exchange = self.exchange()
            print("[INFO] Connected to exchange: %s." % self.config['exchange'])
        except AttributeError:
            print("[ERROR] Exchange %s could not be found!" % exchange_id)
            raise SystemExit

        # Check whether exchange supports OHLC
        if not self.exchange.has["fetchOHLCV"]:
            print("[ERROR] Cannot load data from %s because it doesn't support OHLCV-data" % self.config['exchange'])
            raise SystemExit

        # Check whether exchange supports requested timeframe
        if (not hasattr(self.exchange, 'timeframes')) or (self.config['timeframe'] not in self.exchange.timeframes):
            print("[ERROR] Requested timeframe is not available from %s" % self.config['exchange'])
            raise SystemExit

        self.load_markets()

    def load_markets(self) -> None:
        self.exchange.load_markets()
        self.config_from_to()
        self.load_historical_data()

    def load_historical_data(self) -> None:
        """
        Method checks for datafile existence, if not existing, download data and save to file
        :return: None
        :rtype: None
        """
        # for pair in self.config['pairs']:
        #     if not self.check_for_datafile_existence(pair, self.config['timeframe']):
        #         # datafile doesn't exist. Start downloading data, create datafile
        #         print("[INFO] Did not find datafile for %s" % pair)
        #         self.download_data_for_pair(pair, True)
        #     elif self.does_datafile_cover_backtesting_period(pair, self.config['timeframe']):
        #         # load data from datafile instead of exchange
        #         self.read_data_from_datafile(pair, self.config['timeframe'])
        #     elif not self.does_datafile_cover_backtesting_period(pair, self.config['timeframe']):
        #         # remove file, download data from exchange, create new datafile
        #         if self.check_for_datafile_existence(pair, self.config['timeframe']):
        #             self.delete_file(pair, self.config['timeframe'])
        #         self.download_data_for_pair(pair, True)

        for pair in self.config['pairs']:
            if not self.check_datafolder(pair):
                print("[INFO] Did not find datafile for %s" % pair)
                pair_dict = self.download_data_for_pair(pair, self.backtesting_from, self.backtesting_to)
            else:
                print("[INFO] Checking datafile for %s" % pair)
                pair_dict = self.read_data_from_datafile(pair)
                if not pair_dict:
                    print("[INFO] Datafile incorrect. Downloading new data for %s" % pair)
                    self.delete_file(pair)
                    pair_dict = self.download_data_for_pair(pair, self.backtesting_from, self.backtesting_to)
            self.history_data[pair] = pair_dict

        self.backtesting_module.start_backtesting(self.history_data, self.backtesting_from, self.backtesting_to)

    def parse_ohlcv_data(self, data, pair: str) -> [OHLCV]:
        """
        :param data: OHLCV data provided by CCXT in array format []
        :type data: float array
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :return: OHLCV array
        :rtype: [OHLCV]
        """
        return_value = {}
        for candle in data:
            ohlcv = OHLCV(candle, pair)
            return_value[candle[0]] = ohlcv
        return return_value

    def download_data_for_pair(self, pair: str, data_from: str, data_to: str) -> dict:
        """
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param write_to_datafile: Whether to write downloaded data to jsonfile
        :type write_to_datafile: boolean
        :return: None
        :rtype: None
        """
        start_date = data_from
        fetch_ohlcv_limit = 1000

        print("[INFO] Downloading %s's data" % pair)
        
        return_dict = {}
        while start_date < data_to:
            # Request ticks for given pair (maximum = 1000)
            remaining_ticks = (data_to - start_date) / self.timeframe_calc
            asked_ticks = min(remaining_ticks, fetch_ohlcv_limit)
            result = self.exchange.fetch_ohlcv(symbol=pair, timeframe=self.config['timeframe'], \
                                                since=int(start_date), limit=int(asked_ticks))

            # Store OHLCV data in dictionary
            temp_dict = self.parse_ohlcv_data(result, pair)
            return_dict = {**return_dict, **temp_dict}
            start_date += np.around(asked_ticks * self.timeframe_calc)

        print("[INFO] [%s] %s candles downloaded" % (pair, len(return_dict)))

        self.save_file(pair, return_dict)
        return return_dict

    def config_timeframe_calc(self) -> None:
        """
        Method checks for valid timeframe input in config file.
        Besides sets self.timeframe_calc property, which is used
        to calculate how much time has passed based on an amount of candles
        so:
        self.timeframe_calc * 10 candles passed = milliseconds passed
        """
        print('[INFO] Configuring timeframe')
        timeframe = self.config['timeframe']
        match = re.match(r"([0-9]+)([mdh])", timeframe, re.I)
        if not match:
            print("[ERROR] Error whilst parsing timeframe")
            raise SystemExit
        items = re.split(r'([0-9]+)', timeframe)
        if items[2] == 'm':
            self.timeframe_calc = int(items[1]) * minute
        elif items[2] == 'h':
            self.timeframe_calc = int(items[1]) * hour

    def config_from_to(self) -> None:
        """
        This method sets the self.backtesting_to / backtesting_from properties
        with 8601 parsed timestamp
        :return: None
        :rtype: None
        """
        test_from = self.config['backtesting-from']
        test_to = self.config['backtesting-to']
        test_till_now = self.config['backtesting-till-now']

        self.backtesting_from = self.exchange.parse8601("%sT00:00:00Z" % test_from)
        if test_till_now == 'True':
            print('[INFO] Gathering data from %s until now' % test_from)
            self.backtesting_to = self.exchange.milliseconds()
        elif test_till_now == 'False':
            print('[INFO] Gathering data from %s until %s' % (test_from, test_to))
            self.backtesting_to = self.exchange.parse8601("%sT00:00:00Z" % test_to)
        else:
            print(
                "[ERROR] Something went wrong parsing config. Please use yyyy-mm-dd format at 'backtesting-from', 'backtesting-to'")

    def check_datafolder(self, pair: str) -> bool:
        """
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param timeframe: Time frame of coin pair f.e. "1h" / "5m"
        :type timeframe: string
        :return: Returns whether datafile for specified pair / timeframe already exists
        :rtype: boolean
        """
        # Check if datafolder exists
        filename = self.generate_datafile_name(pair)
        exchange_path = os.path.join("data/backtesting-data", self.config["exchange"])
        if not path.exists(exchange_path):
            self.create_directory(exchange_path)

        # Checks if datafile exists
        dirpath = os.path.join(exchange_path, filename)
        return path.exists(dirpath)

    def create_directory(self, directory: str) -> None:
        """
        :param directory: string of path to directory
        :type directory: string
        :return: None
        :rtype: None
        """
        try:
            os.makedirs(directory)
        except OSError:
            print("Creation of the directory %s failed" % path)
        else:
            print("Successfully created the directory %s " % path)

    def read_data_from_datafile(self, pair) -> dict:
        """
        When datafile is covering requested backtesting period,
        this method reads the data from the files. Saves this in
        self.historical_data
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param timeframe: Time frame of coin pair f.e. "1h" / "5m"
        :type timeframe: string
        :return: None
        :rtype: None
        """
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config["exchange"], filename)
        try:
            with open(filepath, 'r') as datafile:
                data = datafile.read()
        except FileNotFoundError:
            print("[ERROR] Backtesting datafile was not found.")
            raise SystemExit
        except:
            print("[ERROR] Something went wrong loading datafile", sys.exc_info()[0])
            raise SystemExit

        print("[INFO] Loading historic data of %s from existing datafile." % pair)

        # Check backtesting period
        historic_data = json.loads(data)
        if historic_data["from"] == self.backtesting_from and historic_data["to"] == self.backtesting_to:
            # Load json file if in correct range
            return_dict = {}
            for tick in historic_data['ohlcv']:
                parsed_tick = json.loads(tick)
                ohlcv_class = OHLCV(list(parsed_tick.values()), pair)
                return_dict = {**return_dict, **{ohlcv_class.time: ohlcv_class}}
            return return_dict
        return None

    def save_file(self, pair: str, data: dict) -> None:
        """
        Method creates new json datafile for pair in timeframe
        :param data: Downloaded data to write to the datafile
        :type data: OHLCV array
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param timeframe: Time frame of coin pair f.e. "1h" / "5m"
        :type timeframe: string
        :return: None
        :rtype: None
        """
        data_for_file = {
            "from" : self.backtesting_from,
            "to" : self.backtesting_to,
            "ohlcv" : []
        }
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config["exchange"], filename)
        for tick in data:
            ohlcv = data[tick]
            json_ohlcv = OHLCVEncoder().encode(ohlcv)
            data_for_file["ohlcv"].append(json_ohlcv)
        with open(filepath, 'w') as outfile:
            json.dump(data_for_file, outfile, indent=4)

    def generate_datafile_name(self, pair: str) -> str:
        """
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :return: returns a filename for specified pair / timeframe
        :rtype: string
        """
        coin, base = pair.split('/')
        return "data-{}{}{}.json".format(coin, base, self.config['timeframe'])

    def delete_file(self, pair: str):
        """
        Method removes existing datafile, as it does not cover requested
        backtesting period.
        :param pair: Certain coin pair in "AAA/BBB" format
        :type pair: string
        :param timeframe: Time frame of coin pair f.e. "1h" / "5m"
        :type timeframe: string
        :return: None
        :rtype: None
        """
        filename = self.generate_datafile_name(pair)
        filepath = os.path.join("data/backtesting-data/", self.config["exchange"], filename)
        os.remove(filepath)

    def customOHLCVDecoder(self, ohlcv_dict) -> namedtuple:
        """
        This method is used for reading ohlcv-data from saved json datafiles.
        :param ohlcv_dict: dictionary-format ohlcv-model, which is 1 candle in specified timeframe
        :type ohlcv_dict: json-format ohlcv-model
        :return: named tuple with OHLCV properties (more or less the same as the model)
        :rtype: namedtuple
        """
        return namedtuple('OHLCV', ohlcv_dict.keys())(*ohlcv_dict.values())
