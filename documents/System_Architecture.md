# AI 期貨交易系統 - 系統架構說明

## 1. 系統概述

### 1.1 系統目標

本系統是一個基於 AI Agent 的期貨自動交易系統，透過永豐期貨 Shioaji API 進行交易，並整合 LLM 大語言模型實現自然語言交易操作與策略生成。

### 1.2 技術堆疊

| 層面 | 技術 |
|------|------|
| 交易 API | Shioaji (永豐期貨) |
| 程式語言 | Python 3.10+ |
| AI Agent | Nanobot 架構概念 |
| LLM | OpenRouter / OpenAI / Anthropic / DeepSeek / Ollama (本地) |
| 技術指標 | pandas_ta |
| 通知 | Telegram Bot |
| 資料儲存 | JSON 檔案 |

---

## 2. 系統架構圖

### 2.1 整體架構 (8層)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Layer (用戶層)                          │
│                  Telegram / Command Line                             │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent Layer (AI Agent 層)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Trading Tools  │  │ System Prompt   │  │  LLM Provider   │    │
│  │  - place_order  │  │                 │  │                 │    │
│  │  - get_position│  │  交易規則       │  │  GPT/Claude     │    │
│  │  - get_perform │  │ 策略定義       │  │  DeepSeek       │    │
│  │  - 自動生成ID  │  │ 對話歷史       │  │  Ollama         │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Engine Layer (引擎層) - 策略執行                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ LLM Generator   │  │ TradingStrategy │  │ StrategyExecutor│    │
│  │  策略代碼生成   │  │    策略框架     │  │   策略執行器     │    │
│  │  (自由格式)     │  │ (TradingStrategy)│ │                 │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Business Layer (業務層)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Strategy Manager│  │ Position Manager│  │  Order Manager  │      │
│  │   管理多策略     │  │  按策略分開部位  │  │    訂單管理     │      │
│  │  (自動生成ID)   │  │                 │  │                 │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent Layer (AI Agent 層)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Trading Tools  │  │ System Prompt   │  │  LLM Provider   │    │
│  │  - place_order  │  │                 │  │                 │    │
│  │  - get_position│  │  交易規則       │  │  GPT/Claude     │    │
│  │  - get_perform │  │  策略定義       │  │  DeepSeek       │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Engine Layer (引擎層) - 策略執行                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ LLM Generator   │  │ TradingStrategy │  │ StrategyExecutor│    │
│  │  策略代碼生成   │  │    策略框架     │  │   策略執行器     │    │
│  │  (自由格式)     │  │ (TradingStrategy)│ │                 │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Business Layer (業務層)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │ Strategy Manager│  │ Position Manager│  │  Order Manager  │      │
│  │   管理3個策略    │  │  按策略分開部位  │  │    訂單管理     │      │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Risk Layer (風控層)                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Risk Manager                             │    │
│  │  - 單日最大虧損檢查  - 最大部位檢查   - 頻率限制           │    │
│  │  - 停損止盈監控     - 異常訂單檢查                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Adapter Layer (適配層)                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │ Shioaji Client  │  │ Connection Mgr   │  │ Order Callback  │    │
│  │                 │  │  斷線重連機制    │  │                 │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API Layer (Shioaji API)                         │
│                    永豐期貨 API                                     │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Market Data (市場)                                │
│                    期貨交易所                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Fallback 命令處理機制

系統在 Agent Layer 和 LLM 之間實現了 **Fallback 機制**：

```
User Command
     │
     ▼
┌─────────────────────────┐
│  Regex Pattern Match   │
└──────────┬────────────┘
           │
     ┌─────┴─────┐
    是          否
     │           │
     ▼           ▼
┌─────────┐  ┌─────────────────┐
│ 直接    │  │  LLM 處理      │
│ 函式    │  │  (自然語言)    │
│ 調用    │  └─────────────────┘
└─────────┘
```

**支援的命令**：`status`, `positions`, `strategies`, `performance`, `risk`, `orders`, `enable <ID>`, `disable <ID>`, `new`, `help`

