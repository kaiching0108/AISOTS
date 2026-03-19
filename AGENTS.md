# AI Futures Trading System - Agent Guidelines

**Version**: 0.6.0

## Overview

AI-powered futures trading system using Shioaji API (Taiwan Futures Exchange). Supports multiple trading strategies, risk management, Web Interface, and Telegram notifications.

## Project Structure

```
AISOTS/
├── main.py                 # Entry point
├── config.yaml            # Configuration
├── src/
│   ├── api/              # Shioaji API wrappers
│   ├── trading/          # Trading logic
│   ├── engine/           # Strategy execution engine
│   ├── analysis/         # Performance analysis
│   ├── storage/          # Data persistence (JSON, SQLite)
│   ├── services/         # Background services
│   ├── agent/            # AI agent tools
│   ├── notify/           # Telegram notifications
│   └── web/              # Web Interface (Flask)
├── tests/                 # Test files
└── workspace/            # Runtime data
```

---

## Build / Lint / Test Commands

```bash
# Install
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run
python main.py              # Development
python main.py --simulate   # Simulation mode

# Test
pytest tests/test_trading.py::test_risk_manager  # Single test (key command)
pytest tests/test_trading.py        # Single file
pytest -v                           # Verbose
pytest --cov=src --cov-report=html  # Coverage

# Lint
mypy src/ --ignore-missing-imports  # Type check
black src/ tests/ main.py           # Format
```

---

## Code Style Guidelines

- **Language**: Python 3.10+ | **Encoding**: UTF-8 | **Line Length**: Max 120 | **Indentation**: 4 spaces

### Import Order

```python
# Standard library
import asyncio
import logging
from pathlib import Path

# Third-party
import shioaji as sj
from pydantic import BaseModel

# Local application
from src.config import load_config
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `StrategyManager` |
| Functions/methods | snake_case | `get_positions()` |
| Variables | snake_case | `position_manager` |
| Constants | UPPER_SNAKE | `MAX_POSITION = 10` |
| Private methods | `_` prefix | `_setup_logging()` |

### Type Hints

```python
def get_position(self, strategy_id: str) -> Optional[Position]:
    pass
```

### Error Handling

```python
try:
    result = self.api.place_order(contract, order)
except Exception as e:
    logger.error(f"Order placement failed: {e}")
    return None
```

### Async/Await

Use `async`/`await` for I/O. Handle `asyncio.CancelledError`. Use `asyncio.create_task()`.

---

## Key Patterns

### Strategy Framework

```python
from src.engine.framework import TradingStrategy, BarData

class MyStrategy(TradingStrategy):
    def on_bar(self, bar: BarData) -> str:
        rsi = self.ta('RSI', period=14)
        if rsi is None:
            return 'hold'
        if rsi.iloc[-1] < 30:
            return 'buy'
        return 'hold'
```

**Important**: Use `self.ta()` for pandas_ta (NOT ta-lib). Return: 'buy', 'sell', 'close', 'hold'. Check for `None`.

### Strategy ID

- **Format**: `{symbol}{YY}{4 digits}` (e.g., `TMF260001`)
- Only ONE enabled per futures code
- Auto-disable old versions when enabling new

---

## Analysis Module

### Backtest Engine

```python
from src.engine.backtest_engine import BacktestEngine

engine = BacktestEngine(shioaji_client)
result = await engine.run_backtest(
    strategy_code=strategy_code,
    class_name=class_name,
    symbol="TXF",
    timeframe="15m",
    initial_capital=1_000_000,
    commission=0.0002
)
```

### Signal Recording

```python
from src.analysis.signal_recorder import SignalRecorder

recorder = SignalRecorder(Path("workspace"))
signal_id = recorder.record_signal(
    strategy_id="TMF260001",
    strategy_version=2,
    signal="buy",
    price=18500
)
```

---

## Important Notes

Use the Read tool first before overwriting it

### Technical Indicators

Use only `pandas_ta`. `ta()` returns `None` when < 2 bars:

```python
rsi = self.ta('RSI', period=14)
if rsi is None:
    return 'hold'
```

### Shioaji API Timestamp Format

Shioaji API 返回的 timestamp 為**奈秒（nanoseconds）**格式，儲存到 SQLite 時需轉換為**秒（seconds）**：

```python
# 奈秒 → 秒轉換
ts_sec = ts // 1_000_000_000 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts)

# 完整範例
ts_list = list(kbars_raw.ts)
kbars_data = {
    "ts": [ts // 1_000_000_000 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts) for ts in ts_list],
    "open": list(kbars_raw.Open),
    "high": list(kbars_raw.High),
    "low": list(kbars_raw.Low),
    "close": list(kbars_raw.Close),
    "volume": list(kbars_raw.Volume),
}
```

### K-bar Data Fetching

系統有兩種 K-bars 資料來源：

1. **Initial Fetch（歷史補抓）**：系統啟動時，從最舊資料往更早時間填補歷史缺口（`source='initial'`）
2. **Recovery（當日補抓）**：系統啟動或斷線重連後，從 Shioaji API 補抓當日 00:00 到 now 的所有 K-bars（`source='recovery'`）

**觸發時機**：
- 系統啟動時 → `check_and_update_on_login()` → `fetch_today()`
- 斷線重連後 → `_on_reconnected()` → `fetch_today()`
- 實盤 Realtime → `RealtimeKBarAggregator` 每分鐘寫入（`source='realtime'`）

**Recovery 不消耗配額**：不寫入 `fetch_log`，直接覆蓋當日所有資料。

### Shioaji API

- `timeout` 參數單位為**毫秒**，預設 5000（5 秒）
- 使用 `on_seqno_assigned` 回調解決 race condition

### LLM Strategy Generation

- Generated strategies inherit from `TradingStrategy`
- Only `pandas_ta` allowed
- Two-stage verification: LLM Review + Backtest

### SQLite

See [SQLite_Storage.md](documents/SQLite_Storage.md) for Kbar data storage & query rules.

### Web Interface

Primary user platform. See `documents/Web_Interface.md` for details.

### Fallback Commands

| Command | Handler |
|---------|---------|
| `status` | `get_system_status()` |
| `positions` | `get_positions()` |
| `enable <ID>` | `enable_strategy()` |
| `backtest <ID>` | `backtest_strategy()` |

---

## Security

- Never commit API keys/secrets
- Use environment variables
- Validate user inputs
- Always use risk checks before executing orders

---

## Documentation

See `documents/`:
- `Web_Interface.md` - Web interface & API
- `System_Architecture.md` - Architecture
- `User_Manual.md` - User manual
- `Features.md` - Features

## Shioaji - Taiwan's Leading Cross Platform Trading API
See `Shioaji_Docs/`:
- `llms.txt - Usage documentation Subject list 
- `llms-full.txt - Full Detail Usage Document
