"""策略框架 - 提供 LLM 生成策略的執行環境"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.logger import logger

SIGNAL_BUY = "buy"
SIGNAL_SELL = "sell"
SIGNAL_CLOSE = "close"
SIGNAL_HOLD = "hold"


@dataclass
class BarData:
    """K棒數據"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def pct_change(self) -> float:
        if self.open == 0:
            return 0.0
        return (self.close - self.open) / self.open
    
    def get_change_from(self, price: float) -> float:
        if price == 0:
            return 0.0
        return (self.close - price) / price


@dataclass
class FillData:
    """成交回報"""
    symbol: str
    side: str
    price: float
    quantity: int
    timestamp: datetime


class TradingStrategy(ABC):
    """策略框架 - LLM 需要實作的方法"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.position = 0
        self.entry_price = 0.0
        self.context: Dict[str, Any] = {}
        self._bars: List[BarData] = []
        self._df_cache: Optional[Any] = None
    
    @abstractmethod
    def on_bar(self, bar: BarData) -> Optional[str]:
        """每根 K 棒時呼叫，回傳訊號"""
        pass
    
    def on_fill(self, fill: FillData) -> None:
        """成交回報（可選實作）"""
        if fill.side == "buy":
            self.position += fill.quantity
            self.entry_price = fill.price
        elif fill.side == "sell":
            self.position -= fill.quantity
            if self.position == 0:
                self.entry_price = 0.0
    
    def get_position(self) -> int:
        return self.position
    
    def get_entry_price(self) -> float:
        return self.entry_price
    
    def get_bars(self, count: Optional[int] = None) -> List[BarData]:
        if count is None:
            return self._bars.copy()
        return self._bars[-count:]
    
    def _add_bar(self, bar: BarData) -> None:
        self._bars.append(bar)
        self._df_cache = None
        if len(self._bars) > 500:
            self._bars = self._bars[-500:]
    
    def get_dataframe(self, lookback: int = 100) -> Any:
        """取得 pandas DataFrame（使用 pandas_ta 計算指標）"""
        import pandas as pd
        
        if self._df_cache is not None:
            return self._df_cache
        
        bars = self.get_bars(lookback)
        if len(bars) < 2:
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'timestamp': [b.timestamp for b in bars],
            'open': [b.open for b in bars],
            'high': [b.high for b in bars],
            'low': [b.low for b in bars],
            'close': [b.close for b in bars],
            'volume': [b.volume for b in bars]
        })
        
        self._df_cache = df
        return df
    
    def ta(self, indicator: str, **kwargs) -> Any:
        """使用 pandas_ta 計算技術指標
        
        Args:
            indicator: 指標名稱 (如 RSI, MACD, BB, SMA, EMA 等)
            **kwargs: 指標參數
            
        Returns:
            指標結果 Series 或 DataFrame
        """
        try:
            import pandas_ta as ta
            
            df = self.get_dataframe()
            if df.empty:
                return None
            
            close = df['close']
            
            indicator_upper = indicator.upper()
            
            if indicator_upper == 'RSI':
                period = kwargs.get('period', 14)
                return ta.rsi(close, length=period)
            
            elif indicator_upper == 'MACD':
                fast = kwargs.get('fast', 12)
                slow = kwargs.get('slow', 26)
                signal = kwargs.get('signal', 9)
                return ta.macd(close, fast=fast, slow=slow, signal=signal)
            
            elif indicator_upper in ['SMA', 'SMA_EMA']:
                period = kwargs.get('period', 20)
                return ta.sma(close, length=period)
            
            elif indicator_upper == 'EMA':
                period = kwargs.get('period', 20)
                return ta.ema(close, length=period)
            
            elif indicator_upper == 'BB':
                period = kwargs.get('period', 20)
                std = kwargs.get('std', 2.0)
                return ta.bbands(close, length=period, std=std)
            
            elif indicator_upper == 'ATR':
                period = kwargs.get('period', 14)
                return ta.atr(df['high'], df['low'], df['close'], length=period)
            
            elif indicator_upper == 'STOCH':
                period = kwargs.get('period', 14)
                return ta.stoch(df['high'], df['low'], df['close'], length=period)
            
            elif indicator_upper == 'ADX':
                period = kwargs.get('period', 14)
                return ta.adx(df['high'], df['low'], df['close'], length=period)
            
            elif indicator_upper == 'CCI':
                period = kwargs.get('period', 20)
                return ta.cci(df['high'], df['low'], df['close'], length=period)
            
            elif indicator_upper == 'OBV':
                return ta.obv(df['close'], df['volume'])
            
            elif indicator_upper == 'VWAP':
                return ta.vwap(df['high'], df['low'], df['close'], df['volume'])
            
            elif indicator_upper == 'WILLR':
                period = kwargs.get('period', 14)
                return ta.willr(df['high'], df['low'], df['close'], length=period)
            
            else:
                logger.warning(f"Unknown indicator: {indicator}")
                return None
                
        except ImportError:
            logger.warning("pandas_ta not installed")
            return None
        except Exception as e:
            logger.error(f"Error calculating indicator {indicator}: {e}")
            return None


class StrategyExecutor:
    """策略執行器"""
    
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
        self._running = False
    
    async def execute_bar(self, bar: BarData) -> Optional[str]:
        self.strategy._add_bar(bar)
        
        try:
            signal = self.strategy.on_bar(bar)
            
            if signal in [SIGNAL_BUY, SIGNAL_SELL, SIGNAL_CLOSE, SIGNAL_HOLD]:
                return signal
            
            logger.warning(f"Invalid signal: {signal}")
            return SIGNAL_HOLD
            
        except Exception as e:
            logger.error(f"Error executing strategy on_bar: {e}")
            return SIGNAL_HOLD
    
    def on_fill(self, fill: FillData) -> None:
        try:
            self.strategy.on_fill(fill)
        except Exception as e:
            logger.error(f"Error in on_fill: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "position": self.strategy.get_position(),
            "entry_price": self.strategy.get_entry_price(),
            "symbol": self.strategy.symbol,
            "bars_count": len(self.strategy.get_bars())
        }
    
    def reset(self) -> None:
        self.strategy.position = 0
        self.strategy.entry_price = 0.0
        self.strategy.context.clear()
        self.strategy._bars.clear()
        self.strategy._df_cache = None
