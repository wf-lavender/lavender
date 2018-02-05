# -*- coding:utf-8 -*-
"""
Analyse and plot fundamental data.
Authors: Wang Fei
History: 2017.6.16
"""

import os
import matplotlib
import tushare as ts
import lavender.config as cfg
import pandas as pd
import numpy as np
import seaborn as sns
import lavender.constant as ct
import lavender.DataCollecting.category as ctg
import matplotlib.font_manager as fm
from matplotlib.pyplot import *
from sklearn import covariance, cluster
from lavender.util.DailyKLineIO import KLine


matplotlib.style.use('ggplot')


# TODO: join pools
def join_pools(pools):
    """
    Merge stock pools, drop duplicates and keep only code and name column.
    Args:
        pools:

    Returns:

    """
    merge_pool = pd.DataFrame([], columns=["code", "name"])
    for pool in pools:
        data_path = os.path.join(cfg.pool_dir, pool)
        pooled_stocks = pd.read_csv(data_path, header=None, names=["code", "name"], delim_whitespace=True,
                                    dtype={"code": "str"})
        merge_pool.append(pooled_stocks)
    merge_pool.drop_duplicates(subset=["code"], inplace=True)
    merge_pool.to_csv()


def show_single_code_statement(code, indicators, season=4, draw_pic=True,
                               save_name=None):
    """

    Args:
        code: <str>: stock code.
        indicators: <dict>: the indicator in the financial statement to show.
                            The key is the name of financial statement database;
                            the value is a list of indicators.
        season: <int>: the season(1-4) of financial statement.
        draw_pic: <bool>: weather to draw pictures.
        save_name: <str>: file name of the picture to save.
    Returns:

    """
    ind_data = pd.DataFrame()
    for table_name in indicators:
        engine = ct.gen_engine(table_name)
        state_data = pd.read_sql_table(code, engine)
        if season is not None:
            state_data = state_data[(state_data.season == season)]
        indicator_chars = [indicator.decode("utf8") for indicator in indicators[table_name]]
        indicators[table_name] = indicator_chars
        state_data.index = state_data.year
        ind_data = pd.concat([ind_data, state_data[indicator_chars].copy()], axis=1)
    if draw_pic:
        print(ind_data)
        font = fm.FontProperties(fname=ct.FONT_PATH)
        ax = ind_data.plot()
        ax.set_title(label="%s (%s)" % (ct.get_code_name(code), code), fontproperties=font)
        legends = reduce(lambda x, y: x+y, [indicators[state] for state in indicators])
        ax.legend(legends, prop=font)
        if save_name is None:
            show()
        else:
            save_dir = os.path.join(cfg.fundamental_pic_dir, code)
            if not os.path.exists(save_dir):
                os.system("%s %s" % (ct.SYS_COMMAND["mkdir"], save_dir))
            save_path = os.path.join(save_dir, save_name)
            savefig(save_path)


def show_single_code_basics(code, indicators, season=4,
                            draw_pic=True, save_name=None):
    """
    show data in the database based on sql syntax.
    Args:
        indicators: <dict>: the fundamental indicator to show.
        code: <str>: stock code.
        season: <int>:
        draw_pic: <bool>:
        save_name: <str>: file name of the picture to save.
    """
    ind_data = pd.DataFrame()
    for table_name in indicators:
        engine = ct.gen_engine(table_name)
        data_table = pd.read_sql_table(table_name, engine)
        sel_data = data_table[(data_table.code == code) & (data_table.season == season)]
        sel_data.index = sel_data.year
        ind_data = pd.concat([ind_data, sel_data[indicators[table_name]].copy()], axis=1)
    if draw_pic:
        print(ind_data)
        font = fm.FontProperties(fname=ct.FONT_PATH)
        ax = ind_data.plot()
        ax.set_title(label="%s (%s)" % (ct.get_code_name(code), code), fontproperties=font)
        if save_name is None:
            show()
        else:
            save_dir = os.path.join(cfg.fundamental_pic_dir, code)
            if not os.path.exists(save_dir):
                os.system("%s %s" % (ct.SYS_COMMAND["mkdir"], save_dir))
            save_path = os.path.join(save_dir, save_name)
            savefig(save_path)


