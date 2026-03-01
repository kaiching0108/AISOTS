# AI Futures Trading System - Agent Guidelines

**文件版本**: 4.6.1

## Overview

This is an AI-powered futures trading system using Shioaji API (Taiwan Futures Exchange), with support for multiple trading strategies, risk management, **Web Interface (primary)** for user interaction, and **Telegram notifications** for alerts.

## Project Structure

```
AISOTS/
├── main.py                 # Entry point
├── config.yaml            # Configuration
├── requirements.txt       # Dependencies
├── src/
│   ├── api/              # Shioaji API wrappers
│   ├── trading/          # Trading logic (strategies, positions, orders)
│   ├── engine/           # Strategy execution engine (LLM generator, rule engine)
│   ├── analysis/          # Performance analysis (signal recorder, analyzer, strategy reviewer)
│   ├── market/           # Market data services
│   ├── risk/             # Risk management
│   ├── storage/          # JSON data persistence
│   ├── agent/            # AI agent tools and LLM providers
│   ├── notify/           # Telegram notifications & bot
│   └── web/              # Web Interface (Flask)
├── tests/                 # Test files
├── workspace/            # Runtime data (JSON files)
└── documents/            # Documentation
```

---

## Build / Lint / Test Commands

### Installation

```bash
cd AISOTS
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Running the Application

```bash
# Run in development
python main.py

# Run in simulation mode (skip Shioaji API login, for testing)
python main.py --simulate
```

### Simulation Mode

Using `--simulate` flag:
- Skips Shioaji API login
- Simulated orders fill immediately
- Simulated positions and PnL are tracked
- **Mock price generation with trend simulation** (see below)
- Suitable for development and testing

#### Mock Price Generation (New in v4.4.0)

The simulation mode now uses a **trend-based price generation algorithm** instead of static prices:

**Algorithm Features:**
- Base fluctuation: 0.3% ~ 0.8% (approx. 54-144 points)
- Trend momentum: Increases for first 5 bars (1.0x → 1.75x)
- Trend fatigue: Decreases after 5 bars (1.75x → 0.5x)
- Random noise: ±0.2%
- Reversal probability: 30% (simulates market turning points)

**Benefits:**
- RSI indicators can reach 70+ (overbought) and 30- (oversold)
- MACD generates clear golden/dead crosses during trends
- Breakout strategies trigger properly with continuous price movement
- Prevents false stop-loss triggers caused by fixed 18000 price

**Implementation:**
- All strategies run at **1-minute K-bar frequency** in simulation
- The strategy's `timeframe` parameter only affects internal logic
- Real market data is used in live trading (simulation doesn't affect live mode)

**Position Entry Price Handling:**
- When creating MockContract, the system checks existing positions
- Uses position's `avg_price` as `last_price` to avoid false stop-loss triggers
- Logs: "Using position entry price XXXX as mock price for SYMBOL"

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_trading.py

# Run a single test
pytest tests/test_trading.py::test_risk_manager

# Run with verbose output
pytest -v

# Run with coverage (if installed)
pytest --cov=src --cov-report=html
```

### Testing Strategy Commands via Fallback

Since explicit English commands are handled via fallback, you can test the system by directly calling `fallback_handle_command()`:

```python
# Example: Test status command
from main import AITradingSystem

bot = AITradingSystem()
result = bot.fallback_handle_command("status")
print(result)

# Test create flow
result = bot.fallback_handle_command("create")
result = bot.fallback_handle_command("RSI策略")  # Input strategy name
```

### Test Structure

```
tests/
├── test_trading.py          # Basic unit tests
├── test_fallback.py         # Fallback command tests
├── test_create_flow.py      # Q&A strategy creation flow
├── test_backtest.py         # Backtest engine tests
└── conftest.py             # Shared fixtures
```

### Test Coverage

| Category | Test Items |
|----------|------------|
| Basic Commands | status, positions, strategies, performance, risk, orders |
| Strategy Management | enable, disable, create |
| Q&A Flow | create Q&A steps |
| Error Handling | invalid commands, invalid parameters |

### Running Specific Tests

```bash
# Run fallback tests
pytest tests/test_fallback.py -v

# Run create flow tests
pytest tests/test_create_flow.py -v

# Run all tests
pytest tests/ -v
```

### Type Checking (Optional)

```bash
# Install mypy
pip install mypy

# Run type checking
mypy src/ --ignore-missing-imports
```

### Code Formatting (Optional)

```bash
# Install black
pip install black

# Format code
black src/ tests/ main.py

# Check formatting without modifying
black --check src/ tests/ main.py
```

---

## Code Style Guidelines

### General Rules

- **Language**: Python 3.10+
- **Encoding**: UTF-8
- **Line Length**: Maximum 120 characters (soft limit)
- **Indentation**: 4 spaces (no tabs)

### Import Organization

Order imports as follows (separated by blank lines):

1. Standard library
2. Third-party libraries
3. Local application imports

```python
# Standard library
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Third-party
import shioaji as sj
from pydantic import BaseModel

# Local application
from src.config import load_config
from src.api import ShioajiClient
from src.trading import StrategyManager
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `class StrategyManager` |
| Functions/methods | snake_case | `def get_positions()` |
| Variables | snake_case | `position_manager` |
| Constants | UPPER_SNAKE | `MAX_POSITION = 10` |
| Private methods | snake_case with prefix `_` | `def _setup_logging()` |
| Files (modules) | snake_case | `strategy_manager.py` |

### Type Hints

Use type hints for function signatures:

```python
# Good
def get_position(self, strategy_id: str) -> Optional[Position]:
    pass

