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
| LLM | OpenRouter / OpenAI / Anthropic / Ollama (本地) |
| 技術指標 | pandas_ta |
| 通知 | Telegram Bot |
| 資料儲存 | JSON 檔案 |

---

## 2. 系統架構圖

### 2.1 整體架構 (8層)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Layer (用戶層)                          │
│     Web Interface (主要) / Telegram Notification (通知)               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent Layer (AI Agent 層)                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Trading Tools  │  │ System Prompt   │  │  LLM Provider   │    │
│  │  - place_order  │  │                 │  │                 │    │
│  │  - get_position│  │  交易規則       │  │  GPT/Claude     │    │
│  │  - get_perform │  │ 策略定義       │  │  Ollama         │    │
│  │  - 自動生成ID  │  │ 對話歷史       │  │                 │    │
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
│  │  - get_perform │  │  策略定義       │  │  Ollama         │    │
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

**支援的命令**：`create`, `status`, `positions`, `strategies`, `performance`, `risk`, `orders`, `enable <ID>`, `disable <ID>`, `new`, `help`

**直接處理的輸入**：
- 所有明確英文指令 → Fallback 直接執行，確保 100% 成功
- `create` → 問答式建立策略流程
- `enable <ID>` / `disable <ID>` → 直接執行
- `status`, `positions`, `strategies` 等 → 直接查詢

**LLM 處理範圍**：
- 目標驅動建立策略
- 策略討論

**優勢**：確保基本命令 100% 執行成功，響應速度更快，不依賴 LLM 工具調用穩定性

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
用戶指令 (Web Interface)
      │
      ▼
┌─────────────────┐
│ 判斷指令類型    │ ◄─── 分析是明確指令還是目標驅動
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ 明確指令 │ │ LLM    │
│ (Fallback)│         │ ◄─── 目標驅動、策略討論
└────┬───┘ └────┬───┘
     │           │
     ▼           ▼
直接執行   策略相關處理

---

## 3. 核心模組說明

### 3.1 API 層 (src/api/)

| 檔案 | 說明 |
|------|------|
| `shioaji_client.py` | Shioaji API 封裝，包含登入、下單、取得部位等 |
| `connection.py` | 連線管理，自動重連機制 |
| `order_callback.py` | 訂單/報價回調處理，區分委託回報與成交回報 |

### 3.2 交易層 (src/trading/)

| 檔案 | 說明 |
|------|------|
| `strategy.py` | 策略類別 (含 LLM 生成程式碼欄位) |
| `strategy_manager.py` | 策略管理器，管理3個策略 |
| `position.py` | 部位類別 |
| `position_manager.py` | 部位管理器，按策略分開追蹤 |
| `order.py` | 訂單類別 |
| `order_manager.py` | 訂單管理器（含 seqno ↔ order_id 映射） |

### 3.3 引擎層 (src/engine/)

| 檔案 | 說明 |
|------|------|
| `framework.py` | 策略框架 (TradingStrategy, StrategyExecutor) |
| `llm_generator.py` | LLM 策略生成器 |
| `runner.py` | 策略執行協調器 |
| `backtest_engine.py` | backtesting.py 歷史回測引擎 |

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
| `providers.py` | LLM 提供者 (Ollama/OpenAI/Anthropic/OpenRouter) |

### 3.8 數據存儲層 (src/storage/)

| 檔案 | 說明 |
|------|------|
| `kbar_sqlite.py` | SQLite K 棒存儲（1m 歷史數據，自動清理） |

### 3.9 數據存儲層 (src/storage/)

| 檔案 | 說明 |
|------|------|
| `kbar_sqlite.py` | SQLite K 棒存儲（1m 歷史資料，自動清理） |

### 3.9 數據服務層 (src/services/)

| 檔案 | 說明 |
|------|--------|
| `data_updater.py` | K 棒數據更新服務（每日定時抓取、啟動檢查） |
| `realtime_kbar_aggregator.py` | 實時 K-bar 聚合器（tick 轉 K-bar） |

**Phase 7 修復說明：右側對齊 (2026-03-04)**
```python
# kbar_sqlite.py:382 & kbar_manager.py:77
df.resample('15min', closed='right', label='right')  # Shioaji API 最佳實踐
```

