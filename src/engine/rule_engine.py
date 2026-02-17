"""規則引擎 - 根據解析後的規則產生交易訊號"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

Signal = str
SIGNAL_BUY = "buy"
SIGNAL_SELL = "sell"
SIGNAL_CLOSE = "close"
SIGNAL_HOLD = "hold"


class MarketData:
    """市場數據結構"""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.close_prices: List[float] = []
        self.high_prices: List[float] = []
        self.low_prices: List[float] = []
        self.open_prices: List[float] = []
        self.volumes: List[float] = []
        self.timestamps: List[datetime] = []
        self.current_price: Optional[float] = None
    
    def add_bar(self, timestamp: datetime, open_price: float, high: float, 
                low: float, close: float, volume: float) -> None:
        """新增 K 棒數據"""
        self.timestamps.append(timestamp)
        self.open_prices.append(open_price)
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)
        self.volumes.append(volume)
        self.current_price = close
    
    def to_dataframe(self) -> pd.DataFrame:
        """轉換為 DataFrame"""
        if not self.close_prices:
            return pd.DataFrame()
        
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'open': self.open_prices,
            'high': self.high_prices,
            'low': self.low_prices,
            'close': self.close_prices,
            'volume': self.volumes
        })
    
    def get_recent(self, n: int) -> Dict[str, List]:
        """取得最近 n 筆數據"""
        return {
            'close': self.close_prices[-n:] if len(self.close_prices) >= n else self.close_prices,
            'high': self.high_prices[-n:] if len(self.high_prices) >= n else self.high_prices,
            'low': self.low_prices[-n:] if len(self.low_prices) >= n else self.low_prices,
            'volume': self.volumes[-n:] if len(self.volumes) >= n else self.volumes
        }


class RuleEngine:
    """規則引擎"""
    
    def __init__(self):
        self._init_indicators()
    
    def _init_indicators(self) -> None:
        """初始化技術指標計算函數"""
        try:
            import pandas_ta as ta
            self.ta = ta
            self.ta_available = True
            logger.info("pandas_ta available, using technical indicators")
        except ImportError:
            self.ta = None
            self.ta_available = False
            logger.warning("pandas_ta not available, using basic indicators")
    
    async def evaluate(self, rules: Dict[str, Any], market_data: MarketData, 
                       position_exists: bool = False) -> Signal:
        """評估規則產生訊號
        
        Args:
            rules: 解析後的規則
            market_data: 市場數據
            position_exists: 是否有現有部位
            
        Returns:
            交易訊號 (buy, sell, close, hold)
        """
        if not market_data.close_prices or len(market_data.close_prices) < 20:
            logger.warning("Insufficient market data for evaluation")
            return SIGNAL_HOLD
        
        try:
            df = market_data.to_dataframe()
            
            if position_exists:
                signal = self._evaluate_exit(rules, df)
            else:
                signal = self._evaluate_entry(rules, df)
            
            logger.info(f"Rule evaluation result: {signal}")
            return signal
            
        except Exception as e:
            logger.error(f"Error evaluating rules: {e}")
            return SIGNAL_HOLD
    
    def _evaluate_entry(self, rules: Dict[str, Any], df: pd.DataFrame) -> Signal:
        """評估進場規則"""
        entry_indicator = rules.get("entry_indicator", "price_breaks_high")
        entry_params = rules.get("entry_params", {})
        
        signal = self._calculate_indicator(entry_indicator, entry_params, df)
        
        if signal:
            return SIGNAL_BUY
        return SIGNAL_HOLD
    
    def _evaluate_exit(self, rules: Dict[str, Any], df: pd.DataFrame) -> Signal:
        """評估出場規則"""
        exit_indicator = rules.get("exit_indicator", "price_below_low")
        exit_params = rules.get("exit_params", {})
        
        signal = self._calculate_indicator(exit_indicator, exit_params, df)
        
        if signal:
            return SIGNAL_CLOSE
        return SIGNAL_HOLD
    
    def _calculate_indicator(self, indicator: str, params: Dict, df: pd.DataFrame) -> bool:
        """計算技術指標
        
        Args:
            indicator: 指標名稱
            params: 指標參數
            df: K 棒數據
            
        Returns:
            指標是否觸發
        """
        if len(df) < 2:
            return False
        
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values if 'volume' in df.columns else np.zeros(len(close))
        
        period = params.get("period", 20)
        threshold = params.get("threshold", 30)
        multiplier = params.get("multiplier", 2.0)
        
        if indicator == "price_breaks_high":
            period = params.get("period", 20)
            if len(close) < period + 1:
                return False
            highest = np.max(high[-period-1:-1])
            return close[-1] > highest
        
        elif indicator == "price_below_low":
            period = params.get("period", 10)
            if len(close) < period + 1:
                return False
            lowest = np.min(low[-period-1:-1])
            return close[-1] < lowest
        
        elif indicator == "price_breaks_ma":
            period = params.get("period", 20)
            if len(close) < period:
                return False
            ma = np.mean(close[-period:])
            return close[-1] > ma
        
        elif indicator == "price_below_ma":
            period = params.get("period", 20)
            if len(close) < period:
                return False
            ma = np.mean(close[-period:])
            return close[-1] < ma
        
        elif indicator == "rsi_oversold":
            return self._calculate_rsi(close, period) < threshold
        
        elif indicator == "rsi_overbought":
            return self._calculate_rsi(close, period) > (100 - threshold)
        
        elif indicator == "rsi_cross_up":
            return self._rsi_cross(close, period, "up")
        
        elif indicator == "rsi_cross_down":
            return self._rsi_cross(close, period, "down")
        
        elif indicator == "macd_cross_up":
            return self._macd_cross(close, "up")
        
        elif indicator == "macd_cross_down":
            return self._macd_cross(close, "down")
        
        elif indicator == "macd_histogram_positive":
            return self._macd_histogram(close) > 0
        
        elif indicator == "macd_histogram_negative":
            return self._macd_histogram(close) < 0
        
        elif indicator == "ma_cross_up":
            short_period = params.get("short_period", 5)
            long_period = params.get("long_period", 20)
            return self._ma_cross(close, short_period, long_period, "up")
        
        elif indicator == "ma_cross_down":
            short_period = params.get("short_period", 5)
            long_period = params.get("long_period", 20)
            return self._ma_cross(close, short_period, long_period, "down")
        
        elif indicator == "volume_surge":
            multiplier = params.get("multiplier", 2.0)
            if len(volume) < period:
                return False
            avg_volume = np.mean(volume[-period:])
            return volume[-1] > avg_volume * multiplier
        
        elif indicator == "volume_decline":
            period = params.get("period", 20)
            if len(volume) < period + 1:
                return False
            avg_volume = np.mean(volume[-period-1:-1])
            return volume[-1] < avg_volume * 0.5
        
        elif indicator == "consecutive_up":
            period = params.get("period", 3)
            if len(close) < period:
                return False
            for i in range(-period, 0):
                if close[i] <= close[i-1]:
                    return False
            return True
        
        elif indicator == "consecutive_down":
            period = params.get("period", 3)
            if len(close) < period:
                return False
            for i in range(-period, 0):
                if close[i] >= close[i-1]:
                    return False
            return True
        
        elif indicator == "price_at_upper_band":
            return self._bollinger_bands(close, period, multiplier) == "upper"
        
        elif indicator == "price_at_lower_band":
            return self._bollinger_bands(close, period, multiplier) == "lower"
        
        elif indicator == "price_breaks_upper":
            return self._bollinger_bands(close, period, multiplier) == "above_upper"
        
        elif indicator == "price_breaks_lower":
            return self._bollinger_bands(close, period, multiplier) == "below_lower"
        
        elif indicator == "kd_oversold":
            return self._kd_value(close, high, low) < 20
        
        elif indicator == "kd_overbought":
            return self._kd_value(close, high, low) > 80
        
        elif indicator == "kd_cross_up":
            return self._kd_cross(close, high, low, "up")
        
        elif indicator == "kd_cross_down":
            return self._kd_cross(close, high, low, "down")
        
        return False
    
    def _calculate_rsi(self, close: np.ndarray, period: int = 14) -> float:
        """計算 RSI"""
        if len(close) < period + 1:
            return 50.0
        
        deltas = np.diff(close[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _rsi_cross(self, close: np.ndarray, period: int, direction: str) -> bool:
        """RSI 穿越閾值"""
        if len(close) < period + 2:
            return False
        
        rsi_now = self._calculate_rsi(close, period)
        rsi_prev = self._calculate_rsi(close[:-1], period)
        
        if direction == "up":
            return rsi_prev < 30 and rsi_now >= 30
        elif direction == "down":
            return rsi_prev > 70 and rsi_now <= 70
        return False
    
    def _macd_cross(self, close: np.ndarray, direction: str) -> bool:
        """MACD 交叉"""
        if len(close) < 34:
            return False
        
        ema12 = self._ema(close, 12)
        ema26 = self._ema(close, 26)
        signal = self._ema(ema26, 9)
        
        macd = ema12[-1] - ema26[-1]
        macd_prev = self._ema(close[:-1], 12)[-1] - self._ema(close[:-1], 26)[-1]
        
        if direction == "up":
            return macd_prev < signal and macd >= signal
        elif direction == "down":
            return macd_prev > signal and macd <= signal
        return False
    
    def _macd_histogram(self, close: np.ndarray) -> float:
        """MACD Histogram"""
        if len(close) < 34:
            return 0.0
        
        ema12 = self._ema(close, 12)
        ema26 = self._ema(close, 26)
        macd = ema12 - ema26
        signal = self._ema(macd, 9)
        
        return macd[-1] - signal[-1]
    
    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """計算 EMA"""
        if len(data) < period:
            return data
        
        ema = np.zeros_like(data)
        ema[0] = data[0]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(data)):
            ema[i] = (data[i] - ema[i-1]) * multiplier + ema[i-1]
        
        return ema
    
    def _ma_cross(self, close: np.ndarray, short_period: int, 
                  long_period: int, direction: str) -> bool:
        """MA 交叉"""
        if len(close) < long_period + 1:
            return False
        
        short_ma = np.mean(close[-short_period:])
        long_ma = np.mean(close[-long_period:])
        
        short_ma_prev = np.mean(close[-short_period-1:-1])
        long_ma_prev = np.mean(close[-long_period-1:-1])
        
        if direction == "up":
            return short_ma_prev <= long_ma_prev and short_ma > long_ma
        elif direction == "down":
            return short_ma_prev >= long_ma_prev and short_ma < long_ma
        return False
    
    def _bollinger_bands(self, close: np.ndarray, period: int = 20, 
                         multiplier: float = 2.0) -> str:
        """布林帶位置"""
        if len(close) < period:
            return "middle"
        
        recent = close[-period:]
        ma = np.mean(recent)
        std = np.std(recent)
        
        upper = ma + multiplier * std
        lower = ma - multiplier * std
        
        current = close[-1]
        
        if current > upper:
            return "above_upper"
        elif current < lower:
            return "below_lower"
        elif abs(current - upper) < std * 0.1:
            return "upper"
        elif abs(current - lower) < std * 0.1:
            return "lower"
        return "middle"
    
    def _kd_value(self, close: np.ndarray, high: np.ndarray, 
                  low: np.ndarray, period: int = 9) -> float:
        """KD 指標 K 值"""
        if len(close) < period:
            return 50.0
        
        recent_close = close[-period:]
        recent_high = high[-period:]
        recent_low = low[-period:]
        
        k_val = np.max(recent_high)
        d_val = np.min(recent_low)
        
        if k_val == d_val:
            return 50.0
        
        k = ((recent_close[-1] - d_val) / (k_val - d_val)) * 100
        return k
    
    def _kd_cross(self, close: np.ndarray, high: np.ndarray, 
                   low: np.ndarray, direction: str) -> bool:
        """KD 交叉"""
        if len(close) < 10:
            return False
        
        k_now = self._kd_value(close, high, low)
        k_prev = self._kd_value(close[:-1], high[:-1], low[:-1])
        
        if direction == "up":
            return k_prev < 20 and k_now >= 20
        elif direction == "down":
            return k_prev > 80 and k_now <= 80
        return False
    
    def calculate_stop_loss(self, rules: Dict[str, Any], 
                             entry_price: float, direction: str) -> float:
        """計算停損價格"""
        points = rules.get("stop_loss_points", 50)
        
        if direction == "buy":
            return entry_price - points
        else:
            return entry_price + points
    
    def calculate_take_profit(self, rules: Dict[str, Any], 
                               entry_price: float, direction: str) -> float:
        """計算停利價格"""
        points = rules.get("take_profit_points", 100)
        
        if direction == "buy":
            return entry_price + points
        else:
            return entry_price - points
    
    def get_position_size(self, rules: Dict[str, Any]) -> int:
        """取得倉位大小"""
        return rules.get("position_size", 1)
    
    def get_timeframe(self, rules: Dict[str, Any]) -> str:
        """取得時間週期"""
        return rules.get("timeframe", "15m")
    
    def get_required_bars(self, indicator: str, params: Dict) -> int:
        """計算每個指標所需的最小 K 棒數量（含動態緩衝）
        
        Args:
            indicator: 指標名稱
            params: 指標參數
            
        Returns:
            所需的 K 棒數量
        """
        if indicator == "price_breaks_high":
            period = params.get("period", 20)
            return period + self._calculate_buffer(period)
        
        elif indicator == "price_below_low":
            period = params.get("period", 10)
            return period + self._calculate_buffer(period)
        
        elif indicator == "price_breaks_ma":
            period = params.get("period", 20)
            return period + self._calculate_buffer(period)
        
        elif indicator == "price_below_ma":
            period = params.get("period", 20)
            return period + self._calculate_buffer(period)
        
        elif indicator in ["rsi_oversold", "rsi_overbought", "rsi_cross_up", "rsi_cross_down"]:
            period = params.get("period", 14)
            return period + self._calculate_buffer(period)
        
        elif indicator in ["macd_cross_up", "macd_cross_down", "macd_histogram_positive", "macd_histogram_negative"]:
            return 34 + self._calculate_buffer(34)
        
        elif indicator in ["ma_cross_up", "ma_cross_down"]:
            long_period = params.get("long_period", 20)
            return long_period + self._calculate_buffer(long_period)
        
        elif indicator in ["volume_surge", "volume_decline"]:
            period = params.get("period", 20)
            return period + self._calculate_buffer(period)
        
        elif indicator in ["consecutive_up", "consecutive_down"]:
            period = params.get("period", 3)
            return period + self._calculate_buffer(period)
        
        elif indicator in ["price_at_upper_band", "price_at_lower_band", "price_breaks_upper", "price_breaks_lower"]:
            period = params.get("period", 20)
            return period + self._calculate_buffer(period)
        
        elif indicator in ["kd_oversold", "kd_overbought", "kd_cross_up", "kd_cross_down"]:
            return 10 + self._calculate_buffer(10)
        
        return 50 + self._calculate_buffer(50)
    
    def _calculate_buffer(self, base_period: int) -> int:
        """計算緩衝數量 - 使用 base_period 的 100% 作為緩衝
        
        Args:
            base_period: 基礎週期
            
        Returns:
            緩衝數量（至少 20，最多等於 base_period）
        """
        return max(base_period, 20)