def calculate_pnl(self, current_price: float) -> float:
    pass
```

### Docstrings

Use Google-style docstrings for public methods:

```python
def calculate_pnl(self, current_price: float) -> float:
    """Calculate unrealized profit/loss.
    
    Args:
        current_price: Current market price of the contract.
        
    Returns:
        Profit/loss amount in NTD.
    """
    pass
```

### Error Handling

- Use try/except blocks with specific exception types
- Always log errors with meaningful messages
- Never expose raw exceptions to users

```python
# Good
try:
    result = self.api.place_order(contract, order)
except Exception as e:
    logger.error(f"Order placement failed: {e}")
    return None
```

### Async/Await

- Use `async`/`await` for I/O-bound operations
- Always handle `asyncio.CancelledError` in main loops
- Use `asyncio.create_task()` for background tasks

```python
async def _main_loop(self):
    while self.is_running:
        try:
            await self._update_positions()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Loop error: {e}")
```

### Class Structure

Follow this structure for classes:

```python
class ExampleClass:
    """Class docstring."""
    
    def __init__(self, param1: str, param2: int = 10):
        """Initialize the class."""
        self.param1 = param1
        self.param2 = param2
        self._private_attr = None
    
    def public_method(self) -> None:
        """Public method docstring."""
        pass
    
    def _private_method(self) -> None:
        """Private method docstring."""
        pass
```

---

## Key Patterns

### Creating New Modules

When adding new functionality:

1. Create module in appropriate `src/` subdirectory
2. Add `__init__.py` with exports
3. Follow naming conventions
4. Add tests in `tests/`

### Adding New Trading Tools

For AI agent tools, follow the pattern in `src/agent/tools.py`:

```python
def new_tool(self, param: str) -> str:
    """Tool description for LLM."""
    # Implementation
    return result
```

### Strategy Framework

When creating new strategy-related code:

- Use `TradingStrategy` base class from `src/engine/framework.py`
- Implement `on_bar(bar: BarData) -> str` method
- Use `self.ta()` for pandas_ta indicators (NOT ta-lib)
- Return values: 'buy', 'sell', 'close', 'hold'

```python
from src.engine.framework import TradingStrategy, BarData

class MyStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        rsi = self.ta('RSI', period=14)
        if rsi is None:
            return 'hold'
        if rsi.iloc[-1] < 30:
            return 'buy'
        return 'hold'
```

### Database/Storage

The system uses per-strategy JSON files for persistence in `workspace/`:

| Directory | Description |
|-----------|-------------|
| `strategies/` | Strategy configurations with versioning |
| `positions/` | Position tracking per strategy |
| `orders/` | Order history per strategy |
| `signals/` | Versioned signal records per strategy |
| `performance.json` | Performance data (global) |

#### Per-Strategy Storage Structure

```
workspace/
├── strategies/           # Strategies with versioning
│   ├── TMF260001_v1.json    # New ID format: symbol + YY + 4 digits
│   ├── TMF260001_v2.json
│   └── ...
├── positions/           # Positions per strategy
│   ├── TMF260001_positions.json
│   └── ...
├── orders/             # Orders per strategy
│   ├── TMF260001_orders.json
│   └── ...
├── signals/            # Signals with versioning
│   ├── TMF260001_v1.json
│   ├── TMF260001_v2.json
│   └── ...
└── performance.json
```

#### Strategy ID System

The system uses **auto-generated strategy IDs**:

- **Format**: `{symbol}{YY}{4 digits}` (e.g., `TMF260001`, `TXF260001`, `EFF260001`)
- **Generation**: Automatically generated when creating a strategy via `create_strategy` or `confirm_create_strategy`
- **Symbol exclusivity**: Only ONE enabled strategy per futures code at a time
- **Auto-disable**: When enabling a new strategy version, old versions with the same symbol are automatically disabled

Example flow:
1. User: "幫我設計一個每日賺500元的策略"
2. System asks for futures code (if not provided)
 3. User confirms → Strategy created with auto-generated ID like `TMF260001`
4. System automatically runs two-stage verification
5. User enables → Old MXF strategies auto-disabled → System auto-starts

#### Strategy Verification

When a strategy is created, the system automatically performs **two-stage verification**:

1. **Stage 1: LLM Self-Review** (single attempt)
   - Compares generated code with prompt description
   - Checks if logic correctly implements the strategy
   - If fails: **immediately returns failure** (no auto-retry)

2. **Stage 2: Historical Backtest** (only runs if Stage 1 passes)
   - Uses last 100 K-bars to test the strategy
   - Checks signal distribution (e.g., not all hold, not over-trading)
   - If fails: returns error to user

3. **On failure**: Notifies user with error details and log file link, user must redesign strategy

#### Stage 1 Review Logging (New in v4.6.0)

When Stage 1 verification fails, detailed logs are saved to help diagnose issues:

**Location:** `workspace/logs/stage1_review/`

**File format:** `{StrategyName}_{timestamp}_failed.txt`

**Log contents:**
- Strategy ID and timestamp
- User's original prompt
- Failure reason (from LLM review)
- Suggestion for fixes (from LLM)
- Complete generated code
- Full LLM review response

**Example log file:**
```
================================================================================
STAGE 1 REVIEW FAILED - DETAILED REPORT
================================================================================

