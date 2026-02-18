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
cd ai_futures_trading
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

# CLI 模式（本地命令行操作）
python main.py --cli

# 模擬 + CLI 模式
python main.py --simulate --cli

# 指定配置文件
python main.py --config custom.yaml
```

#### 命令行參數說明

| 參數 | 說明 | 範例 |
|------|------|------|
| `command` | 命令 (預設: start) | `start` |
| `--simulate` | 模擬模式，跳過 Shioaji API 登入 | |
| `--cli` | 啟用本地命令行界面 | |
| `--config` | 指定配置文件路徑 | `--config myconfig.yaml` |

#### 模擬模式說明

使用 `--simulate` 參數時：
- 跳過 Shioaji API 登入
- 模擬下單會立即成交
- 模擬部位和損益會被追蹤
- 適合開發測試使用

#### CLI 模式說明

使用 `--cli` 參數時：
- 啟動本地命令行界面
- 無需 Telegram Bot 也能操作系統
- 適合無法使用 Telegram 的環境

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
- 用戶確認後策略建立，ID 自動生成（如 MXFA01）
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

#### 方式一：手動輸入完整參數

```
建立策略 ID=my_rsi, 名稱=RSI策略, 代碼=TXF, 描述=RSI低於30買入高於70賣出, 週期=15m, 數量=1, 停損=50, 停利=100
```

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
| ID | 策略唯一識別碼 | 是 | my_rsi |
| 名稱 | 策略顯示名稱 | 是 | RSI策略 |
| 代碼 | 期貨代碼 | 是 | TXF, MXF, EFF |
| 描述 | 策略交易邏輯 | 是 | RSI低於30買入 |
| 週期 | K線週期 | 是 | 15m, 5m, 1h |
| 數量 | 每次交易口數 | 否 | 1 (預設) |
| 停損 | 停損點數 | 否 | 50 (0=不啟用) |
| 停利 | 止盈點數 | 否 | 100 (0=不啟用) |

#### 更新策略描述

```
更新策略 my_rsi 為 RSI低於20買入高於80賣出
```

#### 刪除策略

```
刪除策略 my_rsi
```

#### 啟用/停用策略

```
enable my_rsi
disable my_rsi
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
ID: auto_每日收益策略_txf_123
名稱: 每日收益策略_TXF
期貨代碼: TXF
策略描述: 價格站上均線買入，跌破均線賣出，配合移動停損，嚴格執行停損
K線週期: 15m
數量: 1
停損: 50點
止盈: 50點

請使用 enable auto_每日收益策略_txf_123 啟用策略
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
5. 確認後建立策略，ID 自動生成（如 `MXFA01`）

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

### 4.6 策略可用屬性

| 屬性 | 說明 |
|------|------|
| `self.position` | 當前部位 (正=多單，負=空單，0=無部位) |
| `self.entry_price` | 進場價格 |
| `self.context` | 字典，可儲存自定義狀態 |
| `self.symbol` | 合約代碼 |

### 4.7 策略可用方法

| 方法 | 說明 |
|------|------|
| `self.get_bars(n)` | 取得最近 n 根 K 棒 |
| `self.get_dataframe(n)` | 取得 pandas DataFrame |
| `self.ta(指標, **參數)` | 使用 pandas_ta 計算指標 |

### 4.6 可用技術指標

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

### 5.1 策略管理

#### 查看所有策略

```
輸入: strategies
或: 策略
```

回覆：
```
📋 策略列表

*台指 RSI 策略*
  ID: MXFA01
  合約: TXF
  狀態: ✅ 啟用
  策略類別: RSIStrategy
  版本: 1

*小台均值回歸*
  ID: strategy_002
  合約: MXF
  狀態: ✅ 啟用
  ...
```

#### 啟用策略

```
輸入: enable MXFA01
```

#### 停用策略

```
輸入: disable MXFA01
```

#### 查看策略狀態

```
輸入: status MXFA01
```

回覆：
```
📊 策略狀態

ID: MXFA01
名稱: 台指 RSI 策略
合約: TXF
狀態: 執行中
策略類別: RSIStrategy
版本: 1
最後訊號: buy
最後訊號時間: 2024-01-15 10:30:00
```

### 5.2 查看部位

```
輸入: positions
或: 部位
```

回覆：
```
📊 目前部位
──────────────

🟢 台指 RSI 策略
  合約: TXF202301
  方向: Buy 2口
  進場: 18500 → 現價: 18520
  損益: +8000
──────────────
總口數: 2
總損益: +8000
```

### 5.3 查看績效

```
輸入: performance
或: 績效
```

回覆：
```
📊 績效統計
──────────────
日期: 2024-01-15
總委託: 5
成交: 3
取消: 1
待處理: 1

部位損益: +8000
當日風控損益: +8000
```

### 5.4 查看報價

```
輸入: price TXF
```

回覆：
```
📈 台指期貨
──────────────
最新價: 18520
漲停: 18650
跌停: 18350
```

---

## 6. 命令列表

### 6.1 基本命令

| 命令 | 說明 | 範例 |
|------|------|------|
| `status` | 系統狀態 | status |
| `positions` | 目前部位 | positions |
| `strategies` | 策略列表 | strategies |
| `performance` | 整體當日績效 | performance |
| `risk` | 風控狀態 | risk |
| `orders` | 訂單歷史 | orders |
| `enable <id>` | 啟用策略 | enable MXFA01 |
| `disable <id>` | 停用策略 | disable MXFA01 |
| `price <symbol>` | 查詢報價 | price TXF |
| `status <id>` | 策略狀態 | status MXFA01 |

### 6.2 績效分析命令

