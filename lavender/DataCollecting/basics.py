"""
    Get fundamental data of stocks using tushare from Sina website.
    (e.g. http://vip.stock.finance.sina.com.cn/q/go.php/vFinanceAnalyze/kind/profit/index.phtml)
    Authors: Wang Fei
    History: 2017.06.08, initialization.
             2017.08.29, add functions that get financial statements from Sina website.
        (e.g. http://money.finance.sina.com.cn/corp/go.php/vFD_CashFlow/stockid/002230/ctrl/2009/displaytype/4.phtml)
                         b.t.w. Sina's financial statement data is not completed as 163's
                         (e.g. http://quotes.money.163.com/f10/lrb_000895.html?type=2016,
                         "zycwzb" for balance sheet, "xjllb" for cash flow), especially for
                         profit statements.
"""


import os
import sqlite3
import lxml.html
import time
import socket
import threading
import requests
# import urllib2    urllib2 deprecated in python3
import lavender.config as cfg
import tushare as ts
import lavender.constant as ct
import numpy as np
import pandas as pd
import stock_code as sc
from lxml import etree
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy import create_engine
# from urllib2 import urlopen, Request     python2
# from pandas.compat import StringIO        python2
from io import StringIO


def _get_fin_statement(code, fin_state_type, years, retry_count=3, pause=0.001):
    """
    Get selected financial statement of selected stock code from 
    the Sina website.


    Args:
        code: <str>: 股票代码
        fin_state_type: <str>: 报表类型: 资产负债表："BalanceSheet"
                                         利润表："ProfitStatement"
                                         现金流量表："CashFlow"
        years: <list: int>:
        retry_count: <int>:
        pause: 
    Returns:
        state_data: <pd.DataFrame>
    """
    ct.write_head()
    for _ in range(retry_count):
        state_data = pd.DataFrame()
        try:
            for year in years:
                ct.write_console()
                response = requests.get(ct.FIN_STATE_SITE % (fin_state_type, code, str(year)))
                response.encoding = "GBK"
                markup = response.text
                markup = markup.replace('--', "")     # fill '--' with NaN
                # markup = markup.replace('--', "0")    # fill '--' with 0
                soup = BeautifulSoup(markup, "html5lib", )
                # Don't use <tbody> tag, because soup.find_all('tbody') would catch <table> tags as well!
                table_node = soup.find_all('table', attrs={'id': 'BalanceSheetNewTable0'})[0]
                # print(ct.FIN_STATE_SITE % (fin_state_type, code, year))
                tbody_node = str(table_node.tbody).replace("tbody", "table")
                # print(tbody_node)
                df = pd.read_html(tbody_node, header=0, index_col=0)[0]

                # debug: data of 603801/603938 have duplicated columns in 2014-2016
                # http://money.finance.sina.com.cn/corp/go.php/vFD_BalanceSheet/stockid/603801/ctrl/2016/displaytype/4.phtml
                # update on 2019.11.05, the bad data have been fixed.
                # df.columns = map(lambda x: x[:10], df.columns)

                df.dropna(axis=1, how="all", inplace=True)
                # All columns of the first row equal nan, drop it.
                df = df[pd.notna(df.index)]

                # Is there any duplicates?
                # df = df.T.drop_duplicates().T
                state_data = state_data.append(df.transpose().iloc[::-1])
                time.sleep(pause)

            dates = pd.to_datetime(state_data.index)
            # print(dates.month / 3)
            # state_data["season"] = dates.month / 4 + 1
            state_data["season"] = dates.month / 3
            state_data["year"] = dates.year
            return state_data
        except Exception as e:
            print(e)
            print("Try Again...")


def get_fin_states_csv(statement, retry_count=3):
    """

    Args:
        statement:
        retry_count:
    Returns:

    """
    state_names = {"BalanceSheet": "balance_sheet", "ProfitStatement": "profit_statement",
                   "CashFlow": "cash_flow"}
    func = getattr(ts, "get_%s" % state_names[statement])
    stock_list = sc.get_stock_codes()
    codes = stock_list.code
    names = stock_list.name

    for code, name in zip(codes, names):
        print("\r%s" % name)
        for _ in range(retry_count):
            try:
                state = func(code)
                save_name = "%s.csv" % code
                save_dir = getattr(cfg, "%s_dir" % state_names[statement])
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                save_path = os.path.join(save_dir, save_name)
                state.to_csv(save_path)
            except socket.error:  # or urllib2.HTTPError:
                print("Try Again...")
                time.sleep(0.1)


