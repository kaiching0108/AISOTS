"""訂單類別"""
from datetime import datetime
from typing import Optional
import uuid


class Order:
    """訂單類別"""
    
    def __init__(
        self,
        strategy_id: str,
        strategy_name: str,
        symbol: str,
        action: str,  # Buy / Sell
        quantity: int,
        price: float = 0,
        price_type: str = "LMT",
        order_type: str = "ROD",
        reason: str = ""
    ):
        self.order_id = f"ord_{uuid.uuid4().hex[:8]}"
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.action = action
        self.quantity = quantity
        self.price = price
        self.price_type = price_type
        self.order_type = order_type
        self.reason = reason
        
        self.status = "Pending"  # Pending, Submitted, Filled, Cancelled, Rejected
        self.filled_price: Optional[float] = None
        self.filled_time: Optional[str] = None
        self.timestamp = datetime.now().isoformat()
        
        # Shioaji 相關
        self.shioaji_trade: Optional[any] = None
        self.seqno: Optional[str] = None
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "order_id": self.order_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "price_type": self.price_type,
            "order_type": self.order_type,
            "reason": self.reason,
            "status": self.status,
            "filled_price": self.filled_price,
            "filled_time": self.filled_time,
            "timestamp": self.timestamp,
            "seqno": self.seqno
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        """從字典建立"""
        order = cls(
            strategy_id=data.get("strategy_id", ""),
            strategy_name=data.get("strategy_name", ""),
            symbol=data.get("symbol", ""),
            action=data.get("action", "Buy"),
            quantity=data.get("quantity", 0),
            price=data.get("price", 0),
            price_type=data.get("price_type", "LMT"),
            order_type=data.get("order_type", "ROD"),
            reason=data.get("reason", "")
        )
        order.order_id = data.get("order_id", order.order_id)
        order.status = data.get("status", "Pending")
        order.filled_price = data.get("filled_price")
        order.filled_time = data.get("filled_time")
        order.timestamp = data.get("timestamp", order.timestamp)
        order.seqno = data.get("seqno")
        return order
    
    def mark_submitted(self, seqno: str = None) -> None:
        """標記為已提交"""
        self.status = "Submitted"
        if seqno:
            self.seqno = seqno
    
    def mark_filled(self, filled_price: float) -> None:
        """標記為已成交"""
        self.status = "Filled"
        self.filled_price = filled_price
        self.filled_time = datetime.now().isoformat()
    
    def mark_cancelled(self) -> None:
        """標記為已取消"""
        self.status = "Cancelled"
    
    def mark_rejected(self, reason: str = "") -> None:
        """標記為已拒絕"""
        self.status = "Rejected"
        self.reason = reason
    
    def __repr__(self) -> str:
        return f"Order({self.symbol} {self.action} {self.quantity} @ {self.price}, status={self.status})"