**直接處理的輸入**：
- 確認關鍵詞：「確認」「OK」「好」→ 直接建立策略
- 期貨代碼：直接回覆 TXF/MXF/TMF → 繞過 LLM 直接建立策略

**優勢**：確保基本命令 100% 執行成功，響應速度更快，使用體驗更佳

### 2.3 Telegram Markdown 清理機制

系統在發送訊息到 Telegram 前，自動清理 Markdown 格式：

| 項目 | 處理方式 |
|------|----------|
| 粗體 **text** | 移除 ** 標記 |
| 斜體 *text* | 移除 * 標記 |
| 標題 ### | 移除 # 標記 |
| 表格 | 轉換為清單格式 |
| 分隔線 --- | 改為 ───────────── |

### 2.4 策略執行流程

```
用戶策略描述
     │
     ▼
┌─────────────────┐
│ LLM Generator   │ ◄─── 將描述轉換為策略程式碼
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Strategy Class  │ ◄─── 繼承 TradingStrategy
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ StrategyExecutor│ ◄─── 執行策略的 on_bar()
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│ buy   │ │ sell  │
│ close │ │ hold  │
└───────┘ └───────┘
```

### 2.3 數據流向圖

```
用戶指令 (Telegram)
      │
      ▼
┌─────────────────┐
│  Agent Loop     │ ◄─── LLM 分析用戶意圖
└────────┬────────┘
          │
          ▼
┌─────────────────┐
│  Tool 選擇      │ ◄─── 根據意圖選擇工具
└────────┬────────┘
          │
     ┌────┴────┐
     │         │
     ▼         ▼
 ┌───────┐ ┌───────┐
 │ 風控  │ │ 交易  │
 │ 檢查  │ │ 執行  │
 └───┬───┘ └───┬───┘
     │         │
     │    ┌────┴────┐
     │    │         │
     ▼    ▼         ▼
 ┌─────────┐  ┌─────────┐
 │ 、風控阻擋 │  │ Shioaji│
 └─────────┘  │  API   │
              └────────┘
```

---

## 3. 核心模組說明

### 3.1 API 層 (src/api/)

| 檔案 | 說明 |
|------|------|
| `shioaji_client.py` | Shioaji API 封裝，包含登入、下單、取得部位等 |
| `connection.py` | 連線管理，自動重連機制 |
| `order_callback.py` | 訂單/報價回調處理 |

### 3.2 交易層 (src/trading/)

| 檔案 | 說明 |
|------|------|
| `strategy.py` | 策略類別 (含 LLM 生成程式碼欄位) |
| `strategy_manager.py` | 策略管理器，管理3個策略 |
| `position.py` | 部位類別 |
| `position_manager.py` | 部位管理器，按策略分開追蹤 |
| `order.py` | 訂單類別 |
| `order_manager.py` | 訂單管理器 |

### 3.3 引擎層 (src/engine/)

| 檔案 | 說明 |
|------|------|
| `framework.py` | 策略框架 (TradingStrategy, StrategyExecutor) |
| `llm_generator.py` | LLM 策略生成器 |
| `runner.py` | 策略執行協調器 |

### 3.4 市場數據層 (src/market/)

| 檔案 | 說明 |
|------|------|
| `price_cache.py` | 價格快取 |
| `data_service.py` | 市場資料服務 |

### 3.5 風控層 (src/risk/)

| 檔案 | 說明 |
|------|------|
| `risk_manager.py` | 風控檢查、停損止盈監控 |

### 3.6 通知層 (src/notify/)

| 檔案 | 說明 |
|------|------|
| `telegram.py` | Telegram 機器人通知 |

### 3.7 Agent 層 (src/agent/)

| 檔案 | 說明 |
|------|------|
| `tools.py` | AI Agent 交易工具集 (含策略管理工具) |
| `prompts.py` | 系統提示詞 |
| `providers.py` | LLM 提供者 (Ollama/OpenAI/Anthropic/DeepSeek/OpenRouter) |

