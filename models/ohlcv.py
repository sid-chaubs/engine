# ======================================================================
# OHLCV Class is used for candle-data served by CCXT
#
# © 2021 DemaTrading.AI
# ======================================================================


class OHLCV:

    
    def __init__(self, candle, pair):
        self.time = candle[0]
        self.open = candle[1]
        self.high = candle[2]
        self.low = candle[3]
        self.close = candle[4]
        self.volume = candle[5]
        self.pair = pair

    def get_data(self):
        return [self.time, self.open, self.high, self.low, self.close, self.volume]

    def get_indicator_names(self):
        return ['time', 'open', 'high', 'low', 'close', 'volume']