def _plot_codes_heatmap(codes, table_name, indicator, save_name="test.png",
                        season=4, main_title="", **kwargs):
    """
    
    Args:
        codes: <list: str>: list of codes.
        table_name: <str>: table name of database.
        indicator: <str>: the fundamental indicator to plot. 
        save_name: <str>: name of the picture to save.
        season: <int>: season of report.
        **kwargs: 

    """
    engine = ct.gen_engine(table_name)
    table_data = pd.read_sql_table('%s' % table_name, engine)
    idc_data = pd.DataFrame()
    for code in codes:
        code_df = table_data[(table_data.code == code) & (table_data.season == season)]
        year_ind = [pd.Period(year) for year in code_df.year]
        idc_series = code_df[indicator]

        idc_series.index = year_ind
        idc_series.name = ct.get_code_name(code)

        # if raise errors of shape matching, check duplicate years in data.
        idc_data = pd.concat([idc_data, idc_series], axis=1)

    height = int(len(codes)/2)
    figure(figsize=(14, height))
    # ax = fig.add_subplot(111)
    font = fm.FontProperties(fname=ct.FONT_PATH)
    ax = sns.heatmap(idc_data.transpose(), annot=True, fmt=".1f", cmap="seismic", **kwargs)
    ax.set_yticklabels(idc_data.transpose().index[::-1], fontproperties=font)

    xticks(rotation=90)
    yticks(rotation=0)
    title(main_title)
    # idc_data.plot()
    save_path = os.path.join(cfg.fundamental_pic_dir, save_name)
    savefig(save_path)


def _cal_free_cash_flow(code, season=4):
    """
    Calculate series of free cash flow of the selected stock.
    """
    engine = ct.gen_engine("Statement_CashFlow")
    state_data = pd.read_sql_table(code, engine)
    state_data = state_data[(state_data.season == season)]

    cfo = state_data["经营活动产生的现金流量净额".decode("utf8")]
    cfi1 = state_data["购建固定资产、无形资产和其他长期资产所支付的现金".decode("utf8")]
    cfi2 = state_data["取得子公司及其他营业单位支付的现金净额".decode("utf8")]
    cfi3 = state_data["处置固定资产、无形资产和其他长期资产所收回的现金净额".decode("utf8")]
    cfi4 = state_data["处置子公司及其他营业单位收到的现金净额".decode("utf8")]
    cfi1[np.isnan(cfi1)] = 0
    cfi2[np.isnan(cfi2)] = 0
    cfi3[np.isnan(cfi3)] = 0
    cfi4[np.isnan(cfi4)] = 0
    fcf = cfo - cfi1 - cfi2 + cfi3 + cfi4
    fcf.index = state_data.year
    return fcf


def cash_flow_valuation(code, growth_rate=None,
                        required_return=0.1, season=4):
    """
    Args:
        code:
        growth_rate:
        required_return: <float>: required rate of return
        season:
    Returns:
    """
    fcf = _cal_free_cash_flow(code)
    # fcf.plot()
    # show()
    if growth_rate is not None:
        # TODO: simulate growth rate of free cash flow.
        pass
    engine = ct.gen_engine("Statement_BalanceSheet")
    state_data = pd.read_sql_table(code, engine)
    state_data = state_data[(state_data.season == season)]
    shares = state_data["实收资本(或股本)".decode("utf8")]
    price = fcf.iloc[-1] / shares.iloc[-1] * (1 + growth_rate) / (required_return - growth_rate)

    print(price)


def dupont_decomposition(code, season=4, draw_pic=True, save_name=None):
    """
    Show time series for DuPont Analysis.
    """
    engine = ct.gen_engine("Statement_ProfitStatement")
    state_data = pd.read_sql_table(code, engine)
    state_data = state_data[(state_data.season == season)]
    state_data.index = state_data.year
    revenue = state_data["营业收入".decode("utf8")]
    net_income = state_data["归属于母公司所有者的净利润".decode("utf8")]

    engine = ct.gen_engine("Statement_BalanceSheet")
    state_data = pd.read_sql_table(code, engine)
    state_data = state_data[(state_data.season == season)]
    state_data.index = state_data.year
    asset = state_data["资产总计".decode("utf8")]
    equity = state_data["归属于母公司股东权益合计".decode("utf8")]

    net_profit_ratio = net_income/revenue * 100
    asset_turnover = revenue/asset
    leverage = asset/equity

    dupont = pd.concat([net_profit_ratio, asset_turnover, leverage,
                        net_profit_ratio*asset_turnover*leverage], axis=1)
    dupont.columns = ["net profit ratio", "asset turnover", "leverage", "roe"]
    print dupont
    if draw_pic:
        matplotlib.style.use('bmh')

        font = fm.FontProperties(fname=ct.FONT_PATH)
        fig, ax1 = subplots()
        ax1.plot(dupont.index, dupont[["net profit ratio", "roe"]])
        ax1.set_title(label="%s (%s)" % (ct.get_code_name(code), code), fontproperties=font)
        ax1.set_ylabel("Percent")
        ax1.legend(["Net profit ratio (%)", "ROE (%)"], loc="lower left")
        ax1.grid("off")
        ax1.grid("on", axis="x")

        ax2 = ax1.twinx()
        ax2.plot(dupont.index, dupont["asset turnover"], "c--")
        ax2.plot(dupont.index, dupont["leverage"], "y--")
        ax2.set_ylabel("Ratio")
        ax2.legend(["Asset turnover", "Leverage"], loc="upper right")
        ax2.grid("on", axis="y")
        if save_name is None:
            show()
        else:
            save_dir = os.path.join(cfg.fundamental_pic_dir, code)
            if not os.path.exists(save_dir):
                os.system("%s %s" % (ct.SYS_COMMAND["mkdir"], save_dir))
            save_path = os.path.join(save_dir, save_name)
            savefig(save_path)


