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

**最後更新**: 2026-03-07
