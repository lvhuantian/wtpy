"""
趋势指标计算模块
提供MA计算、趋势判断、突破检测等功能
"""

import numpy as np
from typing import Tuple, List, Optional


class TrendIndicator:
    """趋势指标计算器"""

    def __init__(self, ma_periods: List[int] = None, breakout_days: int = 20):
        """
        初始化趋势指标计算器

        @ma_periods    均线周期列表，如[5, 10, 20, 60]
        @breakout_days 突破检测天数
        """
        self.ma_periods = ma_periods or [5, 10, 20, 60]
        self.breakout_days = breakout_days

    def calc_ma(self, closes: np.ndarray, period: int) -> np.ndarray:
        """
        计算移动平均线

        @closes   收盘价序列
        @period   均线周期
        @return   均线序列
        """
        if len(closes) < period:
            return np.array([])

        ma = np.zeros(len(closes))
        ma[:period-1] = np.nan

        for i in range(period - 1, len(closes)):
            ma[i] = np.mean(closes[i-period+1:i+1])

        return ma

    def calc_all_mas(self, closes: np.ndarray) -> dict:
        """
        计算所有均线

        @closes   收盘价序列
        @return   {周期: 均线序列} 字典
        """
        result = {}
        for period in self.ma_periods:
            result[period] = self.calc_ma(closes, period)
        return result

    def is_bullish_alignment(self, closes: np.ndarray, periods: List[int] = None) -> bool:
        """
        判断是否均线多头排列

        @closes   收盘价序列
        @periods  均线周期列表，默认使用[5, 10, 20]
        @return   是否多头排列
        """
        if periods is None:
            periods = [5, 10, 20]

        if len(closes) < max(periods):
            return False

        mas = []
        for period in periods:
            ma = np.mean(closes[-period:])
            mas.append(ma)

        # 检查是否 MA5 > MA10 > MA20
        for i in range(len(mas) - 1):
            if mas[i] <= mas[i + 1]:
                return False

        return True

    def check_price_breakout(self, highs: np.ndarray, closes: np.ndarray,
                              days: int = None) -> Tuple[bool, float]:
        """
        检测价格突破

        @highs    最高价序列
        @closes   收盘价序列
        @days     突破天数
        @return   (是否突破, 突破价格)
        """
        if days is None:
            days = self.breakout_days

        if len(highs) < days + 1:
            return False, 0.0

        # 计算N日高点（不含当日）
        breakout_price = np.max(highs[-days-1:-1])
        current_close = closes[-1]

        is_breakout = current_close > breakout_price
        return is_breakout, breakout_price

    def check_trend_up(self, closes: np.ndarray, highs: np.ndarray) -> Tuple[bool, dict]:
        """
        检查是否处于上涨趋势

        综合判断：
        1. 均线多头排列
        2. 价格突破N日高点

        @closes   收盘价序列
        @highs    最高价序列
        @return   (是否上涨趋势, 详细信息)
        """
        info = {
            'bullish_alignment': False,
            'price_breakout': False,
            'breakout_price': 0.0,
            'current_price': closes[-1] if len(closes) > 0 else 0
        }

        # 检查均线多头排列
        info['bullish_alignment'] = self.is_bullish_alignment(closes)

        # 检查价格突破
        is_breakout, breakout_price = self.check_price_breakout(highs, closes)
        info['price_breakout'] = is_breakout
        info['breakout_price'] = breakout_price

        # 综合判断
        is_trend_up = info['bullish_alignment'] and info['price_breakout']

        return is_trend_up, info

    def is_ma_rising(self, closes: np.ndarray, period: int = 5, check_bars: int = 5) -> bool:
        """
        判断均线是否上行

        @closes      收盘价序列
        @period      均线周期
        @check_bars  检查的K线数量
        @return      均线是否上行
        """
        if len(closes) < period + check_bars:
            return False

        # 计算最近check_bars根K线的均线值
        recent_mas = []
        for i in range(check_bars):
            ma = np.mean(closes[-(period+i):len(closes)-i if i > 0 else None])
            recent_mas.append(ma)

        # 检查均线是否逐渐抬高
        for i in range(len(recent_mas) - 1):
            if recent_mas[i] <= recent_mas[i + 1]:
                return False

        return True

    def price_above_ma(self, closes: np.ndarray, period: int = 5) -> bool:
        """
        判断当前价格是否在均线上方

        @closes   收盘价序列
        @period   均线周期
        @return   是否在均线上方
        """
        if len(closes) < period:
            return False

        current_price = closes[-1]
        ma = np.mean(closes[-period:])

        return current_price > ma


def check_upper_shadow(opens: np.ndarray, highs: np.ndarray,
                        closes: np.ndarray, ratio: float = 2.0) -> bool:
    """
    检查是否有长上影线

    @opens    开盘价序列
    @highs    最高价序列
    @closes   收盘价序列
    @ratio    上影线/实体比例阈值
    @return   是否有长上影线
    """
    if len(opens) == 0 or len(highs) == 0 or len(closes) == 0:
        return False

    open_price = opens[-1]
    high = highs[-1]
    close = closes[-1]

    # 上影线
    upper_shadow = high - max(open_price, close)
    # 实体
    body = abs(close - open_price)

    if body == 0:
        return upper_shadow > 0

    return upper_shadow > body * ratio


def check_big_yin_line(opens: np.ndarray, closes: np.ndarray,
                        ratio: float = 3.0) -> bool:
    """
    检查是否有大阴线

    @opens    开盘价序列
    @closes   收盘价序列
    @ratio    跌幅比例阈值(%)
    @return   是否有大阴线
    """
    if len(opens) == 0 or len(closes) == 0:
        return False

    open_price = opens[-1]
    close = closes[-1]

    # 大阴线：收盘价低于开盘价，且跌幅超过阈值
    if close >= open_price:
        return False

    drop_ratio = (open_price - close) / open_price * 100
    return drop_ratio >= ratio