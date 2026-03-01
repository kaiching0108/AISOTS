# Web Interface 開發者指南

## 1. 概述

> **重要資訊**：**Web Interface 是 AISOTS 的主要操作介面**。Telegram 機器人僅用於發送通知（如成交通知、風控警告），**不再接受任何指令**。

Web Interface 是 AISOTS 的網頁介面，提供圖形化操作方式，讓用戶可以透過瀏覽器管理策略和查看系統狀態。

### 功能範圍

| Phase | 功能 | 說明 |
|-------|------|------|
| Phase 1 | 系統總覽 | 系統狀態、策略數、部位數、當日損益、**重要交易訊息** |
| Phase 1 | 策略管理 | 列表、啟用、停用、刪除（含 Modal 確認）、**回測** |
| Phase 1 | 部位查詢 | 部位列表、損益顯示 |
| Phase 1 | **訂單查詢** | **訂單列表、狀態、原因、成交價** |
| Phase 1 | 風控狀態 | 風控參數顯示 |
| Phase 1 | 歷史回測 | 執行回測並顯示結果 |
| Phase 2 | 策略建立 | 表單式建立策略、兩階段驗證 |
| Phase 2 | 回測分析 | 策略分析說明、圖表顯示 |

---

## 2. 系統需求

- Python 3.10+
- Flask 3.x
- 現代瀏覽器（Chrome, Firefox, Safari, Edge）

### 安裝依賴

```bash
pip install flask
```

---

## 3. 安裝與啟動

### 啟動方式

1. 編輯 `config.yaml` 啟用 Web 界面：

```yaml
web:
  enabled: true
  host: "127.0.0.1"
  port: 5000
```

2. 啟動主系統：

```bash
python main.py
```

3. 打開瀏覽器訪問：`http://127.0.0.1:5000`

---

## 4. 架構設計

### 檔案結構

```
src/web/
├── __init__.py           # Package init
├── app.py               # Flask 應用工廠
├── routes/
│   ├── __init__.py
│   ├── status.py        # /api/status
│   ├── strategies.py     # /api/strategies
│   ├── positions.py     # /api/positions
│   ├── risk.py         # /api/risk
│   ├── backtest.py     # /api/backtest
│   └── create.py       # /api/strategies/preview, /api/strategies/confirm

src/web/templates/
├── base.html            # 基礎模板
├── index.html          # 首頁
├── strategies.html      # 策略頁面
├── positions.html      # 部位頁面
└── create_strategy.html # 策略建立頁面
```

### 設計原則

- **錯誤隔離**：Web 模組錯誤不影響主交易系統
- **配置驅動**：透過 `config.yaml` 控制開關
- **Async 處理**：使用 `nest_asyncio` 處理 Flask 中的 async 調用

---

## 5. API 列表

### 基礎 API

| Method | URL | 說明 |
|--------|-----|------|
| GET | `/api/status` | 系統狀態 |
| GET | `/api/strategies` | 策略列表 |
| GET | `/api/strategies/<id>` | 策略詳情 |
| POST | `/api/strategies/<id>/enable` | 啟用策略 |
| POST | `/api/strategies/<id>/disable` | 停用策略（需確認時回傳 Modal 資料）|
| DELETE | `/api/strategies/<id>` | 刪除策略（需確認時回傳 Modal 資料）|
| DELETE | `/api/strategies/<id>/delete` | 確認刪除（強制平倉）|
| GET | `/api/positions` | 部位列表 |
| GET | `/api/orders` | **訂單列表（含原因欄位）** |
| GET | `/api/risk` | 風控狀態 |
| GET | `/api/trade-logs` | **交易日誌（重要交易訊息）** |
| GET | `/api/trade-logs/stats` | **交易日誌統計** |
| POST | `/api/backtest/<id>` | 執行回測 |

### 策略建立 API（Phase 2）

| Method | URL | 說明 |
|--------|-----|------|
| GET | `/strategies/create` | 策略建立頁面 |
| POST | `/api/strategies/preview` | 生成策略描述預覽 |
| POST | `/api/strategies/confirm` | 確認並生成策略代碼（含驗證）|

