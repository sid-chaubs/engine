import numpy
import talib as ta
from pandas import DataFrame

from models.ohlcv import OHLCV
from models.trade import Trade

# ======================================================================
# Strategy-class is responsible for populating indicators / signals
#
# © 2021 DemaTrading.AI
# ======================================================================


class Strategy:
    min_candles = 21

    def generate_indicators(self, past_candles: DataFrame, current_candle: DataFrame) -> DataFrame:
        """
        :param past_candles: Array of candle-data (OHLCV models)
        :type past_candles: [OHLCV]
        :param current_candle: Last candle
        :type current_candle: OHLCV model
        :return: dictionary filled with indicator-data
        :rtype: dictionary
        """
        return {}

    def buy_signal(self, indicators: DataFrame, current_candle: DataFrame) -> DataFrame:
        """
        :param indicators: indicator dictionary created by generate_indicators method
        :type indicators: dictionary
        :param current_candle: last candle
        :type current_candle: OHLCV model
        :return: returns whether to buy or not buy specified coin (True = buy, False = skip)
        :rtype: boolean
        """
        current_candle['buy'] = 1
        return current_candle

    def sell_signal(self, indicators: DataFrame, current_candle: DataFrame, trade: Trade) -> DataFrame:
        """
        :param indicators: indicator dictionary created by generate_indicators method
        :type indicators: dictionary
        :param current_candle: last candle
        :type current_candle: OHLCV model
        :param trade: current open trade
        :type trade: Trade model
        :return: returns whether to close or not close specified trade (True = sell, False = skip)
        :rtype: boolean
        """
        current_candle['sell'] = 0
        return current_candle
