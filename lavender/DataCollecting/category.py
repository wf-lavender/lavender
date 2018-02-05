# -*- coding:utf-8 -*-

"""
    get codes of stocks with selected categories.
    (see http://tushare.org/classifying.html#id3)
    Authors: Wang Fei
    History: 2016.08.09
"""

import os
import lavender.config as cfg
import tushare as ts
import lavender.constant as ct


def get_classified_code(classify_stand, category=None, save_name=None, **kwargs):
    """
    get classified stock codes using tushare functions. see details
    on http://tushare.org/classifying.html#id2.
    Args:
        classify_stand: <str>: standards used to classify stocks
        category: <str>: selected category name of the standard
        save_name: <str>: file name of saved classified codes. Data would not be saved if save_name is None.
    Returns:
        pandas series(with category assigned) or DataFrame(category is None).
    """
    if classify_stand in ct.CLASSIFY_STANDARD:
        try:
            ts_func_name = 'get_'+classify_stand+'_classified'
            ts_func = getattr(ts, ts_func_name)
        except AttributeError:
            ts_func_name = 'get_'+classify_stand
            ts_func = getattr(ts, ts_func_name)
        category_data = ts_func(**kwargs)
        # bug in tushare: get_industry_classified(standard="sw") may get
        # duplicate stocks(codes).
        category_data.drop_duplicates(inplace=True)
        if category is None:
            if save_name is not None:
                save_path = os.path.join(cfg.pool_dir, save_name)
                category_data.to_csv(save_path, sep=" ", index=False, header=False, encoding="utf8")
            return category_data.code
        else:
            if category.decode("utf8") in category_data.c_name.unique():
                if save_name is not None:
                    save_path = os.path.join(cfg.pool_dir, save_name)
                    category_data[category_data.c_name == category.decode("utf8")].to_csv(
                        save_path, sep=" ", index=False, header=False, encoding="utf8")
                return category_data.code[category_data.c_name == category.decode("utf8")]
            else:
                print "%s not in %s standards: " % (category, classify_stand)
                for c_name in category_data.c_name.unique():
                    print c_name
    else:
        print "Supported standards: %s." % [st for st in ct.CLASSIFY_STANDARD]


if __name__ == "__main__":
    # print get_classified_code("industry", category="家电行业", save_name="家电行业.csv".decode("utf8"))
    print get_classified_code("industry", category="煤炭行业", save_name="煤炭行业.csv".decode("utf8"))

    # print get_classified_code("zz500s", save_name="zz500.csv")
