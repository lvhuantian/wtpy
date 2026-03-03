"""
策略模块初始化
"""

from .trend_indicator import TrendIndicator, check_upper_shadow, check_big_yin_line
from .position_manager import PositionManager, PositionInfo
from .trend_selection_strategy import TrendSelectionStrategy

__all__ = [
    'TrendIndicator',
    'check_upper_shadow',
    'check_big_yin_line',
    'PositionManager',
    'PositionInfo',
    'TrendSelectionStrategy'
]