#### Agent Tools 一覽

| Tool 名稱 | 功能 |
|-----------|------|
| `create_strategy` | 建立新策略 |
| `update_strategy_prompt` | 更新策略描述 |
| `delete_strategy` | 刪除策略 |
| `enable_strategy` | 啟用策略 |
| `disable_strategy` | 停用策略 |
| `place_order` | 手動下單 |
| `close_position` | 平倉 |
| `get_positions` | 取得部位 |
| `get_strategies` | 取得策略列表 |
| `get_performance` | 取得績效 |

---

## 4. 策略框架說明

### 4.1 TradingStrategy 抽象類別

所有 LLM 生成的策略必須繼承 `TradingStrategy`：

```python
from src.engine.framework import TradingStrategy, BarData

class MyStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        # 策略邏輯
        return 'hold'  # 或 'buy', 'sell', 'close'
```

### 4.2 BarData（K棒資料）

| 屬性 | 說明 |
|------|------|
| `bar.timestamp` | 時間戳 |
| `bar.open` | 開盤價 |
| `bar.high` | 最高價 |
| `bar.low` | 最低價 |
| `bar.close` | 收盤價 |
| `bar.volume` | 成交量 |
| `bar.pct_change` | 漲跌幅（小數，如 0.05 代表 5%） |
| `bar.get_change_from(price)` | 相對於某價格的漲跌幅 |

### 4.3 FillData（成交回報）

| 屬性 | 說明 |
|------|------|
| `fill.symbol` | 合約代碼 |
| `fill.side` | 買賣方向 ('buy' 或 'sell') |
| `fill.price` | 成交價格 |
| `fill.quantity` | 成交數量 |
| `fill.timestamp` | 成交時間 |

### 4.4 可用屬性

| 屬性 | 說明 |
|------|------|
| `self.position` | 當前部位 (正=多單，負=空單，0=無部位) |
| `self.entry_price` | 進場價格 |
| `self.context` | 字典，可儲存自定義狀態 |
| `self.symbol` | 合約代碼 |

### 4.5 可用方法

| 方法 | 說明 |
|------|------|
| `self.get_bars(n)` | 取得最近 n 根 K 棒 |
| `self.get_dataframe(n)` | 取得 pandas DataFrame |
| `self.ta(指標, **參數)` | 使用 pandas_ta 計算技術指標 |
| `self.on_fill(fill)` | 成交回調（可選實作） |

> **注意**：當 K 棒數據不足（少於 2 根）時，`ta()` 回傳 `None`。策略應檢查返回值是否為 `None` 再使用。
> 
> ```python
> rsi = self.ta('RSI', period=14)
> if rsi is None:
>     return 'hold'  # 數據不足時保持觀望
> rsi_value = rsi.iloc[-1]
> ```

### 4.6 pandas_ta 支援的指標

| 指標 | 說明 | 參數 |
|------|------|------|
| RSI | 相對強弱指標 | period=14 |
| MACD | 指數平滑異同移動平均線 | fast=12, slow=26, signal=9 |
| SMA | 簡單移動平均 | period=20 |
| EMA | 指數移動平均 | period=20 |
| BB | 布林帶 | period=20, std=2.0 |
| ATR | 平均真實波幅 | period=14 |
| STOCH | KD 指標 | period=14 |
| ADX | 平均趨向指標 | period=14 |
| CCI | 商品通道指標 | period=20 |
| OBV | 能量潮 | - |
| VWAP | 成交量加權平均價 | - |
| WILLR | 威廉指標 | period=14 |

### 4.7 on_bar 回傳值

| 回傳值 | 動作 |
|--------|------|
| `'buy'` | 買進開多 |
| `'sell'` | 賣出開空 |
| `'close'` | 平倉 |
| `'hold'` | 無動作 |

### 4.8 策略程式碼範例

