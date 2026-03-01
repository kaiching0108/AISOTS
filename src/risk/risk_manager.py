"""風控管理器"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.logger import logger


class RiskManager:
    """風控管理器"""
    
    def __init__(self, config: dict):
        self.max_daily_loss = config.get("max_daily_loss", 50000)
        self.max_position = config.get("max_position", 10)
        self.max_orders_per_minute = config.get("max_orders_per_minute", 5)
        self.enable_stop_loss = config.get("enable_stop_loss", True)
        self.enable_take_profit = config.get("enable_take_profit", True)
        
        # 記錄
        self.daily_pnl = 0.0
        self.daily_start_time = datetime.now()
        self.order_timestamps: list[datetime] = []
    
    def check_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        current_positions: int,
        daily_pnl: float
    ) -> Dict[str, Any]:
        """檢查下單是否通過風控"""
        
        # 1. 檢查下單頻率
        if not self._check_order_rate():
            return {
                "passed": False,
                "reason": f"下單頻率過高，超過 {self.max_orders_per_minute} 次/分鐘"
            }
        
        # 2. 檢查最大口數 (使用絕對值)
        new_total = abs(current_positions) + abs(quantity)
        if new_total > self.max_position:
            return {
                "passed": False,
                "reason": f"超過最大部位限制 {self.max_position} 口 (目前: {abs(current_positions)}, 新增: {abs(quantity)})"
            }
        
        # 3. 檢查單日虧損
        if daily_pnl < -self.max_daily_loss:
            return {
                "passed": False,
                "reason": f"單日虧損已達 {self.max_daily_loss} 元 (目前: {daily_pnl})，停止交易"
            }
        
        # 4. 檢查價格合理性
        if price > 0:
            # 這裡可以加入價格合理性檢查
            pass
        
        # 記錄下單時間
        self.order_timestamps.append(datetime.now())
        
        return {
            "passed": True,
            "reason": "風控檢查通過"
        }
    
    def _check_order_rate(self) -> bool:
        """檢查下單頻率"""
        now = datetime.now()
        
        # 清除超過1分鐘的記錄
        self.order_timestamps = [
            t for t in self.order_timestamps 
            if (now - t).seconds < 60
        ]
        
        return len(self.order_timestamps) < self.max_orders_per_minute
    
    def check_stop_loss(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        stop_loss_points: int
    ) -> bool:
        """檢查是否觸發停損"""
        if not self.enable_stop_loss:
            return False
        
        if direction == "Buy":
            loss = entry_price - current_price
        else:
            loss = current_price - entry_price
        
        return loss >= stop_loss_points
    
    def check_take_profit(
        self,
        entry_price: float,
        current_price: float,
        direction: str,
        take_profit_points: int
    ) -> bool:
        """檢查是否觸發止盈"""
        if not self.enable_take_profit:
            return False
        
        if direction == "Buy":
            profit = current_price - entry_price
        else:
            profit = entry_price - current_price
        
        return profit >= take_profit_points
    
    def reset_daily(self) -> None:
        """重置每日風控"""
        self.daily_pnl = 0.0
        self.daily_start_time = datetime.now()
        self.order_timestamps.clear()
        logger.info("風控每日重置")
    
    def update_daily_pnl(self, pnl: float) -> None:
        """更新當日損益"""
        self.daily_pnl = pnl
    
    def get_status(self) -> Dict[str, Any]:
        """取得風控狀態"""
        return {
            "daily_pnl": self.daily_pnl,
            "max_daily_loss": self.max_daily_loss,
            "max_position": self.max_position,
            "orders_this_minute": len(self.order_timestamps),
            "max_orders_per_minute": self.max_orders_per_minute,
            "stop_loss_enabled": self.enable_stop_loss,
            "take_profit_enabled": self.enable_take_profit
        }
    
    def is_trading_allowed(self) -> bool:
        """檢查是否允許交易"""
        if self.daily_pnl < -self.max_daily_loss:
            logger.warning(f"單日虧損達限，停止交易: {self.daily_pnl}")
            return False
        return True
