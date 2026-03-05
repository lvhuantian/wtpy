# 文件结构

misc/
├── config/
│   ├── stock_pool.json               # 股票池配置，包含10只示例A股
│   └── strategy_params.yaml          # 策略参数配置
├── strategy/
│   ├── trend_indicator.py            # 趋势指标计算模块
│   ├── position_manager.py           # 仓位管理模块
│   ├── trend_selection_strategy.py   # 主策略类
│   └── __init__.py                   # 模块初始化文件
├── scripts/
│   └── download_data.py              # 数据下载脚本
├── run_backtest.py                   # 回测入口
└── configbt.yaml                     # 回测配置文件

# 策略架构

TrendSelectionStrategy (BaseSelStrategy)
├── on_init() - 初始化，订阅行情
├── on_session_begin() - 交易日开始，重置状态
├── on_calculate() - 日线收盘后选股
├── on_bar() - 分钟线进场/止损判断
└── on_session_end() - 交易日结束

TrendIndicator (趋势指标)
├── calc_ma() - 计算均线
├── is_bullish_alignment() - 多头排列判断
├── check_price_breakout() - 价格突破检测
└── check_trend_up() - 综合趋势判断

PositionManager (仓位管理)
├── add/remove_position() - 持仓管理
├── can_open_position() - 开仓检查
├── get/set_candidates() - 候选股票管理
└── to_dict/from_dict() - 状态持久化

# 策略实现

## 数据准备

- 在 on_init 方法中，你需要为所有潜在的标的订阅日K线数据。
```python
# 在 on_init 方法中
for code in self.__codes__: # self.__codes__ 是策略初始化时传入的标的代码列表
    context.stra_prepare_bars(code, "d1", self.__bar_cnt__) # 准备足够多的日K数据，例如250天用于计算60日新高和均线
```

- 在 on_calculate 方法中，获取日K线数据：
```python
df_bars_d1 = context.stra_get_bars(code, "d1", self.__bar_cnt__)
if df_bars_d1 is None or len(df_bars_d1.closes) < max_lookback_period: # 确保数据足够
    continue
closes_d1 = df_bars_d1.closes
highs_d1 = df_bars_d1.highs
```

## 选股
### 成交额
个股成交额大于10亿
板块成交额大于500亿（TODO，暂时无板块信息）


### 趋势上涨判断逻辑

- 位于5日线上方：
```python
ma5 = np.mean(closes_d1[-5:])
is_above_ma5 = closes_d1[-1] > ma5
```

- 位于10日线上方：
```python
ma10 = np.mean(closes_d1[-10:])
is_above_ma10 = closes_d1[-1] > ma10
```

- 位于20日线上方：
```python
ma20 = np.mean(closes_d1[-20:])
is_above_ma20 = closes_d1[-1] > ma20
```

- 60 交易日周期内新高：
```python
highest_60_days = np.amax(highs_d1[-60:])
is_new_high_60 = highs_d1[-1] >= highest_60_days # 或者使用收盘价判断
```

- 历史新高：
```python
# TODO
is_new_high_all = closes_d1[-1] >= np.amax(closes_d1)
```

### 涨停
涨停数越多，优先级越高
区分5cm和10cm和20cm


 
 标的优先级： 在 on_calculate 中，你可以为每个标的计算一个综合得分或使用优先级链。

```
candidate_codes = []
# 按照优先级筛选，例如：
if is_new_high_60:
    candidate_codes.append((code, 1)) # 优先级最高
elif is_above_ma5 and is_above_ma10 and is_above_ma20:
    candidate_codes.append((code, 2))
elif is_above_ma10 and is_above_ma20:
    candidate_codes.append((code, 3))
elif is_above_ma20:
    candidate_codes.append((code, 4))

# 根据优先级对 candidate_codes 进行排序或选择
# 在 on_calculate 周期内，将选出的高优先级标的作为当天或下个交易周期关注的对象。
# [SelContext](%2Fwondertrader%2Fwtpy%2Fwtpy%2FSelContext.py#L5) 提供了 stra_get_all_codes、stra_get_codes_by_product 等方法来获取所有合约或按产品筛选合约，方便你构建完整的标的池。
```

