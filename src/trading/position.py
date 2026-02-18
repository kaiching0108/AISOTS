"""部位類別"""
from datetime import datetime
from typing import Optional
from src.storage.models import PositionDirection


class Position:
    """部位類別"""
    
    def __init__(
        self,
        strategy_id: str,
        strategy_name: str,
        symbol: str,
        direction: str,  # Buy (多) / Sell (空)
        quantity: int,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        signal_id: Optional[str] = None,
        strategy_version: int = 1
    ):
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.direction = direction
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_time = datetime.now().isoformat()
        
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.signal_id = signal_id
        self.strategy_version = strategy_version
        
        self.current_price = entry_price
        self.pnl = 0.0
        
        # 點數價值 (大台200元/點, 小台50元/點)
        self.point_value = 200 if "TXF" in symbol or "T" in symbol else 50
    
    def calculate_pnl(self, current_price: float) -> float:
        """計算未實現損益"""
        self.current_price = current_price
        
        if self.direction == "Buy":
            self.pnl = (current_price - self.entry_price) * self.quantity * self.point_value
        else:  # Sell
            self.pnl = (self.entry_price - current_price) * self.quantity * self.point_value
        
        return self.pnl
    
    def check_stop_loss(self, current_price: float) -> bool:
        """檢查是否觸發停損"""
        if not self.stop_loss:
            return False
        
        if self.direction == "Buy":
            return current_price <= self.stop_loss
        else:
            return current_price >= self.stop_loss
    
    def check_take_profit(self, current_price: float) -> bool:
        """檢查是否觸發止盈"""
        if not self.take_profit:
            return False
        
        if self.direction == "Buy":
            return current_price >= self.take_profit
        else:
            return current_price <= self.take_profit
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "direction": self.direction,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "current_price": self.current_price,
            "pnl": self.pnl,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "signal_id": self.signal_id,
            "strategy_version": self.strategy_version
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """從字典建立"""
        position = cls(
            strategy_id=data.get("strategy_id", ""),
            strategy_name=data.get("strategy_name", ""),
            symbol=data.get("symbol", ""),
            direction=data.get("direction", "Buy"),
            quantity=data.get("quantity", 0),
            entry_price=data.get("entry_price", 0),
            stop_loss=data.get("stop_loss"),
            take_profit=data.get("take_profit"),
            signal_id=data.get("signal_id"),
            strategy_version=data.get("strategy_version", 1)
        )
        position.entry_time = data.get("entry_time", position.entry_time)
        position.current_price = data.get("current_price", position.entry_price)
        position.pnl = data.get("pnl", 0)
        return position
    
    def __repr__(self) -> str:
        return f"Position({self.symbol} {self.direction} {self.quantity}口 @ {self.entry_price}, PnL: {self.pnl})"
