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
│   ├── market/           # Market data services
│   ├── risk/             # Risk management
│   ├── storage/          # JSON data persistence
│   ├── agent/            # AI agent tools and LLM providers
│   └── notify/           # Telegram notifications
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

# Or with specific config
python main.py --config config.yaml
```

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

The system uses JSON files for persistence in `workspace/`:

- `strategies.json` - Strategy configurations (including LLM-generated code)
- `positions.json` - Position tracking
- `orders.json` - Order history
- `performance.json` - Performance data

Use `JSONStore` from `src/storage/json_store.py` for custom storage.

---

## Testing Guidelines

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
- Generated code is stored in `strategies.json` along with version info

### Technical Indicators

Use only `pandas_ta` for technical analysis:

```python
self.ta('RSI', period=14)
self.ta('MACD', fast=12, slow=26, signal=9)
self.ta('BB', period=20, std=2.0)
```