Strategy ID: BreakoutStrategy
Timestamp: 2026-03-01 04:02:13
User Prompt: price > 前5根K棒的最高價買進...

================================================================================
FAILURE ANALYSIS
================================================================================

Failure Reason:
策略邏輯未能正確實現突破買入條件...

Suggestion:
建議修改為：high_5 = max(b.high for b in bars[-5:])...

================================================================================
GENERATED CODE
================================================================================

class BreakoutStrategy(TradingStrategy):
    def on_bar(self, bar: BarData) -> str:
        ...

================================================================================
FULL LLM REVIEW RESPONSE
================================================================================

審查結果：不通過
原因：程式碼邏輯錯誤，應該使用 max() 計算5日最高價
修正建議：修改 high_5 的計算方式

================================================================================
END OF REPORT
================================================================================
```

**Purpose:**
- Debug why LLM review failed
- Understand the gap between user intent and generated code
- Improve strategy descriptions based on failure patterns

Only strategies that pass verification can be enabled by users.

#### Strategy States

The system uses **three** state properties:

| State | Property | Description |
|-------|----------|-------------|
| Verified | `verified` | Whether strategy passed two-stage verification |
| Enabled | `enabled` | User-level switch (on/off) |
| Running | `is_running` | System execution state |

- **`verified`**: Set to `True` when strategy passes verification (LLM review + backtest)
- **`enabled`**: Set to `True` when user enables the strategy via `enable <ID>`
- **`is_running`**: Set to `True` when the system actually starts executing the strategy

When a strategy is enabled, the main loop (`run_all_strategies()`) will automatically call `start_strategy()` to:
1. Set `is_running = True`
2. Subscribe to market quotes
3. Begin executing trades

#### Versioning

- **Strategies**: Version increments on prompt update or optimization
- **Signals**: Each strategy version has its own signal file
- **Positions/Orders**: Per-strategy files without versioning

When a strategy is updated (prompt change or optimization), the version increments and new signals are recorded to the new version file.

Use `JSONStore` from `src/storage/json_store.py` for custom storage.

---

## Analysis Module

### Overview

The system includes an `analysis` module for performance tracking and strategy optimization:

```
src/analysis/
├── __init__.py
├── signal_recorder.py       # Records trading signals
├── performance_analyzer.py  # Analyzes strategy performance
└── strategy_reviewer.py    # LLM-based strategy review
```

### BacktestEngine Module

The system includes a `BacktestEngine` module for historical backtesting using backtesting.py:

```
src/engine/
├── backtest_engine.py      # backtesting.py 回測引擎
├── framework.py            # 策略框架 (TradingStrategy)
├── llm_generator.py        # LLM 策略生成器
└── runner.py              # 策略執行協調器
```

#### Timeframe Configuration

The backtest period is determined by the strategy's timeframe:

| Timeframe | Backtest Period | K-bars (approx) | Description |
|-----------|-----------------|-----------------|-------------|
| `1m` | 1 week | ~2,000-2,500 | Minute frequency |
| `5m` | 2 weeks | ~1,000 | Minute frequency |
| `15m` | 1 month | ~600-700 | Minute frequency |
| `30m` | 1 month | ~300-340 | Minute frequency |
| `60m` / `1h` | 3 months | ~1,200-1,400 | Hour frequency |
| `1d` | 1 year | ~250 | Daily frequency |

#### Indicator Integration

The BacktestEngine uses **pandas_ta** for indicator calculation, integrated with backtesting.py:

```
┌─────────────────────────────────────────────────────────┐
│  Data Flow                                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Historical K-bars (Shioaji)                           │
│       ↓                                                 │
│  pandas DataFrame + pandas_ta (calculate indicators)    │
│       ↓                                                 │
│  backtesting.py Strategy uses self.I() to access       │
│       ↓                                                 │
│  backtesting.py Backtest executes strategy → trades    │
│       ↓                                                 │
│  Stats calculate performance                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Process:**
1. Compile and execute strategy code directly (real-time indicator calculation)
2. Strategy's `ta()` method calculates indicators on-demand using full historical DataFrame
3. Create backtesting.py Strategy class that wraps the compiled TradingStrategy
4. Run backtest - strategy calculates indicators in real-time for each bar
5. Output performance report with chart and text analysis

> **Important Change (v4.6.0)**: The backtest engine no longer pre-calculates indicators. Instead, the strategy's `ta()` method calculates indicators on-demand using the full historical DataFrame. This ensures backtest results exactly match live trading behavior.

#### Backtest Metrics Calculation (v4.6.0+)

**Total PnL Calculation:**
```python
# OLD (incorrect): 
# total_pnl = initial_capital * return_pct / 100 * contract_multiplier

# NEW (correct):
equity_final = stats.get('Equity Final [$]', initial_capital)
total_pnl = equity_final - initial_capital  # Actual equity change
```

