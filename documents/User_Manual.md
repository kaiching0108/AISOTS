# AI 期貨交易系統 - User 使用手冊

## 目錄

1. [安裝指南](#1-安裝指南)
2. [快速開始](#2-快速開始)
3. [配置說明](#3-配置說明)
4. [策略撰寫](#4-策略撰寫)
5. [使用教學](#5-使用教學)
6. [命令列表](#6-命令列表)
7. [故障排除](#7-故障排除)
8. [FAQ](#8-faq)

---

## 1. 安裝指南

### 1.1 環境需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Linux / Windows / macOS |
| Python | 3.10 或更高版本 |
| 記憶體 | 2GB 以上 |
| 網路 | 穩定網路連線 |

### 1.2 安裝步驟

#### Step 1: 複製專案

```bash
git clone <repository-url>
cd AISOTS
```

#### Step 2: 建立虛擬環境 (建議)

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

#### Step 3: 安裝依賴

```bash
pip install -r requirements.txt
```

#### Step 4: 配置系統

編輯 `config.yaml` 檔案，填入您的 API Key。

---

## 2. 快速開始

### 2.1 取得 API Key

#### Shioaji API Key

1. 登入永豐期貨官網
2. 申請 API Token
3. 取得 `api_key` 和 `secret_key`

#### Telegram Bot Token

1. 打開 Telegram，搜尋 @BotFather
2. 輸入 `/newbot` 建立新機器人
3. 取得 Bot Token

#### LLM API Key (可選)

使用以下任一服務：
- [OpenRouter](https://openrouter.ai) (推薦)
- [OpenAI](https://platform.openai.com)
- [Anthropic](https://console.anthropic.com)
- [DeepSeek](https://platform.deepseek.com)
- **Ollama** (本地端，支援多種開源模型)

#### Ollama 本地端設定

如果您使用 Ollama 作為本地 LLM：

1. [下載並安裝 Ollama](https://ollama.ai)
2. 啟動 Ollama 服務
3. 下載模型：`ollama pull llama3`
4. 設定 config.yaml

### 2.2 配置 config.yaml

```yaml
shioaji:
  api_key: "YOUR_API_KEY"
  secret_key: "YOUR_SECRET_KEY"
  simulation: true  # 測試模式

telegram:
  enabled: true
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

# Ollama 範例
llm:
  provider: "custom"
  api_key: ""
  model: "llama3"
  base_url: "http://localhost:11434/v1"

# 或 OpenRouter 範例
# llm:
#   provider: "openrouter"
#   api_key: "YOUR_OPENROUTER_KEY"
#   model: "anthropic/claude-sonnet-4-20250514"

risk:
  max_daily_loss: 50000
  max_position: 10
  max_orders_per_minute: 5

# 策略透過 Telegram 對話建立，不在此處設定
# strategies: []
```

### 2.3 啟動系統

```bash
# 一般啟動（需要 Shioaji 登入）
python main.py

# 模擬模式（跳過 API 登入，用於測試）
python main.py --simulate
```

#### 命令行參數說明

| 參數 | 說明 | 範例 |
|------|------|------|
| `command` | 命令 (預設: start) | `start` |
| `--simulate` | 模擬模式，跳過 Shioaji API 登入 | |

#### 模擬模式說明

使用 `--simulate` 參數時：
- 跳過 Shioaji API 登入
- 模擬下單會立即成交
- 模擬部位和損益會被追蹤
- 適合開發測試使用

成功啟動後會看到類似輸出：

```
2024-01-15 10:00:00 - INFO - AI 期貨交易系統初始化中...
2024-01-15 10:00:00 - INFO - 載入 3 個策略:
2024-01-15 10:00:00 - INFO -   - 台指 RSI 策略 (TXF): 啟用
2024-01-15 10:00:00 - INFO -   - 小台均值回歸 (MXF): 啟用
2024-01-15 10:00:00 - INFO -   - 電子期動量 (EFF): 停用
2024-01-15 10:00:00 - INFO - LLM 策略生成器初始化完成
2024-01-15 10:00:00 - INFO - 系統啟動完成
```

同時會收到 Telegram 通知：

```
🤖 AI 期貨交易系統啟動

模式: 模擬
策略數: 3
風控: 單日最大虧損 50000 元
```

---

## 3. 配置說明

### 3.1 Shioaji 配置

| 參數 | 說明 | 範例 |
|------|------|------|
| api_key | Shioaji API Key | "YOUR_API_KEY" |
| secret_key | Shioapi Secret Key | "YOUR_SECRET_KEY" |
| simulation | 模擬模式 | true/false |

### 3.2 Telegram 配置

| 參數 | 說明 | 範例 |
|------|------|------|
| enabled | 啟用通知 | true |
| bot_token | Bot Token | "123456:ABC-DEF" |
| chat_id | 接收訊息的 ID | "123456789" |

取得 Chat ID：
1. 將機器人加入群組或直接傳訊息
2. 拜訪 `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. 從回應中取得 `chat.id`

### 3.3 LLM 配置

| 參數 | 說明 | 範例 |
|------|------|------|
| provider | LLM 供應商 | "openrouter" |
| api_key | API Key | "sk-or-..." |
| model | 模型名稱 | "anthropic/claude-sonnet-4-20250514" |
| temperature | 生成溫度 | 0.7 |

### 3.4 風控配置

| 參數 | 說明 | 預設值 |
|------|------|--------|
| max_daily_loss | 單日最大虧損 (元) | 50000 |
| max_position | 最大口數 | 10 |
| max_orders_per_minute | 每分鐘最大下單數 | 5 |
| enable_stop_loss | 啟用停損 | true |
| enable_take_profit | 啟用止盈 | true |

### 3.5 策略配置

**注意**：系統已改為對話式策略建立，config.yaml 中的 strategies 欄位已移除。

策略透過 Telegram 對話建立：
- 用戶：「幫我設計一個每日賺500元的策略」
- 系統詢問期貨代碼
- 用戶確認後策略建立，ID 自動生成（如 TMF260001）
    prompt: |                   # 交易邏輯描述 (自然語言)
      RSI 低於 30 買入，高於 70 賣出
    params:
      timeframe: "15m"          # K線週期
      stop_loss: 50             # 停損點數
      take_profit: 100          # 止盈點數
      position_size: 2           # 部位大小
```

#### 目標設定說明

| 欄位 | 類型 | 說明 | 範例 |
|------|------|------|------|
| `goal` | float | 目標數值（可選）| 500 |
| `goal_unit` | string | 目標單位 | daily/weekly/monthly/quarterly/yearly |

**目標單位說明**：

| 單位 | 說明 | 範例 |
|------|------|------|
| `daily` | 每日目標 | goal: 500, goal_unit: "daily" = 每日賺 500 元 |
| `weekly` | 每週目標 | goal: 3000, goal_unit: "weekly" = 每週賺 3000 元 |
| `monthly` | 每月目標 | goal: 15000, goal_unit: "monthly" = 每月賺 15000 元 |
| `quarterly` | 每季目標 | goal: 50000, goal_unit: "quarterly" = 每季賺 50000 元 |
| `yearly` | 每年目標 | goal: 200000, goal_unit: "yearly" = 每年賺 200000 元 |

---

## 4. 策略撰寫

### 4.1 建立策略（透過 AI Agent）

您可以透過 AI Agent 對話建立策略，無需手動編輯 JSON 檔案。

系統提供兩種建立策略的方式：

#### 方式一：手動輸入（問答式）

輸入 `create` 啟動問答式建立流程，系統會一步一步詢問：
1. 策略名稱
2. 期貨代碼（TXF/MXF/TMF/T5F/XIF/TE）
3. 策略描述
4. K線週期（1m/5m/15m/30m/60m/1h/1d）
5. 交易口數
6. 停損點數
7. 止盈點數
8. 確認建立

#### 方式二：目標驅動（自動推斷參數）

只需要告訴 LLM 您的目標：

```
幫我設計一個 RSI 策略
設計一個每日賺500元的策略
```

LLM 會：
1. 詢問期貨代碼
2. 自動推斷參數（名稱、策略描述、K線週期、停損止盈）
3. 展示參數要求確認
4. 用戶可修改參數（如「停損改成50點」）
5. 確認後建立策略

#### 參數說明

| 參數 | 說明 | 必填 | 範例 |
|------|------|------|------|
| ID | 策略唯一識別碼 | 是 | TMF260001 |
| 名稱 | 策略顯示名稱 | 是 | RSI策略 |
| 代碼 | 期貨代碼 | 是 | TXF, MXF, TMF, T5F, XIF, TE |
| 描述 | 策略交易邏輯 | 是 | RSI低於30買入 |
| 週期 | K線週期 | 是 | 15m, 5m, 1h |
| 數量 | 每次交易口數 | 否 | 1 (預設) |
| 停損 | 停損點數 | 否 | 50 (0=不啟用) |
| 停利 | 止盈點數 | 否 | 100 (0=不啟用) |

#### 更新策略描述

```
更新策略 TMF260001 為 RSI低於20買入高於80賣出
```

#### 刪除策略

```
刪除策略 TMF260001
```

#### 啟用/停用策略

```
enable TMF260001
disable TMF260001
```

### 4.2 目標驅動策略建立範例

以下是使用目標驅動方式建立策略的完整流程：

```
用戶: 幫我設計一個每日賺500元的策略

LLM: 請問要使用哪個期貨合約？（如 TXF、MXF、EFF）

用戶: TXF

LLM: 
📋 策略參數確認
────────────────
請確認以下參數是否正確：

• 名稱: 每日收益策略_TXF
• 期貨代碼: TXF
• 策略描述: 價格站上均線買入，跌破均線賣出，配合移動停損
• K線週期: 15m
• 交易口數: 1
• 停損: 30點
• 止盈: 50點

────────────────
輸入「確認」建立策略，或修改部分參數（如「停損改成50點」）

用戶: 停損改成50點

LLM:
✏️ 參數已更新
────────────────
📋 策略參數確認

• 名稱: 每日收益策略_TXF
• 期貨代碼: TXF
• 策略描述: 價格站上均線買入，跌破均線賣出，配合移動停損，嚴格執行停損
• K線週期: 15m
• 交易口數: 1
• 停損: 50點
• 止盈: 50點

────────────────
輸入「確認」建立策略，或繼續修改參數

用戶: 確認

LLM:
✅ 策略已建立
────────────────
ID: TXF260001
名稱: 每日收益策略_TXF
期貨代碼: TXF
策略描述: 價格站上均線買入，跌破均線賣出，配合移動停損，嚴格執行停損
K線週期: 15m
數量: 1
停損: 50點
止盈: 50點

請使用 enable TXF260001 啟用策略
```

#### 可用的參數修改指令

| 指令 | 說明 |
|------|------|
| 停損改成XX點 | 修改停損點數 |
| 止盈改成XX點 | 修改止盈點數 |
| 週期改成Xm | 修改K線週期 |
| 口數改成X | 修改交易口數 |
| 期貨代碼改成XXX | 修改期貨代碼 |

### 4.3 撰寫策略 Prompt

策略透過 Telegram 對話建立，Prompt 由 LLM 根據用戶目標自動生成：

1. 輸入：「幫我設計一個 RSI 策略」或「每日賺500元」
2. 系統詢問期貨代碼
3. 系統自動推斷參數並生成策略描述
4. 用戶可修改參數
5. 確認後建立策略，ID 自動生成（如 `TMF260001`）

### 4.4 策略 Prompt 範例

#### 範例 1：RSI 策略
```yaml
prompt: |
  RSI 低於 30 買入，RSI 高於 70 賣出
```

#### 範例 2：MACD 交叉策略
```yaml
prompt: |
  MACD 金叉買入，死叉賣出
```

#### 範例 3：漲停板策略
```yaml
prompt: |
  買進後，如果遇到漲停板隔日跌-6%以上就平倉
```

#### 範例 4：成交量策略
```yaml
prompt: |
  成交量暴增超過平均2倍且價格上漲買入
```

#### 範例 5：布林帶策略
```yaml
prompt: |
  價格跌破布林下軌買入，漲破上軌賣出
```

#### 範例 6：多指標組合
```yaml
prompt: |
  當 RSI 低於 30 且 MACD 為黃金交叉時買入，
  當 RSI 高於 70 或 MACD 為死亡交叉時賣出
```

#### 範例 7：均線策略
```yaml
prompt: |
  價格站上 20 日均線買入，跌破 20 日均線賣出
```

### 4.5 策略框架說明

系統會將您的策略描述交給 LLM 生成策略程式碼。策略需要：

1. 繼承 `TradingStrategy` 類別
2. 實作 `on_bar(bar)` 方法
3. 回傳 `buy`、`sell`、`close` 或 `hold`

### 4.6 BarData（K棒資料）

| 屬性 | 說明 |
|------|------|
| `bar.timestamp` | 時間戳 |
| `bar.open` | 開盤價 |
| `bar.high` | 最高價 |
| `bar.low` | 最低價 |
| `bar.close` | 收盤價 |
| `bar.volume` | 成交量 |
| `bar.pct_change` | 漲跌幅（小數） |
| `bar.get_change_from(price)` | 相對於某價格的漲跌幅 |

### 4.7 策略可用屬性

| 屬性 | 說明 |
|------|------|
| `self.position` | 當前部位 (正=多單，負=空單，0=無部位) |
| `self.entry_price` | 進場價格 |
| `self.context` | 字典，可儲存自定義狀態 |
| `self.symbol` | 合約代碼 |

### 4.8 策略可用方法

| 方法 | 說明 |
|------|------|
| `self.get_bars(n)` | 取得最近 n 根 K 棒 |
| `self.get_dataframe(n)` | 取得 pandas DataFrame |
| `self.ta(指標, **參數)` | 使用 pandas_ta 計算指標 |
| `self.on_fill(fill)` | 成交回調（可選實作） |

> **注意**：當 K 棒數據不足（少於 2 根）時，`ta()` 回傳 `None`。策略應檢查返回值是否為 `None` 再使用。
> 
> ```python
> rsi = self.ta('RSI', period=14)
> if rsi is None:
>     return 'hold'  # 數據不足時保持觀望
> rsi_value = rsi.iloc[-1]
> ```

### 4.9 on_bar 回傳值

| 回傳值 | 動作 |
|--------|------|
| `'buy'` | 買進開多 |
| `'sell'` | 賣出開空 |
| `'close'` | 平倉 |
| `'hold'` | 無動作 |

### 4.10 可用技術指標

```python
# RSI
self.ta('RSI', period=14)

# MACD
self.ta('MACD', fast=12, slow=26, signal=9)

# 布林帶
self.ta('BB', period=20, std=2.0)

# SMA / EMA
self.ta('SMA', period=20)
self.ta('EMA', period=20)

# ATR
self.ta('ATR', period=14)

# KD
self.ta('STOCH', period=14)
```

---

## 5. 使用教學

> **重要資訊**：系統已改為 **Web Interface 為主要操作介面**，Telegram 機器人僅用於通知，不接受指令。

### 5.1 啟動系統

1. 啟動主系統：
```bash
python main.py
```

2. 打開瀏覽器訪問：`http://127.0.0.1:5001`（或 config.yaml 中設定的 port）

3. 系統會自動載入所有資料，無需登入。

### 5.2 頁面導覽

| 頁面 | 網址 | 功能 |
|------|------|------|
| 首頁 | `/` | 系統總覽、策略數、部位數、當日損益 |
| 策略頁面 | `/strategies` | 策略列表、啟用/停用/刪除/回測 |
| 部位頁面 | `/positions` | 目前部位、損益顯示 |
| 策略建立 | `/strategies/create` | 建立新策略（兩階段驗證）|

### 5.3 策略管理

#### 查看所有策略

訪問 `/strategies` 頁面即可查看所有策略。

頁面分為兩個區塊：
- **已啟用策略**：目前正在執行的策略
- **已停用策略**：目前未執行的策略

#### 啟用策略

1. 訪問 `/strategies` 頁面
2. 找到要啟用的策略
3. 點擊「啟用」按鈕
4. 如果策略有部位，會顯示確認視窗，確認後強制平倉

#### 停用策略

1. 訪問 `/strategies` 頁面
2. 找到要停用的策略
3. 點擊「停用」按鈕
4. 如果策略有部位，會顯示確認視窗，確認後強制平倉

#### 刪除策略

1. 訪問 `/strategies` 頁面
2. 找到要刪除的策略
3. 點擊「刪除」按鈕
4. 如果策略有部位，會顯示確認視窗，確認後強制平倉並刪除

**注意**：有部位的策略無法直接刪除，需先停用策略強制平倉。

### 5.4 建立新策略

1. 點擊導航列「建立策略」或訪問 `/strategies/create`
2. 填寫策略參數：
   - 期貨代碼（TXF/MXF/TMF）
   - 交易方向（做多/做空/多空都做）
   - 策略描述
   - K線週期（1m/5m/15m/30m/60m/1h/1d）
   - 停損點數
   - 止盈點數
   - 交易口數
3. 點擊「Generate」生成策略描述預覽
4. 確認參數後點擊「確認建立」
5. 系統會執行兩階段驗證：
   - Stage 1：LLM 自我審查
   - Stage 2：歷史回測
6. 驗證通過後，策略建立成功

### 5.5 查看部位

訪問 `/positions` 頁面即可查看目前所有部位。

顯示資訊：
- 策略名稱
- 期貨合約
- 方向與口數
- 進場價格與現價
- 未平倉損益

### 5.6 歷史回測

1. 訪問 `/strategies` 頁面
2. 找到要回測的策略
3. 點擊「回測」按鈕
4. 系統會執行回測並顯示結果：
   - 文字報告（總損益、Sharpe Ratio、勝率等）
   - 圖表（K線與交易標記）

### 5.7 風控狀態

首頁 `/` 會顯示風控狀態：
- 單日最大虧損限制
- 最大口數限制
- 風控開關狀態
輸入: strategies
或: 策略
```

回覆：
```
📋 策略列表（共 2 個）
────────────────────

✅ 啟用 台指 RSI 策略
• ID: TMF260001
• 期貨代碼: TXF（臺股期貨）
• 版本: v1
• 策略描述: RSI低於30買入，高於70賣出
• K線週期: 15分鐘
• 口數: 1口
• 停損: 50點
• 止盈: 100點

❌ 停用 小台均值回歸
• ID: MXFA02
• 期貨代碼: MXF（小型臺指）
• 版本: v1
...
```

#### 啟用策略

```
輸入: enable TMF260001
```

#### 停用策略

```
輸入: disable TMF260001
```

#### 刪除策略

```
輸入: delete TMF260001
```

**注意**：有部位的策略無法刪除，需先平倉或停用策略。

#### 查看策略狀態

```
輸入: status TMF260001
```

回覆：
```
📊 策略狀態

ID: TMF260001
名稱: 台指 RSI 策略
合約: TXF
狀態: 執行中
策略類別: RSIStrategy
版本: 1
最後訊號: buy
最後訊號時間: 2024-01-15 10:30:00
```

---

## 6. 命令列表

> **注意**：系統已改為 Web Interface 為主要操作介面，以下命令適用於 Web Interface API 或開發者調用。

### 6.1 Web Interface 操作

所有操作透過瀏覽器訪問 Web 頁面完成：

| 頁面 | 網址 | 操作 |
|------|------|------|
| 首頁 | `/` | 查看系統總覽 |
| 策略 | `/strategies` | 啟用/停用/刪除/回測 |
| 部位 | `/positions` | 查看目前部位 |
| 建立策略 | `/strategies/create` | 建立新策略 |

### 6.2 API 端點

可直接呼叫的 API（適用於開發者）：

| Method | URL | 說明 |
|--------|-----|------|
| GET | `/api/status` | 系統狀態 |
| GET | `/api/strategies` | 策略列表 |
| POST | `/api/strategies/<id>/enable` | 啟用策略 |
| POST | `/api/strategies/<id>/disable` | 停用策略 |
| DELETE | `/api/strategies/<id>` | 刪除策略 |
| GET | `/api/positions` | 部位列表 |
| GET | `/api/risk` | 風控狀態 |
| POST | `/api/backtest/<id>` | 執行回測 |

### 6.3 回測期間

回測期間根據策略的 timeframe 自動決定：

| Timeframe | 回測期間 | 說明 |
|-----------|---------|------|
| `1m` | 1週 | 分鐘頻率 |
| `5m` | 2週 | 分鐘頻率 |
| `15m` | 1個月 | 分鐘頻率 |
| `30m` | 1個月 | 分鐘頻率 |
| `60m` / `1h` | 3個月 | 小時頻率 |
| `1d` | 1年 | 日頻率 |

### 6.4 訂單類型

| 環境 | 訂單類型 | 說明 |
|------|---------|------|
| **回測** | 市價單（下一根 K 棒開盤價）| 模擬市價單成交 |
| **實盤** | MKT + ROD | 市價單，當日有效 |
| `performance <ID> <begin> <end>` | 自訂日期範圍 | performance TMF260001 2025-01-01 2025-01-31 |

### 6.5 重要提醒

1. **回測結果僅供參考**：過去績效不代表未來結果
2. **回測期間依 timeframe 而定**：分鐘線回測期間較短，日線回測期間較長

---

## 7. 故障排除

### 7.1 常見錯誤

#### 錯誤：Shioaji 登入失敗

**原因**：API Key 或 Secret Key 錯誤

**解決**：
1. 確認 config.yaml 中的 key 正確
2. 檢查 Shioaji 帳號是否已簽署服務條款
3. **使用模擬模式測試**：`python main.py --simulate`

#### 模擬模式測試

如果您沒有有效的 Shioaji API Key，可以使用模擬模式進行測試：

```bash
# 模擬模式
python main.py --simulate
```

模擬模式下：
- 跳過 Shioaji API 登入
- 模擬下單會立即成交
- 部位和損益會被追蹤
- 可以測試策略建立、修改等功能

#### 錯誤：Telegram 訊息發送失敗

**原因**：Bot Token 或 Chat ID 錯誤

**解決**：
1. 確認 bot_token 正確
2. 確認 chat_id 正確
3. 檢查機器人是否已被停用

#### 錯誤：風控擋單

**原因**：超過風控限制

**解決**：
1. 檢查風控狀態：`risk` 命令
2. 調整 config.yaml 中的風控參數

#### 錯誤：LLM 策略生成失敗

**原因**：LLM API 錯誤或網路問題

**解決**：
1. 檢查 LLM 配置是否正確
2. 策略將不會執行
3. 查看日誌中的錯誤訊息
4. 修改策略描述後重新嘗試

#### 錯誤：部位同步失敗

**原因**：與 Shioaji 資料不一致

**解決**：
1. 重新啟動系統
2. 手動檢查 positions.json

### 7.2 解決方法

#### 重啟系統

```bash
# 按 Ctrl+C 停止
# 重新啟動
python main.py
```

#### 查看日誌

```bash
tail -f workspace/logs/trading.log
```

#### 重置資料

```bash
# 刪除 workspace 目錄內容
rm -rf workspace/*
# 重新啟動系統
python main.py
```

---

## 8. FAQ

### Q1: 如何切換模擬/實盤模式？

修改 `config.yaml`：
```yaml
shioaji:
  simulation: true   # 模擬
  # 或
  simulation: false  # 實盤
```

或使用命令行參數：
```bash
python main.py --simulate  # 模擬模式
python main.py             # 正常模式（需要 API 登入）
```

### Q2: 沒有 API Key 如何測試？

使用模擬模式：
```bash
python main.py --simulate
```

這樣可以在沒有 Shioaji API 的情況下測試系統功能。

### Q3:如何新增/修改策略？

#### 新增策略

系統提供兩種建立策略的方式：
1. **問答式**：輸入 `create` 逐步輸入參數
2. **目標驅動**：告訴 LLM 你的目標（如「每日賺500元」）

#### 修改策略

有兩種修改方式：

**方式一：建立時修改參數**
在目標驅動建立策略的確認階段，可以用自然語言修改參數：
- 「停損改成50點」
- 「止盈改成100點」
- 「週期改成15m」
- 「口數改成2」

**方式二：建立後修改描述**
策略建立後，可以透過 LLM 討論修改策略描述：
- 討論策略邏輯
- LLM 自動更新 prompt 並遞增版本
- 舊版本訊號歸檔，新版本訊號重新記錄

### Q4: 為什麼有些命令不用經過 LLM？

系統採用 **Fallback 機制**：明確英文指令直接調用函數，確保一定會執行，不會因為 LLM 工具調用不穩定而失敗。

**LLM 處理範圍**：
- 目標驅動建立策略
- 策略討論

使用自然語言描述您的交易目標：
- 「設計一個每日賺500元的 RSI 策略」
- 「幫我建立一個趨勢策略」

### Q4:系統支援哪些期貨？單位是什麼？

**僅支援期貨交易**，不支援股票或選擇權。

#### 可交易期貨及規格

**系統目前僅支援以下三種期貨商品**：

| 期貨代碼 | 名稱 | 點數價值 | 說明 |
|---------|------|---------|------|
| TXF | 臺股期貨（大台）| 200元/點 | 大型臺指，流動性最好 |
| MXF | 小型臺指（小台）| 50元/點 | 小型臺指，門檻適中 |
| TMF | 微型臺指（微台）| 10元/點 | 微型臺指，門檻最低 |

> **注意**：系統暫時僅支援以上三種商品，其他期貨代碼（如 T5F、XIF、TE 等）暫不支援。

**重要**：
- **單位：口 (contracts/lots)**
- 例如：買入 TXF 1口，價格上漲 10點 → 獲利 2,000 元 (10點 × 200元)
- 例如：買入 TMF 1口，價格上漲 10點 → 獲利 100 元 (10點 × 10元)

系統會從 Shioaji API 取得期貨代碼的中文名稱並顯示。

**無效代碼處理**：
- 若輸入不支援的代碼，系統會顯示錯誤訊息：
  ```
  ❌ 無效的期貨代碼：T5F
  可用代碼：TXF(臺股期貨), MXF(小型臺指), TMF(微型臺指)
  ```

### Q5:停損止盈是如何觸發？

系統每60秒檢查一次部位價格：
- 虧損 >= 停損點數 → 自動平倉
- 獲利 >= 止盈點數 → 自動平倉

### Q6:斷線時會怎麼樣？

1. 系統自動偵測斷線
2. 嘗試自動重連 (最多50次)
3. 發送 Telegram 通知
4. 重連成功後恢復運作

### Q7:可以同時執行多少個策略？

目前支援最多 3 個策略。

### Q8:如何查看歷史交易記錄？

```
輸入: orders
```

可以查看所有訂單記錄。

### Q9:如果 LLM 生成失敗怎麼辦？

策略將不會執行，系統會發送通知。您可以檢查日誌中的錯誤訊息，修正策略描述後重新嘗試。

### Q10:策略程式碼會儲存嗎？

是的，策略程式碼會儲存在 `strategies.json` 中，修改 prompt 後會自動重新生成。

### Q11:下單使用的是市價單還是限價單？

系統預設使用**市價單 (MKT)**，配合 ROD（當日有效）order type，確保快速成交。

### Q12:期貨合約的到期日如何處理？

系統**自動選擇近月合約**進行交易，無需用戶指定到期日：
- 用戶輸入「TXF」→ 系統自動使用「TXFR1」（近月合約）
- 用戶輸入「MXF」→ 系統自動使用「MXFR1」（近月合約）
- 用戶輸入「TMF」→ 系統自動使用「TMFR1」（近月合號）

**優點**：
1. 無需關心到期日
2. 近月合約流動性最好
3. 合約到期時自動換月

---

## 附錄

### 系統架構圖

```
User (Telegram)
     │
     ▼
┌────────────────┐
│  AI Agent      │
│  (處理指令)    │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ LLM Generator  │
│ (生成策略代碼) │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ TradingStrategy│
│  (策略框架)    │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ 風控檢查      │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  Shioaji API  │
│  (執行交易)   │
└───────────────┘
```

### 技術支援

如有技術問題，請聯絡系統管理員。

---

**版本**: 3.8.0  
**更新日期**: 2026-02-26