```python
from src.engine.framework import TradingStrategy, BarData

class RSIStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        rsi = self.ta('RSI', period=14)
        if rsi is None:
            return 'hold'
        
        rsi_value = rsi.iloc[-1]
        
        if rsi_value < 30 and self.position == 0:
            return 'buy'
        elif rsi_value > 70 and self.position > 0:
            return 'sell'
        elif self.position > 0:
            # 有部位時檢查是否該停損/止盈
            pnl_pct = (bar.close - self.entry_price) / self.entry_price
            if pnl_pct < -0.02:  # 停損 2%
                return 'close'
        
        return 'hold'
```

### 4.9 策略執行流程

LLM 生成策略程式碼後，盯盤執行由以下元件負責：

| 元件 | 檔案 | 職責 |
|------|------|------|
| `StrategyRunner` | `runner.py` | 策略執行協調器 |
| `StrategyExecutor` | `framework.py` | 實際執行策略訊號 |

#### 執行流程

```
LLM 生成策略程式碼
       ↓
StrategyRunner.start_strategy()  ← 啟動策略
       ↓
StrategyRunner._create_executor()  ← 建立 StrategyExecutor
       ↓
StrategyRunner.run_all_strategies()  ← 每 60 秒執行
       ↓
StrategyRunner.execute_strategy()
       ↓
StrategyRunner.execute_strategy_llm()
       ↓
StrategyExecutor.execute_bar(bar)  ← 將 K 棒傳入策略
       ↓
TradingStrategy.on_bar(bar)  ← 策略邏輯產生訊號
       ↓
回傳 'buy'/'sell'/'close'/'hold'
```

#### 關鍵程式碼位置

| 功能 | 行號 |
|------|------|
| 執行所有策略循環 | `runner.py:428` (`run_all_strategies`) |
| 建立執行器 | `runner.py:285` (`_create_executor`) |
| 執行策略訊號 | `runner.py:313` (`execute_strategy_llm`) |
| 執行 K 棒 | `framework.py:216` (`execute_bar`) |

#### 執行週期

- `run_all_strategies()` 每 **60 秒**（可配置）執行一次
- 檢查所有 `enabled` 且 `is_running` 的策略
- 將最新 K 棒傳入 `StrategyExecutor.execute_bar()`
- 策略產生訊號後，透過 `on_signal` callback 處理下單

### 4.10 K Bar 資料取得

#### 資料來源

| 來源 | 檔案/方法 | 說明 |
|------|----------|------|
| 歷史 K 線 | `shioaji_client.py:get_kbars()` | 呼叫 Shioaji API 取得歷史 K 棒 |
| 實時報價 | `shioaji_client.py:subscribe_quote()` | 訂閱合約即時報價 |

#### 取得流程

```
1. 策略啟動時
   │
   ▼
Runner.ensure_sufficient_data()
   │
   ▼
MarketDataService.fetch_historical(symbol, timeframe, count)
   │
   ▼
ShioajiClient.get_kbars(contract, timeframe, count)
   │
   ▼
api.kbars(contract)  ← Shioaji API 取得真實 K 線
   │
   ▼
回傳 K 棒列表 [{timestamp, open, high, low, close, volume}, ...]
```

#### 關鍵程式碼位置

| 功能 | 位置 |
|------|------|
| 取得 K 線 | `shioaji_client.py:152` (`get_kbars`) |
| Shioaji API 呼叫 | `shioaji_client.py:158` |
| 歷史資料取得 | `data_service.py:131` (`fetch_historical`) |
| 報價訂閱 | `data_service.py:22` (`subscribe`) |
| 價格快取 | `price_cache.py:44` (`PriceCache`) |

#### 模擬 vs 非模擬

| 模式 | 資料來源 |
|------|----------|
| 模擬 (`simulation: true`) | `_generate_mock_kbars()` 產生模擬資料 |
| 非模擬 | `api.kbars(contract)` 取得真實市場資料 |

---
#### 實時報價處理
1. 透過 subscribe_quote() 訂閱合約報價
2. 報價資料存入 PriceCache
3. StrategyRunner 定時取得最新報價轉換為 K 棒
4. 傳入 StrategyExecutor.execute_bar() 執行策略

#### Timeframe 處理

