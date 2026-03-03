"""
A股趋势选股策略

策略逻辑：
1. 选股阶段：每日收盘后，根据日K线选出趋势上涨的股票
   - 均线多头排列（MA5 > MA10 > MA20）
   - 价格突破N日高点
2. 交易阶段：下一交易日根据1分钟K线判断进场时机
   - 价格维持在均线上方
   - 均线上行
3. 止损条件：
   - 持续N天价格低于买入价
   - 尾盘出现长上影线或大阴线
"""

import json
import yaml
import os
import numpy as np
from typing import List, Dict, Optional

from wtpy import BaseSelStrategy, SelContext

# 导入自定义模块
from .trend_indicator import TrendIndicator, check_upper_shadow, check_big_yin_line
from .position_manager import PositionManager


class TrendSelectionStrategy(BaseSelStrategy):
    """A股趋势选股策略"""

    def __init__(self, name: str, config_path: str = None):
        """
        初始化策略

        @name         策略名称
        @config_path  配置文件路径
        """
        BaseSelStrategy.__init__(self, name)

        # 默认配置
        self.config = {
            'trend': {
                'ma_periods': [5, 10, 20, 60],
                'breakout_days': 20
            },
            'trading': {
                'max_positions': 5,
                'entry_ma_period': 5,
                'entry_check_time': 1000,
                'stop_entry_time': 1430
            },
            'stop_loss': {
                'price_below_days': 3,
                'shadow_trigger_time': 1430,
                'shadow_ratio': 2.0,
                'big_yin_ratio': 3.0
            },
            'capital': {
                'total_capital': 1000000,
                'position_ratio': 0.2
            }
        }

        # 加载配置
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)

        # 股票池
        self.stock_pool: List[str] = []

        # 趋势指标计算器
        self.indicator = TrendIndicator(
            ma_periods=self.config['trend']['ma_periods'],
            breakout_days=self.config['trend']['breakout_days']
        )

        # 仓位管理器
        self.position_mgr = PositionManager(
            max_positions=self.config['trading']['max_positions'],
            position_ratio=self.config['capital']['position_ratio'],
            total_capital=self.config['capital']['total_capital']
        )

        # 日内状态
        self.__daily_selected__: bool = False  # 当日是否已选股
        self.__current_date__: int = 0          # 当前日期

        # 数据缓存键
        self.KEY_CANDIDATES = "candidates"
        self.KEY_POSITIONS = "positions"

    def _load_config(self, config_path: str):
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                cfg = yaml.safe_load(f)
            else:
                cfg = json.load(f)

        # 合并配置
        if 'trend' in cfg:
            self.config['trend'].update(cfg['trend'])
        if 'trading' in cfg:
            self.config['trading'].update(cfg['trading'])
        if 'stop_loss' in cfg:
            self.config['stop_loss'].update(cfg['stop_loss'])
        if 'capital' in cfg:
            self.config['capital'].update(cfg['capital'])

    def load_stock_pool(self, pool_path: str):
        """
        加载股票池

        @pool_path   股票池配置文件路径
        """
        with open(pool_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stock_pool = [stock['code'] for stock in data.get('stocks', [])]

    def on_init(self, context: SelContext):
        """
        策略初始化
        """
        context.stra_log_text("TrendSelection策略初始化...")

        # 尝试加载持久化状态
        saved_candidates = context.user_load_data(self.KEY_CANDIDATES, None, str)
        if saved_candidates:
            try:
                candidates = json.loads(saved_candidates)
                self.position_mgr.set_candidates(candidates)
                context.stra_log_text(f"恢复候选股票: {candidates}")
            except:
                pass

        # 订阅股票池行情
        for code in self.stock_pool:
            # 订阅日线
            context.stra_get_bars(code, "d", 100)
            # 订阅分钟线
            context.stra_get_bars(code + "Q", "m1", 50)
            # 订阅tick
            context.stra_sub_ticks(code)

        context.stra_log_text(f"已订阅{len(self.stock_pool)}只股票的行情")

    def on_session_begin(self, context: SelContext, curTDate: int):
        """
        交易日开始事件

        @curTDate   交易日，格式为20210220
        """
        context.stra_log_text(f"交易日开始: {curTDate}")

        # 重置日内状态
        self.__daily_selected__ = False
        self.__current_date__ = curTDate

    def on_session_end(self, context: SelContext, curTDate: int):
        """
        交易日结束事件

        @curTDate   交易日，格式为20210220
        """
        context.stra_log_text(f"交易日结束: {curTDate}")

        # 清空候选股票
        self.position_mgr.clear_candidates()

    def on_calculate(self, context: SelContext):
        """
        K线闭合时调用
        主要用于日线收盘后的选股逻辑
        """
        curTime = context.stra_get_time()

        # 日线选股逻辑（收盘后执行）
        # 检查是否在交易时间内
        if curTime >= 1500:  # 15:00收盘后
            if not self.__daily_selected__:
                self._do_daily_selection(context)
                self.__daily_selected__ = True

    def on_bar(self, context: SelContext, stdCode: str, period: str, newBar: dict):
        """
        K线闭合时回调

        @context    策略上下文
        @stdCode    合约代码
        @period     K线周期
        @newBar     最新闭合的K线
        """
        curTime = context.stra_get_time()

        # 只处理分钟线
        if period != "m1":
            return

        # 提取股票代码（去掉Q后缀）
        code = stdCode.replace("Q", "")

        # 检查是否在候选列表或已持仓
        candidates = self.position_mgr.get_candidates()
        has_position = self.position_mgr.has_position(code)

        if code not in candidates and not has_position:
            return

        # 检查交易时间
        entry_check_time = self.config['trading']['entry_check_time']
        stop_entry_time = self.config['trading']['stop_entry_time']

        if curTime < entry_check_time or curTime > stop_entry_time:
            return

        # 持仓检查止损
        if has_position:
            self._check_stop_loss(context, code, curTime)
        else:
            # 候选股票检查进场信号
            if self.position_mgr.can_open_position():
                self._check_entry_signal(context, code, curTime)

    def on_tick(self, context: SelContext, stdCode: str, newTick: dict):
        """
        Tick数据回调
        """
        # 可以在这里实现更精细的进场时机判断
        pass

    def _do_daily_selection(self, context: SelContext):
        """
        执行日选股逻辑
        """
        context.stra_log_text("开始执行日选股...")

        candidates = []

        for code in self.stock_pool:
            try:
                # 获取日K线数据
                df_bars = context.stra_get_bars(code, "d", 100)
                if df_bars is None or len(df_bars) < 60:
                    continue

                closes = df_bars.closes
                highs = df_bars.highs

                # 检查趋势
                is_trend_up, info = self.indicator.check_trend_up(closes, highs)

                if is_trend_up:
                    candidates.append(code)
                    context.stra_log_text(
                        f"选入 {code}: 均线多头排列={info['bullish_alignment']}, "
                        f"价格突破={info['price_breakout']:.2f} > {info['breakout_price']:.2f}"
                    )

            except Exception as e:
                context.stra_log_text(f"选股错误 {code}: {str(e)}", level=3)
                continue

        # 更新候选股票列表
        self.position_mgr.set_candidates(candidates)

        # 持久化候选列表
        context.user_save_data(self.KEY_CANDIDATES, json.dumps(candidates))

        context.stra_log_text(f"选股完成，共选出{len(candidates)}只股票: {candidates}")

    def _check_entry_signal(self, context: SelContext, code: str, curTime: int) -> bool:
        """
        检查进场信号

        @context    策略上下文
        @code       股票代码
        @curTime    当前时间
        @return     是否进场
        """
        try:
            # 获取分钟K线
            df_bars = context.stra_get_bars(code + "Q", "m1", 50)
            if df_bars is None or len(df_bars) < 10:
                return False

            closes = df_bars.closes
            entry_ma_period = self.config['trading']['entry_ma_period']

            # 检查价格是否在均线上方
            if not self.indicator.price_above_ma(closes, entry_ma_period):
                return False

            # 检查均线是否上行
            if not self.indicator.is_ma_rising(closes, entry_ma_period, check_bars=5):
                return False

            # 进场
            current_price = closes[-1]
            curDate = context.stra_get_date()

            # 计算仓位（简单起见，固定买入100股）
            # 实际应根据资金管理和价格计算
            qty = 100

            context.stra_set_position(code, qty, "entry")
            context.stra_log_text(f"进场 {code} @ {current_price:.2f}, 数量: {qty}")

            # 记录持仓信息
            self.position_mgr.add_position(
                code=code,
                qty=qty,
                entry_price=current_price,
                entry_date=curDate,
                entry_time=curTime,
                tag="entry"
            )

            return True

        except Exception as e:
            context.stra_log_text(f"进场检查错误 {code}: {str(e)}", level=3)
            return False

    def _check_stop_loss(self, context: SelContext, code: str, curTime: int):
        """
        检查止损条件

        @context    策略上下文
        @code       股票代码
        @curTime    当前时间
        """
        pos_info = self.position_mgr.get_position(code)
        if pos_info is None:
            return

        try:
            # 获取日线数据检查持续下跌
            df_daily = context.stra_get_bars(code, "d", 10)
            if df_daily is not None:
                closes = df_daily.closes
                entry_price = pos_info.entry_price
                price_below_days = self.config['stop_loss']['price_below_days']

                # 检查是否持续低于买入价
                below_count = sum(1 for c in closes[-price_below_days:] if c < entry_price)
                if below_count >= price_below_days:
                    self._exit_position(context, code, "持续下跌止损")
                    return

            # 尾盘止损检查
            shadow_trigger_time = self.config['stop_loss']['shadow_trigger_time']
            if curTime >= shadow_trigger_time:
                # 获取当日分钟K线
                df_min = context.stra_get_bars(code + "Q", "m1", 240)
                if df_min is not None and len(df_min) > 0:
                    opens = df_min.opens
                    highs = df_min.highs
                    closes = df_min.closes

                    # 检查长上影线
                    if check_upper_shadow(opens, highs, closes,
                                          self.config['stop_loss']['shadow_ratio']):
                        self._exit_position(context, code, "长上影线止损")
                        return

                    # 检查大阴线
                    if check_big_yin_line(opens, closes,
                                          self.config['stop_loss']['big_yin_ratio']):
                        self._exit_position(context, code, "大阴线止损")
                        return

        except Exception as e:
            context.stra_log_text(f"止损检查错误 {code}: {str(e)}", level=3)

    def _exit_position(self, context: SelContext, code: str, reason: str):
        """
        平仓

        @context    策略上下文
        @code       股票代码
        @reason     平仓原因
        """
        current_price = context.stra_get_price(code)

        context.stra_set_position(code, 0, reason)
        context.stra_log_text(f"平仓 {code} @ {current_price:.2f}, 原因: {reason}")

        # 移除持仓记录
        self.position_mgr.remove_position(code)

    def on_backtest_end(self, context: SelContext):
        """
        回测结束回调
        """
        context.stra_log_text("回测结束")

        # 输出最终持仓
        positions = self.position_mgr.get_all_positions()
        if positions:
            context.stra_log_text(f"最终持仓: {list(positions.keys())}")