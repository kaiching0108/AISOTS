"""訂單回調處理"""
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from src.logger import logger


class OrderCallbackHandler:
    """訂單回調處理器"""
    
    def __init__(self):
        # 儲存待處理的 trade 物件
        self.pending_trades: Dict[str, Any] = {}
        
        # 回調函數
        self.on_order_submitted: Optional[Callable] = None
        self.on_order_filled: Optional[Callable] = None
        self.on_order_cancelled: Optional[Callable] = None
        self.on_order_rejected: Optional[Callable] = None
        self.on_order_updated: Optional[Callable] = None
    
    def register_trade(self, order_id: str, trade: Any) -> None:
        """註冊 trade 物件"""
        self.pending_trades[order_id] = trade
    
    def get_trade(self, order_id: str) -> Optional[Any]:
        """取得 trade 物件"""
        return self.pending_trades.get(order_id)
    
    def remove_trade(self, order_id: str) -> None:
        """移除 trade 物件"""
        if order_id in self.pending_trades:
            del self.pending_trades[order_id]
    
    def handle_callback(self, stat: Any, msg: Dict) -> None:
        """處理訂單回調"""
        try:
            operation = msg.get("operation", {})
            op_type = operation.get("op_type", "")
            op_code = operation.get("op_code", "")
            op_msg = operation.get("op_msg", "")
            
            order_info = msg.get("order", {})
            order_id = order_info.get("id", "")
            
            status_info = msg.get("status", {})
            
            # 根據操作類型處理
            if op_type == "New":
                if op_code == "00":
                    logger.info(f"新委託成功: {order_id}")
                    if self.on_order_submitted:
                        self.on_order_submitted(order_id, msg)
                else:
                    logger.warning(f"新委託失敗: {order_id}, 原因: {op_msg}")
                    if self.on_order_rejected:
                        self.on_order_rejected(order_id, msg)
                    
            elif op_type == "Cancel":
                if op_code == "00":
                    logger.info(f"取消委託成功: {order_id}")
                    if self.on_order_cancelled:
                        self.on_order_cancelled(order_id, msg)
                    self.remove_trade(order_id)
                else:
                    logger.warning(f"取消委託失敗: {order_id}, 原因: {op_msg}")
            
            elif op_type == "Update":
                if op_code == "00":
                    logger.info(f"更新委託成功: {order_id}")
                    if self.on_order_updated:
                        self.on_order_updated(order_id, msg)
            
            # 檢查成交
            self._check_filled(status_info, order_id, msg)
            
        except Exception as e:
            logger.error(f"處理訂單回調失敗: {e}")
    
    def _check_filled(self, status_info: Dict, order_id: str, msg: Dict) -> None:
        """檢查是否成交"""
        # 成交數量
        order_quantity = status_info.get("order_quantity", 0)
        cancel_quantity = status_info.get("cancel_quantity", 0)
        
        if order_quantity > 0 and cancel_quantity == 0:
            logger.info(f"委託成交: {order_id}")
            if self.on_order_filled:
                self.on_order_filled(order_id, msg)
    
    def create_callback(self) -> Callable:
        """建立回調函數"""
        def callback(stat, msg):
            self.handle_callback(stat, msg)
        return callback
    
    def get_pending_count(self) -> int:
        """取得待處理委託數量"""
        return len(self.pending_trades)
    
    def clear_pending(self) -> None:
        """清除所有待處理委託"""
        self.pending_trades.clear()


class QuoteCallbackHandler:
    """報價回調處理器"""
    
    def __init__(self):
        self.latest_prices: Dict[str, float] = {}
        self.on_price_update: Optional[Callable] = None
    
    def handle_tick(self, exchange: Any, tick: Any) -> None:
        """處理 Tick 資料"""
        try:
            # 取得合約代碼和價格
            contract = tick.contract if hasattr(tick, "contract") else None
            if contract:
                symbol = contract.code
                price = tick.price if hasattr(tick, "price") else 0
                
                self.latest_prices[symbol] = price
                
                if self.on_price_update:
                    self.on_price_update(symbol, price, tick)
                    
        except Exception as e:
            logger.error(f"處理報價失敗: {e}")
    
    def create_tick_callback(self) -> Callable:
        """建立 Tick 回調函數"""
        def callback(exchange, tick):
            self.handle_tick(exchange, tick)
        return callback
    
    def get_price(self, symbol: str) -> Optional[float]:
        """取得最新價格"""
        return self.latest_prices.get(symbol)
    
    def get_all_prices(self) -> Dict[str, float]:
        """取得所有最新價格"""
        return self.latest_prices.copy()
