# SQLite Storage 存儲規範

## 1. Symbol Mapping 規則

### 存儲格式
- SQLite 只儲存 **實際合約代碼**：`TXFR1`、`MXFR1`、`TMFR1`
- 基本代碼（`TXF`、`MXF`、`TMF`）**不會**被儲存
- 系統自動維護 `symbol_mapping` 表

### Mapping 規則
| 基本代碼 | 實際代碼 |
|---|---|
| TXF | TXFR1 |
| MXF | MXFR1 |
| TMF | TMFR1 |

---

## 2. Mapping 方法

### `get_actual_code(base_code)`
**用途**：基本代碼 → 實際代碼

```python
actual = sqlite.get_actual_code('TMF')  # → 'TMFR1'
```

**使用時機**：
- SQL 插入時（確保使用實際代碼）
- SQL 查詢時（確保能找到資料）

### `get_base_code(actual_code)`
**用途**：實際代碼 → 基礎代碼

```python
base = sqlite.get_base_code('TMFR1')  # → 'TMF'
```

**使用時機**：
- 報告顯示基礎代碼
- 使用者 UI 簡化顯示

---

## 3. SQL 查詢規範

### ✅ 正確寫法
```python
# 所有查詢方法都使用 get_actual_code()
kbars = await sqlite.get_kbars('TMF', start, end)  
# → 自動轉換為 TMFR1 查詢

latest = await sqlite.get_latest_kbar('MXF')
# → 自動轉換查詢
```

### ❌ 錯誤寫法
```python
# 會查無資料（因為資料庫只有 TMFR1）
kbars = sqlite.get_kbars('TMF', start, end)  # 不轉換
```

---

## 4. 重要 API 方法

| 方法 | 說明 | 自動轉換 |
|---|---|---|
| `get_kbars()` | 範圍查詢 | ✓ |
| `get_latest_kbar()` | 最新 K 棒 | ✓ |
| `get_oldest_kbar()` | 最舊 K 棒 | ✓ |
| `get_count()` | 資料數量 | ✓ |
| `get_today_count()` | 今日數量 | ✓ |
| `insert_kbars()` | 插入 K 棒 | ✓ |

---

## 5. 程式碼範例

### 完整範例
```python
from src.storage.kbar_sqlite import KBarSQLite

sqlite = KBarSQLite(Path('workspace/kbars.sqlite'))

# 插入時（自動使用實際代碼）
count = sqlite.insert_kbars('TMF', kbars_data)

# 查詢時（自動轉換）
kbars = sqlite.get_kbars('TMF', start_ts, end_ts)
latest = sqlite.get_latest_kbar('TMF')

# 基礎代碼統計
total = sqlite.get_count('TMF')
today = sqlite.get_today_count('TXF')
```

---

## 6. 常見問題

### Q: 為什麼用基本代碼查無資料？
A: 因為資料庫只存實際代碼（`TMFR1`），必須使用 `get_actual_code()` 轉換查詢。

### Q: 如何確認 Symbol 是否正確？
A: 使用 `status` 方法：
```python
status = sqlite.get_status()
# 回傳所有存儲的實際代碼及數量
```

### Q: 可以儲存基本代碼資料嗎？
A: 不建議。系統設計為只儲存實際代碼，基本代碼只是 Mapping 參考。

---

## 7. 測試工具

### 快速測試
```python
# 測試查詢
result = sqlite.get_kbars('TMF', 0, 9999999999)
print(f'資料筆數：{len(result)}')
```

### 狀態檢查
```python
status = sqlite.get_status()
print(f'總筆數：{status["total_count"]}')
print(f'代碼：{status["symbols"]}')
```

---

## 6. fetch_log 表

用於記錄補抓結果，避免重複檢查已確認的日期。

### 表結構
```sql
CREATE TABLE IF NOT EXISTS fetch_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    check_date TEXT NOT NULL,
    records_fetched INTEGER,
    status TEXT,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, check_date)
);
```

### 欄位說明
| 欄位 | 類型 | 說明 |
|------|------|------|
| symbol | TEXT | 期貨代碼（如 TXFR1） |
| check_date | TEXT | 檢查的日期 (YYYY-MM-DD) |
| records_fetched | INTEGER | 取得的資料筆數 |
| status | TEXT | 'success'（有資料）/ 'no_data'（無資料，假日）/ 'error'（錯誤） |
| checked_at | TIMESTAMP | 檢查時間 |

### 用途
- 避免重複補抓已確認無資料的日期（假日）
- 避免重複補抓已有資料的日期
- 工作日缺口和交易時段異常檢查時排除已確認的日期

---

## 7. 完整性檢查方法

### check_workday_gaps(symbol)
檢查工作日是否有整日遺漏（排除已確認無資料的日期）。

```python
result = sqlite.check_workday_gaps('TXFR1')
# 返回:
{
    "days_checked": 100,      # 檢查的天數
    "workday_gaps": 2,        # 工作日缺口數（需補抓）
    "weekend_gaps": 15,       # 週末天數（正常）
    "workday_gap_dates": ['2026-02-13', '2026-02-14'],  # 缺口日期
    "confirmed_no_data": 6     # 已確認無資料的天數
}
```

