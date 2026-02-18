"""下單管理器"""
from typing import List, Optional, Dict, Any, Callable
from pathlib import Path
from datetime import datetime, timedelta

from src.logger import logger
from src.trading.order import Order
from src.storage.json_store import OrderStore


class OrderManager:
    """下單管理器"""
    
    def __init__(self, workspace_dir: Path):
        self.store = OrderStore(workspace_dir)
        self.pending_orders: Dict[str, Order] = {}  # order_id -> Order
        self.order_timestamps: List[datetime] = []  # 用於頻率限制
        
        # 回調
        self.on_order_submitted: Optional[Callable] = None
        self.on_order_filled: Optional[Callable] = None
        self.on_order_cancelled: Optional[Callable] = None
        self.on_order_rejected: Optional[Callable] = None
    
    def create_order(
        self,
        strategy_id: str,
        strategy_name: str,
        symbol: str,
        action: str,
        quantity: int,
        price: float = 0,
        price_type: str = "LMT",
        order_type: str = "ROD",
        reason: str = ""
    ) -> Order:
        """建立訂單"""
        order = Order(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            price_type=price_type,
            order_type=order_type,
            reason=reason
        )
        
        # 儲存到待處理
        self.pending_orders[order.order_id] = order
        
        # 記錄時間戳
        self.order_timestamps.append(datetime.now())
        
        # 寫入儲存
        self.store.add_order(order.to_dict())
        
        logger.info(f"建立訂單: {order}")
        return order
    
    def submit_order(self, order_id: str, seqno: str = None) -> bool:
        """提交訂單"""
        order = self.pending_orders.get(order_id)
        if not order:
            return False
        
        order.mark_submitted(seqno)
        
        # 更新儲存
        self.store.update_order_status(order_id, "Submitted")
        
        if self.on_order_submitted:
            self.on_order_submitted(order)
        
        logger.info(f"訂單已提交: {order_id}, seqno: {seqno}")
        return True
    
    def fill_order(self, order_id: str, filled_price: float) -> Optional[Order]:
        """成交"""
        order = self.pending_orders.get(order_id)
        if not order:
            return None
        
        order.mark_filled(filled_price)
        
        # 更新儲存
        self.store.update_order_status(order_id, "Filled", filled_price)
        
        if self.on_order_filled:
            self.on_order_filled(order)
        
        logger.info(f"訂單成交: {order_id} @ {filled_price}")
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """取消訂單"""
        order = self.pending_orders.get(order_id)
        if not order:
            return False
        
        order.mark_cancelled()
        
        # 更新儲存
        self.store.update_order_status(order_id, "Cancelled")
        
        # 從待處理移除
        del self.pending_orders[order_id]
        
        if self.on_order_cancelled:
            self.on_order_cancelled(order)
        
        logger.info(f"訂單已取消: {order_id}")
        return True
    
    def reject_order(self, order_id: str, reason: str = "") -> bool:
        """拒絕訂單"""
        order = self.pending_orders.get(order_id)
        if not order:
            return False
        
        order.mark_rejected(reason)
        
        # 更新儲存
        self.store.update_order_status(order_id, "Rejected")
        
        # 從待處理移除
        del self.pending_orders[order_id]
        
        if self.on_order_rejected:
            self.on_order_rejected(order, reason)
        
        logger.warning(f"訂單被拒絕: {order_id}, 原因: {reason}")
        return True
    
    def get_pending_orders(self) -> List[Order]:
        """取得待處理訂單"""
        return list(self.pending_orders.values())
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """取得訂單"""
        return self.pending_orders.get(order_id)
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[dict]:
        """取得策略的訂單"""
        return self.store.get_by_strategy(strategy_id)
    
    def get_today_orders(self) -> List[dict]:
        """取得今日訂單"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.store.get_by_date(today)
    
    def check_rate_limit(self, max_orders_per_minute: int = 5) -> bool:
        """檢查下單頻率限制"""
        now = datetime.now()
        
        # 清除超過1分鐘的記錄
        self.order_timestamps = [
            t for t in self.order_timestamps 
            if (now - t).seconds < 60
        ]
        
        if len(self.order_timestamps) >= max_orders_per_minute:
            logger.warning(f"下單頻率過高: {len(self.order_timestamps)}/{max_orders_per_minute}")
            return False
        
        return True
    
    def cleanup_old_orders(self, days: int = 30) -> None:
        """清理舊訂單"""
        # 這裡可以實作清理邏輯
        pass
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """取得訂單統計"""
        today_orders = self.get_today_orders()
        
        filled = [o for o in today_orders if o.get("status") == "Filled"]
        cancelled = [o for o in today_orders if o.get("status") == "Cancelled"]
        
        return {
            "total_orders": len(today_orders),
            "filled": len(filled),
            "cancelled": len(cancelled),
            "pending": len(self.pending_orders),
            "today": datetime.now().strftime("%Y-%m-%d")
        }
