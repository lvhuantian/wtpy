import os

from constants import *
from utils import get_stk_code_name_list

import baostock as bs
import pandas as pd
import akshare as ak


# def get_stk_code_name_list(market: str) -> list:
#     """
#     获取指定证券交易所股票代码与名称列表
#     :return: 代码名称对组成的列表：[{'code': 'code1': 'name': 'name1'}, ...]
#     """
#     # 获取深圳股票代码表
#     if market == MARKET.SZ:
#         # ind_list = ["A股列表", "B股列表"]
#         ind_list = ["A股列表"]
#         df = None
#         for ind in ind_list:
#             tmp_df = ak.stock_info_sz_name_code(ind)
#             tmp_df.rename(columns={'A股代码': 'code', 'A股简称': 'name'}, inplace=True)
#             df = pd.concat([df, tmp_df]) if df is not None else tmp_df
#         print("获取深圳证券交易所股票数量: {}", len(df) if df is not None else 0)
#         return df[['code', 'name']].to_dict(orient='records') if df is not None else []

#     # 获取上证股票代码表
#     if market == MARKET.SH:
#         # ind_list = ["主板A股", "主板B股", "科创板"]
#         ind_list = ["主板A股"]
#         df = None
#         for ind in ind_list:
#             tmp_df = ak.stock_info_sh_name_code(ind)
#             tmp_df.rename(columns={'证券代码': 'code', '证券简称': 'name'}, inplace=True)
#             df = pd.concat([df, tmp_df]) if df is not None else tmp_df
#         print("获取上海证券交易所股票数量: {}", len(df) if df is not None else 0)
#         return df[['code', 'name']].to_dict(orient='records') if df is not None else []

#     # 获取北京股票代码表
#     if market == MARKET.BJ:
#         df = ak.stock_info_bj_name_code()
#         df.rename(columns={'证券代码': 'code', '证券简称': 'name'}, inplace=True)
#         print("获取北京证券交易所股票数量: {}", len(df) if df is not None else 0)
#         return df[['code', 'name']].to_dict(orient='records') if df is not None else []



def download_kline(code: str, start_date: str, end_date: str,
                   freq: str, market: str, result_path: str):
    # #### 登陆系统 ####
    # lg = bs.login()
    # # 显示登陆返回信息
    # print('login respond error_code:' + lg.error_code)
    # print('login respond  error_msg:' + lg.error_msg)

    #### 获取沪深A股历史K线数据 ####
    # 详细指标参数，参见“历史行情指标参数”章节；“分钟线”参数与“日线”参数不同。“分钟线”不包含指数。
    # 分钟线指标：date,time,code,open,high,low,close,volume,amount,adjustflag
    # 周月线指标：date,code,open,high,low,close,volume,amount,adjustflag,turn,pctChg

    code_label = f"{market}.{code}".lower()
    rs = bs.query_history_k_data_plus(code_label,
                                      "date,time,code,open,high,low,close,volume,amount,adjustflag",
                                      start_date=start_date, end_date=end_date,
                                      frequency=freq, adjustflag="1")

    print('query_history_k_data_plus respond error_code:' + rs.error_code)
    print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())
    df = pd.DataFrame(data_list, columns=rs.fields)

    df.to_parquet(os.path.join(result_path, f'{code}.{market}.parquet'))

    # #### 登出系统 ####
    # bs.logout()


if __name__ == '__main__':
    # market = MARKET.SH
    market = MARKET.SZ
    # code = "002869"
    start_date = "2024-01-01"
    end_date = "2024-09-13"
    freq = "5"
    result_path = "/Users/equation42/Desktop/CZSC2/baostock"

    df = get_stk_code_name_list(market=market)
    print(type(df))

    #### 登陆系统 ####
    lg = bs.login()
    # 显示登陆返回信息
    print('login respond error_code:' + lg.error_code)
    print('login respond  error_msg:' + lg.error_msg)


    stocks = get_stk_code_name_list(MARKET.SZ)
    for stock in stocks:
        print(f"download stock: {stock}")
        code = stock['code']
        download_kline(code=code, start_date=start_date, end_date=end_date,
                       freq=freq, market=market, result_path=result_path)

    # download_kline(code=code, start_date=start_date, end_date=end_date,
    #                freq=freq, market=market, result_path=result_path)

    #### 登出系统 ####
    bs.logout()
