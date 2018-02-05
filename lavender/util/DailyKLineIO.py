"""
This module defines the class of historic K Lines and
relative functions.
Authors: Wang Fei
History: 2016.06.19
"""

import os
import re
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn import linear_model

import lavender.config as cfg
import lavender.constant as ct
import lavender.util.plotReturn as Pr


def linear_weight(shift, slope, intercept):
    if type(shift) in ct.ARRAY_LIKE_TYPE:
        cof = [intercept + slope * i for i in shift]
        return [i / sum(cof) for i in cof]
    else:
        return intercept + slope * shift


def _month_return(daily_stock):
    """
    calculate monthly return from daily stock data.
    Args:
        daily_stock: <pandas.DataFrame>: should have column named "close" and have
                    daily dates as index.
    Returns:
        month_return
    """
    month_group = daily_stock.groupby(pd.TimeGrouper(freq="M"))
    last_day = month_group.last()
    if len(month_group) >= 2:
        month_return = last_day.close/last_day.shift(1).close
        return month_return
    else:
        print("Stock data is less than two months!")
        raise ValueError


class KLine:
    """
    class restoring a stock's historical K Lines
    Members:
        _stock_whole_data: <pandas.DataFrame>: original data
        stock_data: <pandas.DataFrame>: data in specified date
    Methods:
    """
    def __init__(self, code):
        if os.path.exists(code):
            # "code" input is already a path
            self.code = os.path.basename(code.split('.')[0])
            file_path = code
        else:
            self.code = code
            file_name = code + ct.FILE_EXT['csv']
            file_path = os.path.join(cfg.kline_dir, file_name)
            if not os.path.exists(file_path):
                raise IOError("no data for %s!" % code)

        self.beta_coef = None
        self.market_return = None
        self._stock_whole_data = pd.read_csv(file_path, index_col=0, parse_dates=True)
        self.stock_data = pd.read_csv(file_path, index_col=0, parse_dates=True)

    def __getitem__(self, item):
        return self.stock_data[item]

    def __len__(self):
        return len(self._stock_whole_data)

    @property
    def date(self):
        return self.stock_data.index

    @property
    def years(self):
        """
        fractional years
        """
        fst_doy = self.date[0].timetuple().tm_yday
        lst_doy = self.date[-1].timetuple().tm_yday
        year_fraction = self.date.year[-1]-self.date.year[0] + (lst_doy - fst_doy) / 365.0
        return year_fraction

    @property
    def tr(self):
        # add true range to stock_data DataFrame
        if 'TR' in self.stock_data:
            return self.stock_data['TR']
        else:
            tr_list = list()
            for i, close_price in enumerate(self._stock_whole_data.close.ix[:-1]):
                high_price = self._stock_whole_data.high.ix[i + 1]
                low_price = self._stock_whole_data.low.ix[i + 1]  # the last day's close price
                tr_list.append(max(abs(high_price - low_price),
                                   abs(low_price - close_price),
                                   abs(high_price - close_price)))

            tr_series = pd.Series(index=self._stock_whole_data.index)
            tr_series[1:] = tr_list
            self._stock_whole_data.loc[:, 'TR'] = tr_series
            self.stock_data.loc[self.date, 'TR'] = self._stock_whole_data.loc[self.date, 'TR'].copy()
            return self.stock_data.loc[self.date, 'TR']

    @property
    def support(self):
        """
        Find minimum prices in moving window(defined with cfg.support_window).
        """
        if 'support' in self.stock_data:
            support_up2date = self._stock_whole_data.loc[:self.date[-1], 'support'].copy()
            return support_up2date
        else:
            support_line = np.full(len(self), np.nan)
            index = self._stock_whole_data.index
            minimum = self._stock_whole_data["low"].rolling(window=2 * cfg.support_window + 1, center=True).min()
            for iday in range(len(self)):
                if self._stock_whole_data.low[index[iday]] == minimum[index[iday]]:
                    support_line[iday] = self._stock_whole_data.low[index[iday]]
            support_line = pd.Series(support_line, index=self._stock_whole_data.index)
            self._stock_whole_data['support'] = support_line
            self.stock_data.loc[self.date, 'support'] = self._stock_whole_data.loc[self.date, 'support'].copy()
            support_up2date = self._stock_whole_data.loc[:self.date[-1], 'support'].copy()
            return support_up2date

    @property
    def resistance(self):
        """
        Find maximum prices in moving window(defined with cfg.resistance_window).
        """
        if 'resistance' in self.stock_data:
            support_up2date = self._stock_whole_data.loc[:self.date[-1], 'resistance'].copy()
            return support_up2date
        else:
            resistance_line = np.full(len(self), np.nan)
            index = self._stock_whole_data.index
            maximum = self._stock_whole_data["high"].rolling(window=2 * cfg.resistance_window + 1, center=True).max()
            for iday in range(len(self)):
                if self._stock_whole_data.high[index[iday]] == maximum[index[iday]]:
                    resistance_line[iday] = self._stock_whole_data.high[index[iday]]
            resistance_line = pd.Series(resistance_line, index=self._stock_whole_data.index)
            self._stock_whole_data['resistance'] = resistance_line
            self.stock_data.loc[self.date, 'resistance'] = self._stock_whole_data.loc[self.date, 'resistance'].copy()
            support_up2date = self._stock_whole_data.loc[:self.date[-1], 'resistance'].copy()
            return support_up2date

    def beta(self, date_range="2012:2016", ref_index="000001"):
        """
        Calculate the beta coefficient of the stock, using linear
        regression with monthly return.
        """
        month_return = _month_return(self.stock_data)
        ref_kline = KLine(os.path.join(cfg.index_dir, ref_index+ct.FILE_EXT["csv"]))
        ref_month_return = _month_return(ref_kline.stock_data)

        st_date, ed_date = re.split('\D+', date_range.strip())
        if len(st_date) == 0:
            st_date = None
        if len(ed_date) == 0:
            ed_date = None

        month_return = month_return[st_date:ed_date]
        ref_month_return = ref_month_return[st_date:ed_date]
        # Assume index series is always more integrated.
        if len(ref_month_return) != len(month_return):
            ref_month_return = ref_month_return[month_return.index]
        month_return_arr = np.array(month_return)
        ref_month_return_arr = np.array(ref_month_return)
        # print month_return
        # print ref_month_return
        sel_ref_return_arr = ref_month_return_arr[~np.isnan(month_return_arr) & ~np.isnan(ref_month_return_arr)]
        sel_return_arr = month_return_arr[~np.isnan(month_return_arr) & ~np.isnan(ref_month_return_arr)]

        reg = linear_model.LinearRegression()
        reg.fit(sel_ref_return_arr.reshape(-1, 1), sel_return_arr)

        self.beta_coef = reg.coef_[0]
        self.market_return = np.prod(sel_ref_return_arr) ** (12.0/len(sel_ref_return_arr)) - 1

        # print np.prod(sel_return_arr) ** (12.0/len(sel_ref_return_arr)) - 1   # should be the same as required return?
        return self.beta_coef

    def required_return(self, rf=0.04, date_range="2012:2016",
                        ref_index="000001", show_beta=True,
                        market_return=None):
        """
        calculate required return of a stock based on CAPM model:
        RR = Rf + beta * (Rm - Rf)
        Args:
            rf: <float>: risk-free rate of return.
            date_range:
            ref_index:
            show_beta
            market_return: <float>: expected return of market.
                            default: None(use return of past years as expected return)
        Returns:
            rr: <float>: required rate of return.
        """
        beta_coef = self.beta(date_range=date_range, ref_index=ref_index)
        # print beta_coef, self.market_return
        if market_return is None:
            rr = rf + beta_coef * (self.market_return - rf)
        else:
            rr = rf + beta_coef * (market_return - rf)
        if show_beta:
            print("beta: %0.3f" % beta_coef)
        return rr

    def ma(self, ma_days):
        # since property-decorated functions are illegal to have args.
        key = 'MA'+str(ma_days)
        if key in self.stock_data:
            return self.stock_data[key]
        else:
            self.stock_data[key] = self._stock_whole_data['close'].rolling(
                                                window=ma_days, center=False).mean()
            return self.stock_data[key]

    def atr(self, atr_days):
        """
        Average true range for selected length of trading days.
        Args:
            atr_days:
        Returns:
        """
        key = 'ATR'+str(atr_days)
        if key in self.stock_data:
            return self.stock_data[key]
        else:
            _ = self.tr
            self.stock_data[key] = self._stock_whole_data['TR'].rolling(
                                                window=atr_days, center=False).mean()
            return self.stock_data[key]

    def std_dev(self, std_days):
        key = 'STD' + str(std_days)
        if key in self.stock_data:
            return self.stock_data[key]
        else:
            self.stock_data[key] = self._stock_whole_data['close'].rolling(
                                                window=std_days, center=False).std()
            return self.stock_data[key]

    def date_cut(self, date):
        """
        get a range of dates of stock data.
        Args:
            date:
        """
        st_date, ed_date = re.split('\D+', date.strip())
        if len(st_date) == 0:
            st_date = None
        if len(ed_date) == 0:
            ed_date = None

        self.stock_data = self._stock_whole_data.loc[st_date:ed_date].copy()

    def show(self, *args):
        plot_generator = Pr.GenPlot(self.stock_data)
        plot_generator.series_line(*args, title=self.code)


class Indicator(KLine):
    def __init__(self, code):
        KLine.__init__(self, code)


if __name__ == '__main__':

    kline = KLine("000895")
    print "required return: %0.4f" % kline.required_return(ref_index="000300", market_return=0.08)
    # print kline.date[-5:-1]
    # print kline.stock_data[:5]
    # # print kline.stock_data.ix['20151020']
    #
    # print "*"*10+"ma_generator test"+"*"*10
    # ma60 = kline.ma(60)
    # print kline.ma(70)[-5:]
    # print kline.stock_data[-34:-30]
    #
    # print "*"*10+"date_cut test"+"*"*10
    # print kline.support[~np.isnan(KlineClass.support)]
    # print kline.resistance[~np.isnan(KlineClass.resistance)]
    # kline.date_cut('2010:')

    # print kline.stock_data[:5]
    print kline.tr[-20:]
    print kline.atr(10)
    # print kline.ma(20)[18:22]
    print kline.support[~np.isnan(kline.support)]
    kline.ma(60)
    kline.std_dev(60)
    kline.ma(150)
    kline.std_dev(150)
    kline.ma(250)
    # KlineClass.show('close', 'MA20', 'MA150', 'MA60', 'MA250')
    kline.show('close', 'MA60', 'MA250')
