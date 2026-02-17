"""資料模型"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class OrderAction(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class OrderStatus(str, Enum):
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"


class PositionDirection(str, Enum):
    LONG = "Long"
    SHORT = "Short"


class StrategyModel(BaseModel):
    """策略模型"""
    id: str
    name: str
    symbol: str
    prompt: str
    enabled: bool = False
    params: dict
    created_at: str = ""
    
    def __init__(self, **data):
        if "created_at" not in data or not data["created_at"]:
            data["created_at"] = datetime.now().isoformat()
        super().__init__(**data)


class PositionModel(BaseModel):
    """部位模型"""
    strategy_id: str
    strategy_name: str
    symbol: str
    direction: str  # Buy/Sell
    quantity: int
    entry_price: float
    entry_time: str
    current_price: Optional[float] = None
    pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def calculate_pnl(self, current_price: float) -> float:
        """計算未實現損益"""
        self.current_price = current_price
        if self.direction == "Buy":
            self.pnl = (current_price - self.entry_price) * self.quantity * 200  # 大台點數價值
        else:
            self.pnl = (self.entry_price - current_price) * self.quantity * 50  # 小台點數價值
        return self.pnl


class OrderModel(BaseModel):
    """訂單模型"""
    order_id: str
    strategy_id: str
    strategy_name: str
    symbol: str
    action: str  # Buy/Sell
    quantity: int
    price: float
    status: str = "Pending"
    filled_price: Optional[float] = None
    filled_time: Optional[str] = None
    timestamp: str
    reason: str = ""
    seqno: Optional[str] = None  # Shioaji 委託書號


class PerformanceModel(BaseModel):
    """績效模型"""
    date: str
    strategy_id: str
    strategy_name: str
    symbol: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    max_profit: float = 0.0
    max_loss: float = 0.0
    max_drawdown: float = 0.0
