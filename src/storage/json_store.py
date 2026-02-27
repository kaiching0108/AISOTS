"""JSON 檔案儲存"""
import json
from pathlib import Path
from typing import Any, Optional, List
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
        path.parent.mkdir(parents=True, exist_ok=True)
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
    """策略儲存 - per-strategy + versioning"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.strategies_dir = workspace_dir / "strategies"
        self.strategies_dir.mkdir(exist_ok=True)
    
    def _get_strategy_file(self, strategy_id: str, version: int = None) -> Path:
        """取得策略檔案路徑"""
        if version is None:
            version = self._get_latest_version(strategy_id)
        return self.strategies_dir / f"{strategy_id}_v{version}.json"
    
    def _get_latest_version(self, strategy_id: str) -> int:
        """取得策略的最新版本"""
        files = list(self.strategies_dir.glob(f"{strategy_id}_v*.json"))
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
    
    def get_all_versions(self, strategy_id: str) -> List[int]:
        """取得策略的所有版本"""
        files = list(self.strategies_dir.glob(f"{strategy_id}_v*.json"))
        versions = []
        for f in files:
            try:
                version = int(f.stem.split("_v")[1])
                versions.append(version)
            except (ValueError, IndexError):
                continue
        return sorted(versions)
    
    def get_all(self) -> List[dict]:
        """取得所有策略（相容性方法）"""
        return self.get_all_strategies()
    
    def load_strategy(self, strategy_id: str, version: int = None) -> Optional[dict]:
        """載入策略"""
        if version is None:
            version = self._get_latest_version(strategy_id)
        path = self._get_strategy_file(strategy_id, version)
        if path.exists():
            return self.load(f"strategies/{strategy_id}_v{version}.json")
        return None
    
    def save_strategy(self, strategy: dict) -> None:
        """儲存策略"""
        strategy_id = strategy.get("id", "")
        version = strategy.get("strategy_version", 1)
        filename = f"strategies/{strategy_id}_v{version}.json"
        strategies = self.load(filename, [])
        
        for i, s in enumerate(strategies):
            if s.get("id") == strategy_id:
                strategies[i] = strategy
                break
        else:
            strategies.append(strategy)
        
        self.save(filename, strategies)
    
    def save_strategy_new_version(self, strategy: dict, old_version: int, new_version: int) -> None:
        """儲存新版本策略"""
        strategy_id = strategy.get("id", "")
        old_filename = f"strategies/{strategy_id}_v{old_version}.json"
        new_filename = f"strategies/{strategy_id}_v{new_version}.json"
        
        old_data = self.load(old_filename, [])
        self.save(old_filename, old_data)
        
        self.save(new_filename, [strategy])
    
    def get_all_strategies(self) -> List[dict]:
        """取得所有策略（最新版本）"""
        all_strategies = {}
        
        for f in self.strategies_dir.glob("*.json"):
            try:
                parts = f.stem.split("_v")
                if len(parts) != 2:
                    continue
                strategy_id = parts[0]
                version = int(parts[1])
                
                if strategy_id not in all_strategies or version > all_strategies[strategy_id]["version"]:
                    data = self.load(f"strategies/{f.name}", [])
                    if data:
                        all_strategies[strategy_id] = {
                            "version": version,
                            "data": data[0] if isinstance(data, list) else data
                        }
            except (ValueError, IndexError):
                continue
        
        return [s["data"] for s in all_strategies.values()]
    
    def get_enabled_strategies(self) -> List[dict]:
        """取得啟用的策略"""
        return [s for s in self.get_all_strategies() if s.get("enabled", False)]
    
    def get_by_id(self, strategy_id: str, version: int = None) -> Optional[dict]:
        """根據 ID 取得策略"""
        return self.load_strategy(strategy_id, version)
    
    def enable_strategy(self, strategy_id: str) -> bool:
        """啟用策略"""
        strategy = self.load_strategy(strategy_id)
        if strategy:
            if isinstance(strategy, list) and len(strategy) > 0:
                strategy = strategy[0]
            strategy["enabled"] = True
            self.save_strategy(strategy)
            return True
        return False
    
    def disable_strategy(self, strategy_id: str) -> bool:
        """停用策略"""
        strategy = self.load_strategy(strategy_id)
        if strategy:
            if isinstance(strategy, list) and len(strategy) > 0:
                strategy = strategy[0]
            strategy["enabled"] = False
            self.save_strategy(strategy)
            return True
        return False
    
    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略所有版本及其相關檔案"""
        deleted = False
        
        # 刪除策略檔案（所有版本）
        for f in self.strategies_dir.glob(f"{strategy_id}_v*.json"):
            f.unlink()
            deleted = True
        
        # 刪除部位檔案
        position_file = self.workspace / "positions" / f"{strategy_id}_positions.json"
        if position_file.exists():
            position_file.unlink()
            deleted = True
        
        # 刪除訂單檔案
        order_file = self.workspace / "orders" / f"{strategy_id}_orders.json"
        if order_file.exists():
            order_file.unlink()
            deleted = True
        
        # 刪除訊號檔案（所有版本）
        signals_dir = self.workspace / "signals"
        if signals_dir.exists():
            for f in signals_dir.glob(f"{strategy_id}_v*.json"):
                f.unlink()
                deleted = True
        
        # 刪除回測圖片（所有版本）
        backtest_dir = self.workspace / "backtests"
        if backtest_dir.exists():
            for f in backtest_dir.glob(f"{strategy_id}_v*.png"):
                f.unlink()
                deleted = True
        
        return deleted