### API 詳細說明

#### POST /api/strategies/preview

生成策略描述預覽，讓用戶確認策略參數。

**請求參數：**
```json
{
    "symbol": "TMF",           // 期貨代碼：TXF/MXF/TMF
    "prompt": "RSI 低於 30 買入", // 策略描述
    "direction": "long",       // 交易方向：long/short/both
    "timeframe": "15m",        // 時間框架
    "stop_loss": 30,           // 停損點數
    "take_profit": 50,         // 止盈點數
    "quantity": 1              // 交易口數
}
```

**回應：**
```json
{
    "success": true,
    "data": {
        "symbol": "TMF",
        "prompt": "完整策略描述...",
        "direction": "long",
        "timeframe": "15m",
        "stop_loss": 30,
        "take_profit": 50,
        "quantity": 1
    }
}
```

#### POST /api/strategies/confirm

確認並生成策略代碼，執行兩階段驗證。

**請求參數：** 同 `/api/strategies/preview`

**回應（成功）：**
```json
{
    "success": true,
    "data": {
        "strategy_id": "TMF260001",
        "name": "策略_TMF",
        "verification": {
            "stage1_passed": true,
            "stage1_error": null,
            "stage2_passed": true,
            "stage2_error": null,
            "trade_count": 5,
            "win_rate": 60,
            "total_return": 5.2
        },
        "chart_path": "/workspace/backtests/TMF260001_v1_20260227120000.html",
        "report_path": "/workspace/backtests/TMF260001_v1_20260227120000.txt",
        "analysis": "📊 策略分析...\n\n✅ 策略在回測期間為您賺了..."
    }
}
```

**說明：**
- `chart_path`：回測圖表 HTML 檔案路徑，用於 iframe 嵌入顯示
- `report_path`：回測文字報告 TXT 檔案路徑（v4.6.0+ 新增）
- `analysis`：策略分析文字
- `verification.trade_count`：回測交易次數
- `verification.win_rate`：勝率（%）
- `verification.total_return`：總回報率（%）

#### GET /api/backtest/<id>/check

檢查是否存在最新的回測報告。

**回應：**
```json
{
    "has_report": true,
    "chart_path": "/workspace/backtests/TMF260001_v1_20260301003042.html",
    "report_path": "/workspace/backtests/TMF260001_v1_20260301003042.txt",
    "report_time": "2026-03-01 00:30:42",
    "time_ago": "40 分鐘前",
    "strategy_name": "策略_TMF",
    "version": 1
}
```

**用途：**
- 顯示"查看已存在報告 / 執行新回測"選擇 Modal
- 避免重複執行相同的回測

### Modal 確認流程

當操作有風險時（如停用/刪除有部位的策略），API 會回傳：

```json
{
    "needs_confirmation": true,
    "title": "確認停用",
    "message": "此策略仍有部位，停用將強制平倉",
    "position": {
        "symbol": "TXF",
        "quantity": 1,
        "direction": "Buy"
    },
    "risks": [
        "強制平倉 (1口 TXF)",
        "策略將被停用"
    ]
}
```

前端收到此回應後，顯示 Modal 確認視窗，用戶確認後再執行確認 API。

---

## 6. 前端模板說明

### 基礎模板 (base.html)

包含：
- Navbar 導航
- 統一 CSS 樣式
- Modal 確認視窗組件
- JavaScript API 輔助函數
- 30 秒自動刷新

### 頁面模板

| 頁面 | 路由 | 功能 |
|------|------|------|
| 首頁 | `/` | 系統總覽、策略概覽、部位概覽、風控狀態、**重要交易訊息** |
| 策略頁面 | `/strategies` | 策略列表、啟用/停用/刪除按鈕，回測按鈕 |
| 部位頁面 | `/positions` | 部位列表、損益顯示 |
| **訂單頁面** | **`/orders`** | **訂單列表、狀態、原因、成交價** |
| 策略建立頁面 | `/strategies/create` | 策略參數輸入、預覽、驗證、進度條 |

### 策略建立頁面功能（Phase 2）

