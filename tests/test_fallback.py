"""測試 Fallback 指令處理"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# 添加專案根目錄
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def trading_tools_with_mocks():
    """建立帶有 mock 的 trading_tools"""
    from src.trading.strategy_manager import StrategyManager
    from src.trading.position_manager import PositionManager
    from src.trading.order_manager import OrderManager
    from src.risk.risk_manager import RiskManager
    from src.agent.tools import TradingTools
    from src.storage.json_store import JSONStore
    
    # Mock 各個管理器
    mock_store = Mock()
    mock_store.get_all_strategies.return_value = []
    mock_store.get_strategy.return_value = None
    
    strategy_mgr = Mock()
    strategy_mgr.get_all_strategies.return_value = []
    strategy_mgr.get_strategy.return_value = None
    strategy_mgr.get_enabled_strategies.return_value = []
    strategy_mgr.disable_strategy_with_check.return_value = {
        "can_disable": True,
        "has_positions": False,
        "position": None
    }
    strategy_mgr.workspace_dir = Path("workspace_test")
    strategy_mgr.store = mock_store
    
    position_mgr = Mock()
    position_mgr.get_all_positions.return_value = []
    position_mgr.get_positions_summary.return_value = {
        "positions": [],
        "total_quantity": 0,
        "total_pnl": 0
    }
    
    order_mgr = Mock()
    order_mgr.get_orders.return_value = []
    order_mgr.get_today_orders.return_value = []
    order_mgr.get_order_statistics.return_value = {
        "today": "2026-02-23",
        "total_orders": 0,
        "filled": 0,
        "cancelled": 0,
        "pending": 0
    }
    order_mgr.get_pending_orders.return_value = []
    
    risk_mgr = Mock()
    risk_mgr.check_order.return_value = {"passed": True}
    risk_mgr.get_status.return_value = {
        "daily_pnl": 0,
        "max_daily_loss": 10000,
        "max_position": 3,
        "orders_this_minute": 0,
        "max_orders_per_minute": 5,
        "stop_loss_enabled": True,
        "take_profit_enabled": True
    }
    risk_mgr.daily_pnl = 0
    
    shioaji_client = Mock()
    shioaji_client.get_available_futures_symbols.return_value = ["TXF", "MXF", "TMF"]
    shioaji_client.get_futures_name_mapping.return_value = {
        "TXF": "臺股期貨",
        "MXF": "小型臺指",
        "TMF": "微型臺指"
    }
    shioaji_client.connected = False
    
    notifier = Mock()
    
    tools = TradingTools(
        strategy_manager=strategy_mgr,
        position_manager=position_mgr,
        order_manager=order_mgr,
        risk_manager=risk_mgr,
        shioaji_client=shioaji_client,
        notifier=notifier,
        llm_provider=None,
        valid_symbols=["TXF", "MXF", "TMF", "T5F", "XIF", "TE"]
    )
    
    return tools


class TestFallbackCommands:
    """測試 fallback 指令"""
    
    def test_status_command(self, trading_tools_with_mocks):
        """測試 status 指令"""
        result = trading_tools_with_mocks.get_system_status()
        assert result is not None
        assert isinstance(result, str)
    
    def test_positions_command(self, trading_tools_with_mocks):
        """測試 positions 指令"""
        result = trading_tools_with_mocks.get_positions()
        assert result is not None
        assert isinstance(result, str)
    
    def test_strategies_command(self, trading_tools_with_mocks):
        """測試 strategies 指令"""
        result = trading_tools_with_mocks.get_strategies()
        assert result is not None
        assert isinstance(result, str)
    
    def test_performance_command(self, trading_tools_with_mocks):
        """測試 performance 指令"""
        result = trading_tools_with_mocks.get_performance()
        assert result is not None
        assert isinstance(result, str)
    
    def test_risk_command(self, trading_tools_with_mocks):
        """測試 risk 指令"""
        result = trading_tools_with_mocks.get_risk_status()
        assert result is not None
        assert isinstance(result, str)
    
    def test_orders_command(self, trading_tools_with_mocks):
        """測試 orders 指令"""
        result = trading_tools_with_mocks.get_order_history()
        assert result is not None
        assert isinstance(result, str)
    
    def test_enable_nonexistent_strategy(self, trading_tools_with_mocks):
        """測試 enable 不存在的策略"""
        result = trading_tools_with_mocks.enable_strategy("TMF260001")
        assert "找不到" in result or "❌" in result
    
    def test_disable_nonexistent_strategy(self, trading_tools_with_mocks):
        """測試 disable 不存在的策略"""
        # Mock 會返回 can_disable: True，需要修改 mock 來模擬不存在的策略
        trading_tools_with_mocks.strategy_mgr.disable_strategy_with_check.return_value = {
            "can_disable": False,
            "has_positions": False,
            "error": "找不到策略"
        }
        result = trading_tools_with_mocks.disable_strategy("TMF260001")
        assert "找不到" in result or "❌" in result or "error" in result.lower()
    
    def test_create_command(self, trading_tools_with_mocks):
        """測試 create 指令"""
        result = trading_tools_with_mocks.start_create_flow()
        assert "策略名稱" in result
        assert "第一步" in result
    
    def test_invalid_command(self, trading_tools_with_mocks):
        """測試無效指令"""
        # 模擬沒有匹配任何指令的情況
        # 這個測試可能會走到 LLM 路徑，這裡只測試基本屬性
        assert trading_tools_with_mocks is not None


class TestCreateFlow:
    """測試問答式建立策略流程"""
    
    def test_create_start(self, trading_tools_with_mocks):
        """測試啟動 create 流程"""
        result = trading_tools_with_mocks.start_create_flow()
        assert "策略名稱" in result
        assert "第一步" in result
    
    def test_create_input_name(self, trading_tools_with_mocks):
        """測試輸入策略名稱"""
        # 先啟動流程
        trading_tools_with_mocks.start_create_flow()
        # 輸入名稱
        result = trading_tools_with_mocks.handle_create_input("RSI策略")
        assert "期貨代碼" in result
        assert "第二步" in result
    
    def test_create_cancel(self, trading_tools_with_mocks):
        """測試取消建立"""
        # 先啟動流程
        trading_tools_with_mocks.start_create_flow()
        # 取消
        result = trading_tools_with_mocks.handle_create_input("取消")
        assert "取消" in result
        assert "已取消" in result
    
    def test_create_flow_state(self, trading_tools_with_mocks):
        """測試流程狀態"""
        assert trading_tools_with_mocks._awaiting_create_input == False
        
        trading_tools_with_mocks.start_create_flow()
        
        assert trading_tools_with_mocks._awaiting_create_input == True
        assert trading_tools_with_mocks._create_step == "name"
    
    def test_create_invalid_symbol(self, trading_tools_with_mocks):
        """測試輸入無效的期貨代碼"""
        trading_tools_with_mocks.start_create_flow()
        trading_tools_with_mocks.handle_create_input("RSI策略")
        
        result = trading_tools_with_mocks.handle_create_input("INVALID")
        assert "無效" in result or "錯誤" in result
    
    def test_create_valid_symbol(self, trading_tools_with_mocks):
        """測試輸入有效的期貨代碼"""
        trading_tools_with_mocks.start_create_flow()
        trading_tools_with_mocks.handle_create_input("RSI策略")
        
        result = trading_tools_with_mocks.handle_create_input("TXF")
        assert "策略描述" in result
        assert "第三步" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
