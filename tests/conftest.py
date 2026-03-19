"""共用測試 fixtures"""
import pytest
import sys
from pathlib import Path

# 添加專案根目錄
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def workspace_test(tmp_path):
    """測試用的 workspace"""
    workspace = tmp_path / "workspace_test"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_config():
    """測試用的 config"""
    return {
        "shioaji": {
            "api_key": "test_key",
            "secret_key": "test_secret",
            "simulation": True
        },
        "llm": {
            "provider": "custom",
            "model": "test-model",
            "api_key": "",
            "base_url": "http://localhost:11434/v1",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": ""
        },
        "risk": {
            "max_daily_loss": 10000,
            "max_position": 3,
            "max_orders_per_minute": 1,
            "enable_stop_loss": True,
            "enable_take_profit": True
        },
        "trading": {
            "check_interval": 60,
            "trading_hours": {
                "day_start": "08:45",
                "day_end": "13:45",
                "night_start": "15:00",
                "night_end": "05:00"
            }
        },
        "auto_review": {
            "enabled": False,
            "schedules": []
        }
    }


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing"""
    class MockProvider:
        def __init__(self):
            self.model = "mock-model"
            self.base_url = "http://localhost:11434/v1"
        
        async def generate(self, prompt: str):
            return {"text": "Mock response"}
        
        async def chat(self, messages: list):
            return {"text": "Mock chat response"}
    
    return MockProvider()
