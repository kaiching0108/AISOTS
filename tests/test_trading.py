"""測試模組"""
import pytest
from pathlib import Path
import sys

# 添加專案根目錄
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_import():
    """測試匯入"""
    try:
        from src.config import load_config
        from src.storage import JSONStore, StrategyStore
        from src.trading import Strategy, StrategyManager
        from src.risk import RiskManager
        from src.notify import TelegramNotifier
        from src.agent.providers import ProviderFactory, CustomProvider
        assert True
    except ImportError as e:
        pytest.fail(f"匯入失敗: {e}")


def test_strategy_store():
    """測試策略儲存"""
    from src.storage import StrategyStore
    
    workspace = Path("workspace_test")
    workspace.mkdir(exist_ok=True)
    
    store = StrategyStore(workspace)
    strategies = store.get_all()
    
    assert isinstance(strategies, list)


def test_risk_manager():
    """測試風控"""
    from src.risk import RiskManager
    
    config = {
        "max_daily_loss": 50000,
        "max_position": 10,
        "max_orders_per_minute": 5,
        "enable_stop_loss": True,
        "enable_take_profit": True
    }
    
    risk_mgr = RiskManager(config)
    
    # 測試風控檢查
    result = risk_mgr.check_order(
        symbol="TXF",
        action="Buy",
        quantity=1,
        price=18500,
        current_positions=0,
        daily_pnl=0
    )
    
    assert result["passed"] == True


def test_provider_factory():
    """測試 LLM Provider 工廠"""
    from src.config import LLMConfig
    from src.agent.providers import ProviderFactory, CustomProvider, OpenRouterProvider
    
    # 測試 custom provider
    config = LLMConfig(
        provider="custom",
        model="llama3",
        base_url="http://localhost:11434/v1"
    )
    provider = ProviderFactory.create(config)
    assert isinstance(provider, CustomProvider)
    assert provider.model == "llama3"
    assert provider.base_url == "http://localhost:11434/v1"
    
    # 測試 openrouter provider
    config2 = LLMConfig(
        provider="openrouter",
        api_key="test-key",
        model="anthropic/claude-sonnet-4-20250514"
    )
    provider2 = ProviderFactory.create(config2)
    assert isinstance(provider2, OpenRouterProvider)
    
    # 測試可用 providers 列表
    providers = ProviderFactory.get_available_providers()
    assert "custom" in providers
    assert "openrouter" in providers
    assert "openai" in providers
    assert "anthropic" in providers
    assert "deepseek" in providers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