**修復問題**：
- ❌ 左側對齊：每日最後一根 K 棒（收盤價）被分給下一天資料
- ✅ 右側對齊：每日最後一根 K 棒正確歸類到該天資料中
- ✅ 符合 Shioaji API 官方建議

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
5. **Tick 回調更新價格快取**：`_latest_prices[symbol] = tick.close`

#### 價格快取機制（v0.5.1+）

系統透過 `ShioajiClient._latest_prices` 字典快取即時報價，提供統一的價格查詢介面：

| 方法 | 檔案位置 | 說明 |
|------|---------|------|
| `update_latest_price()` | `shioaji_client.py` | 從 Tick 回調更新最新價格 |
| `get_latest_price()` | `shioaji_client.py` | 取得特定 symbol 的最新價格 |

**報價訂閱邏輯**：
- `simulation: true`（實盤登入 + 下虛擬單）：**仍需訂閱報價**以取得即時價格
- `skip_login: true`（完全模擬）：跳過報價訂閱
- 只有 `skip_login` 會跳過報價訂閱，`simulation` 只影響下單是否為虛擬單

**價格來源優先順序**：
1. 報價快取 `_latest_prices`（即時價格）
2. 合約參考價 `contract.reference`（開盤參考價，fallback）

#### Timeframe 處理

- 策略啟動時從 `strategy.params.timeframe` 讀取週期參數
- `get_kbars(contract, timeframe, count)` 取得該週期 K 棒
- 由於設計上每個 symbol 同時只有一個策略，採用 `market_data_cache[symbol]` 儲存，不會有衝突

#### 期貨合約自動近月選擇

系統在 `get_contract()` 方法中**自動選擇近月合約**：

```python
near_month_map = {
    "TXF": "TXFR1",
    "MXF": "MXFR1", 
    "TMF": "TMFR1",
}

if symbol in near_month_map:
    symbol = near_month_map[symbol]
```

**運作方式**：
1. 用戶輸入基本代碼（如 "TXF"）
2. 系統自動轉換為近月合約代碼（如 "TXFR1"）
3. 取得近月合約進行交易

**優點**：
- 無需用戶指定到期日
- 近月合約流動性最好
- 合約到期時自動使用新的近月合約

#### 支援商品限制

**系統目前僅支援以下三種期貨商品**：

| 期貨代碼 | 名稱 | 點值 |
|---------|------|------|
| TXF | 臺股期貨（大台）| 200元/點 |
| MXF | 小型臺指（小台）| 50元/點 |
| TMF | 微型臺指（微台）| 10元/點 |

**限制原因**：
1. 簡化系統初期複雜度
2. 聚焦於流動性最好的三個商品
3. 避免用戶輸入錯誤商品代碼

**驗證機制**：
- 用戶輸入非允許的代碼時，系統會顯示錯誤訊息並列出可用代碼
- 例如輸入 "T5F" 時會顯示：
  ```
  ❌ 無效的期貨代碼：T5F
  可用代碼：TXF(臺股期貨), MXF(小型臺指), TMF(微型臺指)
  ```

#### 回測績效計算

回測系統在計算績效時會使用合約乘數和固定手續費：

```python
# 合約乘數（點值）
contract_multiplier_map = {
    "TXF": 200,  # 臺股期貨
    "MXF": 50,   # 小型臺指
    "TMF": 10,   # 微型臺指
}
contract_multiplier = contract_multiplier_map.get(symbol, 1)

# 固定手續費（每口）
fixed_commission_map = {
    "TXF": 40,  # 大台
    "MXF": 20,  # 小台
    "TMF": 14,  # 微台
}
commission_per_trade = fixed_commission_map.get(symbol, 0)

# 計算總手續費（開倉+平倉）
total_commission = trade_count * 2 * commission_per_trade

# 總損益 = 報酬率% × 初始資金 × 合約乘數 - 手續費
total_pnl = initial_capital * total_return / 100 * contract_multiplier - total_commission
```

