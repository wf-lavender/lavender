# coding = utf-8
"""
picking ShangHai and ShenZhen stock code from
the website listed in config.py
"""
import lavender.config as cfg
import time
import os
import lxml.html
import requests
import lavender.constant as ct
import pandas as pd
from lxml import etree
# from pandas.compat import StringIO
from io import StringIO


def _download_stock_codes():
    """
    get stock lists directly
    获取股票名和股票代码对应列表
    """
    save_path = os.path.join(cfg.stock_code_dir, 'StockList.csv')

    # request = urllib2.Request(ct.STOCK_LIST_SITE["ts"])
    # text = urllib2.urlopen(request, timeout=10).read()
    response = requests.get(ct.STOCK_LIST_SITE["ts"])
    response.encoding = "GBK"
    text = response.text

    code_list = pd.read_csv(StringIO(text), dtype={'code': 'object'})
    code_list.to_csv(save_path, header=False, index=False, columns=["name", "code"])


def get_stock_codes():
    """
    Download stock list from tushare server("file.tushare.org/tsdata/all.csv").
    """
    data_path = os.path.join(cfg.stock_code_dir, 'StockList.csv')
    # mtime = os.path.getmtime(data_path)
    # pass_time = time.time() - mtime
    # if stock list files ware modified in last 12h, then read the file directly.
    # if pass_time > 12 * ct.SECONDS_IN_HOUR:
    _download_stock_codes()
    return pd.read_csv(data_path, header=None, names=["name", "code"],
                       dtype={"code": "str"},)   # encoding="GBK")


def get_market_stock_codes(market):
    """
    Deprecated!
    get code lists of stocks from "http://quote.eastmoney.com/stocklist.html".
    bugs: cannot get the whole ShenZhen codes! (1259 stocks got)
    Args:
        market: <str>: 'SH' or 'SZ'
    """
    import urllib2

    html = urllib2.urlopen(ct.STOCK_LIST_SITE["em"])
    save_path = os.path.join(cfg.stock_code_dir, 'StockList%s.csv' % market)
    content = html.read()
    # contents(lxml > 4.1.1) don't need decode! or else xpath would get nothing.
    # content = unicode(content, "gb18030").encode("utf8")
    # tree = etree.HTML(content)
    tree = lxml.html.parse(StringIO(content))
    # print content.decode("gbk")
    if market == "SH":
        market_xpath = '/html/body/div[@class="qox"]//ul[1]//li//a/text()'
    elif market == "SZ":
        # !! cannot get the whole ShenZhen codes! (1259 stocks got)
        market_xpath = '/html/body/div[@class="qox"]//ul[2]//li/a/text()'
    else:
        print("Wrong market keyword! (only 'SH' and 'SZ' supported)")
        return
    market_codes = tree.xpath(market_xpath)
    print(len(market_codes))
    codes_series = pd.Series(market_codes)
    # print codes_series
    # extract names and codes in parentheses.
    codes_series = codes_series.apply(lambda x: pd.Series([x[0:x.find("(")], x[x.find("(")+1:x.find(")")]]))
    codes_series.to_csv(save_path, header=False, index=False, encoding="gb18030")


if __name__ == "__main__":
    # get_market_stock_codes("SH")
    # get_market_stock_codes("SZ")
    print(get_stock_codes())
