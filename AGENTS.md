# AI Futures Trading System - Agent Guidelines

## Overview

This is an AI-powered futures trading system using Shioaji API (Taiwan Futures Exchange), with support for multiple trading strategies, risk management, Telegram notifications, and LLM-based strategy generation.

## Project Structure

```
ai_futures_trading/
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
│   └── notify/           # Telegram notifications & bot
├── tests/                 # Test files
├── workspace/            # Runtime data (JSON files)
└── documents/            # Documentation
```

---

## Build / Lint / Test Commands

### Installation

```bash
cd ai_futures_trading
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Running the Application

```bash
# Run in development
python main.py

# Run in simulation mode (skip Shioaji API login, for testing)
python main.py --simulate

# Or with specific config
python main.py --config config.yaml

# Simulation + CLI mode
python main.py --simulate --cli
```

### Simulation Mode

Using `--simulate` flag:
- Skips Shioaji API login
- Simulated orders fill immediately
- Simulated positions and PnL are tracked
- Suitable for development and testing

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
│   ├── MXFA01_v1.json    # New ID format: symbol + 3 random chars
│   ├── MXFA01_v2.json
│   └── ...
├── positions/           # Positions per strategy
│   ├── MXFA01_positions.json
│   └── ...
├── orders/             # Orders per strategy
│   ├── MXFA01_orders.json
│   └── ...
├── signals/            # Signals with versioning
│   ├── MXFA01_v1.json
│   ├── MXFA01_v2.json
│   └── ...
└── performance.json
```

#### Strategy ID System

The system uses **auto-generated strategy IDs**:

- **Format**: `{FuturesCode}{3 random chars}` (e.g., `MXFA01`, `TXFZZZ`, `EFF12X`)
- **Generation**: Automatically generated when creating a strategy via `create_strategy` or `confirm_create_strategy`
- **Symbol exclusivity**: Only ONE enabled strategy per futures code at a time
- **Auto-disable**: When enabling a new strategy version, old versions with the same symbol are automatically disabled

Example flow:
1. User: "幫我設計一個每日賺500元的策略"
2. System asks for futures code (if not provided)
3. User confirms → Strategy created with auto-generated ID like `MXFA01`
4. User enables → Old MXF strategies auto-disabled → System auto-starts → Strategy code generated

#### Strategy States

The system uses two state properties:

| State | Property | Description |
|-------|----------|-------------|
| Enabled | `enabled` | User-level switch (on/off) |
| Running | `is_running` | System execution state |

- **`enabled`**: Set to `True` when user enables the strategy via `enable <ID>`
- **`is_running`**: Set to `True` when the system actually starts executing the strategy (generates code, subscribes to market data, begins trading)

When a strategy is enabled but not yet running, the main loop (`run_all_strategies()`) will automatically call `start_strategy()` to:
1. Set `is_running = True`
2. Generate strategy code via LLM
3. Subscribe to market quotes
4. Begin executing trades

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

### Signal Recording

Use `SignalRecorder` to record trading signals:

```python
from src.analysis.signal_recorder import SignalRecorder
from pathlib import Path

recorder = SignalRecorder(Path("workspace"))

# Record a signal (include strategy version)
signal_id = recorder.record_signal(
    strategy_id="MXFA01",
    strategy_version=2,
    signal="buy",
    price=18500,
    indicators={"rsi": 28.5, "macd": "golden_cross"}
)

# Update result when position is closed
recorder.update_result(
    signal_id=signal_id,
    strategy_id="MXFA01",
    strategy_version=2,
    status="filled",
    exit_price=18600,
    exit_reason="take_profit",
    pnl=6000
)

# Get signals for latest version
signals = recorder.get_signals("MXFA01")

# Get signals for specific version
signals = recorder.get_signals("MXFA01", version=2)

# Archive to new version when strategy is updated
recorder.archive_to_new_version(
    strategy_id="MXFA01",
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
report = analyzer.format_performance_report("MXFA01", "month")

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
review = reviewer.review("MXFA01", strategy_info)
```

### Strategy Optimization

Use `TradingTools` for self-optimizing strategies:

```python
# Set a goal for the strategy
tools.set_strategy_goal("MXFA01", goal=500, goal_unit="daily")

# Run optimization - checks goal achievement and triggers LLM review if needed
result = tools.optimize_strategy("MXFA01")

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
    - strategy_id: "MXFA01"
      period: 5
      unit: "day"      # Trigger every 5 days
    - strategy_id: "TXF001"
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
- Generated code is stored in per-strategy JSON files (e.g., `workspace/strategies/MXFA01_v1.json`) along with version info
- Strategy ID is auto-generated (format: `{symbol}{3 random chars}`)

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

### Telegram Bot

The system includes a Telegram bot for receiving user commands:

```python
from src.notify import TelegramBot

# Initialize with config and command handler
bot = TelegramBot(
    config={"bot_token": "...", "chat_id": "..."},
    command_handler=llm_process_command
)

# Start bot
await bot.start()

# Stop bot
await bot.stop()
```

The bot supports commands: `/start`, `/help`, `/new`, and text messages forwarded to the LLM.

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
# 5. User confirms → strategy created with auto-generated ID (e.g., MXFA01)
```

**Strategy ID is auto-generated**: `{symbol}{3 random chars}` (e.g., `MXFA01`, `TXFZZZ`)

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
- Cleared via Telegram `/new` command
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
| `status` | `get_system_status()` | System status |
| `positions` / `部位` / `持倉` | `get_positions()` | Current positions |
| `strategies` / `策略` | `get_strategies()` | All strategies |
| `performance` / `績效` | `get_performance()` | Daily performance |
| `risk` / `風控` / `風險` | `get_risk_status()` | Risk status |
| `orders` / `訂單` | `get_order_history()` | Order history |
| `new` / `新對話` | `clear_history()` | Clear conversation |
| `help` / `幫助` | `show_help()` | Show help |
| `enable <ID>` | `enable_strategy()` | Enable strategy |
| `disable <ID>` | `disable_strategy()` | Disable strategy |

### Design Principles

1. **Simple, explicit commands** → Fallback handles directly
2. **Complex natural language** → Pass to LLM (e.g., creating strategies)

### Advantages

- **Reliability**: Basic commands always execute
- **Speed**: Direct function calls are faster than LLM inference
- **Fault tolerance**: Complex commands still handled by LLM

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
