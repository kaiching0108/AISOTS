"""市場數據服務"""
import asyncio
import logging
from typing import Dict, Set, Optional, Callable, List, Any
from datetime import datetime

from src.market.price_cache import PriceCache, PriceData
from src.api.shioaji_client import ShioajiClient

logger = logging.getLogger(__name__)


class MarketDataService:
    """市場數據服務"""
    
    def __init__(self, client: ShioajiClient, price_cache: Optional[PriceCache] = None):
        self.client = client
        self.price_cache = price_cache or PriceCache()
        
        self._subscribed_symbols: Set[str] = set()
        self._callbacks: List[Callable] = []
        self._is_running = False
    
    def subscribe(self, symbol: str) -> bool:
        """訂閱合約報價
        
        Args:
            symbol: 合約代碼
            
        Returns:
            是否成功
        """
        if symbol in self._subscribed_symbols:
            logger.debug(f"Already subscribed: {symbol}")
            return True
        
        try:
            contract = self.client.get_contract(symbol)
            if not contract:
                logger.warning(f"Contract not found: {symbol}")
                return False
            
            self.client.subscribe_quote(contract)
            self._subscribed_symbols.add(symbol)
            logger.info(f"Subscribed to: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe {symbol}: {e}")
            return False
    
    def unsubscribe(self, symbol: str) -> bool:
        """取消訂閱
        
        Args:
            symbol: 合約代碼
            
        Returns:
            是否成功
        """
        if symbol not in self._subscribed_symbols:
            return True
        
        try:
            contract = self.client.get_contract(symbol)
            if contract:
                self.client.unsubscribe_quote(contract)
            
            self._subscribed_symbols.discard(symbol)
            logger.info(f"Unsubscribed from: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe {symbol}: {e}")
            return False
    
    def add_callback(self, callback: Callable[[str, PriceData], None]) -> None:
        """新增價格回調
        
        Args:
            callback: 回調函數 (symbol, price_data)
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable) -> None:
        """移除回調"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def on_price_update(self, symbol: str, timestamp: datetime, 
                        open_price: float, high: float, low: float, 
                        close: float, volume: float) -> None:
        """價格更新處理
        
        Args:
            symbol: 合約代碼
            timestamp: 時間戳
            open_price: 開盤價
            high: 最高價
            low: 最低價
            close: 收盤價
            volume: 成交量
        """
        self.price_cache.update(
            symbol, timestamp, open_price, high, low, close, volume
        )
        
        price_data = self.price_cache.get_current(symbol)
        
        for callback in self._callbacks:
            try:
                callback(symbol, price_data)
            except Exception as e:
                logger.error(f"Error in price callback: {e}")
    
    def get_price(self, symbol: str) -> Optional[PriceData]:
        """取得最新價格"""
        return self.price_cache.get_current(symbol)
    
    def get_history(self, symbol: str, count: int = 100) -> List[Dict]:
        """取得歷史價格"""
        return self.price_cache.get_history(symbol, count)
    
    def get_subscribed_symbols(self) -> List[str]:
        """取得已訂閱的合約"""
        return list(self._subscribed_symbols)
    
    def is_subscribed(self, symbol: str) -> bool:
        """檢查是否已訂閱"""
        return symbol in self._subscribed_symbols
    
    async def fetch_historical(
        self, symbol: str, timeframe: str, count: int = 100
    ) -> List[Dict]:
        """取得歷史K線
        
        Args:
            symbol: 合約代碼
            timeframe: 時間週期 (1m, 5m, 15m, 30m, 1h, 1d)
            count: 取得筆數
            
        Returns:
            K線數據列表
        """
        try:
            contract = self.client.get_contract(symbol)
            if not contract:
                logger.warning(f"Contract not found: {symbol}")
                return []
            
            bars = self.client.get_kbars(contract, timeframe, count)
            
            if not bars:
                return []
            
            result = []
            for i in range(len(bars.get("ts", [])):
                result.append({
                    "timestamp": datetime.fromtimestamp(bars["ts"][i]),
                    "open": float(bars["open"][i]),
                    "high": float(bars["high"][i]),
                    "low": float(bars["low"][i]),
                    "close": float(bars["close"][i]),
                    "volume": float(bars["volume"][i])
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return []
    
    def has_sufficient_data(self, symbol: str, min_bars: int = 20) -> bool:
        """檢查是否有足夠的數據"""
        return self.price_cache.has_data(symbol, min_bars)
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """取得快取摘要"""
        return self.price_cache.get_summary()
    
    async def subscribe_strategies(self, strategies: List) -> None:
        """訂閱策略所需的合約
        
        Args:
            strategies: 策略列表
        """
        symbols = set()
        for strategy in strategies:
            if hasattr(strategy, "symbol"):
                symbols.add(strategy.symbol)
        
        for symbol in symbols:
            self.subscribe(symbol)
    
    def unsubscribe_all(self) -> None:
        """取消所有訂閱"""
        for symbol in list(self._subscribed_symbols):
            self.unsubscribe(symbol)
