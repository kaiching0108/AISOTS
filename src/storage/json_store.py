"""JSON 檔案儲存"""
import json
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class JSONStore:
    """JSON 檔案儲存管理器"""
    
    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir
        self.workspace.mkdir(exist_ok=True)
    
    def _get_file_path(self, filename: str) -> Path:
        return self.workspace / filename
    
    def load(self, filename: str, default: Any = None) -> Any:
        """載入 JSON 檔案"""
        path = self._get_file_path(filename)
        if not path.exists():
            return default if default is not None else {}
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default if default is not None else {}
    
    def save(self, filename: str, data: Any) -> None:
        """儲存 JSON 檔案"""
        path = self._get_file_path(filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    def append(self, filename: str, item: dict) -> None:
        """追加資料到 JSON 陣列"""
        data = self.load(filename, [])
        if not isinstance(data, list):
            data = []
        data.append(item)
        self.save(filename, data)
    
    def update(self, filename: str, key: str, value: Any) -> None:
        """更新 JSON 物件"""
        data = self.load(filename, {})
        data[key] = value
        self.save(filename, data)
    
    def delete(self, filename: str, key: str) -> None:
        """刪除 JSON 物件 key"""
        data = self.load(filename, {})
        if key in data:
            del data[key]
            self.save(filename, data)
    
    def list_all(self, filename: str) -> list:
        """列出所有資料"""
        return self.load(filename, [])
    
    def find(self, filename: str, key: str, value: Any) -> Optional[dict]:
        """查詢資料"""
        data = self.load(filename, [])
        for item in data:
            if item.get(key) == value:
                return item
        return None
    
    def find_all(self, filename: str, key: str, value: Any) -> list:
        """查詢所有符合的資料"""
        data = self.load(filename, [])
        return [item for item in data if item.get(key) == value]
    
    def update_by_key(self, filename: str, key_field: str, key_value: Any, updates: dict) -> bool:
        """根據 key 欄位更新資料"""
        data = self.load(filename, [])
        for i, item in enumerate(data):
            if item.get(key_field) == key_value:
                data[i].update(updates)
                data[i]["updated_at"] = datetime.now().isoformat()
                self.save(filename, data)
                return True
        return False
    
    def delete_by_key(self, filename: str, key_field: str, key_value: Any) -> bool:
        """根據 key 欄位刪除資料"""
        data = self.load(filename, [])
        original_len = len(data)
        data = [item for item in data if item.get(key_field) != key_value]
        if len(data) < original_len:
            self.save(filename, data)
            return True
        return False


class StrategyStore(JSONStore):
    """策略儲存"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.file = "strategies.json"
    
    def get_all(self) -> list:
        return self.load(self.file, [])
    
    def get_by_id(self, strategy_id: str) -> Optional[dict]:
        return self.find(self.file, "id", strategy_id)
    
    def get_enabled(self) -> list:
        return [s for s in self.get_all() if s.get("enabled", False)]
    
    def save_strategy(self, strategy: dict) -> None:
        strategies = self.get_all()
        for i, s in enumerate(strategies):
            if s["id"] == strategy["id"]:
                strategies[i] = strategy
                break
        else:
            strategies.append(strategy)
        self.save(self.file, strategies)
    
    def enable_strategy(self, strategy_id: str) -> bool:
        return self.update_by_key(self.file, "id", strategy_id, {"enabled": True})
    
    def disable_strategy(self, strategy_id: str) -> bool:
        return self.update_by_key(self.file, "id", strategy_id, {"enabled": False})


class PositionStore(JSONStore):
    """部位儲存"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.file = "positions.json"
    
    def get_all(self) -> list:
        return self.load(self.file, [])
    
    def get_by_strategy(self, strategy_id: str) -> list:
        return self.find_all(self.file, "strategy_id", strategy_id)
    
    def get_open_positions(self) -> list:
        return [p for p in self.get_all() if p.get("quantity", 0) > 0]
    
    def add_position(self, position: dict) -> None:
        self.append(self.file, position)
    
    def close_position(self, strategy_id: str) -> bool:
        return self.update_by_key(
            self.file, "strategy_id", strategy_id,
            {"quantity": 0, "closed_at": datetime.now().isoformat()}
        )
    
    def update_position(self, strategy_id: str, updates: dict) -> bool:
        return self.update_by_key(self.file, "strategy_id", strategy_id, updates)


class OrderStore(JSONStore):
    """訂單儲存"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.file = "orders.json"
    
    def get_all(self) -> list:
        return self.load(self.file, [])
    
    def get_by_strategy(self, strategy_id: str) -> list:
        return self.find_all(self.file, "strategy_id", strategy_id)
    
    def get_by_date(self, date: str) -> list:
        return self.find_all(self.file, "date", date)
    
    def add_order(self, order: dict) -> None:
        self.append(self.file, order)
    
    def update_order_status(self, order_id: str, status: str, filled_price: float = None) -> bool:
        updates = {"status": status}
        if filled_price:
            updates["filled_price"] = filled_price
            updates["filled_time"] = datetime.now().isoformat()
        return self.update_by_key(self.file, "order_id", order_id, updates)


class PerformanceStore(JSONStore):
    """績效儲存"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.file = "performance.json"
    
    def get_by_strategy(self, strategy_id: str) -> list:
        return self.find_all(self.file, "strategy_id", strategy_id)
    
    def get_by_date(self, date: str) -> list:
        return self.find_all(self.file, "date", date)
    
    def update_strategy_performance(self, strategy_id: str, date: str, perf: dict) -> None:
        performances = self.load(self.file, [])
        for i, p in enumerate(performances):
            if p.get("strategy_id") == strategy_id and p.get("date") == date:
                performances[i] = perf
                self.save(self.file, performances)
                return
        
        perf["strategy_id"] = strategy_id
        perf["date"] = date
        performances.append(perf)
        self.save(self.file, performances)
    
    def calculate_total_pnl(self, date: str) -> float:
        perfs = self.get_by_date(date)
        return sum(p.get("total_pnl", 0) for p in perfs)
