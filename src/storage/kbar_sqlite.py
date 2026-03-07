"""K棒数据 SQLite 存储模块"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from loguru import logger


class KBarSQLite:
    """K棒数据 SQLite 存储"""
    
    MAX_RECORDS = 600000
    CLEANUP_THRESHOLD = 700000
    
    def __init__(self, db_path: Path):
        """初始化 SQLite 存储
        
        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """初始化库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS symbol_mapping (
                    base_code TEXT PRIMARY KEY,
                    actual_code TEXT NOT NULL
                )
            """)
            
            existing = conn.execute("SELECT COUNT(*) FROM symbol_mapping").fetchone()[0]
            if existing == 0:
                # 首次初始化：创建映射表
                mappings = [
                    ("TXF", "TXFR1"),
                    ("MXF", "MXFR1"),
                    ("TMF", "TMFR1"),
                ]
                conn.executemany(
                    "INSERT OR IGNORE INTO symbol_mapping (base_code, actual_code) VALUES (?, ?)",
                    mappings
                )
                logger.info("已初始化 symbol_mapping 表")
            # 不再删除已有数据，避免影响 get_actual_code() 映射
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS kbars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    open_price REAL NOT NULL,
                    high_price REAL NOT NULL,
                    low_price REAL NOT NULL,
                    close_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, ts)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_ts 
                ON kbars(symbol, ts)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol 
                ON kbars(symbol)
            """)
            
            conn.commit()
        
        logger.info(f"KBarSQLite 数据库初始化完成: {self.db_path}")
    
    def _load_mapping(self) -> Dict[str, str]:
        """加载 symbol mapping 表到内存"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT base_code, actual_code FROM symbol_mapping")
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def get_actual_code(self, base_code: str) -> str:
        """将基本代码转换为实际合约代码
        
        Args:
            base_code: 基本代码 (如 TXF, MXF, TMF)
            
        Returns:
            实际合约代码 (如 TXFR1, MXFR1, TMFR1)
        """
        mapping = self._load_mapping()
        return mapping.get(base_code, base_code)
    
    def get_base_code(self, actual_code: str) -> str:
        """将实际合约代码转换为基本代码
        
        Args:
            actual_code: 实际合约代码 (如 TXFR1, MXFR1, TMFR1)
            
        Returns:
            基本代码 (如 TXF, MXF, TMF)
        """
        mapping = self._load_mapping()
        for base, actual in mapping.items():
            if actual == actual_code:
                return base
        return actual_code
    
    def insert_kbars(self, symbol: str, kbars_data: Dict) -> int:
        """插入 K 棒數據（忽略重複）
        
        Args:
            symbol: 期貨代碼（基本代碼如 TXF，會自動轉換為 TXFR1）
            kbars_data: K 棒數據字典，包含 ts, open, high, low, close, volume
            
        Returns:
            插入的記錄數
        """
        ts_list = kbars_data.get('ts', [])
        if not ts_list:
            return 0
        
        # 使用 get_actual_code 確保 symbol 是實際合約代碼（如 TXFR1）
        actual_symbol = self.get_actual_code(symbol)
        
        open_list = kbars_data.get('open', [])
        high_list = kbars_data.get('high', [])
        low_list = kbars_data.get('low', [])
        close_list = kbars_data.get('close', [])
        volume_list = kbars_data.get('volume', [])
        
        inserted_count = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for i in range(len(ts_list)):
                try:
                    ts_val = ts_list[i]
                    if isinstance(ts_val, (int, float)):
                        ts_val = int(ts_val)
                    
                    cursor = conn.execute("""
                        INSERT OR IGNORE INTO kbars 
                        (symbol, ts, open_price, high_price, low_price, close_price, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        actual_symbol,
                        ts_val,
                        float(open_list[i]) if i < len(open_list) else 0,
                        float(high_list[i]) if i < len(high_list) else 0,
                        float(low_list[i]) if i < len(low_list) else 0,
                        float(close_list[i]) if i < len(close_list) else 0,
                        float(volume_list[i]) if i < len(volume_list) else 0,
                    ))
                    if cursor.rowcount > 0:
                        inserted_count += 1
                except sqlite3.Error:
                    pass
            
            conn.commit()
        
        return inserted_count
    
    def get_kbars(self, symbol: str, start_ts: int, end_ts: int) -> Dict:
        """获取指定时间范围的 K 棒数据
        
        Args:
            symbol: 期货代码（基本代码或实际合约代码）
            start_ts: 开始时间戳
            end_ts: 结束时间戳
            
        Returns:
            K 棒数据字典
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            actual_symbol = self.get_actual_code(symbol)
            cursor = conn.execute("""
                SELECT ts, open_price, high_price, low_price, close_price, volume
                FROM kbars
                WHERE symbol = ? AND ts >= ? AND ts <= ?
                ORDER BY ts ASC
            """, (actual_symbol, start_ts, end_ts))
            
            rows = cursor.fetchall()
            return {
                'ts': [row['ts'] for row in rows],
                'open': [row['open_price'] for row in rows],
                'high': [row['high_price'] for row in rows],
                'low': [row['low_price'] for row in rows],
                'close': [row['close_price'] for row in rows],
                'volume': [row['volume'] for row in rows],
            }
    
    def get_latest_kbar(self, symbol: str) -> Optional[Dict]:
        """获取最新的 K 棒数据
        
        Args:
            symbol: 期货代码（基本代码，会自动转换为实际合约代码）
            
        Returns:
            最新 K 棒数据，if no则返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT ts, open_price, high_price, low_price, close_price, volume
                FROM kbars
                WHERE symbol = ?
                ORDER BY ts DESC
                LIMIT 1
            """, (self.get_actual_code(symbol),))
            
            row = cursor.fetchone()
            if row:
                return {
                    'ts': row['ts'],
                    'open': row['open_price'],
                    'high': row['high_price'],
                    'low': row['low_price'],
                    'close': row['close_price'],
                    'volume': row['volume'],
                }
            return None
    
    def get_oldest_kbar(self, symbol: str) -> Optional[Dict]:
        """获取最旧的 K 棒数据
        
        Args:
            symbol: 期货代码（基本代码，会自动转换为实际合约代码）
            
        Returns:
            最旧 K 棒数据，如果没冇则返回 None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT ts, open_price, high_price, low_price, close_price, volume
                FROM kbars
                WHERE symbol = ?
                ORDER BY ts ASC
                LIMIT 1
            """, (self.get_actual_code(symbol),))
            
            row = cursor.fetchone()
            if row:
                return {
                    'ts': row['ts'],
                    'open': row['open_price'],
                    'high': row['high_price'],
                    'low': row['low_price'],
                    'close': row['close_price'],
                    'volume': row['volume'],
                }
            return None
    
    def get_count(self, symbol: str) -> int:
        """获取指定期货的 K 棒数量
        
        Args:
            symbol: 期货代码（基本代码，会自动转换为实际合约代码）
            
        Returns:
            K 棒数量
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM kbars WHERE symbol = ?
            """, (self.get_actual_code(symbol),))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def get_all_symbols(self) -> List[str]:
        """获取数据库中所有存在的 symbol
        
        Returns:
            symbol 列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT symbol FROM kbars ORDER BY symbol
            """)
            return [row[0] for row in cursor.fetchall()]
    
    def check_workday_gaps(self, symbol: str) -> dict:
        """检查工作日是否有遗漏（整天）
        
        Args:
            symbol: 期货代码
            
        Returns:
            包含工作日缺口统计的字典
        """
        import datetime
        
        symbol = self.get_actual_code(symbol)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT DISTINCT DATE(datetime(ts, 'unixepoch')) as trade_date
                FROM kbars
                WHERE symbol = ?
                ORDER BY trade_date
            """, (symbol,))
            existing_dates = [row[0] for row in cursor.fetchall()]
        
        if not existing_dates:
            return {"days_checked": 0, "workday_gaps": 0, "weekend_gaps": 0}
        
        # 分析日期间隔
        from datetime import datetime, timedelta
        
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in existing_dates]
        dates.sort()
        
        workday_gaps = []
        weekend_gaps = []
        
        for i in range(len(dates) - 1):
            gap_days = (dates[i+1] - dates[i]).days
            
            if gap_days > 1:
                # 有间隔，检查每一天
                for j in range(1, gap_days):
                    check_date = dates[i] + timedelta(days=j)
                    if check_date.weekday() < 5:  # 周一~周五
                        workday_gaps.append(check_date.strftime("%Y-%m-%d"))
                    else:  # 周六、周日
                        weekend_gaps.append(check_date.strftime("%Y-%m-%d"))
        
        return {
            "days_checked": len(existing_dates),
            "workday_gaps": len(workday_gaps),
            "weekend_gaps": len(weekend_gaps),
            "workday_gap_dates": workday_gaps[:10],  # 最多显示10个
        }
    
    def check_trading_hours_completeness(self, symbol: str) -> dict:
        """检查交易时段数据完整性（08:46 ~ 23:59）
        
        Args:
            symbol: 期货代码
            
        Returns:
            包含交易时段完整性统计的字典
        """
        import datetime
        
        symbol = self.get_actual_code(symbol)
        
        with sqlite3.connect(self.db_path) as conn:
            # 获取每天 08:46:00 ~ 23:59:59 的数据笔数
            cursor = conn.execute("""
                SELECT 
                    DATE(datetime(ts, 'unixepoch')) as trade_date,
                    COUNT(*) as count
                FROM kbars
                WHERE symbol = ?
                AND TIME(datetime(ts, 'unixepoch')) >= '08:46:00'
                AND TIME(datetime(ts, 'unixepoch')) <= '23:59:59'
                GROUP BY DATE(datetime(ts, 'unixepoch'))
                ORDER BY trade_date
            """, (symbol,))
            daily_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        if not daily_counts:
            return {"days_checked": 0, "avg_count": 0, "suspicious_days": 0}
        
        # 计算平均笔数
        counts = list(daily_counts.values())
        avg_count = sum(counts) / len(counts)
        
        # 检查异常（低于平均的95%）
        threshold = avg_count * 0.95
        suspicious = []
        
        for date, count in daily_counts.items():
            if count < threshold:
                suspicious.append({
                    "date": date,
                    "count": count,
                    "expected": round(avg_count, 0),
                    "gap": round(avg_count - count, 0)
                })
        
        return {
            "days_checked": len(daily_counts),
            "avg_count": round(avg_count, 0),
            "suspicious_days": len(suspicious),
            "suspicious_details": suspicious[:10],  # 最多显示10个
        }
    
    def get_today_count(self, symbol: str) -> int:
        """获取今日写入的 K 棒数量（指定 symbol）
        
        Args:
            symbol: 期货代码（基本代码，会自动转换为实际合约代码）
            
        Returns:
            今日写入的 K 棒数量
        """
        from datetime import datetime
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM kbars 
                WHERE symbol = ? AND DATE(created_at) = ?
            """, (self.get_actual_code(symbol), today))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def get_total_today_count(self) -> int:
        """获取今日写入的所有 K棒数量（所有 symbol 合计）
        
        Returns:
            今日写入的所有 K棒数量
        """
        from datetime import datetime
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM kbars 
                WHERE DATE(created_at) = ?
            """, (today,))
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def get_total_count(self) -> int:
        """获取所有 K 棒总數量
        
        Returns:
            總數量
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM kbars")
            row = cursor.fetchone()
            return row[0] if row else 0
    
    def cleanup_old_records(self, max_records: Optional[int] = None) -> int:
        """清理旧记录，保留最新的数据
        
        Args:
            max_records: 最大保留记录数，默认使用 MAX_RECORDS
            
        Returns:
            删除的记录数
        """
        max_records = max_records or self.MAX_RECORDS
        
        total = self.get_total_count()
        if total <= max_records:
            return 0
        
        delete_count = total - max_records
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM kbars
                WHERE id IN (
                    SELECT id FROM kbars
                    ORDER BY ts ASC
                    LIMIT ?
                )
            """, (delete_count,))
            conn.commit()
        
        logger.info(f"清理旧记录: 删除了 {delete_count} 条，保留 {max_records} 条")
        return delete_count
    
    def get_status(self) -> Dict:
        """获取存储状态
        
        Returns:
            状态字典
        """
        with sqlite3.connect(self.db_path) as conn:
            # 检查 mapping 表
            cursor = conn.execute(
                "SELECT base_code, actual_code FROM symbol_mapping"
            )
            mappings = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 查询数据库中的实际合约
            cursor = conn.execute(
                "SELECT symbol, COUNT(*) as count FROM kbars GROUP BY symbol"
            )
            actual_symbols = {row[0]: row[1] for row in cursor.fetchall()}
            
            symbols_data = {}
            for base_code, actual_code in mappings.items():
                if actual_code in actual_symbols:
                    symbols_data[base_code] = actual_symbols[actual_code]
            
            return {
                'total_count': self.get_total_count(),
                'max_records': self.MAX_RECORDS,
                'cleanup_threshold': self.CLEANUP_THRESHOLD,
                'needs_cleanup': self.get_total_count() > self.CLEANUP_THRESHOLD,
                'symbols': symbols_data,
                'mappings': mappings,
            }
    
    def delete_all(self, symbol: Optional[str] = None) -> int:
        """删除数据
        
        Args:
            symbol: 期货代码（基本代码），if None 则删除所有
            
        Returns:
            删除的记录数
        """
        with sqlite3.connect(self.db_path) as conn:
            if symbol:
                cursor = conn.execute("""
                    DELETE FROM kbars WHERE symbol = ?
                """, (self.get_actual_code(symbol),))
            else:
                cursor = conn.execute("DELETE FROM kbars")
            conn.commit()
            return cursor.rowcount
    
    def convert_1m_to_timeframe(self, symbol: str, target_timeframe: str) -> Dict:
        """将 1 分钟 K 棒转换为目标时间周期
        
        Args:
            symbol: 期货代码（基本代码）
            target_timeframe: 目标时间周期 (15m, 30m, 1h, 1d)
            
        Returns:
            转换后的 K 棒数据字典
        """
        import pandas as pd
        
        timeframe_minutes = {
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 1440,
        }
        
        if target_timeframe not in timeframe_minutes:
            raise ValueError(f"不支持的时间周期：{target_timeframe}")
        
        # 使用 get_kbars 自動轉換 symbol
        kbars = self.get_kbars(symbol, 0, 2147483647)
        if not kbars:
            return {'ts': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        
        df = pd.DataFrame(kbars)
        df['datetime'] = pd.to_datetime(df['ts'], unit='s')
        df.set_index('datetime', inplace=True)
        
        minutes = timeframe_minutes[target_timeframe]
        
        resampled = df.resample(f'{minutes}min', label='right', closed='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum',
        }).dropna()
        
        ts_list = [int(t.timestamp()) for t in resampled.index]
        
        return {
            'ts': ts_list,
            'open': list(resampled['open'].values),
            'high': list(resampled['high'].values),
            'low': list(resampled['low'].values),
            'close': list(resampled['close'].values),
            'volume': list(resampled['volume'].values),
        }
    
    def get_kbars_with_conversion(self, symbol: str, start_ts: int, end_ts: int, 
                                    timeframe: str = '1m') -> Dict:
        """获取 K 棒数据，自动处理时间周期转换
        
        Args:
            symbol: 期货代码（基本代码如 TXF，会自动转换为实际合约代码 TXFR1）
            start_ts: 开始时间戳
            end_ts: 结束时间戳
            timeframe: 时间周期 (1m, 5m, 15m, 30m, 1h, 1d)
            
        Returns:
            K 棒数据字典
        """
        if timeframe == '1m':
            return self.get_kbars(symbol, start_ts, end_ts)
        
        converted = self.convert_1m_to_timeframe(symbol, timeframe)
        
        if not converted.get('ts'):
            return {'ts': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        
        filtered = []
        for i in range(len(converted['ts'])):
            ts = int(converted['ts'][i])
            if start_ts <= ts <= end_ts:
                filtered.append(i)
        
        if not filtered:
            return {'ts': [], 'open': [], 'high': [], 'low': [], 'close': [], 'volume': []}
        
        return {
            'ts': [int(converted['ts'][i]) for i in filtered],
            'open': [float(converted['open'][i]) for i in filtered],
            'high': [float(converted['high'][i]) for i in filtered],
            'low': [float(converted['low'][i]) for i in filtered],
            'close': [float(converted['close'][i]) for i in filtered],
            'volume': [float(converted['volume'][i]) for i in filtered],
        }
