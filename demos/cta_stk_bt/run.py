import math

import akshare as ak
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
import talib
from matplotlib import pyplot as plt


def init_mysql_setting():
    user = 'root'
    password = 'Admin3.14'
    host = '127.0.0.1'
    port = '3306'
    database = 'stock'

    engine = create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4')
    return engine


def save_bond_list():
    try:
        client = init_mysql_setting()

        bond_zh_hs_cov_spot_df = ak.bond_zh_hs_cov_spot()

        conn = client.connect()
        stat = text("""
            INSERT INTO `bond_list` (`symbol`, `code`, `name`) 
            VALUES (:symbol, :code, :name)
            """)
        for row in bond_zh_hs_cov_spot_df.itertuples():
            data = {
                "symbol": getattr(row, "symbol"),
                "code": getattr(row, "code"),
                "name": getattr(row, "name"),
            },

            conn.execute(stat, data)
            conn.commit()

        conn.close()

    except Exception as e:
        print(f"Error save_bond_list exception! {str(e)}")


def save_bond_day(symbol: str, code: str):
    try:
        client = init_mysql_setting()

        bond_zh_hs_cov_daily_df = ak.bond_zh_hs_cov_daily(symbol=symbol)

        conn = client.connect()
        stat = text("""
            INSERT INTO `bond_day` (`code`, `open`, `high`, `low`, `close`, `vol`, `date`) 
            VALUES (:code, :open, :high, :low, :close, :vol, :date)
            """)
        for row in bond_zh_hs_cov_daily_df.itertuples():
            data = {
                "code": code,
                "open": getattr(row, "open"),
                "high": getattr(row, "high"),
                "low": getattr(row, "low"),
                "close": getattr(row, "close"),
                "vol": getattr(row, "volume"),
                "date": getattr(row, "date"),
            },

            conn.execute(stat, data)
            conn.commit()

        conn.close()

    except Exception as e:
        print(f"Error save_bond_list exception! {str(e)}")


def save_stock_day(symbol: str, code: str):
    try:
        client = init_mysql_setting()

        stock_zh_index_daily_em_df = ak.stock_zh_index_daily_em(symbol=symbol)

        conn = client.connect()
        stat = text("""
            INSERT INTO `stock_day` (`code`, `open`, `high`, `low`, `close`, `vol`, `date`) 
            VALUES (:code, :open, :high, :low, :close, :vol, :date)
            """)
        for row in stock_zh_index_daily_em_df.itertuples():
            data = {
                "code": code,
                "open": getattr(row, "open"),
                "high": getattr(row, "high"),
                "low": getattr(row, "low"),
                "close": getattr(row, "close"),
                "vol": getattr(row, "volume"),
                "date": getattr(row, "date"),
            },

            conn.execute(stat, data)
            conn.commit()

        conn.close()

    except Exception as e:
        print(f"Error save_stock_day exception! {str(e)}")


def query_stock_day(code: str, start_date: str, end_date: str):
    try:
        client = init_mysql_setting()

        conn = client.connect()
        stat = text("""
                SELECT count(1) AS sum
                FROM `stock_day` 
                WHERE `code`=:code 
                    AND `date`>=:start_date  
                    AND `date`<=:end_date
            """)

        # TODO 时间范围处理是否可以更优雅

        data = {
            "code": code,
            "start_date": start_date,
            "end_date": end_date,
        }
        result = conn.execute(stat, data)
        conn.commit()

        stat = text("""
                SELECT `code`, `open`, `high`, `low`, `close`, `vol`, `date` 
                FROM `stock_day` 
                WHERE `code`=:code 
                AND `date`>=:start_date  
                AND `date`<=:end_date
                ORDER BY `id` LIMIT 100 OFFSET :offset
                """)

        df = pd.DataFrame()

        if result.rowcount > 0:
            count = 0
            for item in result:
                count = item[0]
                break

            epochs = math.ceil(count/100)
            for epoch in range(epochs):
                data = {
                    "code": code,
                    "start_date": start_date,
                    "end_date": end_date,
                    "offset": epoch * 100,
                }
                rows = conn.execute(stat, data)
                if rows.rowcount > 0:
                    arr = []
                    for row in rows:
                        arr.append([
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5],
                            row[6],
                        ])

                    d = pd.DataFrame(arr,
                                     columns=[
                                         'code',
                                         'open',
                                         'high',
                                         'low',
                                         'close',
                                         'vol',
                                         'date',
                                     ])
                    df = df.append(d)
        df['date'] = df['date'].astype(
            'datetime64').dt.strftime('%Y%m%d').astype('int64')
        # df['time'] = df['time'].astype('int')
        df['open'] = df['open'].astype('float')
        df['high'] = df['high'].astype('float')
        df['low'] = df['low'].astype('float')
        df['close'] = df['close'].astype('float')
        df['vol'] = df['vol'].astype('int')

        conn.close()
        return df

    except Exception as e:
        print(f"Error save_stock_day exception! {str(e)}")


if __name__ == "__main__":
    # Set the display options to show all rows and columns
    # pd.set_option('display.max_rows', None)
    # pd.set_option('display.max_columns', None)

    # stock_zh_index_spot_df = ak.stock_zh_index_spot()
    # print(stock_zh_index_spot_df)

    # stock_zh_index_daily_em_df = ak.stock_zh_index_daily_em(symbol="sz399300")
    # print(stock_zh_index_daily_em_df)

    # save_stock_day(symbol='sz399300', code='399300')
    df = query_stock_day(code='399300', start_date='2023-01-03',
                         end_date='2023-08-24')
    print(df)
    closed = df['close'].values
    ma5 = talib.SMA(closed, timeperiod=30)
    ma10 = talib.SMA(closed, timeperiod=60)
    ma20 = talib.SMA(closed, timeperiod=250)
    print(closed)
    print(ma5)
    print(ma10)
    print(ma20)

    plt.figure(figsize=(12, 8))
    # 通过plog函数可以很方便的绘制出每一条均线
    plt.plot(closed)
    plt.plot(ma5)
    plt.plot(ma10)
    plt.plot(ma20)
    # 添加网格，可有可无，只是让图像好看点
    plt.grid()
    # 记得加这一句，不然不会显示图像
    plt.show()


# 268  sz399300    沪深300   3758.2270   28.672  0.769   3729.5550   3748.0670
# 173  sh000903    中证100   3584.3926   22.422  0.629   3561.9703   3580.0361
# 174  sh000905    中证500   5741.0606   30.282  0.530   5710.7783   5733.2548
# 175  sh000906    中证800   4088.0033   28.687  0.707   4059.3163   4078.3794
# 271  sz399303   国证2000   7620.2470   59.821  0.791   7560.4260   7593.4740
