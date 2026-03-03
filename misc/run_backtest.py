"""
A股趋势选股策略 - 回测入口

运行回测:
    python run_backtest.py
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from wtpy import WtBtEngine, EngineType
from strategy.trend_selection_strategy import TrendSelectionStrategy


def run_backtest():
    """运行回测"""
    # 获取当前脚本目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 配置路径
    common_dir = os.path.join(script_dir, "../../demos/common")
    config_file = os.path.join(script_dir, "configbt.yaml")
    storage_dir = os.path.join(script_dir, "data")

    # 策略配置
    strategy_config = os.path.join(script_dir, "config/strategy_params.yaml")
    stock_pool = os.path.join(script_dir, "config/stock_pool.json")

    print("=" * 60)
    print("A股趋势选股策略 - 回测")
    print("=" * 60)
    print(f"配置目录: {common_dir}")
    print(f"数据目录: {storage_dir}")
    print(f"策略参数: {strategy_config}")
    print(f"股票池: {stock_pool}")
    print("=" * 60)

    # 创建回测引擎 - 使用SEL引擎
    engine = WtBtEngine(EngineType.ET_SEL)

    # 初始化引擎
    engine.init(
        folder=common_dir + "/",
        cfgfile=config_file,
        commfile="stk_comms.json",
        sessionfile="stk_sessions.json",
        holidayfile="holidays.json"
    )

    # 配置回测时间范围
    # 格式: YYYYMMDDHHMM
    engine.configBacktest(202201010930, 202312311500)

    # 配置数据存储
    engine.configBTStorage(mode="csv", path=storage_dir + "/")

    # 提交配置
    engine.commitBTConfig()

    # 创建策略
    strategy = TrendSelectionStrategy(
        name="TrendSelection",
        config_path=strategy_config
    )

    # 加载股票池
    strategy.load_stock_pool(stock_pool)

    # 设置策略 - 每分钟触发
    engine.set_sel_strategy(
        strategy=strategy,
        time=1,
        period="min"
    )

    print("开始运行回测...")

    # 运行回测
    engine.run_backtest(bAsync=False)

    print("回测完成！")

    # 释放资源
    engine.release_backtest()


if __name__ == "__main__":
    run_backtest()