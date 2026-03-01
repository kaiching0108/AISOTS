# AI Self-Optimizing Trading System (AISOTS)

使用 Shioaji API 的 AI 驅動期貨交易系統，支援 LLM 策略生成與自我優化。

## 功能特色

- 🤖 **AI 策略生成** - 用自然語言描述策略，LLM 自動生成程式碼
- 🎯 **目標驅動策略** - 只需給出目標（如「每日賺500元」），LLM 自動推斷參數並確認後建立
- 🔒 **策略驗證** - 建立策略時自動執行兩階段驗證（LLM審查比對程式碼是否符合策略描述 + 歷史K棒回測）
- 📊 **歷史回測** - 執行完整歷史回測，啟用策略前參考過去績效（含圖表）
- 📈 **自我優化系統** - 設定目標 → LLM 設計策略 → 執行 → 績效分析 → LLM 審查優化 → 達成目標
- 🔔 **Telegram 通知** - 交易提醒、风控警告即时推送（仅通知，不接受命令）
- 🌐 **Web 界面** - **主要操作平台**，图形化管理策略、部位、回测，无需记忆指令
- 📊 **多種 LLM 支援** - Ollama, OpenAI, Anthropic, OpenRouter
- 🛡️ **風控機制** - 單日虧損、最大部位、下單頻率限制
- 💾 **資料持久化** - JSON 格式儲存策略、部位、訂單、訊號

## 安裝

```bash
git clone https://github.com/kaiching0108/AISOTS.git
cd AISOTS
pip install -r requirements.txt
```

## Config設定 (可透過web界面設定)

編輯 `config.yaml`：

```yaml
shioaji:
  api_key: "YOUR_API_KEY"
  secret_key: "YOUR_SECRET_KEY"
  simulation: true  # 測試模式

llm:
  provider: "custom"
  base_url: "http://localhost:11434/v1"
  model: "llama3"

telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

# 風控配置
risk:
  max_daily_loss: 10000          # 單日最大虧損 (元)
  max_position: 3               # 最大口數總和
  max_orders_per_minute: 1       # 每分鐘最大下單數
  enable_stop_loss: true         # 啟用停損
  enable_take_profit: true       # 啟用止盈

# 交易配置
trading:
  check_interval: 60             # 檢查間隔 (秒)
  trading_hours:
    day_start: "08:45"
    day_end: "13:45"
    night_start: "15:00"
    night_end: "05:00"

# Web 界面配置（主要操作界面）
web:
  enabled: true          # 啟用 Web 界面（主要操作平台）
  host: "127.0.0.1"     # 綁定位址（本機）
  port: 5001            # 連接埠
```

## 使用方式

```bash
# 一般啟動（需要 Shioaji 登入）
python main.py

# 模擬模式（跳過 API 登入，用於測試）
python main.py --simulate
```

### 透過 Web 界面建立策略

訪問 `http://127.0.0.1:5001/strategies/create`，填寫表單：

1. 提示詞輸入策略，選擇期貨代碼（TXF/MXF/TMF）
2. 交易方向（做多/做空/多空都做）
3. 策略描述（如「RSI 低於 30 買入，高於 70 賣出」）
4. K線週期（1m/5m/15m/30m/60m/1h/1d）
5. 停損點數、止盈點數、交易口數
6. 點擊 Generate 由AI生成策略描述預覽
7. 確認參數後點擊「確認建立」

系統會自動執行兩階段驗證：
- Stage 1：LLM 自我審查（檢查程式碼是否符合策略描述）
- Stage 2：歷史回測（檢查訊號分佈是否合理）

驗證通過後，策略建立成功。若 Stage 1 失敗，系統會顯示詳細錯誤日誌鏈接，用戶需重新設計策略。

### Telegram 通知 (Option)

#### Create Telegram bot 
- Create a bot
  - Open Telegram, search @BotFather
  - Send /newbot, follow prompts
  - Copy the token

通知類型：
- 系統啟動/停止
- 成交通知
- 停損/止盈觸發
- 風控警告
- 系統錯誤

## 自我優化系統

### 系統願景

```
用戶輸入目標 → LLM 設計策略 → 執行 → 績效分析 → LLM 審查優化 → 達成目標
```

### 目標設定

每個策略可以設定明確的數值目標：

| 欄位 | 說明 | 範例 |
|------|------|------|
| goal | 目標數值（必須為數字）| 500 |
| goal_unit | 目標單位 | daily/weekly/monthly/quarterly/yearly |

### 完整優化流程

```
1. 用戶輸入目標（如「每日賺500元」）
2. LLM 設計策略 → 用戶確認
3. 策略執行 → 記錄訊號 → 更新結果
4. 績效分析 → 檢查目標是否達成
   ├── 已達成 → 維持現狀
   └── 未達成 → LLM 審查 → 建議修改
5. 用戶確認修改 → 更新策略
6. 繼續執行 → 循環直到達成目標
```

### LLM 建議類型

LLM 審查後可能給出以下建議：

