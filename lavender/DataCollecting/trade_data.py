"""
    this module use tushare package to get historical data from Sina website
    (http://vip.stock.finance.sina.com.cn/corp/go.php/vMS_MarketHistory/stockid/002001.phtml?year=2015&jidu=1#).
    See details on "http://tushare.org/trading.html"
    Authors: Wang Fei
    History: 2016.04.15
             2017.04.18: Switch to downloading "Hou Fu Quan" data. 
                         Build a class and add data-updating method.
"""

import pandas as pd
import tushare as ts
import lavender.constant as ct
import stock_code as sc
import datetime
import csv
import os
import re
import lavender.config as cfg


def next_day_str(date_str, date_format="%Y-%m-%d"):
    """
    Get the next date in given format.
    Args:
        date_str: <str>: date in the given format.
        date_format: <str>: format string.
    Returns:
        <str>: the next date in the given format.
    """
    dt = datetime.datetime.strptime(date_str, date_format)
    next_date = dt + datetime.timedelta(days=1)
    return next_date.strftime(date_format)


class StockDownloader:
    """
    Class to download stock history data from Sina.
    """
    def __init__(self, date_range='1990-01-01:', index=False,
                 autype='hfq', method="get_k_data"):
        """
        Args:
            autype: 
            method: <str>: the function name used to get stock data in tushare.
                            support: "get_k_data", "get_h_data".
        """
        self.code_dir = cfg.stock_code_dir
        self.autype = autype
        self.method = method
        self.index = index
        if self.index:
            self.save_dir = cfg.index_dir
        else:
            self.save_dir = cfg.kline_dir
        self.st_date, self.ed_date = date_range.strip().split(':')
        if len(self.st_date) == 0:
            self.st_date = None
        if len(self.ed_date) == 0:
            self.ed_date = None
        self.data_name = "%s"+ct.FILE_EXT['csv']

    def _download_stock_data(self, code, overwrite=False, **kwargs):
        """
        Args:
            code: 
            overwrite: <>
            **kwargs:
    
        Returns:
        """
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        save_path = os.path.join(self.save_dir, self.data_name % code)
        if not overwrite and os.path.exists(save_path):
            print "%s already exist!" % save_path
        else:
            df = getattr(ts, self.method)(code, **kwargs)
            if not df.empty:
                # "get_k_data" use a range of numbers as index,
                # while "get_h_data" use date as index.
                try:
                    df = df.set_index("date")
                except KeyError:
                    pass
                df.sort_index().to_csv(save_path)

    def get_market_stock_data(self):
        """
        get "Fu Quan" data from Sina website using tushare.
        """
        if self.index:
            stock_list_path = os.path.join(self.code_dir, "StockListIndex" + ct.FILE_EXT['csv'])
            stock_list = pd.read_csv(stock_list_path, header=None, names=["name", "code"],
                                     dtype={"code": "str"}, encoding="GBK")
        else:
            stock_list = sc.get_stock_codes()
        codes = stock_list.code
        names = stock_list.name

        for code, stock_name in zip(codes, names):
            print "%s get data: %s %s" % (ct.NEW_LINE_CHAR, stock_name, ct.NEW_LINE_CHAR)
            self._download_stock_data(code, start=self.st_date, end=self.ed_date,
                                      autype=self.autype, index=self.index)

    def update_code_list_stock_data(self):
        """
        Update stocks listed in code list files.
        """
        if self.index:
            stock_list_path = os.path.join(self.code_dir, "StockListIndex"+ct.FILE_EXT['csv'])
            stock_list = pd.read_csv(stock_list_path, header=None, names=["name", "code"],
                                     dtype={"code": "str"}, encoding="GBK")
        else:
            stock_list = sc.get_stock_codes()
        codes = stock_list.code
        names = stock_list.name

        for code, stock_name in zip(codes, names):
            print("%s update data: %s %s" % (ct.NEW_LINE_CHAR, stock_name, ct.NEW_LINE_CHAR))
            stock_file = os.path.join(self.save_dir, code+ct.FILE_EXT['csv'])

            if not os.path.exists(stock_file):
                self._download_stock_data(code, start=self.st_date, end=self.ed_date,
                                          autype=self.autype, index=self.index)
            else:
                data_path = os.path.join(self.save_dir, self.data_name % code)
                old_data = pd.read_csv(data_path, index_col=0)
                continue_date = next_day_str(old_data.index[-1])
                print continue_date
                new_data = getattr(ts, self.method)(code, start=continue_date, end=self.ed_date,
                                                    autype=self.autype, index=self.index)

                if not new_data.empty:
                    # "get_k_data" use a range of numbers as index,
                    # while "get_h_data" use date as index.
                    try:
                        new_data = new_data.set_index("date")
                    except KeyError:
                        pass
                    new_data = new_data.sort_index()
                    new_data.index = new_data.index.astype(str)
                    concat_data = pd.concat([old_data, new_data])
                    concat_data.to_csv(data_path)


if __name__ == "__main__":
    downloader = StockDownloader()
    # downloader.get_market_stock_data()

    downloader.update_code_list_stock_data()

    # downloader = StockDownloader(index=True)
    # downloader.get_market_stock_data()
