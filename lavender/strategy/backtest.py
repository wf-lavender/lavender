# -*- coding:utf-8 -*-
"""
class for back test
Authors: Wang Fei
history: 2016.06.05 Initiated
         2017.09.26 Split PerformanceMeasure and Strategy classes from BackTest.
                    Modified and add Portfolio class to this module.
"""

from pylab import *
from strategy import Strategy
from lavender.util.DailyKLineIO import KLine
from decimal import Decimal as Dec
import pandas as pd
import lavender.config as cfg
import lavender.constant as ct
import matplotlib.font_manager as fm
import matplotlib
import numpy
import os
import time


class PerformanceMeasure:
    """
    class for performance measures for a strategy.
    Attributes:
        dates: <pd.DatetimeIndex>: dates of trading days.
        ndays: <int>: number of trading days.
        net_value: <float>: net value of the portfolio on current day.
                            This attribute should be calculated in subclasses.
        result: <pandas.DataFrame>: DataFrame contains "net value" and "daily return" series.
                                    This attribute should be calculated in subclasses.
    """
    def __init__(self, dates):
        """
        """
        self.dates = dates
        self.ndays = len(dates)

        self.net_value = 1.0
        self.result = None

    @property
    def years(self):
        """
        fractional years
        """
        fst_doy = self.dates[0].timetuple().tm_yday
        lst_doy = self.dates[-1].timetuple().tm_yday
        year_fraction = self.dates.year[-1]-self.dates.year[0] + (lst_doy - fst_doy) / 365.0
        return year_fraction

    def max_draw_down_duration(self):
        """
        calculate longest draw down duration.
        Returns:
            A tuple contains:
                draw_down_duration_max: the number of longest-draw-down trading days
                st_date_max: the start date of the longest-draw-down.
                ed_date_max: the end date of the longest-draw-down.

        """
        draw_down_duration = 0
        draw_down_duration_max = 0
        high_value = 0
        st_date = None
        st_date_max = None
        ed_date_max = None

        for iday in range(self.ndays):
            net_value = self.result.net_value.iloc[iday]
            # using ">=" to exclude duration without holding stock.
            if net_value >= high_value:
                draw_down_duration = 0
                high_value = net_value
                st_date = self.dates[iday]
            else:
                draw_down_duration += 1
                if draw_down_duration > draw_down_duration_max:
                    draw_down_duration_max = draw_down_duration
                    st_date_max = st_date
                    ed_date_max = self.dates[iday]

        return draw_down_duration_max, st_date_max, ed_date_max

    def max_draw_down(self):
        """
        calculate max draw down in the test period.
        """
        draw_down_max = 0
        high_value = 0
        st_date_max = None
        ed_date_max = None
        st_date = None
        for iday in range(self.ndays):
            net_value = self.result.net_value.iloc[iday]
            if net_value > high_value:
                high_value = net_value
                st_date = self.dates[iday]
            else:
                draw_down = 1 - net_value / high_value
                if draw_down_max < draw_down:
                    draw_down_max = draw_down
                    st_date_max = st_date
                    ed_date_max = self.dates[iday]
        return draw_down_max, st_date_max, ed_date_max

    @property
    def sharp_ratio(self):
        """
        Sharp Ratio
        """
        numerator = self.cagr - ct.REF_RETURN
        denominator = numpy.std(self.result.daily_return)
        return numerator/(denominator * numpy.sqrt(ct.TRADE_DAYS))

    @property
    def cagr(self):
        """
        Compound Average Growth Rate.
        """
        return self.net_value**(1.0/self.years) - 1

    def plot(self, save_name=None):
        """
        plot the result of back test.
        Args:
            save_name:
        Returns:
        """
        matplotlib.style.use("bmh")
        fig = figure(figsize=(14, 7))
        ax = fig.add_subplot(111)
        # font = fm.FontProperties(fname=ct.FONT_PATH)
        # ax.set_title(label="%s (%s)" % (ct.get_code_name(self.code), self.code), fontproperties=font)
        self.result.net_value.plot()
        ax.annotate("max draw down: %0.2f%%" % (self.max_draw_down()[0]*100), xy=(0.05, 0.9),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("max draw down duration: %d days" % self.max_draw_down_duration()[0], xy=(0.05, 0.85),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Sharp ratio: %0.2f" % self.sharp_ratio, xy=(0.05, 0.8),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Compound Average Growth Rate: %0.2f%%" % (self.cagr*100), xy=(0.05, 0.75),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        if save_name is not None:
            save_dir = os.path.join(cfg.technical_pic_dir, self.strategy)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            save_path = os.path.join(save_dir, save_name)
            fig.savefig(save_path)
        else:
            show()


class BackTest(Strategy, PerformanceMeasure):
    """
    Back test for a single stock.
    Members:
        k_line: <DailyKLineIO.Kline>: K line class for stock.
        brokerage: <float>: the brokerage of stock exchanging.
        stamp_duty: <float>: the stamp duty of stock exchanging.
        dates: <pd.DatetimeIndex>: dates of trading days(initiated in PerformanceMeasure).
        net_value: <float>: net value of the portfolio on current day.
                            (initiated in PerformanceMeasure)
        hold_list: <list, int>: a list contain holding information,
                if holding the stock till close, append 1, else append 0
        strategy: <str>: the strategy used now.
        result: <pandas.DataFrame>: DataFrame contains net value and daily return series.
                                    (initiated in PerformanceMeasure)
        ndays: <int>: number of trading days.(initiated in PerformanceMeasure)

    Methods:
        __init__: initialization
        ma_strategy: a trending strategy using moving average.
        trade_open: for strategies only exchange at open time.
    """

    def __init__(self, code, date_range=None, brokerage=0.001,
                 stamp_duty=0.001):
        """
        initialization...
        Args:
            code: <str>: code of a stock.
            date_range: <str>: date range of the test.
            brokerage: <float>: the brokerage of stock exchanging.
            stamp_duty: <float>: the stamp duty of stock exchanging.
        """

        self.code = code
        self.date_range = date_range
        self.k_line = KLine(code)
        if date_range is not None:
            self.k_line.date_cut(date_range)
        PerformanceMeasure.__init__(self, self.k_line.date)
        if self.ndays == 0:
            print 'warning: stock data empty!'

        self.brokerage = brokerage
        self.stamp_duty = stamp_duty

        self.hold_list = []

        self.strategy = None

    def ref_line(self, index_code='000001'):
        """
        Args:
            index_code: <str>: string of index code used as reference.
        Returns:
            ref_k_line: <pandas.DataFrame>: daily Kline of reference index.
        """
        file_path = os.path.join(cfg.index_dir, index_code+'.csv')
        ref_k_line = KLine(file_path).stock_data[self.dates[0]: self.dates[-1]]
        return ref_k_line

    @property
    def ref_line_return(self):
        """
        calculate the return of reference line.
        """
        st_net_value = self.ref_line().open.ix[0]
        ed_net_value = self.ref_line().close.ix[-1]
        return ed_net_value/st_net_value

    def trade_open(self, strategy, show_value=True, **kwargs):
        """
        test strategy that check indicators at close time on the first day,
        and trade at open time on the next day.
        Inputs:
            strategy: <str>: string of strategy function name
            show_value: <logic>: weather to print the latest net value.
        """

        if self.result is not None:
            self.__init__(self.code, date_range=self.date_range)

        net_value_list = list()
        daily_return_list = list()

        # strategy initialization
        if hasattr(self, '_init_%s' % strategy):
            getattr(self, '_init_%s' % strategy)(self.k_line)

        is_hold = False
        
        open_price = self.k_line.stock_data['open']
        close_price = self.k_line.stock_data['close']

        for iday in range(0, self.ndays):
            date = self.dates[iday]
            # back test begin if strategy indicators exits
            if not getattr(self, strategy)('exist', self.k_line, date, **kwargs):
                daily_return_list.append(0)
                self.hold_list.append(0)
                net_value_list.append(self.net_value)
                continue
            if is_hold:
                # also held the stock the last day
                if self.hold_list[iday-1] == 1:
                    daily_return = (close_price[iday] -
                                    close_price[iday-1]) / close_price[iday-1]
                    self.net_value *= (1+daily_return)
                # buy in the stock once open
                else:
                    daily_return = close_price[iday] / open_price[iday] \
                                    / (1+self.brokerage) - 1
                    self.net_value *= (1+daily_return)
                self.hold_list.append(1)
                # prepare to sell stock the next day
                if getattr(self, strategy)('sell', self.k_line, date, **kwargs):
                    is_hold = False
        
            else:
                # sell the stock once open
                if iday > 0 and self.hold_list[iday-1] == 1:
                    daily_return = open_price[iday] / close_price[iday-1] \
                                   * (1-self.brokerage-self.stamp_duty) - 1
                    self.net_value *= (1+daily_return)
                                
                # hold no stock
                else:
                    daily_return = 0
                self.hold_list.append(0)
                # prepare to buy the stock the next day
                if getattr(self, strategy)('buy', self.k_line, date, **kwargs):
                    is_hold = True
            net_value_list.append(self.net_value)
            daily_return_list.append(daily_return)
        self.result = pd.DataFrame({'net_value': net_value_list,
                                    'daily_return': daily_return_list},
                                   index=self.dates)
        self.strategy = strategy
        # self.result.to_csv("test_600519.csv", sep=" ", float_format="%.5f")
        if show_value:
            return 20*"*" + "%s Net Value: %f" % (strategy, self.result['net_value'][-1]) + 20*"*"
        else:
            return self.result

    def plot(self, save_name=None):
        """
        plot the result of back test.
        Args:
            save_name:
        Returns:
        """
        matplotlib.style.use("bmh")
        fig = figure(figsize=(14, 7))
        ax = fig.add_subplot(111)
        font = fm.FontProperties(fname=ct.FONT_PATH)
        ax.set_title(label="%s (%s)" % (ct.get_code_name(self.code), self.code), fontproperties=font)
        self.result.net_value.plot()
        ax.annotate("max draw down: %0.2f%%" % (self.max_draw_down()[0]*100), xy=(0.05, 0.9),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("max draw down duration: %d days" % self.max_draw_down_duration()[0], xy=(0.05, 0.85),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Sharp ratio: %0.2f" % self.sharp_ratio, xy=(0.05, 0.8),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Compound Average Growth Rate: %0.2f%%" % (self.cagr*100), xy=(0.05, 0.75),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        if save_name is not None:
            save_dir = os.path.join(cfg.technical_pic_dir, self.strategy)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            save_path = os.path.join(save_dir, save_name)
            fig.savefig(save_path)
        else:
            show()


class Portfolio(Strategy, PerformanceMeasure):
    """
    Back test for a bucket of stocks.
    """

    def __init__(self, pools, date_range=None, brokerage=0.001,
                 stamp_duty=0.001):
        """
        Args:
            pools: <list: str>: list of pool names.
        """
        dates = pd.DatetimeIndex([])
        self.code_pools = dict()
        self.klines = dict()
        self.codes = list()

        # extract codes and dates in pools.
        for pool in pools:
            data_path = os.path.join(cfg.pool_dir, pool)
            codes = pd.read_csv(data_path, header=None, names=["code", " "], delim_whitespace=True,
                                dtype={"code": "str"}, index_col=False).code
            self.code_pools[pool] = codes
            for code in codes:
                self.codes.append(code)
                kline_cl = KLine(code)
                if date_range is not None:
                    kline_cl.date_cut(date_range)
                date = kline_cl.date
                dates = dates.append(date)
                self.klines[code] = kline_cl
        dates = dates.sort_values().drop_duplicates()

        PerformanceMeasure.__init__(self, dates)
        if self.ndays == 0:
            print 'warning: stock data empty!'
        # for code in self.klines:
        #     self.klines[code]

        self.pools = pools
        self.pool_position = list()
        self.strategy = None
        self.cash_held = 1.0

        self.brokerage = brokerage
        self.stamp_duty = stamp_duty

    @property
    def stock_value(self):
        if self.stock_held:
            return sum(self.stock_held.values())
        else:
            return 0.0

    @property
    def unit_position(self):
        return self.net_value/10.0

    @staticmethod
    def deal_success(signal_type, high, low, last_close):
        if signal_type == "sell":
            if high == low and high < last_close:
                return False
            else:
                return True
        if signal_type == "buy":
            if high == low and high > last_close:
                return False
            else:
                return True

    def trade_open(self, strategy, show_value=True, **kwargs):

        if self.result is not None:
            self.__init__(self.pools)

        net_value_list = list()
        daily_return_list = list()

        cash_held_list = list()
        stock_held_list = list()

        # strategy initialization
        if hasattr(self, '_init_%s' % strategy):
            getattr(self, '_init_%s' % strategy)(self.codes, self.klines)

        stock_held = dict()
        for iday in range(0, self.ndays):
            date = self.dates[iday]
            daily_return = 0.0
            stock_held_list.append(stock_held.copy())
            delta_net_value = 0.0

            for code_pool in self.code_pools:
                codes = self.code_pools[code_pool]

                for code in codes:
                    k_line = self.klines[code]

                    if date not in k_line.date:
                        # hold the stock while stock was suspended.
                        if code in stock_held_list[iday-1]:
                            stock_held_list[iday][code] = stock_held_list[iday-1][code]
                        # pause until the stock was available to buy.
                        else:
                            stock_held_list[iday].pop(code, None)
                        continue

                    # back test begin if strategy indicators exist
                    if not getattr(self, strategy)('exist', k_line, date, **kwargs):
                        continue

                    open_price = k_line.stock_data['open']
                    close_price = k_line.stock_data['close']
                    high_price = k_line.stock_data['high']
                    low_price = k_line.stock_data['low']

                    prev_date_ind = k_line.date.get_loc(date) - 1
                    if code in stock_held:
                        # also held the stock the last day, so go on holding.
                        if code in stock_held_list[iday-1]:
                            daily_return += (close_price.ix[date] - close_price.iloc[prev_date_ind]) / \
                                            close_price.iloc[prev_date_ind] * stock_held_list[iday-1][code] / \
                                            net_value_list[iday-1]
                            delta_net_value += (close_price.ix[date] - close_price.iloc[prev_date_ind]) / \
                                close_price.iloc[prev_date_ind] * stock_held_list[iday-1][code]
                            stock_held_list[iday][code] = close_price.ix[date] / close_price.iloc[prev_date_ind] \
                                * stock_held_list[iday-1][code]
                        # buy in the stock once open.
                        else:
                            position = self.unit_position  # TODO: configure position.
                            # not enough money or fail to trade.
                            if Dec(str(self.cash_held)) < Dec(str(position)) and \
                                    not self.deal_success("buy", high_price.ix[date], low_price.ix[date],
                                                          close_price.iloc[prev_date_ind]):
                                stock_held.pop(code)
                                stock_held_list[iday].pop(code)
                                continue

                            self.cash_held -= position
                            daily_return += (close_price.ix[date] / open_price.ix[date]
                                             / (1 + self.brokerage) - 1) * position / net_value_list[iday-1]
                            delta_net_value += (close_price.ix[date] / open_price.ix[date]
                                                / (1 + self.brokerage) - 1) * position

                            stock_held_list[iday][code] = close_price.ix[date] * position \
                                / open_price.ix[date] / (1 + self.brokerage)

                        # prepare to sell stock the next day
                        if getattr(self, strategy)('sell', k_line, date, **kwargs):
                            stock_held.pop(code)

                    else:
                        #  held the stock the last day, sell the stock once open
                        if iday > 0 and code in stock_held_list[iday-1]:
                            # fail to sell, go on holding.
                            if not self.deal_success("sell", high_price.ix[date], low_price.ix[date],
                                                     close_price.iloc[prev_date_ind]):
                                daily_return += (close_price.ix[date] - close_price.iloc[prev_date_ind]) / \
                                    close_price.iloc[prev_date_ind] * stock_held_list[iday - 1][code] / \
                                    net_value_list[iday - 1]
                                delta_net_value += (close_price.ix[date] - close_price.iloc[prev_date_ind]) / \
                                    close_price.iloc[prev_date_ind] * stock_held_list[iday - 1][code]
                                stock_held_list[iday][code] = close_price.ix[date] / close_price.iloc[prev_date_ind] \
                                    * stock_held_list[iday - 1][code]

                            daily_return += (open_price.ix[date] / close_price.iloc[prev_date_ind]
                                             * (1 - self.brokerage - self.stamp_duty) - 1) \
                                * stock_held_list[iday-1][code] / net_value_list[iday-1]
                            delta_net_value += (open_price.ix[date] / close_price.iloc[prev_date_ind] *
                                                (1 - self.brokerage - self.stamp_duty) - 1) \
                                * stock_held_list[iday-1][code]

                            self.cash_held += open_price.ix[date] / close_price.iloc[prev_date_ind]  \
                                * (1 - self.brokerage - self.stamp_duty) \
                                * stock_held_list[iday-1][code]
                        # not hold stock
                        else:
                            pass

                        # prepare to buy the stock the next day
                        if getattr(self, strategy)('buy', k_line, date, **kwargs):
                            stock_held[code] = self.unit_position     # the value for stock_held[code] doesn't matter.

            self.net_value += delta_net_value
            net_value_list.append(self.net_value)
            daily_return_list.append(daily_return)
            cash_held_list.append(self.cash_held)

        self.result = pd.DataFrame({'net_value': net_value_list,
                                    'daily_return': daily_return_list,
                                    'cash_held': cash_held_list,
                                    'stock_held': stock_held_list},
                                   index=self.dates)
        self.result.to_csv("roe_gt_15.csv", sep=" ", float_format="%.5f")
        self.strategy = strategy
        if show_value:
            return 20 * "*" + "%s Net Value: %f" % (strategy, self.result['net_value'][-1]) + 20 * "*"
        else:
            return self.result

    def plot(self, save_name=None, y_scale="linear"):
        """
        plot the result of back test.
        Args:
            save_name:
            y_scale: "linear", "log"
        Returns:
        """
        matplotlib.style.use("bmh")
        fig = figure(figsize=(14, 7))
        ax = fig.add_subplot(111)
        # font = fm.FontProperties(fname=ct.FONT_PATH)
        # ax.set_title(label="%s (%s)" % (ct.get_code_name(self.code), self.code), fontproperties=font)
        self.result.net_value.plot()
        ax.annotate("max draw down: %0.2f%%" % (self.max_draw_down()[0]*100), xy=(0.05, 0.9),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("max draw down duration: %d days" % self.max_draw_down_duration()[0], xy=(0.05, 0.85),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Sharp ratio: %0.2f" % self.sharp_ratio, xy=(0.05, 0.8),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        ax.annotate("Compound Average Growth Rate: %0.2f%%" % (self.cagr*100), xy=(0.05, 0.75),
                    horizontalalignment='left', verticalalignment='center', xycoords="axes fraction")
        if y_scale is not None:
            ax.set_yscale(y_scale)
        if save_name is not None:
            save_dir = os.path.join(cfg.technical_pic_dir, self.strategy)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            save_path = os.path.join(save_dir, save_name)
            fig.savefig(save_path)
        else:
            show()


if __name__ == '__main__':

    # portfolio = Portfolio(["roe_gt_15.csv", "家电行业.csv".decode("utf8")])

    # exit(404)

    # sel_code = "600519"
    # test = BackTest(sel_code)
    # print test.trade_open("random_strategy")
    # test.plot("%s.png" % sel_code)

    # print test.trade_open('extremum_contrary_strategy')
    # print "max draw down:", test.max_draw_down()
    # print "max draw down duration:", test.max_draw_down_duration()
    # print 'sharp:', test.sharp_ratio
    # print test.cagr
    # test.plot("%s.png" % sel_code)
    #
    # print test.trade_open('dual_ma_strategy')
    # test.plot("%s.png" % sel_code)
    # print test.cagr
    # print test.ref_line
    # print "SH reference return:", test.ref_line_return
    #
    # print test.trade_open('bollinger_breakout_strategy')
    # print "max draw down:", test.max_draw_down()
    # print "max draw down duration:", test.max_draw_down_duration()
    # print 'sharp:', test.sharp_ratio
    # test.plot("%s.png" % sel_code)
    # print test.cagr

    # ***********************
    # Portfolio test
    # ***********************
    t0 = time.time()
    portfolio = Portfolio(["roe_gt_15.csv".decode("utf8"), ], date_range=None)
    print portfolio.trade_open("extremum_contrary_strategy")
    portfolio.plot("roe_gt_15.png".decode("utf8"))
    print "time cost:", time.time() - t0

    # Show pictures for net value of simulation.
    # print "max draw down:", test.max_draw_down()
    # print "max draw down duration:", test.max_draw_down_duration()
    # print 'sharp:', test.sharp_ratio
    # figure(1)
    # subplot(311)
    # plot(test.result.net_value)
    # subplot(312)
    # plot(test.result.daily_return)
    # subplot(313)
    # plot(test.hold_list)
    # savefig("test.ps")
