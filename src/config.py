"""配置載入模組"""
import yaml
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List


class ShioajiConfig(BaseModel):
    api_key: str
    secret_key: str
    simulation: bool = True
    offline_mode: bool = False


class LLMConfig(BaseModel):
    """LLM 配置
    
    Provider 選項:
    - openrouter: 使用 OpenRouter API (推薦)
    - openai: 使用 OpenAI API
    - anthropic: 使用 Anthropic Claude
    - deepseek: 使用 DeepSeek
    - custom: 自定義端點 (支援 Ollama 或其他 OpenAI 相容 API)
    
    custom 範例 (Ollama):
    - base_url: http://localhost:11434/v1
    - api_key: (可留空)
    - model: llama3, mistral, codellama 等
    """
    provider: str = "custom"
    api_key: str = ""
    model: str = "llama3"
    temperature: float = 0.7
    max_tokens: int = 2000
    base_url: Optional[str] = None


class TelegramConfig(BaseModel):
    enabled: bool = True
    bot_token: str = ""
    chat_id: str = ""


class RiskConfig(BaseModel):
    max_daily_loss: int = 50000
    max_position: int = 10
    max_orders_per_minute: int = 5
    enable_stop_loss: bool = True
    enable_take_profit: bool = True


class TradingHoursConfig(BaseModel):
    day_start: str = "08:45"
    day_end: str = "13:45"
    night_start: str = "15:00"
    night_end: str = "05:00"


class TradingConfig(BaseModel):
    check_interval: int = 60
    trading_hours: TradingHoursConfig


class StrategyParams(BaseModel):
    timeframe: str
    stop_loss: int
    take_profit: int
    position_size: int


class StrategyConfig(BaseModel):
    id: str
    name: str
    symbol: str
    prompt: str
    enabled: bool = False
    params: StrategyParams
    goal: Optional[float] = None
    goal_unit: Optional[str] = "daily"


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "workspace/logs/trading.log"
    max_bytes: int = 10485760
    backup_count: int = 5


class AutoReviewSchedule(BaseModel):
    """自動 LLM Review 排程設定"""
    strategy_id: str
    period: int = 1
    unit: str = "day"  # day/week/month/quarter/year


class AutoReviewConfig(BaseModel):
    """自動 LLM Review 配置"""
    enabled: bool = False
    schedules: List[AutoReviewSchedule] = []


class AppConfig(BaseModel):
    shioaji: ShioajiConfig
    llm: LLMConfig
    telegram: TelegramConfig
    risk: RiskConfig
    trading: TradingConfig
    strategies: list[StrategyConfig] = []
    logging: LoggingConfig
    auto_review: AutoReviewConfig = AutoReviewConfig()


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """載入配置文件"""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    return AppConfig(**data)


def get_workspace_dir() -> Path:
    """取得工作目錄"""
    return Path("workspace")


def ensure_workspace() -> None:
    """確保工作目錄存在"""
    workspace = get_workspace_dir()
    workspace.mkdir(exist_ok=True)
    (workspace / "logs").mkdir(exist_ok=True)
    (workspace / "signals").mkdir(exist_ok=True)
    (workspace / "strategies").mkdir(exist_ok=True)
    (workspace / "positions").mkdir(exist_ok=True)
    (workspace / "orders").mkdir(exist_ok=True)