- 策略啟動時從 `strategy.params.timeframe` 讀取週期參數
- `get_kbars(contract, timeframe, count)` 取得該週期 K 棒
- 由於設計上每個 symbol 同時只有一個策略，採用 `market_data_cache[symbol]` 儲存，不會有衝突

### 4.11 MarketData 快取架構

#### 兩套快取系統

```
┌─────────────────────────────────────────────────────────────────┐
│                        Shioaji API                              │
│                  (真實市場報價 / 歷史K棒)                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────┐    ┌───────────────────────────────┐
│   MarketDataService     │    │      StrategyRunner            │
│   (price_cache)         │    │   (market_data_cache)          │
│   - 最新價格快取        │    │   - K棒歷史資料               │
└──────────────────────────┘    └───────────────────────────────┘
```

| 快取 | 位置 | 用途 | 資料來源 |
|------|------|------|----------|
| `price_cache` | `data_service.py` | 價格快取 | 即時報價 |
| `market_data_cache` | `runner.py` | K棒快取 | 歷史K棒 + 即時報價 |

#### MarketData 資料結構

```python
class MarketData:
    symbol: str                           # 期貨代碼
    timestamps: List[datetime]            # 時間序列
    open_prices: List[float]              # 開盤價
    high_prices: List[float]              # 最高價
    low_prices: List[float]               # 最低價
    close_prices: List[float]             # 收盤價
    volumes: List[float]                  # 成交量
    current_price: float                  # 最新價格
```

#### 快取運作流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 策略啟動時 (start_strategy)                              │
│    ensure_sufficient_data()                                │
│    → get_kbars() 取得歷史K棒                               │
│    → update_market_data() 存入快取                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. 即時報價 (subscribe_quote)                              │
│    → 價格更新觸發 update_market_data()                     │
│    → 新tick寫入快取，維持最多500根K棒                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 每60秒執行 (run_all_strategies)                        │
│    execute_strategy_llm()                                  │
│    → 從 market_data_cache[symbol] 取最新K棒              │
│    → 傳入 StrategyExecutor.execute_bar()                 │
└─────────────────────────────────────────────────────────────┘
```

#### 關鍵方法

| 方法 | 行號 | 功能 |
|------|------|------|
| `update_market_data()` | `runner.py:393` | 更新 K 棒到快取 |
| `ensure_sufficient_data()` | `runner.py:55` | 確保有足夠歷史資料 |
| `get_market_data()` | `runner.py:424` | 取得某 symbol 的 MarketData |

#### 快取維護

- 最多保留 **500 根** K 棒
- 超過自動截斷舊資料 (`runner.py:414-422`)

### 4.12 策略程式碼驗證流程

#### 驗證流程概述

策略建立時，系統會自動執行兩階段驗證，確保策略程式碼符合 prompt 描述且可正常執行。

```
策略建立
     │
     ▼
┌──────────────────┐
│ Stage 1:        │
│ LLM 自我審查    │ ◄─── 最多 3 次
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
  通過      失敗
    │         │
    ▼         ▼
 Stage 2    重新修正（回到 Stage 1）
             │
             │ (3次後仍失敗)
             ▼
         通知用戶 + 修正建議
             │
             ▼
        用戶重新建立策略