def cash_ps(code, season=4):
    """
    Args:
        code: 
        season: 
    Returns:
    """
    engine = ct.gen_engine("Statement_BalanceSheet")
    state_data = pd.read_sql_table(code, engine)
    state_data = state_data[(state_data.season == season)]
    state_data.index = state_data.year
    cash = state_data["货币资金".decode("utf8")]
    equity = state_data["交易性金融资产".decode("utf8")]
    notes_receivable = state_data["应收票据".decode("utf8")]
    shares = state_data["实收资本(或股本)".decode("utf8")]
    cash[np.isnan(cash)] = 0
    equity[np.isnan(equity)] = 0
    notes_receivable[np.isnan(notes_receivable)] = 0
    t_cash = (cash + equity + notes_receivable)/shares

    return t_cash


def cash_ps_vs_price(save_name):
    """
    Args:
        save_name: 

    Returns:

    """
    # TODO:The function below didn't work frequently, and stocks suspended have
    # all prices equal 0.
    trade_prices = ts.get_today_all()

    fout = open(os.path.join(cfg.pool_dir, save_name), "w")
    for market in ["SH", "SZ"]:
        stock_list_path = os.path.join(cfg.root_data_dir, "StockList" + market + ct.FILE_EXT['csv'])
        stock_list = pd.read_csv(stock_list_path, header=None, names=["name", "code"],
                                 dtype={"code": "str"}, encoding="GBK")
        codes = stock_list.code
        names = stock_list.name

        for code, name in zip(codes, names):
            price = trade_prices[(trade_prices.code == code) & (trade_prices.trade != 0)].trade
            if price.empty:
                continue
            price = price.iloc[0]
            try:
                cash = cash_ps(code).iloc[-1]
            # TODO: stock of banks don't have "货币资金"
            except KeyError:
                continue

            print "%s %s : price: %s, cash: %s\n" % (code, name, price, cash)
            ratio = cash/price
            if ratio > 0.8:
                print 50*"*" + " %s %s " % (code, name) + 50*"*"
                fout.write("%s " % code)
                fout.write(name.encode("utf8"))
                fout.write(" %s %s %s\n" % (cash, price, ratio))
    fout.close()


def plot_category_heatmap(table_name, indicator, classify_stand, category, **kwargs):
    """
    plot heatmap for the fundamental indicator of selected category.
    Args:
        table_name: <str>: table name of database.
        indicator: <str>: the fundamental indicator to plot. 
        classify_stand: <str>: standards used to classify stocks
        category: <str>: selected category name of the standard
        **kwargs: 
    """
    banks = ctg.get_classified_code(classify_stand, category, **kwargs)
    _plot_codes_heatmap(banks, table_name, indicator, save_name="bank_%s.png" % indicator, **kwargs)


def _if_has_year(code, year):
    """
    check if a stock has K-line data in the selected year.
    Args:
        code: <str>: code of the stock to be checked.
        year: <int>: the selected year.
    Returns:
        <bool>
    """
    kline_file = "%s.csv" % code
    kline_path = os.path.join(cfg.kline_dir, kline_file)
    try:
        kline_cl = KLine(kline_path)
    except IOError:
        return False
    if kline_cl[:].index[0].year <= year:
        return True
    else:
        return False


def _first_year(code):
    """
    return the first year of IPO
    Args:
        code: <str>: code of the stock to be checked.
    Returns:
        <int>: year.
    """
    kline_file = "%s.csv" % code
    kline_path = os.path.join(cfg.kline_dir, kline_file)
    kline_cl = KLine(kline_path)
    return kline_cl.date[0].year