class PositionStore(JSONStore):
    """部位儲存 - per-strategy"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.positions_dir = workspace_dir / "positions"
        self.positions_dir.mkdir(exist_ok=True)
    
    def _get_position_file(self, strategy_id: str) -> Path:
        return self.positions_dir / f"{strategy_id}_positions.json"
    
    def get_all_positions(self) -> List[dict]:
        """取得所有策略的最新部位"""
        all_positions = []
        for f in self.positions_dir.glob("*_positions.json"):
            data = self.load(f"positions/{f.name}", [])
            if data and isinstance(data, list):
                all_positions.extend(data)
        return all_positions
    
    def get_by_strategy(self, strategy_id: str) -> List[dict]:
        """取得特定策略的部位"""
        return self.load(f"positions/{strategy_id}_positions.json", [])
    
    def get_open_positions(self) -> list:
        """取得所有未平倉部位"""
        all_pos = self.get_all_positions()
        return [p for p in all_pos if p.get("quantity", 0) > 0]
    
    def add_position(self, position: dict) -> None:
        """新增部位"""
        strategy_id = position.get("strategy_id", "")
        filename = f"positions/{strategy_id}_positions.json"
        positions = self.load(filename, [])
        positions.append(position)
        self.save(filename, positions)
    
    def close_position(self, strategy_id: str) -> bool:
        """平倉"""
        positions = self.get_by_strategy(strategy_id)
        for i, p in enumerate(positions):
            if p.get("quantity", 0) > 0:
                p["quantity"] = 0
                p["closed_at"] = datetime.now().isoformat()
                positions[i] = p
                self.save(f"positions/{strategy_id}_positions.json", positions)
                return True
        return False
    
    def update_position(self, strategy_id: str, updates: dict) -> bool:
        """更新部位"""
        positions = self.get_by_strategy(strategy_id)
        for i, p in enumerate(positions):
            if p.get("quantity", 0) > 0:
                positions[i].update(updates)
                positions[i]["updated_at"] = datetime.now().isoformat()
                self.save(f"positions/{strategy_id}_positions.json", positions)
                return True
        return False


class OrderStore(JSONStore):
    """訂單儲存 - per-strategy"""
    
    def __init__(self, workspace_dir: Path):
        super().__init__(workspace_dir)
        self.orders_dir = workspace_dir / "orders"
        self.orders_dir.mkdir(exist_ok=True)
    
    def _get_order_file(self, strategy_id: str) -> Path:
        return self.orders_dir / f"{strategy_id}_orders.json"
    
    def get_all_orders(self) -> List[dict]:
        """取得所有訂單"""
        all_orders = []
        for f in self.orders_dir.glob("*_orders.json"):
            data = self.load(f"orders/{f.name}", [])
            if data and isinstance(data, list):
                all_orders.extend(data)
        return all_orders
    
    def get_by_strategy(self, strategy_id: str) -> List[dict]:
        """取得特定策略的訂單"""
        return self.load(f"orders/{strategy_id}_orders.json", [])
    
    def get_today_orders(self) -> List[dict]:
        """取得今日訂單"""
        today = datetime.now().strftime("%Y-%m-%d")
        all_orders = self.get_all_orders()
        return [o for o in all_orders if today in o.get("timestamp", "")]
    
    def add_order(self, order: dict) -> None:
        """新增訂單"""
        strategy_id = order.get("strategy_id", "")
        filename = f"orders/{strategy_id}_orders.json"
        orders = self.load(filename, [])
        orders.append(order)
        self.save(filename, orders)
    
    def update_order_status(self, order_id: str, status: str, filled_price: float = None) -> bool:
        """更新訂單狀態"""
        all_orders = self.get_all_orders()
        
        for o in all_orders:
            if o.get("order_id") == order_id:
                o["status"] = status
                if filled_price:
                    o["filled_price"] = filled_price
                    o["filled_time"] = datetime.now().isoformat()
                
                strategy_id = o.get("strategy_id", "")
                self.save(f"orders/{strategy_id}_orders.json", 
                         [x for x in self.get_by_strategy(strategy_id) if x.get("order_id") != order_id] + [o])
                return True
        return False


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