### 开仓
1min K线进场买入点判断逻辑
这部分逻辑也主要在`on_calculate`方法中实现，但需要获取1分钟K线数据。

- 数据准备： 在`on_init`方法中，为选中的标的订阅1分钟K线数据。
```python
# 在 on_init 方法中，假设 self.__long_term_candidates__ 存储了筛选出的标的
for code in self.__long_term_candidates__:
    context.stra_prepare_bars(code, "m1", self.__short_bar_cnt__) # 准备1分钟K数据，例如60根用于1小时均线
```
在`on_calculate`方法中，获取1分钟K线数据：
```python
df_bars_m1 = context.stra_get_bars(code, "m1", self.__short_bar_cnt__)
if df_bars_m1 is None or len(df_bars_m1.closes) < min_lookback_period:
    continue
closes_m1 = df_bars_m1.closes
# 根据需要计算1分钟K线的均线、MACD等指标
```

进场买入点逻辑：

开盘1小时内价格稳定在均线上方： 你需要获取开盘后的1小时内（例如60根1分钟K线）的数据。
```python
# 假设开盘时间是9:30，你可以在on_calculate中判断当前时间是否在10:30之前
# 并计算1分钟K线的均线，检查价格是否持续位于均线上方
cur_time = context.stra_get_time()
if 930 <= cur_time <= 1030:
    ma_short = np.mean(closes_m1[-self.ma_length_short:])
    if closes_m1[-1] > ma_short:
        # 价格稳定在均线上方，可以作为买入信号之一
        pass
```
价格回踩均线后反弹： 这需要更复杂的逻辑来判断回踩和反弹形态，例如：
```python
ma_medium = np.mean(closes_m1[-self.ma_length_medium:])
# 判断价格是否在均线下方，然后又快速回到均线上方
if closes_m1[-2] < ma_medium and closes_m1[-1] > ma_medium:
    # 价格回踩均线后反弹
    pass

旗形突破： 这需要模式识别功能，可能需要自行实现或引入第三方库进行技术形态识别。
```
4. 数据获取和管理
[wtpy](%2Fwondertrader%2Fwtpy%2FREADME.md#L9) 的 SEL 策略使用 SelContext (wtpy/wtpy/SelContext.py) 进行数据交互。

- context.stra_prepare_bars(stdCode, period, count)：预加载指定合约和周期的K线数据。
- context.stra_get_bars(stdCode, period, count)：获取指定合约和周期的K线数据，返回 [WtNpKline](%2Fwondertrader%2Fwtpy%2Fwtpy%2FWtDataDefs.py#L36) 对象，它是一个 NumPy 数组，方便进行向量化计算。
- context.stra_get_time() 和 context.stra_get_date()：获取当前时间和日期，用于控制交易逻辑。
- WtDtServo (wtpy/wtpy/WtDtServo.py) 提供了从底层C++数据服务直接访问历史K线和Tick数据的功能。

5. 交易指令和仓位管理
你将使用 SelContext 提供的方法进行仓位管理。

开仓买入（固定每次20%仓位）： 在 on_calculate 方法中，当买入条件满足时，计算目标仓位。你需要知道总资金和标的的价值。SelContext 提供了 stra_get_fund_data (wtpy/wtpy/SelContext.py#L82) 来获取资金数据，例如：
```python
total_fund = context.stra_get_fund_data(0) # 获取动态权益
product_info = context.stra_get_comminfo(code) # 获取产品信息，例如最小交易单位
if product_info is None:
    continue

# 获取当前价格
cur_price = context.stra_get_price(code)
if cur_price == 0:
    continue

# 计算目标仓位
target_qty_per_trade = (total_fund * 0.20) / (cur_price * product_info.volscale) # volscale是数量乘数
target_qty_per_trade = (int(target_qty_per_trade / product_info.minlots)) * product_info.minlots # 调整到最小交易单位的整数倍

# 如果有现有仓位，需要计算增量
current_pos = context.stra_get_position(code)
new_target_pos = current_pos + target_qty_per_trade # 每次增加20%仓位
context.stra_set_position(code, new_target_pos, 'buy_signal_tag')
```
[stra_set_position](%2Fwondertrader%2Fwtpy%2Fwtpy%2FCtaContext.py#L319) 方法可以直接设置目标仓位，系统会根据当前仓位自动计算买入或卖出量。

### 平仓
平仓支持多种策略：

开盘1小时内持续跌破买入价格： 需要记录买入价格和买入时间。
```python
# 在 on_calculate 中，假设 buy_price 和 entry_time 已经记录
cur_time = context.stra_get_time()
if context.stra_get_position(code) > 0 and 930 <= cur_time <= 1030:
    if cur_price < buy_price: # 持续跌破买入价格
        context.stra_set_position(code, 0, 'exit_open_drop') # 全部平仓
```
收盘半小时内出现大阴线： 需要判断当前时间是否在收盘前，并检查K线形态。
```python
# 假设收盘时间是15:00
cur_time = context.stra_get_time()
if context.stra_get_position(code) > 0 and 1430 <= cur_time <= 1500:
    # 判断大阴线：例如收盘价远低于开盘价，且跌幅超过一定阈值
    if closes_m1[-1] < df_bars_m1.opens[-1] and (df_bars_m1.opens[-1] - closes_m1[-1]) / df_bars_m1.opens[-1] > self.large_bear_candle_threshold:
        context.stra_set_position(code, 0, 'exit_large_bear_candle') # 全部平仓
```
你可以在 on_calculate 中结合这些平仓条件，并在满足条件时调用 context.stra_set_position(code, 0, 'exit_tag') 来平仓所有持仓。


示例代码结构 (StraDualThrustSel 类中 on_calculate 方法的拓展)
你可以参考 wtpy/demos/Strategies/DualThrust_Sel.py 中的 StraDualThrustSel 类，在其 on_calculate 方法中整合上述逻辑。

```python
from wtpy import BaseSelStrategy, SelContext
import numpy as np

class MyMultiFactorSelStrategy(BaseSelStrategy):
    def __init__(self, name:str, codes:list, long_term_bar_cnt:int, short_term_bar_cnt:int,
                 ma_lengths:list, new_high_period:int,
                 entry_ma_length:int, large_bear_candle_threshold:float):
        BaseSelStrategy.__init__(self, name)

        self.__codes__ = codes # 标的池
        self.__long_term_bar_cnt__ = long_term_bar_cnt # 日K线数据量
        self.__short_term_bar_cnt__ = short_term_bar_cnt # 1分钟K线数据量

        self.__ma_lengths__ = ma_lengths # 例如 [5, 10, 20]
        self.__new_high_period__ = new_high_period # 例如 60
        self.__entry_ma_length__ = entry_ma_length # 例如 5 (用于1分钟K线均线)
        self.__large_bear_candle_threshold__ = large_bear_candle_threshold # 例如 0.02 (2%跌幅)

        self.__long_term_candidates__ = {} # 存储通过日K筛选出的标的及其优先级
        self.__entry_prices__ = {} # 记录每个标的的买入价格
        self.__entry_times__ = {} # 记录每个标的的买入时间


    def on_init(self, context:SelContext):
        # 订阅所有标的所需的日K线和1分钟K线
        for code in self.__codes__:
            context.stra_prepare_bars(code, "d1", self.__long_term_bar_cnt__)
            context.stra_prepare_bars(code, "m1", self.__short_term_bar_cnt__)
        context.stra_log_text("策略初始化完成")

    def on_calculate(self, context:SelContext):
        cur_date = context.stra_get_date()
        cur_time = context.stra_get_time()

        # 第一阶段：日K线筛选趋势上涨标的
        self.__long_term_candidates__ = {}
        for code in self.__codes__:
            df_bars_d1 = context.stra_get_bars(code, "d1", self.__long_term_bar_cnt__)
            if df_bars_d1 is None or len(df_bars_d1.closes) < self.__new_high_period__: # 确保数据量足够
                continue

            closes_d1 = df_bars_d1.closes
            highs_d1 = df_bars_d1.highs
            last_close_d1 = closes_d1[-1]
            last_high_d1 = highs_d1[-1]

            # 60日新高
            highest_60_days = np.amax(highs_d1[-self.__new_high_period__:])
            is_new_high_60 = (last_high_d1 >= highest_60_days) # 注意这里可以根据实际需求调整为严格大于

            # 均线判断
            ma_above_count = 0
            is_above_ma5 = False
            is_above_ma10 = False
            is_above_ma20 = False

            if len(closes_d1) >= 20: # 确保有足够数据计算20日均线
                ma20 = np.mean(closes_d1[-20:])
                is_above_ma20 = (last_close_d1 > ma20)

            if len(closes_d1) >= 10:
                ma10 = np.mean(closes_d1[-10:])
                is_above_ma10 = (last_close_d1 > ma10)

            if len(closes_d1) >= 5:
                ma5 = np.mean(closes_d1[-5:])
                is_above_ma5 = (last_close_d1 > ma5)

            # 优先级判断
            priority = 99 # 默认低优先级
            if is_new_high_60:
                priority = 1
            elif is_above_ma5 and is_above_ma10 and is_above_ma20:
                priority = 2
            elif is_above_ma10 and is_above_ma20:
                priority = 3
            elif is_above_ma20:
                priority = 4

            if priority < 99:
                self.__long_term_candidates__[code] = priority

        # 第二阶段：对筛选出的标的进行1分钟K线进场和离场判断
        sorted_candidates = sorted(self.__long_term_candidates__.items(), key=lambda item: item[1]) # 按优先级排序

        for code, priority in sorted_candidates:
            cur_pos = context.stra_get_position(code) # 获取当前持仓

            # 获取1分钟K线数据
            df_bars_m1 = context.stra_get_bars(code, "m1", self.__short_term_bar_cnt__)
            if df_bars_m1 is None or len(df_bars_m1.closes) < self.__entry_ma_length__:
                continue

            closes_m1 = df_bars_m1.closes
            opens_m1 = df_bars_m1.opens
            last_close_m1 = closes_m1[-1]
            last_open_m1 = opens_m1[-1]
            cur_price = context.stra_get_price(code) # 最新价格

            # --- 平仓逻辑 ---
            if cur_pos > 0:
                # 1. 开盘1小时内持续跌破买入价格
                entry_price = self.__entry_prices__.get(code, 0)
                entry_time = self.__entry_times__.get(code, 0)

                # 假设开盘时间是 9:30，1小时内是 10:30 之前
                if entry_price > 0 and 930 <= cur_time <= 1030 and cur_price < entry_price:
                    context.stra_set_position(code, 0, 'exit_open_drop')
                    context.stra_log_text(f"{code} 触发开盘1小时内跌破买入价止损，平仓")
                    del self.__entry_prices__[code]
                    del self.__entry_times__[code]
                    continue

                # 2. 收盘半小时内出现大阴线
                # 假设收盘时间是 15:00，半小时内是 14:30 之后
                if 1430 <= cur_time <= 1500:
                    if last_close_m1 < last_open_m1 and \
                       (last_open_m1 - last_close_m1) / last_open_m1 > self.__large_bear_candle_threshold__:
                        context.stra_set_position(code, 0, 'exit_large_bear_candle')
                        context.stra_log_text(f"{code} 触发收盘大阴线止损，平仓")
                        if code in self.__entry_prices__:
                            del self.__entry_prices__[code]
                            del self.__entry_times__[code]
                        continue

                # 可以在此处添加其他止盈止损逻辑

            # --- 进场逻辑 ---
            # 只有没有持仓时才考虑进场，且优先级高的标的优先进场
            if cur_pos == 0:
                # 1分钟K线均线判断（例如：价格稳定在均线上方）
                ma_short_m1 = np.mean(closes_m1[-self.__entry_ma_length__:])
                is_above_entry_ma = (last_close_m1 > ma_short_m1)

                # 价格回踩均线后反弹（简化逻辑）
                is_rebound_from_ma = False
                if len(closes_m1) >= self.__entry_ma_length__ + 1:
                    prev_ma_short_m1 = np.mean(closes_m1[-(self.__entry_ma_length__ + 1):-1])
                    if closes_m1[-2] < prev_ma_short_m1 and last_close_m1 > ma_short_m1:
                        is_rebound_from_ma = True

                # 旗形突破（简化：这里仅为示例，实际需要复杂的形态识别）
                is_flag_breakout = False # 假设通过某种复杂计算得出

                # 根据进场条件判断
                if (930 <= cur_time <= 1030 and is_above_entry_ma) or \
                   is_rebound_from_ma or is_flag_breakout:

                    # 计算20%仓位
                    total_fund = context.stra_get_fund_data(0)
                    product_info = context.stra_get_comminfo(code)
                    if product_info is None:
                        continue

                    target_qty = (total_fund * 0.20) / (cur_price * product_info.volscale)
                    target_qty = (int(target_qty / product_info.minlots)) * product_info.minlots

                    if target_qty > 0:
                        context.stra_set_position(code, target_qty, 'buy_signal_tag')
                        context.stra_log_text(f"{code} 满足买入条件，买入 {target_qty} 股/手")
                        self.__entry_prices__[code] = cur_price
                        self.__entry_times__[code] = cur_time
                        # 为了避免同时买入过多标的，可以考虑每次只买入一个优先级最高的标的
                        break # 买入后就跳出循环，等待下一个on_calculate周期
```
6. 回测与优化
使用 WtBtEngine (wtpy/wtpy/WtBtEngine.py) 进行回测。
```python
from wtpy import WtBtEngine, EngineType
from wtpy.apps import WtBtAnalyst
from .Strategies.MyStrategy import MyMultiFactorSelStrategy # 假设你的策略类在这个路径下

# 1. 初始化回测引擎
engine = WtBtEngine(eType=EngineType.ET_SEL, logCfg="logcfgbt.yaml", outDir="./outputs_bt_sel")

# 2. 初始化基本数据（品种、合约、会话信息）
engine.init(
    folder="./common/", # 包含 common/contracts.json 等文件
    cfgfile="configbt.yaml", # 回测配置文件
    contractfile="contracts.json",
    sessionfile="sessions.json",
    commfile="commodities.json"
)

# 3. 配置回测时间范围
engine.configBacktest(202201010900, 202301011500) # 例如2022年全年数据

# 4. 创建策略实例并注册
my_strategy = MyMultiFactorSelStrategy(
    name='MySelStrategy',
    codes=['SSE.600000', 'SHFE.rb.HOT'], # 示例标的
    long_term_bar_cnt=250,
    short_term_bar_cnt=60,
    ma_lengths=[5, 10, 20],
    new_high_period=60,
    entry_ma_length=5,
    large_bear_candle_threshold=0.02
)

# 注册SEL策略，这里设置执行周期为每天收盘前5分钟，假设周期是d，时间是1455
engine.set_sel_strategy(my_strategy, date=0, time=1455, period="d", slippage=1)

# 5. 运行回测
engine.run_backtest()

# 6. 分析回测结果
analyst = WtBtAnalyst()
analyst.add_strategy("MySelStrategy", folder="./outputs_bt_sel/MySelStrategy/", init_capital=1000000) # 初始资金
analyst.run()

engine.release_backtest()
```

你可以利用 [WtHftOptimizer](%2Fwondertrader%2Fwtpy%2Fwtpy%2Fapps%2FWtHftOptimizer.py#L38)（虽然名称是HFT，但可以修改后用于CTA/SEL参数优化）或者自定义参数优化脚本来寻找最佳参数组合。在优化器中，你可以将均线周期、新高周期、买入均线长度、大阴线阈值等作为可变参数进行遍历或遗传算法优化。