class BasicsDownloader:
    """
    class for downloading fundamental data of stocks.
    """
    def __init__(self, year_range='1990:', save_format="csv"):
        """
        initialization.
        Args:
            year_range: <str>: The years of data to be downloaded. ("YYYY:YYYY")
        """
        self.years = ct.get_years(year_range)
        self.db_dir = os.path.join(cfg.root_data_dir, cfg.table_subdir)
        self.save_format = save_format
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir)

    def get_fin_state(self, state_type):
        """
        创建财务报表数据库文件，文件已存在强制下载则可能导致重复或遗漏。
        Returns:
        """
        if state_type not in ct.FIN_STATE_NAME:
            raise AttributeError
    
        db_path = os.path.join(self.db_dir, "Statement_%s.db" % state_type)
        engine = create_engine(r"sqlite:///%s" % db_path)
    
        if os.path.exists(db_path):
            cmd = raw_input("Data Base already exists!, still generate data base? (Y/N)")
            if cmd == "Y":
                pass
            else:
                return
    
        stock_list = sc.get_stock_codes()
        codes = stock_list.code
        names = stock_list.name

        for code, name in zip(codes, names):
            print("\r%s" % name)
            state_data = _get_fin_statement(code, state_type, self.years)
            if len(state_data) != 0:
                state_data.to_sql(code, engine, if_exists='append')

    def update_fin_state(self, state_type):
        """
        更新财务报表数据库文件
        Args:
            state_type:
        Returns:
        """
        db_path = os.path.join(self.db_dir, "Statement_%s.db" % state_type)
        conn = sqlite3.connect(db_path)
        latest_year = datetime.now().year

        stock_list = sc.get_stock_codes()
        codes = stock_list.code
        names = stock_list.name

        for code, name in zip(codes, names):
            print("\r%s" % name)
            try:
                cursor = conn.execute("SELECT DISTINCT year FROM '%s'" % code)
                last_year = cursor.fetchall()[-1][0]
                years = range(int(last_year), int(latest_year) + 1)
                conn.execute("DELETE FROM '%s' WHERE year >= %s" % (code, last_year))
                conn.commit()
            except sqlite3.OperationalError:
                print("Table not exits, initialization...")
                years = range(1990, int(latest_year) + 1)

            engine = create_engine(r"sqlite:///%s" % db_path)
            state_data = _get_fin_statement(code, state_type, years)
            if len(state_data) != 0:
                state_data.to_sql(code, engine, if_exists='append')
        conn.close()

    def get_table(self, table):
        """
        Get financial tables from Sina using tushare package and save data in sqlite database.
        Args:
            table: <str>: Financial table, support 'report', 'profit', 'operation', 
                          'growth', 'debtpaying', 'cashflow'
        """
        if table not in ct.TABLES:
            raise AttributeError

        db_path = os.path.join(self.db_dir, "%s.db" % table)
        engine = create_engine(r"sqlite:///%s" % db_path)

        if os.path.exists(db_path):
            cmd = raw_input("Data Base already exists!, still generate data base? (Y/N)")
            if cmd == "Y":
                pass
            else:
                return

        for year in self.years:
            for season in range(4, 5):
                print("%sget data in %s S%s..." % (ct.NEW_LINE_CHAR, year, season))
                try:
                    table_data = getattr(ts, "get_%s_data" % table)(year, season)
                except IOError:
                    print("No data in %s S%s" % (year, season))
                    continue
                table_data['year'] = year
                table_data['season'] = season

                # data in "debtpaying" table contain "--" characters.
                # Numeric columns in DataFrame couldn't compare with a string.
                table_data[table_data[table_data.columns[table_data.dtypes == "object"]] == "--"] = np.nan

                if table == "report":
                    # Since distributions in report table contain Chinese characters and Nan.
                    # Pandas DataFrame use "unicode" type when Chinese characters appear,
                    # use "float" type when there are no Chinese characters. While sqlite3 save
                    # all the distributions as float, this may raise error when loading data
                    # from sqlite3 database. So force all distribution data to "unicode" here.
                    table_data.distrib = table_data.distrib.astype("unicode")
                # print table_data[table_data.code=="000651"]
                # tushare has a bug: get duplicate rows of None for some
                # stock, like 601229.
                table_data.drop_duplicates(inplace=True)  # subset=["code", "year", "season"], inplace=True)
                # print table_data[table_data.code=="000651"]
                table_data.to_sql(table, engine, if_exists='append')

    def update_table(self, table):
        """
        Update tables from the last season till the most recent year.
        Args:
            table: <str>: Financial table, support 'report', 'profit', 'operation', 
                          'growth', 'debtpaying', 'cashflow'
        """
        db_path = os.path.join(self.db_dir, "%s.db" % table)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT DISTINCT year FROM %s" % table)

        last_year = cursor.fetchall()[-1][0]
        latest_year = datetime.now().year
        years = range(int(last_year), int(latest_year) + 1)
        conn.execute("DELETE FROM %s WHERE year >= %s" % (table, last_year))
        conn.commit()
        conn.close()

        engine = create_engine(r"sqlite:///%s" % db_path)
        for year in years:
            for season in range(1, 5):
                print("%sUpdating data in %s S%s..." % (ct.NEW_LINE_CHAR, year, season))
                try:
                    table_data = getattr(ts, "get_%s_data" % table)(year, season)
                except IOError:
                    print("No data in %s S%s" % (year, season))
                    continue
                table_data['year'] = year
                table_data['season'] = season

                # data in "debtpaying" table contain "--" characters.
                # Numeric columns in DataFrame couldn't compare with a string.
                table_data[table_data[table_data.columns[table_data.dtypes == "object"]] == "--"] = np.nan

                if table == "report":
                    # Since distributions in report table contain Chinese characters and
                    # Nan. Pandas DataFrame uses "unicode" type when Chinese characters appear,
                    # uses "float" type when there are no Chinese characters. While sqlite3 save
                    # all the distributions as "float", this may raise error when loading data
                    # from sqlite3 database. So force all distribution data to "unicode" here.
                    table_data.distrib = table_data.distrib.astype("unicode")

                # tushare has a bug: get duplicate rows of None for some
                # stock, like 601229.
                table_data.drop_duplicates(subset=["code", "year", "season"], inplace=True)
                table_data.to_sql(table, engine, if_exists='append')


if __name__ == "__main__":
    pd.set_option("max_columns", 10)

    downloader = BasicsDownloader(year_range="2016:")
    # for table in ['report', 'profit', 'operation', 'growth', 'debtpaying', 'cashflow']:
    #     downloader.get_table(table)
    # downloader.get_table("report")
    # downloader.update_table("report")

    # for state_type in ct.FIN_STATE_NAME:
    #     downloader.get_fin_state(state_type)
    #     downloader.update_fin_state(state_type)
    print(_get_fin_statement("603938", "BalanceSheet", range(2017, 2019), retry_count=1))

    # get_fin_states_csv("ProfitStatement")
    # downloader.update_fin_state("BalanceSheet")