| 命令 | 說明 | 範例 |
|------|------|------|
| `performance <ID>` | 查詢策略全部歷史績效 | performance MXFA01 |
| `performance <ID> today` | 查詢策略今日績效 | performance MXFA01 today |
| `performance <ID> week` | 查詢策略本週績效 | performance MXFA01 week |
| `performance <ID> month` | 查詢策略本月績效 | performance MXFA01 month |
| `performance <ID> quarter` | 查詢策略本季績效 | performance MXFA01 quarter |
| `performance <ID> year` | 查詢策略本年績效 | performance MXFA01 year |
| `performance <ID> <begin> <end>` | 自訂日期範圍 | performance MXFA01 2025-01-01 2025-01-31 |

### 6.3 自我優化命令

| 命令 | 說明 | 範例 |
|------|------|------|
| `goal <ID> <金額> <單位>` | 設定策略目標 | goal MXFA01 500 daily |
| `review <ID>` | LLM 審查策略並給出修改建議 | review MXFA01 |
| `optimize <ID>` | 執行完整優化流程 | optimize MXFA01 |
| `confirm optimize` | 確認執行優化修改 | confirm optimize |
| `確認優化` | 確認執行優化修改 | 確認優化 |

### 6.4 目標設定

```
goal <策略ID> <目標金額> <目標單位>

目標單位:
- daily   (每日)
- weekly  (每週)
- monthly (每月)
- quarterly (每季)
- yearly  (每年)

範例:
goal MXFA01 500 daily      # 每日賺500元
goal MXFA01 3000 weekly    # 每週賺3000元
goal MXFA01 10000 monthly  # 每月賺10000元
```

### 6.5 完整優化流程

```
1. 設定目標:
   goal MXFA01 500 daily

2. 執行策略交易一段時間

3. 開始優化:
   optimize MXFA01
   → 系統分析目標達成情況
   → 若未達成，自動觸發 LLM 審查

4. 查看 LLM 建議

5. 確認修改:
   confirm optimize
   → 系統自動調整參數
```

### 6.6 績效查詢範例

```
用戶: performance MXFA01 month
Bot: 📈 策略績效: MXFA01 (2025-02-01 ~ 2025-02-18)
     ─────────────────────────────
     合約: TXF
     
     已實現損益: +15,000元
     交易次數: 8次
     獲利: 5次
     虧損: 3次
     勝率: 62.5%
     
     停損觸發: 2次
     止盈觸發: 4次
     訊號反向: 2次
```

### 6.5 策略審查範例

```
用戶: review MXFA01
Bot: 📊 LLM 策略審查結果
     ─────────────────────────────
     
     目標: 每日賺 500 元
     現況: 每日平均賺 380 元 (未達成)
     
     🔍 問題分析:
     - 停損觸發次數過多 (15次)
     - 平均獲利金額小於平均虧損
     - RSI 單一指標訊號不穩定
     
     💡 建議:
     1. 參數調整：停損從 30 點放寬到 50 點
     2. Prompt 微調：加入 MACD 確認訊號
     3. 可考慮加入成交量過濾假突破
     
     是否要進行修改？ (確認/取消)
```

### 6.7 自動 LLM Review 排程

除了手動執行 `review <ID>` 之外，系統也支援自動定時觸發 LLM 審查。

#### 設定方式

在 `config.yaml` 中設定：

```yaml
auto_review:
  enabled: true
  schedules:
    - strategy_id: "MXFA01"
      period: 5
      unit: "day"      # 每 5 天觸發一次
    - strategy_id: "TXF01"
      period: 2
      unit: "week"     # 每 2 週觸發一次
```

#### 參數說明

| 參數 | 說明 |
|------|------|
| `enabled` | 是否啟用自動 review (true/false) |
| `strategy_id` | 要自動 review 的策略 ID |
| `period` | 週期數字 |
| `unit` | 單位：day(天) / week(週) / month(月) / quarter(季) / year(年) |

#### 使用範例

```
# 每 5 天自動 review MXFA01
- strategy_id: "MXFA01"
  period: 5
  unit: "day"

# 每 2 週自動 review TXF01
- strategy_id: "TXF01"
  period: 2
  unit: "week"

# 每季自動 review strategy_003
- strategy_id: "strategy_003"
  period: 1
  unit: "quarter"
```

#### 重要規則

| 規則 | 說明 |
|------|------|
| 每天最多 1 次 | 每個策略每天最多自動觸發 1 次 |
| 手動不受限 | 用戶手動輸入 `review <ID>` 不受限制 |
| 無 goal 跳過 | 沒有設定目標的策略不會觸發自動 review |
| 長訊息分段 | 結果太長會自動分成多則訊息發送 |

#### 觸發後的行為

1. 系統自動執行 LLM 策略審查
2. 發送包含 LLM 建議的通知給用戶
3. 用戶決定是否執行優化（輸入 `confirm optimize`）

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

# 模擬 + CLI 模式（無需 Telegram）
python main.py --simulate --cli
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
python main.py --simulate --cli
```

這樣可以在沒有 Shioaji API 的情況下測試系統功能。

### Q3:如何新增/修改策略？

編輯 `config.yaml` 中的 `strategies` 區塊，然後重啟系統。

### Q3:策略 Prompt 應該怎麼撰寫？

使用自然語言描述您的交易邏輯，例如：
- 「RSI 低於 30 買入」
- 「MACD 金叉買入，死叉賣出」
- 「成交量暴增時買入」

### Q4:系統支援哪些期貨？

支援 Shioaji 所有期貨商品：
- TXF (台指期貨)
- MXF (小台指)
- EFF (電子期貨)
- 其他期貨商品

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

**版本**: 2.2.0  
**更新日期**: 2026-02-18