**Profit Factor Calculation:**
```python
# OLD (incorrect):
# profit_factor = avg_win / avg_loss (using total_pnl)

# NEW (correct):
trades_df = stats._trades
winning_trades = trades_df[trades_df['PnL'] > 0]
losing_trades = trades_df[trades_df['PnL'] < 0]
total_wins = winning_trades['PnL'].sum()
total_losses = abs(losing_trades['PnL'].sum())
profit_factor = total_wins / total_losses
```

#### Usage

```python
from src.engine.backtest_engine import BacktestEngine

# Initialize backtest engine
engine = BacktestEngine(shioaji_client)

# Run backtest
result = await engine.run_backtest(
    strategy_code=strategy_code,
    class_name=class_name,
    symbol="TXF",
    timeframe="15m",
    initial_capital=1_000_000,
    commission=0.0002
)

# Output format
# {
#     "passed": bool,
#     "report": str,           # Formatted report
#     "metrics": {
#         "total_return": float,
#         "sharpe_ratio": float,
#         "sqn": float,
#         "win_rate": float,
#         "trade_count": int,
#         "max_drawdown": float,
#     },
#     "error": str,
# }
```

#### Order Types

| Environment | Order Type | Description |
|--------------|------------|-------------|
| **Backtest** | Market (next bar open) | Simulate market order execution |
| **Live** | MKT + ROD | Market order, rest of day |

### Signal Recording

Use `SignalRecorder` to record trading signals:

```python
from src.analysis.signal_recorder import SignalRecorder
from pathlib import Path

recorder = SignalRecorder(Path("workspace"))

# Record a signal (include strategy version)
signal_id = recorder.record_signal(
    strategy_id="TMF260001",
    strategy_version=2,
    signal="buy",
    price=18500,
    indicators={"rsi": 28.5, "macd": "golden_cross"}
)

# Update result when position is closed
recorder.update_result(
    signal_id=signal_id,
    strategy_id="TMF260001",
    strategy_version=2,
    status="filled",
    exit_price=18600,
    exit_reason="take_profit",
    pnl=6000
)

# Get signals for latest version
signals = recorder.get_signals("TMF260001")

# Get signals for specific version
signals = recorder.get_signals("TMF260001", version=2)

# Archive to new version when strategy is updated
recorder.archive_to_new_version(
    strategy_id="TMF260001",
    old_version=1,
    new_version=2
)
```

### Performance Analysis

Use `PerformanceAnalyzer` to analyze strategy performance:

```python
from src.analysis.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(recorder)

# Get performance report
report = analyzer.format_performance_report("TMF260001", "month")

# Check if goal is achieved
achieved = analyzer.check_goal_achieved(
    goal=500,
    goal_unit="daily",
    period_profit=15000,
    period_days=30
)
```

### Strategy Review (LLM)

Use `StrategyReviewer` for AI-powered strategy analysis:

```python
from src.analysis.strategy_reviewer import StrategyReviewer

reviewer = StrategyReviewer(llm_provider, analyzer)

# Get LLM review
review = reviewer.review("TMF260001", strategy_info)
```

### Strategy Optimization

Use `TradingTools` for self-optimizing strategies:

```python
# Set a goal for the strategy
tools.set_strategy_goal("TMF260001", goal=500, goal_unit="daily")

# Run optimization - checks goal achievement and triggers LLM review if needed
result = tools.optimize_strategy("TMF260001")

# Confirm optimization changes
result = tools.confirm_optimize(confirmed=True)
```

The optimization flow:
1. User sets a numeric goal (goal + goal_unit)
2. Strategy executes and records signals
3. Performance analyzer tracks results
4. If goal not achieved → LLM reviewer analyzes and suggests improvements
5. User confirms changes → strategy is updated with new parameters

### Auto Review Scheduler

Use `AutoReviewScheduler` for automated periodic strategy reviews:

```python
from src.analysis.auto_review_scheduler import AutoReviewScheduler

# Initialize scheduler (typically done in main.py)
scheduler = AutoReviewScheduler(
    config=app_config,
    trading_tools=trading_tools,
    notifier=telegram_notifier
)

# Check and trigger reviews (called in main loop)
scheduler.check_and_trigger()

# Get scheduler status
status = scheduler.get_status()
```

Configuration in `config.yaml`:

```yaml
auto_review:
  enabled: true
  schedules:
    - strategy_id: "TMF260001"
      period: 5
      unit: "day"      # Trigger every 5 days
    - strategy_id: "TXF260001"
      period: 2
      unit: "week"     # Trigger every 2 weeks
```

**Rules**:
- Maximum 1 trigger per strategy per day (scheduled triggers only)
- Manual `review <ID>` commands are not limited
- Strategies without goal are skipped
- Long messages are automatically split for Telegram

---

## New Tool Patterns

- Place tests in `tests/` directory
- Name test files as `test_<module>.py`
- Use descriptive test function names
- Mock external dependencies (Shioaji API, Telegram)

```python
def test_function_name():
    """Test description."""
    # Arrange
    ...
    # Act
    result = function_under_test()
    # Assert
    assert result == expected
```

---

## Security Considerations

- Never commit API keys or secrets
- Use environment variables for sensitive data in production
- Validate all user inputs
- Implement rate limiting for trading operations
- Always use risk checks before executing orders

---

## Important Notes

### LLM Strategy Generation

