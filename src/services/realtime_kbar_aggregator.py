"""实时 K-bar 聚合服务"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict

from loguru import logger


class RealtimeKBarAggregator:
    """实时 K-bar 聚合器
    
    将 tick 数据聚合成 1 分钟 K-bar，
    并支持转换为其他时间周期。
    支持将完成的 K-bar 写入 SQLite（仅实盘模式）。
    """
    
    def __init__(self, on_kbar_callback=None, kbar_db=None):
        """初始化聚合器
        
        Args:
            on_kbar_callback: K-bar 生成后的回调函数 (symbol, kbar_data)
            kbar_db: KBarSQLite 实例，用于写入完成的 K-bar
        """
        self.on_kbar_callback = on_kbar_callback
        self._kbar_db = kbar_db
        
        # 存储当前的 K-bar 数据
        # key: symbol, value: dict with 'open', 'high', 'low', 'close', 'volume', 'start_ts'
        self._current_kbars: Dict[str, Dict] = defaultdict(self._create_kbar_slot)
        
        # 存储已完成的 1m K-bars（用于转换到其他周期）
        self._completed_1m_bars: Dict[str, list] = defaultdict(list)
    
    def set_kbar_db(self, kbar_db) -> None:
        """设置 K-bar 数据库实例
        
        Args:
            kbar_db: KBarSQLite 实例
        """
        self._kbar_db = kbar_db
        logger.info("RealtimeKBarAggregator 已连接 K-bar 数据库")
    
    def _create_kbar_slot(self) -> Dict:
        """创建 K-bar 槽位"""
        return {
            'open': None,
            'high': float('-inf'),
            'low': float('inf'),
            'close': 0,
            'volume': 0,
            'start_ts': None,
            'tick_count': 0,
        }
    
    def process_tick(self, symbol: str, price: float, volume: float, timestamp: datetime) -> Optional[Dict]:
        """处理 tick 数据
        
        Args:
            symbol: 期货代码
            price: 最新价格
            volume: 成交量
            timestamp: 时间戳
            
        Returns:
            如果生成了新的 K-bar，返回 K-bar 数据；否则返回 None
        """
        # 调试日志：检查 timestamp 类型
        logger.debug(f"收到 tick: {symbol} price={price} volume={volume} timestamp={timestamp} type={type(timestamp)}")
        
        # 如果 timestamp 是字符串，尝试解析
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except Exception as e:
                logger.error(f"解析 timestamp 失败: {e}")
                return None
        
        current_minute = timestamp.replace(second=0, microsecond=0)
        current_ts = int(current_minute.timestamp()) + 8 * 3600
        
        kbar = self._current_kbars[symbol]
        
        # 检查是否需要开始新的 K-bar（跨分钟）
        if kbar['start_ts'] is None:
            kbar['start_ts'] = current_ts
            kbar['open'] = price
            kbar['high'] = price
            kbar['low'] = price
            kbar['close'] = price
            kbar['volume'] = volume
            kbar['tick_count'] = 1
            return None
        
        # 如果在同一分钟内，更新当前 K-bar
        if current_ts == kbar['start_ts']:
            kbar['high'] = max(kbar['high'], price)
            kbar['low'] = min(kbar['low'], price)
            kbar['close'] = price
            kbar['volume'] += volume
            kbar['tick_count'] += 1
            return None
        
        # 分钟变化，完成当前 K-bar
        logger.info(f"跨分钟触发: {symbol} {kbar['start_ts']} -> {current_ts}")
        
        completed_kbar = {
            'symbol': symbol,
            'ts': kbar['start_ts'],
            'open': kbar['open'],
            'high': kbar['high'],
            'low': kbar['low'],
            'close': kbar['close'],
            'volume': kbar['volume'],
        }
        
        # 保存完成的 K-bar
        self._completed_1m_bars[symbol].append(completed_kbar)
        
        # 保留最多 1000 个 1m K-bar
        if len(self._completed_1m_bars[symbol]) > 1000:
            self._completed_1m_bars[symbol] = self._completed_1m_bars[symbol][-1000:]
        
        # 写入 SQLite（仅实盘模式时启用）
        if self._kbar_db:
            try:
                kbars_data = {
                    'ts': [completed_kbar['ts']],
                    'open': [completed_kbar['open']],
                    'high': [completed_kbar['high']],
                    'low': [completed_kbar['low']],
                    'close': [completed_kbar['close']],
                    'volume': [completed_kbar['volume']],
                }
                logger.info(f"准备写入 realtime K-bar: {symbol} ts={completed_kbar['ts']}")
                inserted = self._kbar_db.insert_kbars(symbol, kbars_data, source='realtime')
                logger.info(f"写入 realtime K-bar 完成: {symbol} inserted={inserted}")
            except Exception as e:
                logger.error(f"写入 K-bar 到 SQLite 失败: {e}")
        else:
            logger.warning("kbar_db 未初始化，跳过写入")
        
        # 重置当前 K-bar
        kbar.clear()
        kbar.update(self._create_kbar_slot())
        kbar['start_ts'] = current_ts
        kbar['open'] = price
        kbar['high'] = price
        kbar['low'] = price
        kbar['close'] = price
        kbar['volume'] = volume
        kbar['tick_count'] = 1
        
        # 触发回调
        if self.on_kbar_callback:
            self.on_kbar_callback(symbol, completed_kbar)
        
        return completed_kbar
    
    def get_1m_bars(self, symbol: str, count: int = 100) -> list:
        """获取最近的 1 分钟 K-bars
        
        Args:
            symbol: 期货代码
            count: 返回数量
            
        Returns:
            K-bar 列表
        """
        bars = self._completed_1m_bars.get(symbol, [])
        return bars[-count:]
    
    def convert_to_timeframe(self, symbol: str, target_timeframe: str, count: int = 100) -> list:
        """将 1m K-bar 转换为目标时间周期
        
        Args:
            symbol: 期货代码
            target_timeframe: 目标时间周期 (5m, 15m, 30m, 1h, 1d)
            count: 返回数量
            
        Returns:
            转换后的 K-bar 列表
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
            logger.warning(f"不支持的时间周期: {target_timeframe}")
            return []
        
        bars = self.get_1m_bars(symbol, count * timeframe_minutes[target_timeframe])
        if not bars:
            return []
        
        df = pd.DataFrame(bars)
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
        
        result = []
        for idx, row in resampled.iterrows():
            result.append({
                'symbol': symbol,
                'ts': int(idx.timestamp()),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
            })
        
        return result[-count:]
    
    def get_current_bar(self, symbol: str) -> Optional[Dict]:
        """获取当前正在形成的 K-bar
        
        Args:
            symbol: 期货代码
            
        Returns:
            当前 K-bar 数据
        """
        kbar = self._current_kbars.get(symbol)
        if kbar and kbar['start_ts'] is not None:
            return {
                'symbol': symbol,
                'ts': kbar['start_ts'],
                'open': kbar['open'],
                'high': kbar['high'],
                'low': kbar['low'],
                'close': kbar['close'],
                'volume': kbar['volume'],
                'is_current': True,
            }
        return None
    
    def clear(self, symbol: Optional[str] = None) -> None:
        """清除数据
        
        Args:
            symbol: 期货代码，如果为 None 则清除所有
        """
        if symbol:
            if symbol in self._current_kbars:
                del self._current_kbars[symbol]
            if symbol in self._completed_1m_bars:
                del self._completed_1m_bars[symbol]
        else:
            self._current_kbars.clear()
            self._completed_1m_bars.clear()