**說明**：
- Shioaji API 的 `unit` 欄位返回值為 1，不是實際點值
- 因此系統使用硬編碼的映射表來獲取正確的合約乘數
- 固定手續費：開倉和平倉各收取一次
- 這個乘數會影響總損益、平均交易損益等以金額計算的指標
- 報酬率 (%) 不受影響
  ```
  ❌ 無效的期貨代碼：T5F
  可用代碼：TXF(臺股期貨), MXF(小型臺指), TMF(微型臺指)
  ```
- 合約到期時自動使用新的近月合號

### 4.10 K-bar 轉換與持久化 (v4.9.0+)
> **Phase 7 修復說明**：2026-03-04 新增，修正 K-bar 轉換邏輯的右側對齊問題。

#### 重要變更 (從 v4.8.0+)

Shioaji API 只能取得 1 分鐘 K 線。為了效能與策略一致性，系統採用以下策略：

**1. 資料獲取流程**
- 實盤模式：透過 Shioaji API 取得 1m K 棒 → SQLite 快取
- 轉換邏輯：在儲存前將 1m 轉為 5m/15m/30m/1h/1d（加速回測）

**2. 右側對齊 (Phase 7)**
`kbar_sqlite.py` Line 382 與 `kbar_manager.py` Line 77：
- **從前**：`closed='left', label='left'`（左側關閉）
- **修正後**：`closed='right', label='right'`（右側關閉，Shioaji 最佳實踐）

**3. 每日 K 棒處理**
使用右側對齊時：
- 每日最後一根 K 棒（收盤價）會被正確歸類到該天資料中
- 而非被分給下一天（左側對齊的問題）

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

（見上方章節）

---

### 4.13 BacktestEngine 回測系統

#### 4.13.1 概述

系統使用 **backtesting.py** 函式庫執行歷史回測，提供用戶在啟用策略前參考過去績效。

#### 4.13.2 架構圖

```
┌─────────────────────────────────────────────────────────┐
│                   BacktestEngine                         │
├─────────────────────────────────────────────────────────┤
│  1. 解析策略代碼 → 提取指標需求 (RSI/MACD/SMA/BB)       │
│  2. 取得歷史 K 棒 (Shioaji) → pandas DataFrame         │
│  3. 用 pandas_ta 計算指標                               │
│  4. 建立 backtesting.py Backtest + 策略           │
│  5. 執行回測 → 輸出績效報告                             │
└─────────────────────────────────────────────────────────┘
```

#### 4.13.3 Timeframe 與回測期間對照表

| Timeframe | 回測期間 | K棒數（估）| 說明 |
|-----------|---------|-----------|------|
| `1m` | 1週 | ~2,000-2,500 | 分鐘頻率，縮短以兼顧效能 |
| `5m` | 2週 | ~1,000 | 分鐘頻率 |
| `15m` | 1個月 | ~600-700 | 分鐘頻率 |
| `30m` | 1個月 | ~300-340 | 分鐘頻率 |
| `60m` / `1h` | 3個月 | ~1,200-1,400 | 小時頻率 |
| `1d` | 1年 | ~250 | 日頻率 |

#### 4.13.4 指標整合方式

系統使用 **pandas_ta 預先計算指標**，再傳給 backtesting.py 執行回測：

```python
# 1. 根據策略代碼提取指標需求
def extract_indicators_from_code(code: str) -> list:
    indicators = []
    if "RSI" in code:
        indicators.append('rsi')
    if "MACD" in code:
        indicators.extend(['macd', 'macd_signal', 'macd_hist'])
    # ...
    return indicators

# 2. 用 pandas_ta 計算指標
df['rsi'] = ta.rsi(df['close'], length=14)
df['macd'] = ta.macd(df['close'])

# 3. backtesting.py 讀取預先計算的指標
class BacktestStrategy(bt.Strategy):
    def next(self):
        if self.data.rsi[0] < 30:
            self.buy()
```

#### 4.13.5 訂單類型

| 環境 | 訂單類型 | 說明 |
|------|---------|------|
| **回測** | 市價單（下一根 K 棒開盤價）| 模擬市價單成交，最保守的估計 |
| **實盤** | MKT + ROD | 市價單，當日有效 |

#### 4.13.6 輸出績效報告格式

