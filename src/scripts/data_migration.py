"""資料遷移腳本：將舊的 TXF/TMF/MXF 基本代碼和近月合約統一轉換為實際合約代碼"""

import sqlite3
from pathlib import Path
from datetime import datetime

def migrate_kbar_data(db_path: Path):
    """資料遷移：將所有 kbars 的 symbol 更新為實際合約代碼"""
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # 載入 mapping
    cursor.execute("SELECT base_code, actual_code FROM symbol_mapping")
    mappings = {row[0]: row[1] for row in cursor.fetchall()}
    
    print("=== 開始資料遷移 ===")
    print(f"Mapping: {mappings}")
    
    # 找出所有需要更新的 symbol
    cursor.execute("SELECT DISTINCT symbol FROM kbars")
    existing_symbols = set(row[0] for row in cursor.fetchall())
    
    print(f"
發現的 actual_code: {existing_symbols}")
    
    migrated_count = 0
    original_migrated_before = False
    
    # 檢查是否有原來的原始代碼（如 TXF，MXF 等）
    for base, actual in mappings.items():
        if base in existing_symbols:
            print(f"\n⚠ 發現基本代碼：{base} (需要遷移到 {actual})")
            cursor.execute("UPDATE kbars SET symbol = ? WHERE symbol = ?", (actual, base))
            cnt = cursor.rowcount
            if cnt > 0:
                print(f"   遷移 {cnt} 筆 {base} → {actual}")
                migrated_count += cnt
            else:
                print(f"   (無 {base} 記錄)")
        
        # 檢查是否有近月合約如 MXF2025XX
        if "TMF" in base or "MXF" in base or "TXF" in base:
            for symbol in existing_symbols:
                if symbol.startswith(base) and len(symbol) > len(base):
                    original = mappings.get(symbol[:3], symbol[:3])
                    actual_target = mappings.get(symbol[:3], base)
                    # 如果原始 code 不在 mapping，保留原合約
                    if original != base:
                        print(f"   ⚠ 近月 {symbol} (實際代碼：{original})")
    
    conn.commit()
    
    # 查詢結果
    cursor.execute("SELECT DISTINCT symbol FROM kbars")
    new_symbols = set(row[0] for row in cursor.fetchall())
    
    print(f"\n=== 遷移完成 ===")
    print(f"已更新：{migrated_count} 筆記錄")
    print(f"剩餘 symbol: {new_symbols}")
    
    return migrated_count

if __name__ == "__main__":
    # 資料庫路徑
    db_path = Path.home() / ".cache" / "AISOTS" / "kbar_data.sqlite"
    
    count = migrate_kbar_data(db_path)
    print(f"\n總共遷移了 {count} 筆記錄")