```

#### Stage 1: LLM 自我審查

| 項目 | 內容 |
|------|------|
| **重試次數** | 最多 3 次 |
| **審查內容** | 比對程式碼與原始 prompt 描述 |
| **審查標準** | 程式碼邏輯是否正確實現策略描述、訊號判斷條件是否正確 |
| **失敗處理** | 重新修正程式碼，回到 Stage 1 |
| **3 次失敗** | 通知用戶 + 修正建議，用戶需重新建立策略 |

#### Stage 2: 歷史 K 棒回測

| 項目 | 內容 |
|------|------|
| **測試資料** | 最近 100 根 K 棒 |
| **異常判斷** | 見下表 |

| 異常條件 | 說明 |
|---------|------|
| buy + sell > 50% | 交易過於頻繁 |
| 全是 hold | 策略從未產生訊號 |
| buy/sell 比例失衡 | 如 100 次訊號全是 buy |
| 執行期 exception | 策略執行出錯 |

| 失敗處理 | 退回 Stage 1 重新執行 |

#### 策略模型新增欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `verified` | bool | 是否已通過驗證 |
| `verification_status` | str | 驗證狀態：'pending', 'passed', 'failed' |
| `verification_error` | str | 驗證失敗原因 |
| `verification_attempts` | int | 驗證嘗試次數 |
| `verified_at` | datetime | 驗證通過時間 |

#### Enable 策略邏輯

```
enable_strategy()
     │
     ├── 檢查策略是否存在
     │
     ├── 檢查是否已通過驗證
     │     ├── 已驗證 → 允許 enable
     │     └── 未驗證/失敗 → 拒絕 enable，顯示原因
     │
     └── enable 策略
```

---

## 6. 部署架構

### 6.1 單機部署

```
┌─────────────────────────────────────┐
│           Linux / Windows           │
│  ┌─────────────────────────────┐   │
│  │      Python Application     │   │
│  │         (main.py)          │   │
│  └─────────────────────────────┘   │
│              │                      │
│    ┌─────────┼─────────┐           │
│    │         │         │           │
│    ▼         ▼         ▼           │
│ ┌─────┐  ┌─────┐  ┌─────┐        │
│ │API  │  │Tlgm │  │LLM  │        │
│ │Key  │  │Bot  │  │API  │        │
│ └─────┘  └─────┘  └─────┘        │
└─────────────────────────────────────┘
```

### 6.2 系統需求

| 項目 | 最低需求 |
|------|----------|
| Python | 3.10+ |
| 記憶體 | 2GB |
| 硬碟 | 1GB |
| 網路 | 穩定網路連線 |

---

## 7. 安全機制

### 7.1 風控檢查順序

```
下單請求
    │
    ▼
1. 檢查下單頻率 (每分鐘最多5次)
    │
    ▼
2. 檢查最大口數 (預設10口)
    │
    ▼
3. 檢查單日虧損 (預設50000元)
    │
    ▼
4. 檢查價格合理性
    │
    ▼
通過 → 執行下單
失敗 → 阻擋並回報原因
```

### 7.2 斷線處理

- 自動偵測連線狀態
- 最多重連50次
- 每次重連間隔5秒
- 斷線時發送 Telegram 通知

### 7.3 LLM 失敗處理

當 LLM 策略生成失敗時：

1. 系統記錄錯誤日誌
2. 策略不會執行
3. 發送 Telegram 通知給用戶
4. 用戶可修改策略描述後重新嘗試

---

## 8. 版本資訊

| 版本 | 日期 | 說明 |
|------|------|------|
| 1.0.0 | 2026-01 | 初始版本，支援3個策略 |
| 2.0.0 | 2026-02 | 新增 LLM 策略生成器與策略框架 |
| 2.1.0 | 2026-02 | 新增 Telegram Bot 接收機制 |
| 3.0.0 | 2026-02 | 新增自我優化系統 - 目標設定、訊號記錄、績效分析 |
| 3.1.0 | 2026-02 | 新增自我優化系統 - LLM 策略審查 |
| 3.2.0 | 2026-02 | 新增自我優化系統 - 半自動優化循環 |
| 3.3.0 | 2026-02 | 新增自動 LLM Review 排程功能 |
| 3.4.0 | 2026-02 | 新增版本化訊號儲存，策略更新時自動遞增版本 |
| 3.5.0 | 2026-02 | 重構儲存系統，採用 per-strategy 結構 |
| 3.6.0 | 2026-02 | 新增 Fallback 命令處理機制，確保基本命令執行成功 |
| 3.7.0 | 2026-02 | 新增 Markdown 清理機制與直接處理輸入優化 |

---

## 9. 技術支援

如有問題，請參閱：
- [功能說明](./Features.md)
- [User使用手冊](./User_Manual.md)
