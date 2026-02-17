"""策略類別"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from src.storage.json_store import StrategyStore
from src.storage.models import StrategyModel


class Strategy:
    """策略類別"""
    
    def __init__(self, strategy_id: str, name: str, symbol: str, prompt: str, 
                 params: Dict[str, Any], enabled: bool = False):
        self.id = strategy_id
        self.name = name
        self.symbol = symbol
        self.prompt = prompt
        self.params = params
        self.enabled = enabled
        self.created_at = datetime.now().isoformat()
        
        # 執行狀態
        self.last_signal: Optional[str] = None
        self.last_signal_time: Optional[str] = None
        self.is_running = False
        
        # 解析後的規則 (由 RuleParser 產生)
        self.rules: Optional[Dict[str, Any]] = None
        self.rules_parsed_at: Optional[str] = None
        
        # LLM 生成的策略程式碼
        self.strategy_code: Optional[str] = None
        self.strategy_class_name: Optional[str] = None
        self.strategy_generated_at: Optional[str] = None
        self.strategy_version: int = 1
        self.prompt_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "prompt": self.prompt,
            "enabled": self.enabled,
            "params": self.params,
            "created_at": self.created_at,
            "last_signal": self.last_signal,
            "last_signal_time": self.last_signal_time,
            "rules": self.rules,
            "rules_parsed_at": self.rules_parsed_at,
            "strategy_code": self.strategy_code,
            "strategy_class_name": self.strategy_class_name,
            "strategy_generated_at": self.strategy_generated_at,
            "strategy_version": self.strategy_version,
            "prompt_hash": self.prompt_hash
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Strategy":
        """從字典建立"""
        strategy = cls(
            strategy_id=data.get("id", ""),
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            prompt=data.get("prompt", ""),
            params=data.get("params", {}),
            enabled=data.get("enabled", False)
        )
        strategy.created_at = data.get("created_at", strategy.created_at)
        strategy.last_signal = data.get("last_signal")
        strategy.last_signal_time = data.get("last_signal_time")
        strategy.rules = data.get("rules")
        strategy.rules_parsed_at = data.get("rules_parsed_at")
        strategy.strategy_code = data.get("strategy_code")
        strategy.strategy_class_name = data.get("strategy_class_name")
        strategy.strategy_generated_at = data.get("strategy_generated_at")
        strategy.strategy_version = data.get("strategy_version", 1)
        strategy.prompt_hash = data.get("prompt_hash")
        return strategy
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """取得參數"""
        return self.params.get(key, default)
    
    def update_last_signal(self, signal: str) -> None:
        """更新最後訊號"""
        self.last_signal = signal
        self.last_signal_time = datetime.now().isoformat()
    
    def set_rules(self, rules: Dict[str, Any]) -> None:
        """設定解析後的規則"""
        self.rules = rules
        self.rules_parsed_at = datetime.now().isoformat()
    
    def clear_rules(self) -> None:
        """清除規則"""
        self.rules = None
        self.rules_parsed_at = None
    
    def has_valid_rules(self) -> bool:
        """檢查是否有有效規則"""
        return self.rules is not None
    
    def set_strategy_code(self, code: str, class_name: str) -> None:
        """設定 LLM 生成的策略程式碼"""
        import hashlib
        self.strategy_code = code
        self.strategy_class_name = class_name
        self.strategy_generated_at = datetime.now().isoformat()
        self.strategy_version += 1
        self.prompt_hash = hashlib.md5(self.prompt.encode()).hexdigest()
    
    def needs_regeneration(self) -> bool:
        """檢查是否需要重新生成策略"""
        if not self.strategy_code or not self.strategy_class_name:
            return True
        import hashlib
        current_hash = hashlib.md5(self.prompt.encode()).hexdigest()
        return current_hash != self.prompt_hash
    
    def has_valid_strategy_code(self) -> bool:
        """檢查是否有有效的策略程式碼"""
        return self.strategy_code is not None and self.strategy_class_name is not None
    
    def __repr__(self) -> str:
        return f"Strategy(id={self.id}, name={self.name}, symbol={self.symbol}, enabled={self.enabled})"