- The system uses LLM to generate trading strategy code from natural language descriptions
- Generated strategies inherit from `TradingStrategy` base class
- Only `pandas_ta` library is allowed for technical indicators (NOT ta-lib)
- If LLM fails to generate strategy code, the strategy will not execute

### Strategy Prompt Storage

- When a strategy's prompt is modified, the system automatically regenerates the strategy code
- Generated code is stored in per-strategy JSON files (e.g., `workspace/strategies/TMF260001_v1.json`) along with version info
- Strategy ID is auto-generated (format: `{symbol}{YY}{4 digits}`)

### Technical Indicators

Use only `pandas_ta` for technical analysis:

```python
self.ta('RSI', period=14)
self.ta('MACD', fast=12, slow=26, signal=9)
self.ta('BB', period=20, std=2.0)
```

**Important**: `ta()` returns `None` when there is insufficient data (< 2 bars). Always check for `None` before using:

```python
rsi = self.ta('RSI', period=14)
if rsi is None:
    return 'hold'  # Insufficient data, stay on hold
rsi_value = rsi.iloc[-1]
```

### Telegram Notifications

The system includes Telegram notifications for alerts and updates. The bot **only sends notifications** and does **not receive commands** - all user interaction happens through the Web Interface.

```python
from src.notify import TelegramBot

# Initialize with config (bot only sends, does not receive commands)
bot = TelegramBot(
    config={"bot_token": "...", "chat_id": "..."}
)

# Start bot for notifications
await bot.start()

# Stop bot
await bot.stop()
```

**Notification types**:
- Strategy enabled/disabled confirmations
- Risk warnings
- Order execution alerts
- Performance reports
- System status updates