```
📊 歷史回測報告 (策略名稱)
══════════════════════════════════════════
📅 回測期間: 2025-01-01 ~ 2025-02-01 (1個月)
📈 初始資金: 1,000,000 NTD
─────────────────────────────────────────
💰 總損益: +85,000 (+8.5%)
💵 最大資金回撤: -32,000 (-3.2%)
📊 Sharpe Ratio: 1.72
📊 SQN: 2.1 (Average)
📊 交易次數: 18
✅ 獲利交易: 12
❌ 虧損交易: 6
📈 勝率: 66.7%
📊 獲利因子: 2.15
📊 平均交易: +4,722
📊 最大單筆獲利: +12,500
📊 最大單筆虧損: -6,800
─────────────────────────────────────────
⚠️ 過去績效不代表未來結果，僅供參考
```

#### 4.13.7 使用時機

1. **獨立指令**：用戶輸入 `回測 <ID>` 或 `backtest <ID>` 查看詳細回測報告（包含圖表）
2. **啟用前顯示**：用戶輸入 `啟用 <ID>` 時，系統自動顯示歷史回測關鍵指標

#### 4.13.8 關鍵類別

```python
class BacktestEngine:
    """backtesting.py 回測引擎"""
    
    TIMEFRAME_CONFIG = {
        "1m": (7, "1週"),
        "5m": (14, "2週"),
        "15m": (30, "1個月"),
        "30m": (30, "1個月"),
        "60m": (90, "3個月"),
        "1h": (90, "3個月"),
        "1d": (365, "1年"),
    }
    
    async def run_backtest(
        self,
        strategy_code: str,
        class_name: str,
        symbol: str,
        timeframe: str = "15m",
        initial_capital: float = 1_000_000,
        commission: float = 0.0002
    ) -> dict:
        """執行歷史回測"""
        # 1. 根據 timeframe 決定回測期間
        # 2. 取得歷史 K 棒
        # 3. 編譯策略
        # 4. 建立 Cerebro + Data Feed + Strategy + Analyzers
        # 5. 執行回測
        # 6. 解析結果
        # 7. 產生績效報告
```

#### 4.13.9 Analyzers 配置

