# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

wtpy is the Python wrapper framework for **WonderTrader**, a quantitative trading system. It provides Python bindings to C++ trading engines for backtesting and live trading across futures, stocks, and other asset classes.

## Core Architecture

### Engine Types
- **WtBtEngine** (`wtpy/WtBtEngine.py`) - Backtest engine
- **WtEngine** (`wtpy/WtEngine.py`) - Live trading engine
- **WtDtEngine** (`wtpy/WtDtEngine.py`) - Data engine

### Strategy Types (defined in `wtpy/StrategyDefs.py`)
- **BaseCtaStrategy** - CTA/trend-following strategies
- **BaseHftStrategy** - High-frequency trading strategies
- **BaseSelStrategy** - Stock selection/portfolio strategies

### Context Classes
Strategies interact with engines through context objects:
- **CtaContext** (`wtpy/CtaContext.py`) - API for CTA strategies
- **HftContext** (`wtpy/HftContext.py`) - API for HFT strategies
- **SelContext** (`wtpy/SelContext.py`) - API for selection strategies

### C++ Bindings (`wtpy/wrapper/`)
- **WtBtWrapper** - Backtest engine C++ bindings
- **WtWrapper** - Live trading engine C++ bindings
- **WtDtWrapper** - Data component C++ bindings
- Platform-specific DLLs are in `x64/`, `x86/`, `linux/` subdirectories

### Application Modules (`wtpy/apps/`)
- **WtBtAnalyst** - Backtest performance analysis
- **WtCtaOptimizer** - CTA parameter optimization (parallel)
- **WtCtaGAOptimizer** - Genetic algorithm optimizer
- **WtHotPicker** - Futures contract rollover rules

## Running Backtests

```python
from wtpy import WtBtEngine, EngineType, BaseCtaStrategy

# Create backtest engine
engine = WtBtEngine(EngineType.ET_CTA)
engine.init('../common/', "configbt.yaml")
engine.configBacktest(201909100930, 201912011500)  # start_time, end_time
engine.configBTStorage(mode="csv", path="../storage/")
engine.commitBTConfig()

# Add strategy
engine.set_cta_strategy(my_strategy)
engine.run_backtest(bAsync=False)
engine.release_backtest()
```

## Strategy Development

Strategies inherit from base classes and implement callback methods:

```python
from wtpy import BaseCtaStrategy, CtaContext

class MyStrategy(BaseCtaStrategy):
    def __init__(self, name: str):
        BaseCtaStrategy.__init__(self, name)

    def on_init(self, context: CtaContext):
        context.stra_get_bars(code, "m5", 100, isMain=True)

    def on_calculate(self, context: CtaContext):
        # Called on bar close
        context.stra_enter_long(code, qty, "tag")
        context.stra_set_position(code, target_qty, "tag")
```

## Configuration Files

Configuration supports both YAML and JSON formats:
- `configbt.yaml` / `configbt.json` - Backtest configuration
- `config.yaml` / `config.json` - Live trading configuration
- Base files in `demos/common/`: commodities.json, contracts.json, sessions.json, holidays.json, hots.json

## Dependencies

See `setup.py` for required packages:
- numpy, pandas - data handling
- fastapi, uvicorn - monitoring service
- deap - genetic algorithm optimization
- pyyaml, chardet, xlsxwriter, pyquery, psutil

## Demo Projects

The `demos/` directory contains examples:
- `cta_fut_bt/` - Futures CTA backtest
- `cta_stk_bt/` - Stock CTA backtest
- `cta_optimizer/` - Parameter optimization
- `hft_fut_bt/` - HFT backtest
- `test_monitor/` - Monitoring service