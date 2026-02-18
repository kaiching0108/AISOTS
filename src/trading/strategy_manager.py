"""策略管理器"""
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.logger import logger
from src.trading.strategy import Strategy
from src.storage.json_store import StrategyStore


class StrategyManager:
    """策略管理器 - 管理3個策略"""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.store = StrategyStore(workspace_dir)
        self.strategies: Dict[str, Strategy] = {}
        self._load_strategies()
    
    def _load_strategies(self) -> None:
        """載入所有策略"""
        strategies_data = self.store.get_all_strategies()
        
        for data in strategies_data:
            strategy = Strategy.from_dict(data)
            self.strategies[strategy.id] = strategy
            logger.info(f"載入策略: {strategy.name} ({strategy.symbol}) - {'啟用' if strategy.enabled else '停用'}")
    
    def get_all_strategies(self) -> List[Strategy]:
        """取得所有策略"""
        return list(self.strategies.values())
    
    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """取得指定策略"""
        return self.strategies.get(strategy_id)
    
    def get_enabled_strategies(self) -> List[Strategy]:
        """取得所有啟用的策略"""
        return [s for s in self.strategies.values() if s.enabled]
    
    def get_strategy_by_symbol(self, symbol: str) -> Optional[Strategy]:
        """根據合約代碼取得策略"""
        for strategy in self.strategies.values():
            if strategy.symbol in symbol:
                return strategy
        return None
    
    def add_strategy(self, strategy: Strategy) -> None:
        """新增策略"""
        self.strategies[strategy.id] = strategy
        self.store.save_strategy(strategy.to_dict())
        logger.info(f"新增策略: {strategy.name}")
    
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> bool:
        """更新策略"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return False
        
        for key, value in updates.items():
            if hasattr(strategy, key):
                setattr(strategy, key, value)
        
        self.store.save_strategy(strategy.to_dict())
        logger.info(f"更新策略: {strategy.name}")
        return True
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """啟用策略"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return False
        
        strategy.enabled = True
        self.store.enable_strategy(strategy_id)
        logger.info(f"啟用策略: {strategy.name}")
        return True
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """停用策略"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return False
        
        strategy.enabled = False
        strategy.is_running = False
        self.store.disable_strategy(strategy_id)
        logger.info(f"停用策略: {strategy.name}")
        return True
    
    def disable_strategy_with_check(self, strategy_id: str, position_manager) -> dict:
        """停用策略 (含部位檢查)
        
        Returns:
            {
                "can_disable": bool,
                "has_positions": bool,
                "position": dict or None,
                "message": str
            }
        """
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return {
                "can_disable": False,
                "has_positions": False,
                "position": None,
                "message": f"找不到策略: {strategy_id}"
            }
        
        # 檢查部位
        position = position_manager.get_position(strategy_id)
        
        if position and position.quantity > 0:
            return {
                "can_disable": False,
                "has_positions": True,
                "position": position.to_dict(),
                "message": f"策略仍有部位: {position.symbol} {position.direction} {position.quantity}口"
            }
        
        # 無部位，可直接停用
        self.disable_strategy(strategy_id)
        return {
            "can_disable": True,
            "has_positions": False,
            "position": None,
            "message": "策略已停用"
        }
    
    def start_strategy(self, strategy_id: str) -> bool:
        """啟動策略執行"""
        strategy = self.strategies.get(strategy_id)
        if not strategy or not strategy.enabled:
            return False
        
        strategy.is_running = True
        logger.info(f"啟動策略: {strategy.name}")
        return True
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略執行"""
        strategy = self.strategies.get(strategy_id)
        if not strategy:
            return False
        
        strategy.is_running = False
        logger.info(f"停止策略: {strategy.name}")
        return True
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略"""
        if strategy_id not in self.strategies:
            return False
        
        strategy = self.strategies[strategy_id]
        del self.strategies[strategy_id]
        
        # 從儲存中刪除（包括策略、部位、訂單、訊號檔案）
        self.store.delete_strategy(strategy_id)
        logger.info(f"刪除策略: {strategy.name}")
        return True
    
    def reload_strategies(self) -> None:
        """重新載入策略"""
        self.strategies.clear()
        self._load_strategies()
    
    def get_strategy_status(self) -> List[Dict[str, Any]]:
        """取得所有策略狀態"""
        return [
            {
                "id": s.id,
                "name": s.name,
                "symbol": s.symbol,
                "enabled": s.enabled,
                "is_running": s.is_running,
                "last_signal": s.last_signal,
                "last_signal_time": s.last_signal_time
            }
            for s in self.strategies.values()
        ]