1. **參數輸入**
   - 期貨代碼選擇（TXF/MXF/TMF）
   - 交易方向選擇（做多/做空/多空都做，預設做多）
   - 策略提示詞輸入
   - 時間框架、停損、止盈、口數

2. **預覽生成**
   - 點擊 Generate 按鈕呼叫 LLM
   - 生成完整策略描述

3. **確認與驗證**
   - 點擊確認按鈕生成策略代碼
   - 兩階段驗證（LLM Review + Backtest）
   - 進度條顯示當前階段
   - 回測圖表與分析說明

### 訂單查詢頁面功能

**訂單列表** (`/orders`)：
- 顯示所有訂單（開倉/平倉）
- **原因欄位**：顯示訂單觸發原因（如「策略訊號: buy」、「平倉: 策略訊號或停損止盈」）
- 支援狀態篩選（待處理/已提交/已成交/已取消/已拒絕）
- 支援策略篩選
- 支援日期篩選（今日/全部）
- 按時間排序（最新在前）

**訂單欄位**：
| 欄位 | 說明 |
|------|------|
| 時間 | 訂單建立時間 |
| 策略 | 策略 ID |
| 期貨 | 合約代碼 |
| 方向 | 買進/賣出（顏色區分）|
| 口數 | 交易數量 |
| 價格 | 訂單價格或「市價」|
| 狀態 | Pending/Submitted/Filled/Cancelled/Rejected |
| **原因** | **訂單觸發原因** |
| 成交價 | 實際成交價格 |

### 交易日誌功能

**重要交易訊息**（系統總覽頁面底部）：

顯示最近的交易日誌，包括：
- **下單成功**（綠色）：策略開倉訂單
- **平倉完成**（藍色）：部位平倉訂單
- **風控擋單**（紅色）：風控阻擋的訂單
- **下單失敗**（黃色）：失敗的訂單嘗試

**功能特性**：
- 顯示最近 50 筆交易日誌
- 支援依事件類型過濾（全部/下單成功/平倉/風控擋單/下單失敗）
- 自動刷新（每 30 秒）
- 手動刷新按鈕
- 統計資訊（24小時/7天筆數、各類型數量）

**日誌內容**：
- 策略名稱與 ID
- 時間戳
- 交易訊息（如「策略A 買進 1口 @ 18500」）
- 損益資訊（平倉時顯示）
- 事件類型標籤

---

## 7. 考量點（供開發者參考）

### 7.1 安全性

- **認證**：目前無登入機制，僅適用於本機開發
- **CORS**：預設關閉，仅允许同源请求
- **部署**：正式環境建議使用 VPN 或 SSH tunnel 訪問
- **Telegram**：機器人僅用於通知，**不接收指令**，所有操作透過 Web Interface 完成

### 7.2 資料更新

- **刷新機制**：前端每 30 秒自動輪詢刷新資料
- **手動刷新**：頁面右上角或按下 F5

### 7.3 錯誤處理

- **Timeout**：API 請求有基本錯誤處理
- **回應格式**：失敗時回傳 `{success: false, error: "訊息"}`

### 7.4 RWD

- **響應式設計**：Phase 1 不支援，僅最佳化桌面瀏覽器

### 7.5 即時通知

- **Phase 1**：不支援即時推播
- **未來規劃**：可考慮 WebSocket 實現即時通知

### 7.6 部署

- **位址綁定**：預設 `127.0.0.1`（本機）
- **Port 配置**：可透過 `config.yaml` 修改
- **Daemon 模式**：Web 執行緒設為 daemon，隨主系統關閉

---

## 8. 回測引擎 K 棒數量限制

### K 棒計算邏輯

回測引擎根據時間框架計算 K 棒數量：

| Timeframe | 天數 | 每天K棒數 | 計算結果 | 實際上限 |
|-----------|------|----------|---------|---------|
| 1m | 7 | 1,440 | 10,080 | 10,000 |
| 5m | 14 | 288 | 4,032 | 4,032 |
| 15m | 30 | 96 | 2,880 | 2,880 |
| 30m | 30 | 48 | 1,440 | 1,440 |
| 60m/1h | 90 | 24 | 2,160 | 2,160 |
| 1d | 365 | 1 | 365 | 365 |

