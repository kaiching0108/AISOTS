"""部位管理器"""
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

from src.trading.position import Position
from src.storage.json_store import PositionStore

logger = logging.getLogger(__name__)


class PositionManager:
    """部位管理器 - 按策略分開管理部位"""
    
    def __init__(self, workspace_dir: Path):
        self.store = PositionStore(workspace_dir)
        self.positions: Dict[str, Position] = {}  # strategy_id -> Position
        self._load_positions()
    
    def _load_positions(self) -> None:
        """載入部位"""
        positions_data = self.store.get_all()
        
        for data in positions_data:
            if data.get("quantity", 0) > 0:  # 只載入有部位的
                position = Position.from_dict(data)
                self.positions[position.strategy_id] = position
                logger.info(f"載入部位: {position.strategy_name} - {position.symbol} {position.direction} {position.quantity}口")
    
    def get_all_positions(self) -> List[Position]:
        """取得所有部位"""
        return list(self.positions.values())
    
    def get_position(self, strategy_id: str) -> Optional[Position]:
        """取得指定策略的部位"""
        return self.positions.get(strategy_id)
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Position]:
        """根據合約取得部位"""
        for position in self.positions.values():
            if position.symbol == symbol:
                return position
        return None
    
    def has_position(self, strategy_id: str) -> bool:
        """檢查是否有部位"""
        position = self.positions.get(strategy_id)
        return position is not None and position.quantity > 0
    
    def get_total_quantity(self) -> int:
        """取得總口數"""
        return sum(p.quantity for p in self.positions.values())
    
    def open_position(
        self,
        strategy_id: str,
        strategy_name: str,
        symbol: str,
        direction: str,
        quantity: int,
        entry_price: float,
        stop_loss_points: int = 0,
        take_profit_points: int = 0,
        signal_id: Optional[str] = None,
        strategy_version: int = 1
    ) -> Position:
        """開倉
        
        Args:
            stop_loss_points: 停損點數（0=不啟用）
            take_profit_points: 止盈點數（0=不啟用）
            signal_id: 訊號 ID（用於關聯訊號記錄）
            strategy_version: 策略版本號
        """
        # 先檢查是否已有部位
        if self.has_position(strategy_id):
            logger.warning(f"策略 {strategy_id} 已有部位，先平倉")
            self.close_position(strategy_id, entry_price)
        
        # 計算停損止盈價格（根據多空方向）
        stop_loss_price = None
        take_profit_price = None
        
        if stop_loss_points > 0:
            if direction == "Buy":
                # 多單：價格下跌觸發停損
                stop_loss_price = entry_price - stop_loss_points
            else:
                # 空單：價格上漲觸發停損
                stop_loss_price = entry_price + stop_loss_points
        
        if take_profit_points > 0:
            if direction == "Buy":
                # 多單：價格上漲觸發止盈
                take_profit_price = entry_price + take_profit_points
            else:
                # 空單：價格下跌觸發止盈
                take_profit_price = entry_price - take_profit_points
        
        position = Position(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=stop_loss_price,
            take_profit=take_profit_price,
            signal_id=signal_id,
            strategy_version=strategy_version
        )
        
        self.positions[strategy_id] = position
        self.store.add_position(position.to_dict())
        
        logger.info(f"開倉: {strategy_name} - {symbol} {direction} {quantity}口 @ {entry_price}, 停損: {stop_loss_price}, 止盈: {take_profit_price}")
        return position
    
    def close_position(self, strategy_id: str, exit_price: float) -> Optional[Dict]:
        """平倉"""
        position = self.positions.get(strategy_id)
        if not position:
            return None
        
        # 計算最終損益
        position.calculate_pnl(exit_price)
        
        result = {
            "strategy_id": position.strategy_id,
            "strategy_name": position.strategy_name,
            "symbol": position.symbol,
            "direction": position.direction,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "exit_price": exit_price,
            "pnl": position.pnl,
            "exit_time": datetime.now().isoformat()
        }
        
        # 更新儲存
        self.store.update_position(strategy_id, {
            "quantity": 0,
            "exit_price": exit_price,
            "exit_time": result["exit_time"],
            "pnl": position.pnl
        })
        
        # 移除記憶體中的部位
        del self.positions[strategy_id]
        
        logger.info(f"平倉: {position.strategy_name} - {symbol} @ {exit_price}, PnL: {position.pnl}")
        return result
    
    def update_prices(self, price_map: Dict[str, float]) -> List[Dict]:
        """更新部位價格"""
        triggered = []
        
        for strategy_id, position in self.positions.items():
            current_price = price_map.get(position.symbol)
            if current_price:
                position.calculate_pnl(current_price)
                
                # 檢查停損止盈
                if position.check_stop_loss(current_price):
                    triggered.append({
                        "strategy_id": strategy_id,
                        "type": "stop_loss",
                        "reason": f"觸發停損 {position.stop_loss}",
                        "exit_price": current_price
                    })
                elif position.check_take_profit(current_price):
                    triggered.append({
                        "strategy_id": strategy_id,
                        "type": "take_profit",
                        "reason": f"觸發止盈 {position.take_profit}",
                        "exit_price": current_price
                    })
        
        return triggered
    
    def get_positions_summary(self) -> List[Dict[str, Any]]:
        """取得部位摘要"""
        summary = []
        total_pnl = 0
        
        for position in self.positions.values():
            summary.append({
                "strategy_id": position.strategy_id,
                "strategy_name": position.strategy_name,
                "symbol": position.symbol,
                "direction": position.direction,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "pnl": position.pnl,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit
            })
            total_pnl += position.pnl
        
        return {
            "positions": summary,
            "total_quantity": self.get_total_quantity(),
            "total_pnl": total_pnl
        }
    
    def sync_with_shioaji(self, shioaji_positions: List) -> None:
        """與 Shioaji 部位同步"""
        # 取得 Shioaji 的部位
        shioaji_map = {}
        for pos in shioaji_positions:
            # 這裡需要根據實際結構調整
            code = pos.code if hasattr(pos, "code") else ""
            shioaji_map[code] = pos
        
        # 檢查差異
        for strategy_id, position in list(self.positions.items()):
            if position.symbol not in shioaji_map:
                logger.warning(f"策略 {strategy_id} 部位在 Shioaji 中找不到，可能已平倉")
