"""訊號記錄器 - 記錄策略交易訊號"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from src.storage.json_store import JSONStore


class SignalRecorder:
    """記錄策略訊號和執行結果"""
    
    def __init__(self, workspace_dir: Path):
        self.store = JSONStore(workspace_dir)
        self.filename = "signals.json"
    
    def record_signal(
        self,
        strategy_id: str,
        signal: str,
        price: float,
        indicators: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> str:
        """記錄訊號
        
        Args:
            strategy_id: 策略 ID
            signal: 訊號類型 (buy/sell/close)
            price: 訊號產生時的價格
            indicators: 當時的指標值
            timestamp: 時間戳
            
        Returns:
            signal_id: 訊號唯一識別碼
        """
        signal_id = f"sig_{uuid.uuid4().hex[:12]}"
        
        record = {
            "signal_id": signal_id,
            "strategy_id": strategy_id,
            "timestamp": timestamp or datetime.now().isoformat(),
            "signal": signal,
            "price": price,
            "indicators": indicators or {},
            "status": "pending",
            "exit_reason": None,
            "exit_price": None,
            "pnl": None,
            "filled_at": None,
            "filled_quantity": None
        }
        
        self.store.append(self.filename, record)
        return signal_id
    
    def update_result(
        self,
        signal_id: str,
        status: str,
        exit_price: Optional[float] = None,
        exit_reason: Optional[str] = None,
        pnl: Optional[float] = None,
        filled_at: Optional[str] = None,
        filled_quantity: Optional[int] = None
    ) -> bool:
        """更新訊號結果（平倉時呼叫）
        
        Args:
            signal_id: 訊號 ID
            status: 狀態 (filled/cancelled)
            exit_price: 出場價格
            exit_reason: 出場原因 (stop_loss/take_profit/signal_reversal)
            pnl: 損益
            filled_at: 成交時間
            filled_quantity: 成交數量
            
        Returns:
            bool: 是否更新成功
        """
        signals = self.store.list_all(self.filename)
        
        for i, sig in enumerate(signals):
            if sig.get("signal_id") == signal_id:
                sig["status"] = status
                if exit_price is not None:
                    sig["exit_price"] = exit_price
                if exit_reason is not None:
                    sig["exit_reason"] = exit_reason
                if pnl is not None:
                    sig["pnl"] = pnl
                if filled_at is not None:
                    sig["filled_at"] = filled_at
                if filled_quantity is not None:
                    sig["filled_quantity"] = filled_quantity
                    
                signals[i] = sig
                self.store.save(self.filename, signals)
                return True
        
        return False
    
    def get_signals(
        self, 
        strategy_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """取得訊號記錄
        
        Args:
            strategy_id: 策略 ID（可選）
            status: 狀態過濾（可選）
            
        Returns:
            List[dict]: 訊號記錄列表
        """
        signals = self.store.list_all(self.filename)
        
        filtered = signals
        if strategy_id:
            filtered = [s for s in filtered if s.get("strategy_id") == strategy_id]
        if status:
            filtered = [s for s in filtered if s.get("status") == status]
            
        return filtered
    
    def get_filled_signals(self, strategy_id: str) -> List[Dict[str, Any]]:
        """取得已成交的訊號"""
        return self.get_signals(strategy_id=strategy_id, status="filled")
    
    def get_pending_signals(self, strategy_id: str) -> List[Dict[str, Any]]:
        """取得待執行的訊號"""
        return self.get_signals(strategy_id=strategy_id, status="pending")
    
    def clear_signals(self, strategy_id: Optional[str] = None) -> int:
        """清除訊號記錄
        
        Args:
            strategy_id: 策略 ID（可選，不提供則清除全部）
            
        Returns:
            int: 清除的數量
        """
        if strategy_id is None:
            self.store.save(self.filename, [])
            return 0
        
        signals = self.store.list_all(self.filename)
        remaining = [s for s in signals if s.get("strategy_id") != strategy_id]
        cleared = len(signals) - len(remaining)
        
        self.store.save(self.filename, remaining)
        return cleared