def get_condition_indicator(table_name, indicator_conditions, save_name,
                            num_year=5, nyear_conditions=None, first_year=2012):
    """
    Pick stocks whose indicator(ROE) larger than 20 in the last n years.
    Args:
        table_name: <str>: table which is to be read and filter indicators from.
        save_name: <str>: txt file name to save stocks filtered.
        num_year: <int>: the number of the latest years to check the condition.
        nyear_conditions: <str>: the conditions to be satisfied by the number of the latest
                                years that satisfied the conditions.
        indicator_conditions: <dict>: key: <str>: fundamental indicators.
                                    value: <str>: the conditions to be satisfied by the indicators.
        first_year: <int>: the year that the stocks should have been listed.
    """
    engine = ct.gen_engine(table_name)
    table_data = pd.read_sql_table('%s' % table_name, engine)

    if nyear_conditions is None:
        nyear_conditions = "==%s" % num_year

    years = np.unique(table_data.year)
    last_n_years = years[(-1*num_year-1):-1]     # 2012, 2013, 2014, 2015, 2016

    picked_codes = list()
    codes = np.unique(table_data.code)
    for code in codes:
        table_data_s4 = table_data[(table_data.code == code) & (table_data.season == 4)
                                   & (table_data.year.isin(last_n_years))].copy()

        select_table = table_data_s4.query(" and ".join(["({} {})".format(indict, condit)
                                                         for indict, condit in indicator_conditions.iteritems()]))

        # stock exchange history longer than n year.
        if eval("%s%s" % (len(select_table), nyear_conditions)) and _if_has_year(code, first_year):
            picked_codes.append(code)
    print "Number of stocks picked: %d" % len(picked_codes)

    fout = open(os.path.join(cfg.pool_dir, save_name), "w")
    for code in picked_codes:
        stock_name = np.unique(table_data[table_data.code == code].name)[0]

        fout.write("%s " % code)
        fout.write(stock_name.encode("utf8"))
        fout.write("\n")
        # sentence below don't work, maybe because of unicode to string.
        # fout.write('%s %s\n' % (code, stock_name.encode("utf8")))
    fout.close()


def plot_pooled_codes_heatmap(pool_name, save_name, table_name, indicator, **kwargs):
    """
    
    Args:
        pool_name: <str>: file name of pooled codes.
        save_name: <str>:
        table_name: <str>:
        indicator: <str>:

    Returns:

    """
    data_path = os.path.join(cfg.pool_dir, pool_name)
    pooled_codes = pd.read_csv(data_path, header=None, names=["code", " "], delim_whitespace=True,
                               dtype={"code": "str"}).code

    _plot_codes_heatmap(pooled_codes, table_name, indicator, save_name, **kwargs)


def stock_variation_cluster(pool_name, date_range="2012:2017",
                            fill_nan=0):
    """
    Args:
        pool_name: 
        date_range:
        fill_nan:
    Returns:

    """
    data_path = os.path.join(cfg.pool_dir, pool_name)
    pooled_stocks = pd.read_csv(data_path, header=None, names=["code", "name"], delim_whitespace=True,
                                dtype={"code": "str"})
    pooled_codes = pooled_stocks.code
    pooled_names = pooled_stocks.name

    pool_variations = pd.DataFrame()
    for code in pooled_codes:
        kline = KLine(code)
        kline.date_cut(date_range)
        variation = kline.stock_data.close - kline.stock_data.open
        variation /= variation.std(axis=0)
        pool_variations = pd.concat([pool_variations, variation], axis=1)

    edge_model = covariance.GraphLassoCV()

    # standardize the time series: using correlations rather than covariance
    # is more efficient for structure recovery
    if fill_nan is None:
        pool_variations.dropna(axis=0, how="any", inplace=True)
    else:
        pool_variations[np.isnan(pool_variations)] = fill_nan
    edge_model.fit(pool_variations)
    print edge_model.covariance_.shape

    _, labels = cluster.affinity_propagation(edge_model.covariance_)
    n_labels = labels.max()

    print labels
    for i in range(n_labels + 1):
        print('Cluster %i: %s' % ((i + 1), ', '.join(pooled_names[labels == i])))


