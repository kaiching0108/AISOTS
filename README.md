# AI 期貨交易系統 (AI Futures Trading System)

使用 Shioaji API 的 AI 驅動期貨交易系統，支援 LLM 策略生成。

## 功能特色

- 🤖 **AI 策略生成** - 用自然語言描述策略，LLM 自動生成程式碼
- 🎯 **目標驅動策略** - 只需給出目標（如「每日賺500元」），LLM 自動推斷參數並確認後建立
- 📊 **多種 LLM 支援** - Ollama, OpenAI, Anthropic, DeepSeek, OpenRouter
- 📈 **技術指標** - 支援 RSI, MACD, SMA, EMA, BB, ATR, KD 等（使用 pandas_ta）
- 🔔 **Telegram 通知** - 下單、成交、風控警告即時通知
- 🛡️ **風控機制** - 單日虧損、最大部位、下單頻率限制
- 💾 **資料持久化** - JSON 格式儲存策略、部位、訂單

## 安裝

```bash
git clone https://github.com/kaiching0108/ai_futures_trading.git
cd ai_futures_trading
pip install -r requirements.txt
```

## 設定

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
```

## 使用方式

```bash
python main.py
```

### 建立策略的兩種方式

#### 方式一：手動輸入完整參數
```
建立策略 ID=my_rsi, 名稱=RSI策略, 代碼=TXF, 描述=RSI低於30買入高於70賣出, 週期=15m, 數量=1, 停損=50, 停利=100
```

#### 方式二：目標驅動（自動推斷參數）
```
幫我設計一個 RSI 策略
設計一個每日賺500元的策略
```

LLM 會自動推斷參數，展示給用戶確認後建立策略。

### 指令列表

| 指令 | 說明 |
|------|------|
| status | 系統狀態 |
| positions | 目前部位 |
| strategies | 策略列表 |
| enable \<ID\> | 啟用策略 |
| disable \<ID\> | 停用策略 |

## 專案結構

```
ai_futures_trading/
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
│   │   └── telegram.py
│   │
│   └── config.py        # 配置載入
│
├── documents/           # 說明文件
│   ├── Features.md
│   ├── System_Architecture.md
│   └── User_Manual.md
│
├── tests/               # 測試檔案
│   └── test_trading.py
│
└── workspace/          # 執行時資料
    ├── strategies.json
    ├── positions.json
    ├── orders.json
    └── logs/
```

## 技術

- Python 3.10+
- Shioaji API
- pandas_ta
- LLM (Ollama/OpenAI/Anthropic)

## License

MIT