```python
cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
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

### 7.2 斷線處理（v0.5.0+）

#### 異步重連機制
- **異步方法**：`handle_disconnect_async()` 使用 `asyncio.sleep()`
- **同步包裝**：`handle_disconnect()` 保留作為同步環境的包裝
- **不阻塞事件迴圈**：避免 Web UI 在重連期間無法響應

#### 斷線期間策略執行
- 主循環每次迭代檢查 `connection_mgr.is_connected` 狀態
- 斷線時：
  1. 跳過策略執行（`run_all_strategies()`）
  2. 跳過部位價格更新
  3. 跳過停損止盈檢查
  4. 呼叫 `handle_disconnect_async()` 嘗試重連
- 重連成功後自動恢復策略執行

#### 重連後恢復
- 觸發 `on_reconnected` 回調
- 重新訂閱 tick 數據（`resubscribe_all_quotes()`）
- 恢復主循環正常執行

#### 連線狀態顯示
- Web UI 首頁動態顯示連線狀態（✅/❌ 圖示 + 重連次數）
- `/api/status` API 返回 `connection` 欄位

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
| 0.1.0 | 2026-01 | 初始版本，支援3個策略 |
| 0.2.0 | 2026-02 | 新增 LLM 策略生成器與策略框架 |
| 0.2.1 | 2026-02 | 新增 Telegram Bot 接收機制 |
| 0.3.0 | 2026-02 | 新增自我優化系統 - 目標設定、訊號記錄、績效分析 |
| 0.3.1 | 2026-02 | 新增自我優化系統 - LLM 策略審查 |
| 0.3.2 | 2026-02 | 新增自我優化系統 - 半自動優化循環 |
| 0.3.3 | 2026-02 | 新增自動 LLM Review 排程功能 |
| 0.3.4 | 2026-02 | 新增版本化訊號儲存，策略更新時自動遞增版本 |
| 0.3.5 | 2026-02 | 重構儲存系統，採用 per-strategy 結構 |
| 0.3.6 | 2026-02 | 新增 Fallback 命令處理機制，確保基本命令執行成功 |
| 0.3.7 | 2026-02 | 新增 Markdown 清理機制與直接處理輸入優化 |
| 0.3.8 | 2026-02 | 新增 BacktestEngine 歷史回測系統 |
| 0.3.9 | 2026-02 | 新增回測圖表生成與 Telegram 圖片發送功能 |
| 0.3.10 | 2026-02 | 新增 delete 指令與回測圖片清理功能 |
| 0.4.0 | 2026-02 | 架構變更：Web Interface 改為主要操作介面，Telegram 僅用於通知 |
| 0.4.1 | 2026-03 | 新增交易日誌系統（TradeLogStore），系統總覽顯示重要交易訊息 |
| 0.4.2 | 2026-03 | 統一平倉流程，確保所有平倉操作都記錄訂單與日誌 |
| 0.4.3 | 2026-03 | 系統日誌重命名（trading.log → system.log），訂單查詢新增原因欄位 |
| 0.4.4 | 2026-03 | 新增啟用策略確認機制（Scheme C），舊策略有部位時需確認強制平倉 |
| 0.4.5 | 2026-03 | 模擬模式價格生成改為趨勢模擬演算法，支援 RSI/MACD 指標正常運作 |
| 0.4.6 | 2026-03 | MockContract 使用部位進場價作為 last_price，避免系統重啟時誤觸停損 |
| 0.4.7 | 2026-03 | 統一停損檢查價格來源：從 strategy_runner 獲取，確保與策略決策使用相同價格 |
| 0.4.8 | 2026-03 | 訂單價格類型預設改為 MKT（市價單），與實盤行為及文檔一致 |
| 0.4.9 | 2026-03 | 刪除策略時連帶刪除所有 backtest 檔案（HTML、TXT、PNG） |
| 0.4.10 | 2026-03 | 模擬價格統一化：回測K線與實時交易統一使用 ShioajiClient.TIMEFRAME_VOLATILITY |
| 0.4.11 | 2026-03-01 | Web Interface 改進：當日損益顯示、策略創建自訂名稱、口數驗證、停損止盈允許為0 |
| 0.4.12 | 2026-03-02 | 策略程式碼編譯失敗時，自動調用 fix_compile_error 嘗試修復一次 |
| 0.4.13 | 2026-03-02 | K棒數據持久化 - SQLite 方案（最大 60 萬筆容量、自動清理） |
| 0.4.14 | 2026-03-04 | 新增 DataUpdater 定時服務、實時 K-bar 聚合器，回測數據不足處理 |
| 0.4.15 | 2026-03-05 | 修正連線狀態同步問題（ConnectionManager.is_connected 與 ShioajiClient.connected 一致） |
| 0.4.16 | 2026-03-06 | 回測數據流程優化：檢查現有報告、SQLite 數據不足時詢問用戶、移除 API 調用 |
| 0.4.17 | 2026-03-07 | DataUpdater 優化：預先計算時間區間、強制往前推進、支援連假處理 |
| 0.4.18 | 2026-03-08 | SQLite 數據完整性檢查：工作日缺口/交易時段異常檢測 |
| 0.5.0 | 2026-03-09 | 異步重連機制：新增 handle_disconnect_async() 不阻塞事件迴圈；斷線期間暫停策略執行；Web UI 首頁顯示連線狀態 |
| 0.5.1 | 2026-03-10 | 修復「實盤登入 + 下虛擬單」模式三個錯誤：(1) 報價訂閱被錯誤跳過；(2) contract.last_price 不存在 - 新增報價快取；(3) _on_order_filled 回調參數不匹配 |
| 0.5.2 | 2026-03-11 | 修復成交價為 0：(1) 區分委託回報與成交回報；(2) 從 msg.get(\"price\") 提取成交價；(3) 實作 seqno ↔ order_id 映射機制；(4) is_close_order 屬性區分開倉/平倉；(5) 平倉改用市價單等待回調；(6) 新增 OrderManager 映射管理方法 |

---

## 9. 技術支援
## 9. 技術支援



如有問題，請參閱：
- [功能說明](./Features.md)
- [User使用手冊](./User_Manual.md)
