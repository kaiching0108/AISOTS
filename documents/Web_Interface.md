# Web Interface 開發者指南

## 1. 概述

Web Interface 是 AISOTS 的網頁介面，提供圖形化操作方式，讓用戶可以透過瀏覽器管理策略和查看系統狀態。

### 功能範圍（Phase 1）

| 功能 | 說明 |
|------|------|
| 系統總覽 | 系統狀態、策略數、部位數、當日損益 |
| 策略管理 | 列表、啟用、停用、刪除（含 Modal 確認）|
| 部位查詢 | 部位列表、損益顯示 |
| 風控狀態 | 風控參數顯示 |
| 歷史回測 | 執行回測並顯示結果 |

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
└── routes/
    ├── __init__.py
    ├── status.py        # /api/status
    ├── strategies.py   # /api/strategies
    ├── positions.py    # /api/positions
    ├── risk.py        # /api/risk
    └── backtest.py    # /api/backtest

src/web/templates/
├── base.html           # 基礎模板
├── index.html         # 首頁
├── strategies.html    # 策略頁面
└── positions.html    # 部位頁面
```

### 設計原則

- **執行緒安全**：使用 `threading.Lock` 保護共享狀態
- **錯誤隔離**：Web 模組錯誤不影響主交易系統
- **配置驅動**：透過 `config.yaml` 控制開關

---

## 5. API 列表

### Phase 1 API

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
| GET | `/api/risk` | 風控狀態 |
| POST | `/api/backtest/<id>` | 執行回測 |

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
| 首頁 | `/` | 系統總覽、策略概覽、部位概覽、風控狀態 |
| 策略頁面 | `/strategies` | 策略列表、啟用/停用/刪除按鈕、回測按鈕 |
| 部位頁面 | `/positions` | 部位列表、損益顯示 |

---

## 7. 考量點（供開發者參考）

### 7.1 安全性

- **認證**：目前無登入機制，僅適用於本機開發
- **CORS**：預設關閉，仅允许同源请求
- **部署**：正式環境建議使用 VPN 或 SSH tunnel 訪問

### 7.2 資料更新

- **刷新機制**：前端每 30 秒自動輪詢刷新資料
- **手動刷新**：頁面右上角或按下 F5

### 7.3 錯誤處理

- **Timeout**：API 請求有基本錯誤處理
- **回應格式**：失敗時回傳 `{success: false, error: "訊息"}`

### 7.4 RWD

- **響應式設計**：Phase 1 不支援，僅最佳化桌面瀏覽器

### 7.5 執行緒安全

- **Lock 機制**：使用 `threading.Lock` 保護 trading_tools 存取
- **隔離運行**：Web 在獨立執行緒運行

### 7.6 即時通知

- **Phase 1**：不支援即時推播
- **未來規劃**：可考慮 WebSocket 或 Server-Sent Events

### 7.7 部署

- **位址綁定**：預設 `127.0.0.1`（本機）
- **Port 配置**：可透過 `config.yaml` 修改
- **Daemon 模式**：Web 執行緒設為 daemon，隨主系統關閉

---

## 8. 未來擴充（Phase 2+）

| 功能 | 說明 |
|------|------|
| 策略建立 | 表單式建立策略 |
| 目標設定 | 設定策略目標 |
| 策略優化 | 執行優化流程 |
| 圖表顯示 | 績效圖表、部位變化圖 |
| 即時通知 | WebSocket 推播 |
| 響應式設計 | 支援手機/平板 |

---

## 9. 故障排除

### 常見問題

| 問題 | 可能原因 | 解決方案 |
|------|----------|----------|
| 無法訪問頁面 | Web 未啟用 | 檢查 `config.yaml` 中 `web.enabled: true` |
| 資料載入失敗 | 主系統未啟動 | 確保 `python main.py` 正常運行 |
| Port 被佔用 | 5000 已被使用 | 修改 `config.yaml` 中 `web.port` |

### 日誌

- Web 錯誤會記錄到主系統日誌
- 可查看 `workspace/logs/` 目錄

---

## 10. 相關檔案

- `config.yaml` - 配置文件
- `src/web/` - Web 原始碼
- `src/config.py` - 配置載入
- `main.py` - 主系統入口
