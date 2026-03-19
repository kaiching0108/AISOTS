"""測試問答式建立策略流程"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# 添加專案根目錄
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCreateFlowComplete:
    """完整測試問答式建立策略流程"""
    
    @pytest.fixture
    def tools_with_mocks(self):
        """建立帶有 mock 的 tools"""
        from src.trading.strategy import Strategy
        from src.trading.strategy_manager import StrategyManager
        from src.trading.position_manager import PositionManager
        from src.trading.order_manager import OrderManager
        from src.risk.risk_manager import RiskManager
        from src.agent.tools import TradingTools
        from src.storage.json_store import JSONStore
        
        # Mock 各個管理器
        strategy_mgr = Mock()
        strategy_mgr.get_all_strategies.return_value = []
        strategy_mgr.get_strategy.return_value = None
        strategy_mgr.workspace_dir = Path("workspace_test")
        strategy_mgr.store = Mock()
        strategy_mgr.store.save_strategy = Mock()
        
        position_mgr = Mock()
        position_mgr.get_all_positions.return_value = []
        position_mgr.get_positions_summary.return_value = {
            "positions": [],
            "total_quantity": 0,
            "total_pnl": 0
        }
        
        order_mgr = Mock()
        order_mgr.get_orders.return_value = []
        
        risk_mgr = Mock()
        risk_mgr.check_order.return_value = {"passed": True}
        risk_mgr.get_status.return_value = {"max_daily_loss": 10000}
        
        shioaji_client = Mock()
        shioaji_client.get_available_futures_symbols.return_value = ["TXF", "MXF", "TMF"]
        shioaji_client.get_futures_name_mapping.return_value = {
            "TXF": "臺股期貨",
            "MXF": "小型臺指",
            "TMF": "微型臺指"
        }
        
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
    
    def test_full_create_flow(self, tools_with_mocks):
        """測試完整建立流程"""
        # Step 1: 啟動
        result = tools_with_mocks.start_create_flow()
        assert "策略名稱" in result
        assert tools_with_mocks._awaiting_create_input == True
        assert tools_with_mocks._create_step == "name"
        
        # Step 2: 輸入名稱
        result = tools_with_mocks.handle_create_input("RSI策略")
        assert "期貨代碼" in result
        assert tools_with_mocks._create_step == "symbol"
        
        # Step 3: 輸入期貨代碼
        result = tools_with_mocks.handle_create_input("TXF")
        assert "策略描述" in result
        assert tools_with_mocks._create_step == "prompt"
        
        # Step 4: 輸入策略描述
        result = tools_with_mocks.handle_create_input("RSI低於30買入高於70賣出")
        assert "K線週期" in result
        assert tools_with_mocks._create_step == "timeframe"
        
        # Step 5: 輸入K線週期
        result = tools_with_mocks.handle_create_input("15m")
        assert "交易口數" in result
        assert tools_with_mocks._create_step == "quantity"
        
        # Step 6: 輸入口數
        result = tools_with_mocks.handle_create_input("1")
        assert "停損點數" in result
        assert tools_with_mocks._create_step == "stop_loss"
        
        # Step 7: 輸入停損
        result = tools_with_mocks.handle_create_input("50")
        assert "止盈點數" in result
        assert tools_with_mocks._create_step == "take_profit"
        
        # Step 8: 輸入止盈
        result = tools_with_mocks.handle_create_input("100")
        assert "確認" in result
        assert tools_with_mocks._create_step == "confirm"
    
    def test_cancel_at_name_step(self, tools_with_mocks):
        """測試在名稱步驟取消"""
        tools_with_mocks.start_create_flow()
        
        result = tools_with_mocks.handle_create_input("取消")
        
        assert "已取消" in result
        assert tools_with_mocks._awaiting_create_input == False
    
    def test_invalid_timeframe(self, tools_with_mocks):
        """測試無效的K線週期"""
        tools_with_mocks.start_create_flow()
        tools_with_mocks.handle_create_input("RSI策略")
        tools_with_mocks.handle_create_input("TXF")
        tools_with_mocks.handle_create_input("RSI策略描述")
        
        result = tools_with_mocks.handle_create_input("invalid")
        
        assert "無效" in result or "錯誤" in result
    
    def test_invalid_quantity(self, tools_with_mocks):
        """測試無效的口數"""
        tools_with_mocks.start_create_flow()
        tools_with_mocks.handle_create_input("RSI策略")
        tools_with_mocks.handle_create_input("TXF")
        tools_with_mocks.handle_create_input("RSI策略描述")
        tools_with_mocks.handle_create_input("15m")
        
        result = tools_with_mocks.handle_create_input("0")
        
        assert "無效" in result or "錯誤" in result or ">= 1" in result
    
    def test_pending_data_storage(self, tools_with_mocks):
        """測試暫存資料儲存"""
        tools_with_mocks.start_create_flow()
        
        assert tools_with_mocks._pending_create_data == {}
        
        tools_with_mocks.handle_create_input("RSI策略")
        
        assert tools_with_mocks._pending_create_data.get("name") == "RSI策略"
        
        tools_with_mocks.handle_create_input("TXF")
        
        assert tools_with_mocks._pending_create_data.get("symbol") == "TXF"
    
    def test_confirm_message_content(self, tools_with_mocks):
        """測試確認訊息內容"""
        # 完成所有步驟
        tools_with_mocks.start_create_flow()
        tools_with_mocks.handle_create_input("RSI策略")
        tools_with_mocks.handle_create_input("TXF")
        tools_with_mocks.handle_create_input("RSI低於30買入高於70賣出")
        tools_with_mocks.handle_create_input("15m")
        tools_with_mocks.handle_create_input("1")
        tools_with_mocks.handle_create_input("50")
        result = tools_with_mocks.handle_create_input("100")
        
        # 驗證確認訊息包含所有輸入的資料
        assert "RSI策略" in result
        assert "TXF" in result
        assert "RSI低於30買入高於70賣出" in result
        assert "15m" in result
        assert "1" in result
        assert "50" in result
        assert "100" in result


class TestCreateFlowEdgeCases:
    """邊界情況測試"""
    
    @pytest.fixture
    def tools(self):
        """建立 tools"""
        from src.agent.tools import TradingTools
        from unittest.mock import Mock
        
        strategy_mgr = Mock()
        strategy_mgr.workspace_dir = Path("workspace_test")
        strategy_mgr.store = Mock()
        
        position_mgr = Mock()
        position_mgr.get_all_positions.return_value = []
        position_mgr.get_positions_summary.return_value = {
            "positions": [],
            "total_quantity": 0,
            "total_pnl": 0
        }
        
        order_mgr = Mock()
        risk_mgr = Mock()
        shioaji_client = Mock()
        shioaji_client.get_available_futures_symbols.return_value = ["TXF", "MXF", "TMF"]
        shioaji_client.get_futures_name_mapping.return_value = {"TXF": "臺股期貨"}
        notifier = Mock()
        
        return TradingTools(
            strategy_manager=strategy_mgr,
            position_manager=position_mgr,
            order_manager=order_mgr,
            risk_manager=risk_mgr,
            shioaji_client=shioaji_client,
            notifier=notifier,
            llm_provider=None,
            valid_symbols=["TXF", "MXF", "TMF"]
        )
    
    def test_input_without_starting_flow(self, tools):
        """測試未啟動流程就輸入"""
        result = tools.handle_create_input("RSI策略")
        # 應該返回錯誤訊息
        assert "錯誤" in result or "請先" in result
    
    def test_double_cancel(self, tools):
        """測試連續取消"""
        tools.start_create_flow()
        result = tools.handle_create_input("取消")
        assert "已取消" in result
        
        # 再次取消也會返回相同的訊息（因為輸入「取消」總是有效的）
        result = tools.handle_create_input("取消")
        assert "已取消" in result
    
    def test_confirm_without_data(self, tools):
        """測試在沒有資料時確認"""
        tools.start_create_flow()
        
        # 跳過輸入直接確認
        result = tools.handle_create_input("確認")
        # 這裡會執行 _execute_create_strategy，可能會有錯誤
        # 但應該不會崩潰
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
