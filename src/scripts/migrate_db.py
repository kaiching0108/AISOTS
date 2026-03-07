"""資料遷移腳本：將舊的混合代碼數據統一轉換為實際合約代碼

功能:
1. 識別並更新基本代碼（TXF → TXFR1）
2. 保留所有近月合約（TXFR1, MXFR1, TMFR1 等）
3. 將過期合約合併到對應的近月合約
4. 建立統一的實際代碼格式用於查詢和儲存
"""

import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Optional


def migrate_kbar_data(db_path: Optional[str] = None) -> dict:
    """遷移舊的 mixed symbol 數據為統一的實際合約代碼格式
    
    Args:
        db_path: SQLite 資料庫路徑（None 則使用預設位置）
        
    Returns:
        遷移統計數據
    """
    # 設定預設資料庫路徑
    if not db_path:
        home = Path.home()
        workspaces = [
            home / ".cache" / "AISOTS" / "kbar_data.sqlite",
            home / ".cache" / "AISOTS" / "kbars.sqlite"
        ]
        for p in workspaces:
            if p.exists():
                db_path = str(p)
                break
    
    if not db_path or not Path(db_path).exists():
        print(f"❌ 資料庫不存在：{db_path}")
        return {}
    
    conn = sqlite3.connect(f"sqlite:///{db_path}", uri=True)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("SQLite KBar 遷移工具")
    print("=" * 60)
    
    # 1. 確認 symbol_mapping 表存在
    cursor.execute("SELECT COUNT(*) FROM symbol_mapping")
    if cursor.fetchone()[0] == 0:
        print("⚠️  warning: symbol_mapping 表不存在，跳過遷移")
        conn.close()
        return {}
    
    # 載入映射關係
    cursor.execute("SELECT base_code, actual_code FROM symbol_mapping")
    mappings = {row[0]: row[1] for row in cursor.fetchall()}
    print(f"\n1. 檢查 symbol_mapping: {list(mappings.keys())}")
    
    # 2. 找出所有唯一的 symbol
    cursor.execute("SELECT DISTINCT symbol FROM kbars ORDER BY symbol")
    all_symbols = [row[0] for row in cursor.fetchall()]
    print(f"\n2. 當前資料庫中共 {len(all_symbols)} 個 unique symbols:")
    
    # 分類符號
    base_symbols = set()
    actual_symbols = set()
    mixed_symbols = []  # 包含基本代碼和過期合約
    valid_actuals = []  # 只有實際合約 code (含 R1)
    
    for sym in sorted(all_symbols):
        # 匹配格式：TXF, MXF, TMF（基本代碼）
        if re.match(r'^(TXF|MXF|TMF)$', sym):
            base_symbols.add(sym)
            mixed_symbols.append((sym, f"實際應遷移到 {mappings.get(sym, sym)}"))
        # 匹配格式：TXFR1, TXFF0624（近月合約）
        elif re.match(r'^(TXF|MXF|TMF)R1$', sym):
            actual_symbols.add(sym)
        # 其他都視為需要處理
        else:
            match = re.search(r'(TXF|MXF|TMF)(\d{4}(\d{2})?)', sym)
            if match:
                bc = match.group(1)  # TXF
                rest = match.group(2)  # F0624, R1 etc.
                if not sym.endswith('R1') and 'TXFR1' in mappings:
                    mixed_symbols.append((sym, f"過期的代碼：{bc}{rest}"))
    
    print(f"   - 基本代碼 (TXF/txf): {len(base_symbols)}")
    print(f"   - 實際近月合約 (TXFR1 ...): {len(actual_symbols)}")
    print(f"   - 需要處理的：{len(mixed_symbols)}")
    
    # 3. 執行遷移
    updated_count = 0
    if base_symbols:
        print(f"\n3. 更新基本代碼 → 實際合約代碼...")
        for base in sorted(base_symbols):
            actual = mappings.get(base, base)
            cursor.execute(
                "UPDATE kbars SET symbol = ? WHERE symbol = ?",
                (actual, base)
            )
            count = cursor.rowcount
            updated_count += count
            if count:
                print(f"   遷移 {base} → {actual}: {count:,}筆")
    
    # 4. 合併過期合約到對應實際代碼（可選）
    # 例如：TXFF0624→TXFR1, TXF0725→TXFR1
    print(f"\n4. (選項) 處理近月合約過期數據...")
    
    base_to_actual = {base: mappings.get(base, base + 'R1') for base in [k for k,v in mappings.items() if re.match(r'^(TXF|MXF|TMF)$', k)]}
    # 合併近月（但保留 TXFR1 本身）
    
    if updated_count > 0 or mixed_symbols:
        print(f"\n5. 遷移完成")
        status = cursor.execute(
            "SELECT symbol, COUNT(*) as cnt FROM kbars GROUP BY symbol ORDER BY length(symbol), cnt"
        ).fetchall()
        print(f"   DB 中的 unique symbols ({len(status)}):")
        for sym, cnt in status:
            bar_count = ', '.join([str(x) for x in range(cnt)]) if cnt < 10 else f'{cnt:,}'
            actual_code = mappings.get(sym, sym)
            print(f"     • {sym:8s} → {actual_code}: {cnt:,}筆")
    
    conn.commit()
    conn.close()
    
    return {
        'total_before_migration': len(all_symbols),
        'updated_records': updated_count,
        'symbols_after': len(cursor.execute('SELECT DISTINCT symbol FROM kbars').fetchall()),
    }


if __name__ == "__main__":
    import shutil
    home = Path.home()
    db_path = home / ".cache" / "AISOTS" / "kbar_data.sqlite"
    backup_path = f"{db_path}~.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 建立備份（選擇性）
    if db_path.exists():
        print(f"\n✅ 備份前狀態：{db_path}")
        backup_path = f"{db_path}~.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(str(db_path), str(backup_path))
    
    # 執行遷移
    result = migrate_kbar_data(str(db_path) if Path(db_path).exists() else None)
    print(f"\n📊 📊 Result: {result}")