**Note**: Telegram bot does NOT accept commands. Use the Web Interface (http://127.0.0.1:5001) for all operations.

### Goal-Driven Strategy Creation

The system supports two ways to create strategies:

1. **Manual parameters**: Provide all parameters explicitly (name, symbol, prompt, timeframe)
2. **Goal-driven**: User provides a goal (e.g., "make 500 yuan per day"), LLM infers parameters

```python
# Goal-driven creation flow
# 1. User: "design a strategy that makes 500 yuan per day"
# 2. LLM asks for symbol if not provided (TXF, MXF, EFF, etc.)
# 3. LLM infers parameters and shows for confirmation
# 4. User can modify parameters (e.g., "停損改成50點")
# 5. User confirms → strategy created with auto-generated ID (e.g., TMF260001)
```

**Strategy ID is auto-generated**: `{symbol}{YY}{4 digits}` (e.g., `TMF260001`, `TXF260001`)

### Self-Optimizing System

The system supports a self-optimizing loop:

1. User sets a numeric goal (e.g., goal: 500, goal_unit: "daily")
2. Strategy executes and records signals
3. Performance analyzer tracks results
4. LLM reviewer analyzes and suggests improvements
5. User confirms changes → strategy updated

This enables continuous strategy optimization based on performance data.

### Logging

The system uses `loguru` for logging (configured in `src/logger.py`):

- Prevents token leakage in logs (doesn't log httpx requests by default)
- Console output with color coding
- File rotation: 1 day, retention 30 days

### Conversation History

The system maintains conversation history for better LLM context:

- Maximum 20 messages stored
- Cleared via Web Interface "New Conversation" button or system restart
- Used in `llm_process_command()` to provide context

### Delete Strategy

When deleting a strategy, the following files are removed:

| File Type | Location |
|------------|----------|
| Strategy | `workspace/strategies/{id}_v*.json` |
| Positions | `workspace/positions/{id}_positions.json` |
| Orders | `workspace/orders/{id}_orders.json` |
| Signals | `workspace/signals/{id}_v*.json` |

---

## Fallback Command Handling

### Overview

The system implements a **fallback mechanism** to handle basic commands reliably without relying on LLM tool calling. This ensures commands like `enable`, `disable`, `status`, etc. always execute successfully.

### Implementation

The fallback is implemented in `main.py`'s `llm_process_command()` function using regex pattern matching:

```python
# Direct command handling in main.py
enable_match = re.match(r'^enable\s+(\w+)$', command_stripped)
disable_match = re.match(r'^disable\s+(\w+)$', command_stripped)

if enable_match:
    strategy_id = enable_match.group(1).upper()
    result = self.trading_tools.enable_strategy(strategy_id)
    return result
```

### Supported Commands

| Command | Handler | Description |
|---------|---------|-------------|
| `create` | `start_create_flow()` | Q&A style strategy creation |
| `status` | `get_system_status()` | System status |
| `positions` / `部位` / `持倉` | `get_positions()` | Current positions |
| `strategies` / `策略` | `get_strategies()` | All strategies |
| `performance` / `績效` | `get_performance()` | Daily performance |
| `risk` / `風控` / `風險` | `get_risk_status()` | Risk status |
| `orders` / `訂單` | `get_order_history()` | Order history |
| `new` / `新對話` | `clear_history()` | Clear conversation |
| `help` / `幫助` | `show_help()` | Show help |
| `enable <ID>` | `enable_strategy()` | Enable strategy (with position check) |
| `confirm enable <ID>` | `confirm_enable_with_close()` | Confirm enable and close old positions |
| `backtest <ID>` | `backtest_strategy()` | Execute historical backtest (with chart) |
| `disable <ID>` | `disable_strategy()` | Disable strategy |
| `delete <ID>` | `delete_strategy_tool()` | Delete strategy |

### Design Principles

1. **Explicit English commands** → Fallback handles directly
2. **Goal-driven strategy creation** → Pass to LLM
3. **Strategy discussion** → Pass to LLM

### Strategy Modification

**Method 1: Modify parameters during creation**
During goal-driven strategy creation confirmation, user can modify parameters:
- "停損改成50點" (change stop loss to 50 points)
- "止盈改成100點" (change take profit to 100 points)
- "週期改成15m" (change timeframe to 15m)

**Method 2: Modify strategy prompt after creation**
After strategy is created, user can discuss with LLM to modify strategy:
- Discuss strategy logic
- LLM automatically updates prompt and increments version
- Old version signals archived, new version signals recorded

### Advantages

- **Reliability**: Basic commands always execute
- **Speed**: Direct function calls are faster than LLM inference
- **Stability**: Excludes LLM tool calling instability

### Adding New Fallback Commands

To add a new fallback command in `main.py`:

```python
# Add regex pattern matching
new_cmd_match = re.match(r'^newcommand$', command_stripped)

if new_cmd_match:
    result = self.trading_tools.new_command_function()
    self._add_to_history(command, result)
    return result
```

---

## Web Interface (Primary)

### Overview

The **Web Interface is the primary user interaction platform** for managing strategies and positions. All operations including strategy creation, enabling/disabling, backtesting, and position monitoring are done through the web browser.

**Key Points**:
- **Primary Interface**: Web Interface is the main way to interact with the system
- **Telegram**: Only used for notifications, not for commands
- **URL**: `http://127.0.0.1:5001` (port may vary based on configuration)

### Startup

Edit `config.yaml`:

```yaml
web:
  enabled: true
  host: "127.0.0.1"
  port: 5000
```

Then start the system:

```bash
python main.py
```

Access: `http://127.0.0.1:5000`

### Pages

| Page | Function |
|------|----------|
| `/` | System overview |
| `/strategies` | Strategy management (enable/disable/delete/backtest) |
| `/positions` | Position list |

### API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/status` | System status |
| GET | `/api/strategies` | Strategy list |
| POST | `/api/strategies/<id>/enable` | Enable strategy |
| POST | `/api/strategies/<id>/disable` | Disable strategy |
| DELETE | `/api/strategies/<id>` | Delete strategy |
| GET | `/api/positions` | Position list |
| GET | `/api/risk` | Risk status |
| POST | `/api/backtest/<id>` | Run backtest |

#### Backtest API Enhancement (v4.6.0+)

**Response Format:**
```json
{
    "success": true,
    "chart_path": "/workspace/backtests/TMF260001_v1_20260301003042.html",
    "report_path": "/workspace/backtests/TMF260001_v1_20260301003042.txt",
    "report": "📊 歷史回測報告...",
    "metrics": {
        "total_return": -15.23,
        "total_pnl": -152300,
        "trade_count": 367,
        "win_rate": 35.2,
        "profit_factor": 0.85,
        "max_drawdown": -25.6,
        "sharpe_ratio": -1.2
    }
}
```

**New Features:**

1. **Text Report Saving** - Backtest now saves both HTML chart and TXT text report
2. **Dual-Path Return** - `chart_path` for iframe display, `report_path` for text analysis
3. **Enhanced Metrics** - Corrected calculations for total_pnl and profit_factor

#### Backtest Choice Modal

When clicking the backtest button, the system shows a choice modal:

**Scenario A: Existing Report Available**
- Shows latest report timestamp
- Button 1: "📄 View Existing Report" - Opens saved HTML/TXT
- Button 2: "🔄 Run New Backtest" - Re-executes backtest

**Scenario B: No Existing Report**
- Shows "No backtest report found"
- Only option: Run first backtest

**Implementation:**
- Check endpoint: `GET /api/backtest/<id>/check`
- Returns: `has_report`, `chart_path`, `report_path`, `time_ago`

### Modal Confirmation

When **enabling/disabling/deleting** a strategy with positions, the API returns modal confirmation data:

#### Enable Strategy with Existing Positions

When enabling a new strategy, if old strategies with the same symbol have positions:

```json
{
    "needs_confirmation": true,
    "title": "確認啟用",
    "message": "舊策略 MXF260006 仍有 5口 部位",
    "position": {
        "symbol": "MXF",
        "quantity": 5,
        "direction": "Buy",
        "pnl": 1200,
        "entry_price": 18500,
        "current_price": 18740
    },
    "risks": [
        "強制平倉 MXF260006 (5口 MXF)",
        "損益: +1,200",
        "啟用新策略"
    ]
}
```

**Confirmation Flow:**
1. User clicks "Enable" for new strategy
2. System checks if old strategies have positions
3. If yes, returns `needs_confirmation: true`
4. Frontend shows modal with position details and PnL
5. User confirms → DELETE request to `/api/strategies/<id>/enable`
6. System:
   - Places market order to close old positions
   - Records order with reason: "Forced close - enabling new strategy"
   - Disables old strategy
   - Enables new strategy
   - Sends Telegram notification

#### Disable/Delete Strategy with Positions

```json
{
    "needs_confirmation": true,
    "title": "確認停用",
    "message": "此策略仍有部位，停用將強制平倉",
    "risks": ["強制平倉 (1口 TXF)", "策略將被停用"]
}
```

### Design Principles

- **Error Isolation**: Web errors don't affect the main trading system
- **Config-Driven**: Enabled via `config.yaml`

### File Structure

```
src/web/
├── app.py               # Flask application factory
└── routes/
    ├── status.py      # /api/status
    ├── strategies.py  # /api/strategies (含績效數據)
    ├── positions.py    # /api/positions
    ├── orders.py      # /api/orders
    ├── risk.py        # /api/risk
    ├── backtest.py    # /api/backtest
    └── performance.py # /api/performance
```

### Performance Page (v4.6.0+)

The performance page (`/performance`) provides comprehensive strategy performance analysis:

#### Features

1. **Total Performance Section (Top)**
   - Period selector: Today/Week/Month/Quarter/Year/All
   - Statistics cards: Trade count, Win rate, Profit factor, Total PnL
   - Charts: Equity curve (daily aggregation), Trade distribution

2. **Individual Strategy Performance Section**
   - Strategy selector dropdown
   - Individual strategy statistics
   - Individual equity curve and trade distribution charts
   - Exit reason analysis (stop loss/take profit/signal reversal count)

#### Data Source

- Total performance: Merged closed signals from all strategies
- Individual performance: Closed signals from that specific strategy
- Time granularity:
  - Total performance: Daily aggregation (one data point per day)
  - Individual strategy: Per trade (one data point per trade)

#### API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/performance` | Total performance (all strategies) |
| GET | `/api/performance/<id>` | Individual strategy performance |

**Query Parameter**: `period` (today/week/month/quarter/year/all)

### Strategy Creation Page

The strategy creation page (`/strategies/create`) provides a user-friendly interface for creating new trading strategies with two-stage verification.

#### Creation Flow

1. **Parameter Input**
   - Select futures symbol (TXF/MXF/TMF)
   - Select trading direction (long/short/both, default: long)
   - Enter strategy prompt (e.g., "RSI below 30 buy, above 70 sell")
   - Configure timeframe, stop loss, take profit, quantity

2. **Preview Generation**
   - Click "Generate" button to call LLM
   - LLM generates complete strategy description
   - User can review and modify parameters

3. **Confirmation & Verification**
   - Click "Confirm" to generate strategy code
   - **Progress Bar Display**: Shows fake progress animation (timer-based)
     - Step 1 (15%): "🔄 Creating strategy..."
     - Step 2 (35%): "📝 Generating strategy code..."
     - Step 3 (55%): "🔍 LLM reviewing (Stage 1)..."
     - Step 4 (75%): "📊 Backtesting (Stage 2)..."
     - Step 5 (90%): "📈 Finalizing results..."
     - Complete (100%): Shows verification results
   - Two-stage verification (LLM Review + Backtest)
   - Backtest chart and analysis displayed

**Note**: The progress bar uses a **timer-based animation** (not real-time SSE) to provide visual feedback during the potentially long verification process (20-60 seconds). The backend actually performs all verification steps synchronously.

#### API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/strategies/create` | Strategy creation page |
| POST | `/api/strategies/preview` | Generate strategy preview |
| POST | `/api/strategies/confirm` | Confirm and create strategy with verification |

### Template Guidelines

When creating new Web templates, follow these rules to avoid common issues:

> **Summary of Recent Issues (2026-02-28)**:
> 1. Orders page had nested `<script>` tags causing `expected expression, got '<'` error
> 2. Multiple templates declared `const REFRESH_INTERVAL` causing "redeclaration" error  
> 3. Missing `get_by_date` method in OrderStore caused API failure
> 
> **Solution**: 
> - base.html wraps `{% block extra_js %}` inside `<script>`, so child templates should NOT add `<script>` tags
> - Use `var` instead of `const` for REFRESH_INTERVAL in child templates (base.html already defines it)
> - Always test API endpoints independently: `curl http://127.0.0.1:5001/api/orders`

#### 1. JavaScript Block Structure

Always place the closing `</script>` tag **before** `{% endblock %}`:

```html
{% block extra_js %}
<script>
    function myFunction() {
        // code
    }
    
    myFunction();
</script>
{% endblock %}
```

**Wrong** (will cause syntax error):
```html
{% block extra_js %}
<script>
    myFunction();
</script>
{% endblock %}
```

#### 2. Template Inheritance

All pages must extend `base.html`:
```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
<!-- Page content -->
{% endblock %}

{% block extra_js %}
<script>
// JavaScript code
</script>
{% endblock %}
```

#### 3. Common Elements

All templates should have:
- `{% block title %}` - Page title
- `{% block content %}` - Main content
- `{% block extra_js %}` - Page-specific JavaScript

#### 4. Testing New Templates

After creating a new template:
1. Restart the server completely (not hot reload)
2. Check browser's Developer Tools → Console for JavaScript errors
3. Verify template renders correctly by viewing page source

#### 5. Common Errors and Solutions

##### Error 1: Duplicate `const` declarations
**Problem**: Multiple templates declare the same `const` variable, causing "redeclaration of const" error.

**Example** (WRONG - in child template):
```html
{% block extra_js %}
<script>
const REFRESH_INTERVAL = 30000;  // ❌ ERROR: base.html already has this

function loadData() { ... }
loadData();
</script>
{% endblock %}
```

**Solution**:
- Use `var` instead of `const` in child templates
- Or check if variable exists before declaring:
```html
{% block extra_js %}
<script>
if (typeof REFRESH_INTERVAL === 'undefined') {
    var REFRESH_INTERVAL = 30000;
}

function loadData() { ... }
loadData();
</script>
{% endblock %}
```

##### Error 2: Nested `<script>` tags
**Problem**: Child template wraps JS in `<script>` tags while base.html also has `<script>` tags around `{% block extra_js %}`.

**Result**: Generated HTML has nested scripts:
```html
<script>  <!-- base.html -->
    <script>  <!-- child template - SYNTAX ERROR! -->
        function loadData() { ... }
    </script>
</script>
```

**Solution**:
- Remove `<script>` tags from child templates when base.html already wraps the block
- Or move `{% block extra_js %}` outside of `<script>` in base.html

##### Error 3: Missing block structure
**Problem**: Template has content but no `{% block content %}` wrapper.

**Result**: "Unexpected end of template" or "looking for endblock" error.

**Solution**: Always wrap page content:
```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
<!-- All HTML content here -->
{% endblock %}

{% block extra_js %}
<script>
// JavaScript here
</script>
{% endblock %}
```

##### Error 4: Browser console shows "expected expression, got '<'"
**Problem**: Usually caused by nested `<script>` tags or HTML being parsed as JavaScript.

**Debug steps**:
1. Check browser Developer Tools → Elements tab
2. Look for nested `<script>` tags
3. Verify `{% block extra_js %}` content is properly wrapped
4. Ensure `</script>` comes before `{% endblock %}`

##### Error 5: Page stuck on "載入中"
**Problem**: JavaScript error prevents `loadOrders()` or similar function from executing.

**Debug steps**:
1. Check Console for JS errors
2. Verify API endpoint works: `curl http://127.0.0.1:5001/api/orders`
3. Check Network tab for failed requests
4. Look for syntax errors in template-generated JS

#### 6. Template Checklist

Before committing new templates:
- [ ] Extends `base.html`
- [ ] Has `{% block title %}`
- [ ] Has `{% block content %}` wrapping all HTML
- [ ] Has `{% block extra_js %}` (if needed) with `<script>` tags
- [ ] `</script>` comes before `{% endblock %}`
- [ ] No duplicate `const` declarations (use `var` or check `typeof`)
- [ ] No nested `<script>` tags
- [ ] Tested in browser with cleared cache
- [ ] Console shows no errors

#### 7. Best Practices

1. **Always restart server** after template changes (Flask caches templates)
2. **Clear browser cache** when testing (Ctrl+Shift+R)
3. **Use browser Developer Tools** to debug JS errors
4. **Check rendered HTML source** to verify template structure
5. **Test API endpoints independently** before testing pages:
   ```bash
   curl http://127.0.0.1:5001/api/orders
   ```
6. **Add `console.log()`** in JavaScript to trace execution

---

## Version History

### v4.6.1 (2026-03-01)

#### Bug Fixes and Improvements

**1. Daily P&L Display Fix**
- Fixed "當日損益" display to include both realized and unrealized P&L
- Added new `/api/performance` endpoint to calculate comprehensive daily performance metrics
- Frontend now displays breakdown: "已實現: X | 未實現: Y"

**2. Strategy Creation Enhancement**
- Users can now customize strategy name during preview phase
- Strategy naming simplified to unified format: `策略_<symbol>`
- Removed keyword inference logic for name generation
- Preview panel layout aligned with create page (strategy name position adjusted)
- Button text changed from "讓 LLM 填充參數" to "**讓 LLM 設計策略**"

**3. Parameter Validation**
- Quantity validation: Must be >= 1 (returns 400 error if invalid)
- Stop loss / Take profit: Now accepts 0 (disabled) or null (defaults to 0)
- Allows users to create strategies without stop loss / take profit mechanisms

**4. Strategy Direction Bug Fix**
- Fixed bug where `from_dict` method didn't load `direction` field
- Strategies now correctly display their configured direction (long/short/both)

**6. Strategy Verification Flow Simplification**
- Removed unused `max_attempts` parameter from `verify_strategy()` method
- Clarified verification flow: Stage 1 (LLM Review) executes once, fails immediately if unsuccessful
- No automatic retry mechanism - users must redesign strategy if Stage 1 fails
- Updated docstring to clearly document the two-stage verification process

**7. Stage 1 Review Log File Link**
- When Stage 1 verification fails, a detailed log file is saved to `workspace/logs/stage1_review/`
- Frontend now displays a link to open the log file in verification results
- API response includes `stage1_log_file` path for easy debugging

**Files Changed:**
- `src/web/routes/performance.py` (new file)
- `src/web/routes/create.py`
- `src/web/app.py`
- `src/web/templates/index.html`
- `src/web/templates/create_strategy.html`
- `src/trading/strategy.py`
- `src/engine/llm_generator.py`
- `src/agent/tools.py`

### v4.6.0 (Previous)
- Performance analysis page
- Backtest API enhancements
- Stage 1 review logging
- Template guidelines
