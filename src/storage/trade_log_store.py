"""交易日誌儲存 - 記錄重要交易事件，保留7天"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class TradeLogEntry:
    """交易日誌條目"""
    id: str                      # 唯一ID (timestamp_random)
    timestamp: str              # ISO 格式時間
    event_type: str            # 事件類型: ORDER_SUCCESS, CLOSE_POSITION, RISK_BLOCKED, ORDER_FAILED
    strategy_id: str           # 策略ID
    strategy_name: str         # 策略名稱
    symbol: str               # 期貨代碼
    message: str              # 詳細訊息
    details: Dict            # 額外資訊 (價格、數量、損益等)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class TradeLogStore:
    """交易日誌儲存類別
    
    功能：
    - 儲存最近7天的交易日誌
    - 最多保留1000條（自動清理舊資料）
    - 支援按事件類型過濾
    """
    
    def __init__(self, workspace_path: str = "workspace"):
        self.workspace = Path(workspace_path)
        self.log_dir = self.workspace / "logs" / "trade"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_entries = 1000   # 最大條目數
        self.retention_days = 7   # 保留天數
        
    def _get_filename(self, date: datetime) -> Path:
        """取得該日期的日誌檔案路徑"""
        return self.log_dir / f"trade_logs_{date.strftime('%Y%m%d')}.json"
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        import random
        return f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"
    
    def add_log(self, event_type: str, strategy_id: str, strategy_name: str, 
                symbol: str, message: str, details: Optional[Dict] = None) -> str:
        """添加交易日誌
        
        Args:
            event_type: ORDER_SUCCESS, CLOSE_POSITION, RISK_BLOCKED, ORDER_FAILED
            strategy_id: 策略ID
            strategy_name: 策略名稱
            symbol: 期貨代碼
            message: 簡短訊息
            details: 額外資訊字典
            
        Returns:
            log_id: 日誌條目ID
        """
        entry = TradeLogEntry(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            message=message,
            details=details or {}
        )
        
        # 寫入當日檔案
        today_file = self._get_filename(datetime.now())
        logs = self._load_file(today_file)
        logs.append(entry.to_dict())
        
        # 如果超過限制，保留最新的
        if len(logs) > self.max_entries:
            logs = logs[-self.max_entries:]
            
        self._save_file(today_file, logs)
        
        # 清理舊檔案
        self._cleanup_old_files()
        
        return entry.id
    
    def _load_file(self, filepath: Path) -> List[Dict]:
        """載入日誌檔案"""
        if not filepath.exists():
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    
    def _save_file(self, filepath: Path, data: List[Dict]):
        """儲存日誌檔案"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _cleanup_old_files(self):
        """清理超過保留期限的檔案"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for file in self.log_dir.glob("trade_logs_*.json"):
            try:
                # 從檔名解析日期
                date_str = file.stem.replace("trade_logs_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d")
                
                if file_date < cutoff_date:
                    file.unlink()
            except Exception:
                pass
    
    def get_recent_logs(self, limit: int = 50, event_type: Optional[str] = None,
                       strategy_id: Optional[str] = None) -> List[Dict]:
        """取得最近的交易日誌
        
        Args:
            limit: 最多返回條數 (預設50)
            event_type: 過濾特定事件類型 (可選)
            strategy_id: 過濾特定策略 (可選)
            
        Returns:
            日誌條目列表 (由新到舊排序)
        """
        all_logs = []
        
        # 載入最近7天的所有檔案
        for days_ago in range(self.retention_days):
            date = datetime.now() - timedelta(days=days_ago)
            filepath = self._get_filename(date)
            logs = self._load_file(filepath)
            all_logs.extend(logs)
        
        # 由新到舊排序
        all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 過濾
        filtered = all_logs
        if event_type:
            filtered = [log for log in filtered if log['event_type'] == event_type]
        if strategy_id:
            filtered = [log for log in filtered if log['strategy_id'] == strategy_id]
        
        return filtered[:limit]
    
    def get_event_types(self) -> List[str]:
        """取得所有可用的事件類型（用於過濾選項）"""
        return ["ORDER_SUCCESS", "CLOSE_POSITION", "RISK_BLOCKED", "ORDER_FAILED", "SYSTEM"]
    
    def get_stats(self) -> Dict:
        """取得日誌統計"""
        logs = self.get_recent_logs(limit=1000)
        return {
            "total_24h": len([l for l in logs if self._is_within_hours(l['timestamp'], 24)]),
            "total_7d": len(logs),
            "by_type": {
                et: len([l for l in logs if l['event_type'] == et])
                for et in self.get_event_types()
            }
        }
    
    def _is_within_hours(self, timestamp: str, hours: int) -> bool:
        """檢查時間戳是否在指定小時內"""
        try:
            log_time = datetime.fromisoformat(timestamp)
            return (datetime.now() - log_time).total_seconds() < hours * 3600
        except:
            return False
