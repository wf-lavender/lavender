"""
module to edit strategies.
Authors: Wang Fei
History: 2017.09.22
"""

import lavender.config as cfg
import numpy as np


# TODO: use a completed object as input attributes of strategies.
class Strategy(object):
    """
    Edit strategies here.
    """
    @staticmethod
    def holding_strategy(signal_type, k_line, date):
        """
        holding all the time.
        """
        if signal_type == "sell":
            return False

        if signal_type == "buy":
            return True

        if signal_type == "exist":
            return True

    @staticmethod
    def random_strategy(signal_type, k_line, date):
        """
        random buy or sell orders.
        Args:
            signal_type:
            k_line:
            date:
        """
        if signal_type == "sell":
            random_num = np.random.uniform(-1, 1)
            if random_num > 0:
                return True
            else:
                return False

        if signal_type == "buy":
            random_num = np.random.uniform(-1, 1)
            if random_num > 0:
                return True
            else:
                return False

        if signal_type == "exist":
            return True

    @staticmethod
    def bollinger_breakout_strategy(signal_type, k_line, date, bl_days=350, scale=2.5):
        """
        Args:
            k_line: <DailyKLineIO.Kline>: K line class for stock.
            date: <pd.DatetimeIndex>: date of trading day.
            signal_type: <str>: type of signal to judge.
            bl_days: <int>: number of days used for moving window.
            scale: <float>: scale for standard error.
        Returns:
            <logic>
        """
        bl_ma = k_line.ma(bl_days)
        close_price = k_line.stock_data['close']
        bl_std = k_line.std_dev(bl_days)
        prev_date = k_line.date.get_loc(date) - 1

        if signal_type == 'sell':
            if close_price.ix[date] < bl_ma.ix[date]:
                return True
            else:
                return False

        if signal_type == 'buy':
            if close_price.ix[date] > bl_ma.ix[date] + scale * bl_std.ix[date] and \
                            close_price.iloc[prev_date] <= bl_ma.iloc[prev_date] + scale * bl_std.iloc[prev_date]:
                return True
            else:
                return False

        if signal_type == 'exist':
            if (prev_date < 0 or np.isnan(bl_ma.iloc[prev_date]) or
                    np.isnan(bl_std.iloc[prev_date]) or
                    np.isnan(close_price.iloc[prev_date])):
                return False
            else:
                return True

    def _init_extremum_contrary_strategy(self, codes, k_lines):
        # TODO: should be modified for portfolio class.
        """
        Initialization of strategy. Mainly to avoid time-wasting slice processing in loop in
        strategy functions.
        """
        support_dict = dict()
        resistance_dict = dict()
        for code in codes:
            kline = k_lines[code]
            support_dict[code] = kline.support[~np.isnan(kline.support)]
            resistance_dict[code] = kline.resistance[~np.isnan(kline.resistance)]
        setattr(self, '_support', support_dict)
        setattr(self, '_resistance', resistance_dict)

    def extremum_contrary_strategy(self, signal_type, k_line, date):
        """
        Args:
            k_line: <DailyKLineIO.Kline>: K line class for stock.
            date: <pd.DatetimeIndex>: date of trading day.
            signal_type: <str>: whether to judge if sell or
               judge if buy or judge if the indicators exist.
        Returns:
            <logic>
        """
        idate = k_line.date.get_loc(date)
        if signal_type == 'exist':
            if idate < cfg.support_window or idate < cfg.resistance_window:
                return False

        #
        # To avoid future information errors of support and resistance. subtract support_window/resistance_window
        # from current index.
        # Be careful, slice of value in pandas series include the last element in slice, which is different
        # from slice of index(exclude the last element).
        #
        support = self._support[k_line.code].loc[:k_line.date[idate - cfg.support_window]][-4:]
        # support = k_line.support[:idate-cfg.support_window+1][~np.isnan(k_line.support)][-4:]
        resistance = self._resistance[k_line.code].loc[:k_line.date[idate - cfg.resistance_window]][-4:]
        # resistance = k_line.resistance[:idate-cfg.resistance_window+1][~np.isnan(k_line.resistance)][-4:]
        close_price = k_line.stock_data['close']

        if signal_type == 'sell':
            cv_res = resistance.std() / resistance.mean()
            if close_price[idate] > resistance.mean() and cv_res < 0.1:
                return True
            else:
                return False

        if signal_type == 'buy':
            cv_sup = support.std() / support.mean()
            if close_price[idate] <= support.mean() and cv_sup < 0.08:
                return True
            else:
                return False

        if signal_type == 'exist':
            if len(support) < 4 or len(resistance) < 4:
                return False
            else:
                return True

    @staticmethod
    def dual_ma_strategy(signal_type, k_line, date, ma_fast=60, ma_slow=250):
        """
        ma_fast < ma_slow: sell
        ma_fast > ma_slow: buy
        Inputs:
            k_line: <DailyKLineIO.Kline>: K line class for stock.
            signal_type: <str>:whether to judge if sell or
                   judge if buy or judge if the indicators exist
                signal_type = 'sell': determine whether to sell shares
                signal_type = 'buy': determine whether to buy shares
                signal_type = 'exist': determine whether indicators exist
            date: <pd.DatetimeIndex>: date of trading day.
        """

        ma_f = k_line.ma(ma_fast)
        ma_s = k_line.ma(ma_slow)

        prev_date = k_line.date.get_loc(date) - 1

        # if sell stock
        if signal_type == 'sell':
            if ma_f.ix[date] < ma_s.ix[date]:
                return True
            else:
                return False
        # if buy stock
        if signal_type == 'buy':
            if ma_f.ix[date] > ma_s.ix[date] and \
                            ma_f.iloc[prev_date] <= ma_s.iloc[prev_date]:
                return True
            else:
                return False
        # if MA exists
        if signal_type == 'exist':
            if prev_date < 0 or \
                    np.isnan(ma_f.iloc[prev_date]) or \
                    np.isnan(ma_s.iloc[prev_date]):
                return False
            else:
                return True