| 類型 | 說明 | 範例 |
|------|------|------|
| 參數調整 | 修改停損、止盈、數量等 | 「停損太近，建議從 30 點改為 50 點」 |
| Prompt 微調 | 修改交易邏輯描述 | 「建議加入 MACD 確認訊號」 |
| 重新設計 | 完全重新設計策略 | 「 RSI 策略不適合當前市場」 |

### 自動 LLM Review 支援自動定時觸發排程

系統 LLM 審查，無需手動輸入命令：

```yaml
auto_review:
  enabled: true
  schedules:
    - strategy_id: "TMF260001"
      period: 5
      unit: "day"      # 每 5 天觸發一次
    - strategy_id: "TXF260001"
      period: 2
      unit: "week"     # 每 2 週觸發一次
```

**規則**：
- 每天每策略最多觸發 1 次
- 手動 `review` 命令不受限制
- 無 goal 策略會跳過

## 專案結構

```
AISOTS/
├── main.py                 # 入口程式
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依賴
├── AGENTS.md             # Agent 開發指南
│
├── src/
│   ├── api/              # Shioaji API 包裝
│   │   ├── shioaji_client.py
│   │   ├── connection.py
│   │   └── order_callback.py
│   │
│   ├── trading/          # 交易邏輯
│   │   ├── strategy.py
│   │   ├── strategy_manager.py
│   │   ├── position.py
│   │   ├── position_manager.py
│   │   ├── order.py
│   │   └── order_manager.py
│   │
│   ├── engine/           # 策略引擎
│   │   ├── framework.py       # 策略框架
│   │   ├── llm_generator.py  # LLM 策略生成器
│   │   ├── runner.py         # 策略執行器
│   │   ├── backtest_engine.py # backtesting.py 回測引擎
│   │   ├── rule_engine.py   # 規則引擎
│   │   └── rule_parser.py   # 規則解析器
│   │
│   ├── agent/            # AI Agent
│   │   ├── tools.py          # 交易工具
│   │   ├── prompts.py       # 提示詞
│   │   └── providers.py     # LLM 提供者
│   │
│   ├── market/           # 市場數據
│   │   ├── data_service.py
│   │   └── price_cache.py
│   │
│   ├── storage/          # 資料儲存
│   │   ├── json_store.py
│   │   └── models.py
│   │
│   ├── risk/            # 風控管理
│   │   └── risk_manager.py
│   │
│   ├── notify/          # 通知系統
│   │   └── telegram.py  # Telegram 通知 + Bot
│   │
│   ├── web/            # Web 界面
│   │   ├── app.py          # Flask 應用
│   │   └── routes/         # API 路由
│   │       ├── status.py
│   │       ├── strategies.py
│   │       ├── positions.py
│   │       ├── risk.py
│   │       └── backtest.py
│   │
│   ├── analysis/        # 績效分析模組
│   │   ├── signal_recorder.py       # 訊號記錄器
│   │   ├── performance_analyzer.py  # 績效分析器
│   │   ├── strategy_reviewer.py     # LLM 策略審查
│   │   └── auto_review_scheduler.py # 自動 Review 排程
│   │
│   └── config.py        # 配置載入
│
├── documents/           # 說明文件
│   ├── Features.md
│   ├── System_Architecture.md
│   ├── User_Manual.md
│   └── Web_Interface.md
│
├── tests/               # 測試檔案
│   ├── test_trading.py
│   ├── test_fallback.py
│   ├── test_create_flow.py
│   └── conftest.py
│
└── workspace/          # 執行時資料
    ├── strategies/       # 策略配置（含版本）
    │   └── TMF260001_v1.json
    ├── positions/        # 部位記錄
    │   └── TMF260001_positions.json
    ├── orders/           # 訂單記錄
    │   └── TMF260001_orders.json
    ├── signals/         # 訊號記錄（含版本）
    │   └── TMF260001_v1.json
    ├── backtests/       # 回測圖表
    │   └── TMF260001.png
    ├── performance.json # 績效數據
    └── logs/
        └── trading.log
```

## 技術

- Python 3.10+
- Shioaji API
- pandas_ta
- backtesting.py
- python-telegram-bot
- LLM (Ollama/OpenAI/Anthropic)

## 版本資訊

| 版本 | 說明 |
|------|------|
| 1.0.0 | 初始版本，支援3個策略 |
| 2.0.0 | 新增 LLM 策略生成器與策略框架 |
| 2.1.0 | 新增 Telegram Bot 接收機制 |
| 3.0.0 | 新增自我優化系統 - 第一階段 |
| 3.1.0 | 新增自我優化系統 - 第二階段 |
| 3.2.0 | 新增自我優化系統 - 第三階段 |
| 3.3.0 | 新增策略程式碼兩階段驗證（LLM審查+歷史K棒回測）|
| 3.4.0 | 新增 BacktestEngine 完整歷史回測系統 |
| 3.5.0 | 新增 Web 界面、刪除策略二次確認、回測圖表匯出 |

## License

MIT
