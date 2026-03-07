# AI Self-Optimizing Trading System (AISOTS)

使用 Shioaji API 的 AI 驅動期貨交易系統，支援 LLM 策略生成與自我優化。

## 功能特色

- 🤖 **AI策略生成** - 用自然語言描述策略，LLM 自動生成程式碼
- 🎯 **目標驅動策略** - 只需給出目標（如「每日賺500元」），LLM 自動推斷參數並確認後建立
- 🔒 **策略驗證** - 建立策略時自動執行兩階段驗證（LLM審查比對程式碼是否符合策略描述 + 歷史K棒回測）
- 📊 **歷史回測** - 執行完整歷史回測，啟用策略前參考過去績效（含圖表）
- 📈 **自我優化系統** - 設定目標 → LLM 設計策略 → 執行 → 績效分析 → LLM 審查優化 → 達成目標
- 🔔 **Telegram 通知** - 交易提醒、风控警告即时推送（仅通知，不接受命令）
- 🌐 **Web 界面** - 图形化管理策略、部位、回测
- 📊 **多種 LLM 支援** - Ollama, OpenAI, Anthropic, OpenRouter
- 🛡️ **風控機制** - 單日虧損、最大部位、下單頻率限制
- 💾 **資料持久化** - JSON、SQLite 格式儲存策略、部位、訂單、訊號、歷史K-bar
- ⚡ **模擬交易機制** - 模擬模式趨勢模擬演算法、回測、模擬下單


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

# Web 界面配置（主要操作平台）
web:
  enabled: true          # 啟用 Web 界面（主要操作平台）
  host: "127.0.0.1"     # 綁定位址（本機）
  port: 5001            # 連接埠

# K-bar 數據更新服務
data_update:
  enabled: true         # 開啟 K-bar 更新服務
  update_time: "06:00" # 每日清晨抓取
  
  storage:              # 存儲配置
    max_records: 600000 # 最大儲存量：60 萬筆
  
  initial_fetch:        # 初始抓取
    daily_limit: 20000  # 初始每日上限
    max_total: 300000   # 每個 symbol 最大總筆數
  
  daily:                # 每日定時抓取
    daily_max: 10000    # 每日上限（所有 symbol 合計）

# 自動 LLM Review
auto_review:
  enabled: false        # 是否啟用自動 Review

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

│   ├── services/         # 背景服務
│   │   ├── data_updater.py              # K-bar 數據更新服務
│   │   └── realtime_kbar_aggregator.py  # 實時 K-bar 聚合器
│   │

│   ├── storage/          # 資料儲存
│   │   ├── json_store.py
│   │   └── models.py
│   │
│   ├── kbar_sqlite.py     # SQLite K 棒儲存（60 萬筆容量）
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

│   ├── config.py        # 配置載入

└── web/                # Web 界面（主要操作平台）
    └── 图形化管理策略、部位、回測、交易訊息

│
├── documents/           # 說明文件
│   ├── Features.md
│   ├── System_Architecture.md
│   ├── User_Manual.md
│   ├── Web_Interface.md   # Web 界面使用說明
│   └── SQLite_Storage.md  # K-bar 儲存規范
```

## 技術

- Python 3.10+
- Shioaji API
- pandas_ta
- backtesting.py
- python-telegram-bot
- LLM (Ollama/OpenAI/Anthropic)

## 版本資訊

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

## License

MIT
