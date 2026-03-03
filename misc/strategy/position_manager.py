"""
仓位管理模块
管理持仓数量、资金分配等功能
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class PositionInfo:
    """持仓信息"""
    code: str           # 股票代码
    qty: float          # 持仓数量
    entry_price: float  # 入场价格
    entry_date: int     # 入场日期
    entry_time: int     # 入场时间
    tag: str = ""       # 入场标记


class PositionManager:
    """仓位管理器"""

    def __init__(self, max_positions: int = 5, position_ratio: float = 0.2,
                 total_capital: float = 1000000):
        """
        初始化仓位管理器

        @max_positions   最大持仓数量
        @position_ratio  单只股票仓位比例
        @total_capital   总资金
        """
        self.max_positions = max_positions
        self.position_ratio = position_ratio
        self.total_capital = total_capital

        # 持仓信息 {code: PositionInfo}
        self.__positions__: Dict[str, PositionInfo] = {}

        # 候选股票列表
        self.__candidates__: List[str] = []

    def get_position_qty(self, code: str) -> int:
        """
        计算单只股票的目标持仓数量

        @code   股票代码
        @return 目标持仓数量（股数，取整到100股）
        """
        position_value = self.total_capital * self.position_ratio
        # 假设价格由外部传入，这里返回资金量
        return int(position_value)

    def can_open_position(self) -> bool:
        """
        检查是否可以开新仓位

        @return 是否可以开仓
        """
        return len(self.__positions__) < self.max_positions

    def get_current_position_count(self) -> int:
        """
        获取当前持仓数量

        @return 持仓数量
        """
        return len(self.__positions__)

    def add_position(self, code: str, qty: float, entry_price: float,
                     entry_date: int, entry_time: int, tag: str = ""):
        """
        添加持仓

        @code          股票代码
        @qty           持仓数量
        @entry_price   入场价格
        @entry_date    入场日期
        @entry_time    入场时间
        @tag           入场标记
        """
        self.__positions__[code] = PositionInfo(
            code=code,
            qty=qty,
            entry_price=entry_price,
            entry_date=entry_date,
            entry_time=entry_time,
            tag=tag
        )

    def remove_position(self, code: str):
        """
        移除持仓

        @code   股票代码
        """
        if code in self.__positions__:
            del self.__positions__[code]

    def get_position(self, code: str) -> Optional[PositionInfo]:
        """
        获取持仓信息

        @code   股票代码
        @return 持仓信息
        """
        return self.__positions__.get(code)

    def has_position(self, code: str) -> bool:
        """
        检查是否持有某股票

        @code   股票代码
        @return 是否持有
        """
        return code in self.__positions__

    def get_all_positions(self) -> Dict[str, PositionInfo]:
        """
        获取所有持仓

        @return 持仓字典
        """
        return self.__positions__.copy()

    def set_candidates(self, candidates: List[str]):
        """
        设置候选股票列表

        @candidates   候选股票代码列表
        """
        self.__candidates__ = candidates

    def get_candidates(self) -> List[str]:
        """
        获取候选股票列表

        @return 候选股票代码列表
        """
        return self.__candidates__.copy()

    def add_candidate(self, code: str):
        """
        添加候选股票

        @code   股票代码
        """
        if code not in self.__candidates__:
            self.__candidates__.append(code)

    def clear_candidates(self):
        """
        清空候选股票列表
        """
        self.__candidates__ = []

    def get_entry_price(self, code: str) -> float:
        """
        获取入场价格

        @code   股票代码
        @return 入场价格，未持有返回0
        """
        pos = self.get_position(code)
        if pos:
            return pos.entry_price
        return 0.0

    def get_entry_date(self, code: str) -> int:
        """
        获取入场日期

        @code   股票代码
        @return 入场日期，未持有返回0
        """
        pos = self.get_position(code)
        if pos:
            return pos.entry_date
        return 0

    def to_dict(self) -> dict:
        """
        转换为字典，用于持久化

        @return 字典形式的状态
        """
        return {
            'positions': {
                code: {
                    'code': pos.code,
                    'qty': pos.qty,
                    'entry_price': pos.entry_price,
                    'entry_date': pos.entry_date,
                    'entry_time': pos.entry_time,
                    'tag': pos.tag
                }
                for code, pos in self.__positions__.items()
            },
            'candidates': self.__candidates__
        }

    def from_dict(self, data: dict):
        """
        从字典恢复状态

        @data   字典形式的状态
        """
        self.__positions__ = {}
        if 'positions' in data:
            for code, pos_data in data['positions'].items():
                self.__positions__[code] = PositionInfo(
                    code=pos_data['code'],
                    qty=pos_data['qty'],
                    entry_price=pos_data['entry_price'],
                    entry_date=pos_data['entry_date'],
                    entry_time=pos_data['entry_time'],
                    tag=pos_data.get('tag', '')
                )

        if 'candidates' in data:
            self.__candidates__ = data['candidates']