"""
数据下载脚本

使用wtpy的datahelper模块下载股票历史数据
支持tushare、akshare、baostock等数据源
"""

import os
import sys
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from wtpy.apps.datahelper import DHFactory


def download_stock_data(
    codes: list,
    start_date: str,
    end_date: str,
    output_dir: str,
    data_source: str = "tushare",
    token: str = None
):
    """
    下载股票历史数据

    @codes         股票代码列表，格式如["SSE.STK.600000", "SZSE.STK.000001"]
    @start_date    开始日期，格式如"20200101"
    @end_date      结束日期，格式如"20231231"
    @output_dir    输出目录
    @data_source   数据源，支持tushare/akshare/baostock
    @token         tushare token（如使用tushare）
    """
    # 创建输出目录
    daily_dir = os.path.join(output_dir, "daily")
    min1_dir = os.path.join(output_dir, "min1")

    os.makedirs(daily_dir, exist_ok=True)
    os.makedirs(min1_dir, exist_ok=True)

    # 创建数据助手
    helper = DHFactory.create_helper(data_source)

    # 认证
    if data_source == "tushare":
        if token is None:
            print("错误: 使用tushare需要提供token")
            print("请在 https://tushare.pro 注册获取token")
            return
        helper.auth(token=token)
    elif data_source == "baostock":
        helper.auth()

    # 转换日期格式
    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")

    # 下载日线数据
    print(f"开始下载日线数据，共{len(codes)}只股票...")
    helper.dmpBarsToFile(
        folder=daily_dir,
        codes=codes,
        start_date=start_dt,
        end_date=end_dt,
        period="day"
    )

    # 下载分钟线数据
    print(f"开始下载分钟线数据，共{len(codes)}只股票...")
    helper.dmpBarsToFile(
        folder=min1_dir,
        codes=codes,
        start_date=start_dt,
        end_date=end_dt,
        period="min1"
    )

    print(f"数据下载完成！")
    print(f"日线数据目录: {daily_dir}")
    print(f"分钟线数据目录: {min1_dir}")


def download_from_stock_pool(
    pool_file: str,
    start_date: str,
    end_date: str,
    output_dir: str,
    data_source: str = "tushare",
    token: str = None
):
    """
    从股票池配置文件下载数据

    @pool_file     股票池配置文件路径
    @start_date    开始日期
    @end_date      结束日期
    @output_dir    输出目录
    @data_source   数据源
    @token         tushare token
    """
    with open(pool_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    codes = [stock['code'] for stock in data.get('stocks', [])]

    download_stock_data(
        codes=codes,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        data_source=data_source,
        token=token
    )


if __name__ == "__main__":
    # 配置参数
    STOCK_POOL_FILE = "../config/stock_pool.json"
    START_DATE = "20220101"
    END_DATE = "20231231"
    OUTPUT_DIR = "../data"
    DATA_SOURCE = "tushare"  # 可选: tushare, baostock, akshare

    # tushare token（需要替换为自己的token）
    TUSHARE_TOKEN = "YOUR_TUSHARE_TOKEN"

    # 获取当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 转换为绝对路径
    stock_pool_path = os.path.join(script_dir, STOCK_POOL_FILE)
    output_path = os.path.join(script_dir, OUTPUT_DIR)

    print("=" * 50)
    print("A股趋势选股策略 - 数据下载工具")
    print("=" * 50)
    print(f"股票池文件: {stock_pool_path}")
    print(f"开始日期: {START_DATE}")
    print(f"结束日期: {END_DATE}")
    print(f"输出目录: {output_path}")
    print(f"数据源: {DATA_SOURCE}")
    print("=" * 50)

    # 执行下载
    download_from_stock_pool(
        pool_file=stock_pool_path,
        start_date=START_DATE,
        end_date=END_DATE,
        output_dir=output_path,
        data_source=DATA_SOURCE,
        token=TUSHARE_TOKEN if DATA_SOURCE == "tushare" else None
    )