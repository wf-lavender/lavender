import os

# daily_kline
# arguments for support and resistance
support_window = 20
resistance_window = 20
lag_window = 500

work_dir = r"C:\Users\Administrator\Desktop\lavender\lavender"

# saving directory of stock data
root_data_dir = os.path.join(work_dir, "data")
daily_kline_subdir = "stocks"
table_subdir = 'tables'
index_subdir = "index"
stock_code_dir = os.path.join(root_data_dir, "code")
table_dir = os.path.join(root_data_dir, table_subdir)
kline_dir = os.path.join(root_data_dir, daily_kline_subdir)
index_dir = os.path.join(root_data_dir, index_subdir)

# directories of financial statements
balance_sheet_dir = os.path.join(root_data_dir, "fin_stat", "balance")
profit_statement_dir = os.path.join(root_data_dir, "fin_stat", "income")
cash_flow_dir = os.path.join(root_data_dir, "fin_stat", "cash_flow")

# directory of filtered stocks
pool_dir = os.path.join(work_dir, "result\pool")

# directory of pictures output
root_pic_dir = os.path.join(work_dir, "result\pics")
fundamental_pic_dir = os.path.join(root_pic_dir, "fundamental")
technical_pic_dir = os.path.join(root_pic_dir, "technical")
