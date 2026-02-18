"""訊號記錄器 - 記錄策略交易訊號（版本化儲存）"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class SignalRecorder:
    """記錄策略訊號和執行結果
    
    檔案結構：
    workspace/signals/
    ├── strategy_001_v1.json   # v1 版本訊號
    ├── strategy_001_v2.json   # v2 版本訊號
    ├── strategy_002_v1.json
    └── ...
    """
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = Path(workspace_dir)
        self.signals_dir = self.workspace_dir / "signals"
        self.signals_dir.mkdir(exist_ok=True)
    
    def _get_version_file(self, strategy_id: str, version: int) -> Path:
        """取得版本檔案路徑"""
        return self.signals_dir / f"{strategy_id}_v{version}.json"
    
    def _load_version_signals(self, strategy_id: str, version: int) -> List[Dict[str, Any]]:
        """載入特定版本的訊號"""
        version_file = self._get_version_file(strategy_id, version)
        if version_file.exists():
            try:
                return json.loads(version_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"載入訊號失敗: {e}")
                return []
        return []
    
    def _save_version_signals(self, strategy_id: str, version: int, signals: List[Dict[str, Any]]) -> None:
        """儲存特定版本的訊號"""
        version_file = self._get_version_file(strategy_id, version)
        version_file.write_text(
            json.dumps(signals, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    
    def _get_latest_version(self, strategy_id: str) -> int:
        """取得策略的最新版本號"""
        files = list(self.signals_dir.glob(f"{strategy_id}_v*.json"))
        if not files:
            return 1
        
        versions = []
        for f in files:
            try:
                version = int(f.stem.split("_v")[1])
                versions.append(version)
            except (ValueError, IndexError):
                continue
        
        return max(versions) if versions else 1
    
    def record_signal(
        self,
        strategy_id: str,
        strategy_version: int,
        signal: str,
        price: float,
        indicators: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None
    ) -> str:
        """記錄訊號
        
        Args:
            strategy_id: 策略 ID
            strategy_version: 策略版本號
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
            "strategy_version": strategy_version,
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
        
        signals = self._load_version_signals(strategy_id, strategy_version)
        signals.append(record)
        self._save_version_signals(strategy_id, strategy_version, signals)
        
        return signal_id
    
    def update_result(
        self,
        signal_id: str,
        strategy_id: str,
        strategy_version: int,
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
            strategy_id: 策略 ID
            strategy_version: 策略版本號
            status: 狀態 (filled/cancelled)
            exit_price: 出場價格
            exit_reason: 出場原因 (stop_loss/take_profit/signal_reversal)
            pnl: 損益
            filled_at: 成交時間
            filled_quantity: 成交數量
            
        Returns:
            bool: 是否更新成功
        """
        signals = self._load_version_signals(strategy_id, strategy_version)
        
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
                self._save_version_signals(strategy_id, strategy_version, signals)
                return True
        
        return False
    
    def get_signals(
        self,
        strategy_id: str,
        version: Optional[int] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """取得訊號記錄
        
        Args:
            strategy_id: 策略 ID
            version: 版本號 (None 表示最新版本)
            status: 狀態過濾（可選）
            
        Returns:
            List[dict]: 訊號記錄列表
        """
        if version is None:
            version = self._get_latest_version(strategy_id)
        
        signals = self._load_version_signals(strategy_id, version)
        
        if status:
            signals = [s for s in signals if s.get("status") == status]
        
        return signals
    
    def get_filled_signals(self, strategy_id: str, version: Optional[int] = None) -> List[Dict[str, Any]]:
        """取得已成交的訊號"""
        return self.get_signals(strategy_id=strategy_id, version=version, status="filled")
    
    def get_pending_signals(self, strategy_id: str, version: Optional[int] = None) -> List[Dict[str, Any]]:
        """取得待執行的訊號"""
        return self.get_signals(strategy_id=strategy_id, version=version, status="pending")
    
    def get_latest_version(self, strategy_id: str) -> int:
        """取得策略的最新版本號"""
        return self._get_latest_version(strategy_id)
    
    def get_all_versions(self, strategy_id: str) -> List[int]:
        """取得策略的所有版本號"""
        files = list(self.signals_dir.glob(f"{strategy_id}_v*.json"))
        versions = []
        for f in files:
            try:
                version = int(f.stem.split("_v")[1])
                versions.append(version)
            except (ValueError, IndexError):
                continue
        return sorted(versions)
    
    def clear_signals(self, strategy_id: str, version: Optional[int] = None) -> int:
        """清除訊號記錄
        
        Args:
            strategy_id: 策略 ID
            version: 版本號 (None 表示最新版本)
            
        Returns:
            int: 清除的數量
        """
        if version is None:
            version = self._get_latest_version(strategy_id)
        
        signals = self._load_version_signals(strategy_id, version)
        count = len(signals)
        
        if count > 0:
            self._save_version_signals(strategy_id, version, [])
        
        return count
    
    def archive_to_new_version(self, strategy_id: str, old_version: int, new_version: int) -> int:
        """將舊版本訊號歸檔到新版本（建立新版本檔案）
        
        Args:
            strategy_id: 策略 ID
            old_version: 舊版本號
            new_version: 新版本號
            
        Returns:
            int: 歸檔的訊號數量
        """
        old_signals = self._load_version_signals(strategy_id, old_version)
        count = len(old_signals)
        
        new_file = self._get_version_file(strategy_id, new_version)
        if not new_file.exists():
            new_file.write_text("[]", encoding="utf-8")
        
        logger.info(f"策略 {strategy_id} 版本 {old_version} → {new_version}，歸檔 {count} 筆訊號")
        return count
