"""訂單回調處理"""
from typing import Callable, Dict, Any, Optional

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
            # 先檢查是否為成交回報（OrderState.FuturesDeal）
            # 成交回報有 trade_id 欄位，與委託回報結構不同
            if "trade_id" in msg:
                # 這是成交回報
                self._handle_deal_event(msg)
                return
            
            # 以下是委託回報的處理邏輯
            operation = msg.get("operation", {})
            op_type = operation.get("op_type", "")
            op_code = operation.get("op_code", "")
            op_msg = operation.get("op_msg", "")
            
            order_info = msg.get("order", {})
            seqno = order_info.get("id", "")  # Shioaji 分配的序號
            
            status_info = msg.get("status", {})
            
            # 根據操作類型處理
            if op_type == "New":
                if op_code == "00":
                    logger.info(f"新委託成功：seqno={seqno}")
                    if self.on_order_submitted:
                        self.on_order_submitted(seqno, msg)
                else:
                    logger.warning(f"新委託失敗：seqno={seqno}, 原因：{op_msg}")
                    if self.on_order_rejected:
                        self.on_order_rejected(seqno, msg)
                    
            elif op_type == "Cancel":
                if op_code == "00":
                    logger.info(f"取消委託成功：seqno={seqno}")
                    if self.on_order_cancelled:
                        self.on_order_cancelled(seqno, msg)
                    self.remove_trade(seqno)
                else:
                    logger.warning(f"取消委託失敗：seqno={seqno}, 原因：{op_msg}")
            
            elif op_type == "Update":
                if op_code == "00":
                    logger.info(f"更新委託成功：seqno={seqno}")
                    if self.on_order_updated:
                        self.on_order_updated(seqno, msg)
            
        except Exception as e:
            logger.error(f"處理訂單回調失敗：{e}")
    
    def _handle_deal_event(self, msg: Dict) -> None:
        """處理成交回報（OrderState.FuturesDeal）
        
        成交回報結構：
        {
            'trade_id': 'xxx',      # 與委託回報的 id 相同
            'seqno': 'xxx',         # 平台單號
            'price': 25.0,          # 成交價
            'quantity': 1,          # 成交量
            'ts': 1764685425.0,     # 成交時間戳
            ...
        }
        """
        seqno = msg.get("seqno", "")
        trade_id = msg.get("trade_id", "")
        filled_price = msg.get("price", 0)
        quantity = msg.get("quantity", 0)
        
        logger.info(f"成交回報：seqno={seqno}, trade_id={trade_id}, price={filled_price}, quantity={quantity}")
        logger.debug(f"成交回報完整訊息：{msg}")
        
        if self.on_order_filled:
            self.on_order_filled(seqno, msg)
    
    def _check_filled(self, status_info: Dict, seqno: str, msg: Dict) -> None:
        """檢查是否成交（已棄用，改用 _handle_deal_event）
        
        注意：此方法已不再使用，因為成交會通過獨立的成交回報回調通知，
        而不是通過委託回報中的 status 判斷。
        """
        pass
    
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
            logger.error(f"處理報價失敗：{e}")
    
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