### check_trading_hours_completeness(symbol)
檢查交易時段數據完整性（排除已確認的日期）。

```python
result = sqlite.check_trading_hours_completeness('TXFR1')
# 返回:
{
    "days_checked": 100,      # 檢查的天數
    "avg_count": 830,         # 平均每天筆數
    "suspicious_days": 1,      # 異常天數（低於平均95%）
    "suspicious_details": [{   # 異常詳情
        "date": "2026-03-06",
        "count": 424,
        "expected": 830,
        "gap": 406
    }],
    "confirmed_no_data": 6,   # 已確認無資料的天數
    "confirmed_with_data": 3  # 已確認有資料的天數
}
```

### log_fetch_attempt(symbol, check_date, records_fetched, status)
記錄補抓結果。

```python
# 記錄成功
sqlite.log_fetch_attempt('TXFR1', '2026-03-06', 1140, 'success')

# 記錄無資料（假日）
sqlite.log_fetch_attempt('TXFR1', '2026-02-13', 0, 'no_data')
```

### get_confirmed_no_data_dates(symbol)
獲取已確認無資料的日期集合。

```python
dates = sqlite.get_confirmed_no_data_dates('TXFR1')
# 返回: {'2026-02-13', '2026-02-16', ...}
```

### get_confirmed_with_data_dates(symbol)
獲取已確認有資料的日期集合。

```python
dates = sqlite.get_confirmed_with_data_dates('TXFR1')
# 返回: {'2026-03-06', '2026-03-07', ...}
```

### get_confirmed_dates(symbol)
獲取所有已確認的日期（不論成功或失敗）。

```python
dates = sqlite.get_confirmed_dates('TXFR1')
# 返回: {'2026-02-13', '2026-03-06', ...}
```

---

## 8. 時間戳格式規定

**重要**：Shioaji API 返回的 timestamp 為**奈秒（nanoseconds）**格式，儲存到 SQLite 時需轉換為**秒（seconds）**。

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

---

## 9. API 方法總覽

| 方法 | 說明 |
|------|------|
| `get_actual_code()` | 基本代碼 → 實際代碼 |
| `get_base_code()` | 實際代碼 → 基礎代碼 |
| `get_all_symbols()` | 獲取所有 symbol |
| `insert_kbars()` | 插入 K 棒（自動轉換時間戳）|
| `get_kbars()` | 範圍查詢 |
| `get_latest_kbar()` | 最新 K 棒 |
| `get_oldest_kbar()` | 最舊 K 棒 |
| `get_count()` | 資料數量 |
| `get_today_count()` | 今日數量 |
| `check_workday_gaps()` | 檢查工作日缺口 |
| `check_trading_hours_completeness()` | 檢查交易時段完整性 |
| `log_fetch_attempt()` | 記錄補抓結果 |
| `get_confirmed_no_data_dates()` | 獲取已確認無資料的日期 |
| `get_confirmed_with_data_dates()` | 獲取已確認有資料的日期 |
| `get_confirmed_dates()` | 獲取所有已確認的日期 |

---

## 10. 實盤即時 K 棒寫入

### 功能說明

實盤模式下，系統會將即時 K 棒即時寫入 SQLite，供圖表頁面即時顯示最新走勢。

### 運作機制

```
Shioaji API (tick)
    ↓
RealtimeKBarAggregator.process_tick()
    ↓ 跨分鐘時
KBarSQLite.insert_kbars() → kbars.sqlite
    ↓
/api/chart/kbars → 讀取 SQLite（含即時資料）
    ↓
前端每 15 秒輪詢更新圖表
```

### 啟用條件

- 僅在**實盤模式**啟用（`--simulate` 模擬模式不寫入）
- 系統初始化時自動檢測模式
- 日誌顯示：「即時 K-bar SQLite 寫入已啟用（實盤模式）」

### 相關程式碼

| 檔案 | 說明 |
|------|------|
| `src/services/realtime_kbar_aggregator.py` | 即時 K 棒聚合器，含 SQLite 寫入 |
| `main.py` | 初始化時連接 KBarSQLite 到 aggregator |

---

## 11. 數據來源標記 (source)

### 字段說明

kbars 表新增 `source` 字段，用於標記數據來源：

| source 值 | 說明 |
|----------|------|
| `historical` | 歷史數據（預設值，舊數據） |
| `initial` | 初始化抓取（系統啟動時） |
| `daily` | 每日定時抓取 |
| `realtime` | 實盤即時寫入（tick 聚合） |

### 查詢示例

```sql
-- 查看所有實時寫入的 K 棒
SELECT * FROM kbars WHERE source = 'realtime';

-- 查看某天的數據來源分布
SELECT source, COUNT(*) as count FROM kbars 
WHERE ts >= 1739539200 AND ts < 1739625600 
GROUP BY source;

-- 查看特定來源的最新數據
SELECT MAX(ts) as latest, source FROM kbars GROUP BY source;
```

---

**最後更新**: 2026-03-16
