# -*- coding:utf-8 -*-

"""
    constant values
"""
import platform
import sys
import os
import sqlite3
import config as cfg
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

STOCK_LIST_SITE = {"em": "http://quote.eastmoney.com/stocklist.html",
                   "ts": "http://file.tushare.org/tsdata/all.csv",
                   }

FIN_STATE_SITE = r"http://money.finance.sina.com.cn/corp/go.php/vFD_%s/stockid/%s/ctrl/%s/displaytype/4.phtml"

# TODO: to be modified on other platforms(other than windows).
FONT_PATH = r'C:\Windows\Fonts\simsun.ttc'

# type of financial statement to fill in FIN_STATE_SITE
FIN_STATE_NAME = ["BalanceSheet", "ProfitStatement", "CashFlow"]

# TODO: use os.linesep
NEW_LINE_CHARS = {'Windows': "\r\n", 'Linux': "\n", 'Darwin': "\r"}
NEW_LINE_CHAR = NEW_LINE_CHARS[platform.system()]

TABLES = ['report', 'profit', 'operation', 'growth', 'debtpaying', 'cashflow']

FILE_EXT = {'csv': '.csv', 'txt': '.txt'}

CLASSIFY_STANDARD = ['industry', 'concept', 'area', 'sme', 'gem', 'st', 'hs300s',
                     'sz50s', 'zz500s', 'terminated', 'suspended']

DATA_MISSING_MESSAGE = "%s data not in %s !"

ARRAY_LIKE_TYPE = ['list', 'numpy.ndarray', ]

TRADE_METHOD_NAME = "trade_%s"
STRATEGY_NAME = "%s_strategy"

REF_RETURN = 0.04       # reference of yearly return.
TRADE_DAYS = 245        # average trading days in a year.
SECONDS_IN_HOUR = 60 * 60


def write_console():
    sys.stdout.write("#")
    sys.stdout.flush()


def write_head():
    sys.stdout.write("\r[Getting data:]")
    sys.stdout.flush()


def get_years(year_range):
    """
    get list of years from a string of year range.
    Args:
        year_range: <str>: "YYYY:YYYY" 
    Returns:
        years: <list: int>: years in the range.
    """
    st_year, ed_year = year_range.strip().split(':')
    if len(ed_year) == 0:
        ed_year = datetime.now().year
    if len(st_year) == 0:
        st_year = "1990"
    years = range(int(st_year), int(ed_year) + 1)
    return years


def gen_engine(table_name):
    """
    Args:
        table_name: <str>: the table of databases to create engine.
    Returns:
        table_engine: <Engine>
    """
    table_dir = cfg.table_dir
    table_path = os.path.join(table_dir, "%s.db" % table_name)
    table_engine = create_engine(r'sqlite:///%s' % table_path)
    return table_engine


def gen_connect(table_name):
    """
    Args:
        table_name: <str>: the table of databases to connect.
    Returns:
        conn: <sqlite3.Connection>
    """
    table_dir = cfg.table_dir
    table_path = os.path.join(table_dir, "%s.db" % table_name)
    conn = sqlite3.connect(table_path)
    return conn


def get_code_name(code):
    """
    get stock name using its code.
    Args:
        code:

    Returns:

    """
    import DataCollecting.stock_code as sc
    codes_data = sc.get_stock_codes()
    try:
        name = codes_data[codes_data.code == code].name.iloc[0]
        return name
    except IndexError:
        return code


if __name__ == "__main__":
    print(get_code_name("600519"))
