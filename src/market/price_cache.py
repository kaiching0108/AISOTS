"""價格快取模組"""
from typing import Dict, Optional, List, Any
from datetime import datetime
from collections import deque

from src.logger import logger


class PriceData:
    """價格數據"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.timestamp: Optional[datetime] = None
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None
        self.volume: Optional[float] = None
    
    def update(self, timestamp: datetime, open_price: float, high: float, 
               low: float, close: float, volume: float) -> None:
        """更新價格數據"""
        self.timestamp = timestamp
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume
        }


class PriceCache:
    """價格快取"""
    
    def __init__(self, max_bars: int = 500):
        self.max_bars = max_bars
        self._prices: Dict[str, PriceData] = {}
        self._history: Dict[str, deque] = {}
    
    def update(self, symbol: str, timestamp: datetime, open_price: float,
               high: float, low: float, close: float, volume: float) -> None:
        """更新價格
        
        Args:
            symbol: 合約代碼
            timestamp: 時間戳
            open_price: 開盤價
            high: 最高價
            low: 最低價
            close: 收盤價
            volume: 成交量
        """
        if symbol not in self._prices:
            self._prices[symbol] = PriceData(symbol)
            self._history[symbol] = deque(maxlen=self.max_bars)
        
        self._prices[symbol].update(timestamp, open_price, high, low, close, volume)
        
        self._history[symbol].append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume
        })
    
    def get_current(self, symbol: str) -> Optional[PriceData]:
        """取得最新價格"""
        return self._prices.get(symbol)
    
    def get_history(self, symbol: str, count: Optional[int] = None) -> List[Dict]:
        """取得歷史價格
        
        Args:
            symbol: 合約代碼
            count: 取得筆數，None 表示全部
            
        Returns:
            歷史價格列表
        """
        if symbol not in self._history:
            return []
        
        history = list(self._history[symbol])
        if count is not None:
            history = history[-count:]
        return history
    
    def get_closes(self, symbol: str, count: int) -> List[float]:
        """取得收盤價列表"""
        history = self.get_history(symbol, count)
        return [h["close"] for h in history if "close" in h]
    
    def get_highs(self, symbol: str, count: int) -> List[float]:
        """取得最高價列表"""
        history = self.get_history(symbol, count)
        return [h["high"] for h in history if "high" in h]
    
    def get_lows(self, symbol: str, count: int) -> List[float]:
        """取得最低價列表"""
        history = self.get_history(symbol, count)
        return [h["low"] for h in history if "low" in h]
    
    def get_volumes(self, symbol: str, count: int) -> List[float]:
        """取得成交量列表"""
        history = self.get_history(symbol, count)
        return [h["volume"] for h in history if "volume" in h]
    
    def get_all_symbols(self) -> List[str]:
        """取得所有追蹤的合約"""
        return list(self._prices.keys())
    
    def has_data(self, symbol: str, min_count: int = 20) -> bool:
        """檢查是否有足夠數據
        
        Args:
            symbol: 合約代碼
            min_count: 最小需要的資料筆數
        """
        if symbol not in self._history:
            return False
        return len(self._history[symbol]) >= min_count
    
    def clear(self, symbol: Optional[str] = None) -> None:
        """清除快取
        
        Args:
            symbol: 指定合約，None 表示全部
        """
        if symbol:
            if symbol in self._prices:
                del self._prices[symbol]
            if symbol in self._history:
                del self._history[symbol]
        else:
            self._prices.clear()
            self._history.clear()
    
    def get_summary(self) -> Dict[str, Any]:
        """取得快取摘要"""
        return {
            "tracked_symbols": len(self._prices),
            "symbols": list(self._prices.keys()),
            "history_counts": {
                symbol: len(history) 
                for symbol, history in self._history.items()
            }
        }