if __name__ == "__main__":
    # plot_category_heatmap("profit", "roe", "industry", "银行", standard="sw")

    # show_single_code_basics('300403', indicators={"profit" :["roe", "gross_profit_rate", "net_profit_ratio"]})
    # show_single_code_basics('601857', indicators={"profit": ["business_income", ]})
    # show_single_code_basics('002230', indicators={"cashflow": ["cf_nm", ]})
    # show_single_code_basics("000651", indicators={"report": ["roe"], "profit": ["roe"]})
    # show_single_code_basics("002572", indicators={"growth": ["mbrg", "nprg", "seg"], })
    # show_single_code_basics("002572", indicators={"profit": ["business_income", "net_profits", ], })

    # engine = ct.gen_engine("report_no_subset")
    # state_data = pd.read_sql_table("report", engine)
    # print state_data[state_data.code=="000651"]

    # stock_variation_cluster("roe_gt_15.csv")

    # 净资产收益率（ROE）选股
    # # 上市满5年，且ROE在近5年里均大于20%
    # get_condition_indicator("profit", {"roe": ">20"}, "roe_gt_20.csv")
    # # 上市满5年，且ROE在近4年里均大于15%
    # get_condition_indicator("report", {"roe": ">15"}, "roe_gt_15_in_4yr.csv", num_year=4)
    # # 上市满5年，且ROE在近5年里至少有4年大于15%
    # get_condition_indicator("report", {"roe": ">15"}, "roe_gt_15_has_4yr.csv", num_year=5,
    #                         nyear_conditions=">=4")
    # # 上市满4年，且近4年里营收和净利润增长均大于15%. (结果和上市满5年一样)
    # get_condition_indicator("growth", {"mbrg": ">15", "nprg": ">15"}, "growth_gt_15_in_4yr.csv",
    #                         num_year=4, first_year=2013)
    # get_condition_indicator("growth", {"mbrg": ">10", "nprg": ">10"}, "growth_gt_10_in_4yr.csv",
    #                         num_year=4, first_year=2013)

    # plot_pooled_codes_heatmap("roe_gt_20.csv", "mbrg_roe_gt_20.png", "growth", "mbrg",
    #                           main_title="Main Business Revenue Growth of stocks(ROE > 20)",
    #                           vmax=100, vmin=-100)
    # plot_pooled_codes_heatmap("roe_gt_15.csv", "mbrg_roe_gt_15.png", "growth", "mbrg",
    #                           main_title="Main Business Revenue Growth of stocks(ROE > 15)",
    #                           vmax=100, vmin=-100)
    # plot_pooled_codes_heatmap("roe_gt_20.csv", "roe_gt_20.png", "profit", "roe",
    #                           main_title="Revenue On Equity of stocks(ROE>20)", vmax=50, vmin=-10)
    # plot_pooled_codes_heatmap("roe_gt_15_in_4yr.csv", "roe_gt_15_in_4yr.png", "profit", "roe",
    #                           main_title="Revenue On Equity of stocks(ROE>15 in last 4 years)", vmax=50, vmin=-10)
    # plot_pooled_codes_heatmap("roe_gt_15_has_4yr.csv", "roe_gt_15_has_4yr.png", "profit", "roe",
    #                           main_title="Revenue On Equity of stocks(ROE>15 in 4 years of the last 5yr)",
    #                           vmax=50, vmin=-10)
    # plot_pooled_codes_heatmap("growth_gt_10_in_4yr.csv", "growth_gt_10_in_4yr.png", "growth", "nprg",
    #                           main_title="Growth of net profit(%)", vmax=100, vmin=-100)
    # plot_pooled_codes_heatmap("growth_gt_10_in_4yr.csv", "ROE_of_growth_gt_10_in_4yr.png", "profit", "roe",
    #                           main_title="Revenue On Equity of stocks(Growth of net profit>10%)",
    #                           vmax=50, vmin=-10)

    # 现金流量表分析
    sel_code = "600377"
    show_single_code_statement(sel_code, {"Statement_ProfitStatement": ["五、净利润", ],
                                          "Statement_CashFlow": ["经营活动产生的现金流量净额", ],
                                          "Statement_BalanceSheet": ["存货", ]},
                               save_name="%s_cash_flow1.png" % sel_code)
    show_single_code_statement(sel_code, {"Statement_ProfitStatement": ["营业收入", ],
                                          "Statement_CashFlow": ["销售商品、提供劳务收到的现金", ],
                                          "Statement_BalanceSheet": ["应收账款", "其他应收款"]},
                               save_name="%s_cash_flow2.png" % sel_code)
    show_single_code_statement(sel_code, {"Statement_CashFlow": ["现金的期末余额",
                                                                 "购建固定资产、无形资产和其他长期资产所支付的现金",
                                                                 "分配股利、利润或偿付利息所支付的现金"],
                                          "Statement_BalanceSheet": ["短期借款", "长期借款"]},
                               save_name="%s_cash_flow3.png" % sel_code)

    # 杜邦分析(DuPont Analysis)
    dupont_decomposition(sel_code, save_name="%s_dupont.png" % sel_code)

    # 自由现金流折现定价
    cash_flow_valuation(sel_code, growth_rate=0)

    # cash_ps_vs_price("cash_gt_0.8price.csv")