### 配置說明

在 `src/engine/backtest_engine.py` 中：

```python
class BacktestEngine:
    # 每個 timeframe 每天的 K 棒數量
    KBARS_PER_DAY = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "30m": 48,
        "60m": 24,
        "1h": 24,
        "1d": 1,
    }
    
    # 最大 K 棒數量限制（避免回測太久）
    MAX_KBARS = 10000
```

### 為什麼要限制？

- 避免回測時間過長
- 確保用戶體驗
- 足夠的歷史數據進行策略驗證

---

## 9. 未來擴充（Phase 2+）

| 功能 | 說明 |
|------|------|
| 目標設定 | 設定策略目標 |
| 策略優化 | 執行優化流程 |
| 圖表顯示 | 績效圖表、部位變化圖 |
| 即時通知 | WebSocket 推播 |
| 響應式設計 | 支援手機/平板 |

---

## 10. 交易方向說明

### 策略方向選項

策略建立時，用戶可以選擇交易方向：

| 選項 | 值 | 說明 |
|------|-----|------|
| 做多 (Long) | `long` | 只產生 buy 訊號，不產生 sell 訊號 |
| 做空 (Short) | `short` | 只產生 sell 訊號，不產生 buy 訊號 |
| 多空都做 | `both` | 可以產生 buy 和 sell 訊號 |

### 預設值

- **預設為做多 (long)**：符合多數投資者的交易習慣

### 實作位置

- **前端**：`src/web/templates/create_strategy.html`
- **後端 API**：`src/web/routes/create.py`
- **策略模型**：`src/trading/strategy.py`（`direction` 欄位）
- **LLM 生成器**：`src/engine/llm_generator.py`（傳遞方向給 LLM）

---

## 11. 回測分析說明

### 分析維度

策略建立完成後，會在回測圖表下方顯示策略分析：

| 維度 | 指標 | 說明 |
|------|------|------|
| 總結 | Total Return | 是否賺錢 |
| 風控 | Max Drawdown | 最大虧損 |
| 穩定性 | Sharpe Ratio | 風險調整後收益 |
| 勝率 | Win Rate | 正確率 |
| 盈虧比 | Profit Factor | 賺赔比 |
| 手續費 | Commission | 回測期間手續費合計 |

### 分析範例

```
✅ 策略在回測期間為您賺了 +5,200 元

📈 風控評估
✅ 最大回撤僅 -3.2%，風險控制良好

📊 穩定性
✅ 夏普比率 1.52，風險調整後收益優秀

🎯 交易頻率
✅ 交易次數 10 次，頻率合理

🏆 勝率
✅ 勝率 60%，表現優異

💰 盈虧比
✅ 盈虧比 1.8，賺多賠少

💸 手續費
📊 回測期間手續費合計：280 元

---
💡 提醒：過去表現不代表未來收益，請謹慎評估風險后再實際交易。
```

---

## 12. 故障排除

### 常見問題

| 問題 | 可能原因 | 解決方案 |
|------|----------|----------|
| 無法訪問頁面 | Web 未啟用 | 檢查 `config.yaml` 中 `web.enabled: true` |
| 資料載入失敗 | 主系統未啟動 | 確保 `python main.py` 正常運行 |
| Port 被佔用 | 5000 已被使用 | 修改 `config.yaml` 中 `web.port` |
| 策略驗證失敗 | LLM 或 Backtest 錯誤 | 查看終端機日誌 |
| 回測圖表無法顯示 | 圖表生成失敗 | 查看終端機日誌 |

### 日誌

- Web 錯誤會記錄到主系統日誌
- 可查看 `workspace/logs/` 目錄
- 策略驗證詳細日誌會顯示在終端機

---

## 13. 相關檔案

- `config.yaml` - 配置文件
- `src/web/` - Web 原始碼
- `src/engine/backtest_engine.py` - 回測引擎
- `src/engine/llm_generator.py` - LLM 策略生成器
- `src/trading/strategy.py` - 策略模型
- `src/config.py` - 配置載入
- `main.py` - 主系統入口
