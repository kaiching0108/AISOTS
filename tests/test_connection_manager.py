"""連線管理器單元測試"""
import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from src.api.connection import ConnectionManager


class TestConnectionManager:
    """測試 ConnectionManager"""
    
    def setup_method(self):
        """每個測試前初始化"""
        self.mock_client = Mock()
        self.mock_client.connected = False
        self.mock_client.simulation = True
        self.mock_client.get_usage = Mock(return_value={'total': 100})
        
        self.config = {
            'reconnect': {
                'max_reconnect': 50,
                'reconnect_interval': 5
            }
        }
        
        self.mgr = ConnectionManager(self.mock_client, self.config)
    
    def test_initial_state(self):
        """測試 1: 初始狀態"""
        assert self.mgr.is_connected == False
        assert self.mgr.reconnect_count == 0
        assert self.mgr.max_reconnect == 50
        assert self.mgr.reconnect_interval == 5
    
    def test_sync_initial_state(self):
        """測試 2: 同步 ShioajiClient 的 connected 狀態"""
        self.mock_client.connected = True
        mgr = ConnectionManager(self.mock_client, self.config)
        assert mgr.is_connected == True
    
    def test_check_connection_success(self):
        """測試 3: 連線檢查成功"""
        self.mgr.is_connected = False
        result = self.mgr.check_connection()
        assert result == True
        assert self.mgr.is_connected == True
    
    def test_check_connection_failure(self):
        """測試 4: 連線檢查失敗"""
        self.mock_client.get_usage = Mock(side_effect=Exception("連線失敗"))
        self.mgr.is_connected = True
        result = self.mgr.check_connection()
        assert result == False
        assert self.mgr.is_connected == False
    
    def test_get_status(self):
        """測試 5: 取得連線狀態"""
        self.mgr.is_connected = True
        self.mgr.reconnect_count = 3
        status = self.mgr.get_status()
        
        assert status['is_connected'] == True
        assert status['reconnect_count'] == 3
        assert status['simulation_mode'] == True
    
    @pytest.mark.asyncio
    async def test_handle_disconnect_async_success(self):
        """測試 6: 異步重連成功"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 0
        
        # 模擬重連成功
        call_count = [0]
        def mock_login():
            call_count[0] += 1
            if call_count[0] >= 3:
                return True
            return False
        
        self.mock_client.login = mock_login
        
        # 替換重連邏輯以加速測試
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', fast_sleep):
            result = await self.mgr.handle_disconnect_async()
        
        assert result == True
        assert self.mgr.is_connected == True
        assert self.mgr.reconnect_count == 0
    
    @pytest.mark.asyncio
    async def test_handle_disconnect_async_max_retries(self):
        """測試 7: 異步重連超過最大次數"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 49  # 接近最大次數
        self.mgr.max_reconnect = 50
        
        # 模擬重連失敗
        self.mock_client.login = Mock(return_value=False)
        
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', fast_sleep):
            result = await self.mgr.handle_disconnect_async()
        
        assert result == False
        assert self.mgr.is_connected == False
        assert self.mgr.reconnect_count >= 50
    
    @pytest.mark.asyncio
    async def test_handle_disconnect_async_with_callback(self):
        """測試 8: 異步重連成功並觸發回調"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 0
        
        callback_called = [False]
        def mock_callback():
            callback_called[0] = True
        
        self.mgr.on_reconnected = mock_callback
        self.mock_client.login = Mock(return_value=True)
        
        result = await self.mgr.handle_disconnect_async()
        
        assert result == True
        assert callback_called[0] == True
    
    def test_wait_for_connection_success(self):
        """測試 9: 等待連線成功"""
        # 設置初始為已連線
        self.mgr.is_connected = True
        
        result = self.mgr.wait_for_connection(timeout=1)
        assert result == True
    
    def test_wait_for_connection_timeout(self):
        """測試 10: 等待連線超時"""
        result = self.mgr.wait_for_connection(timeout=1)
        assert result == False
    
    def test_set_connection_status(self):
        """測試 11: 手動設置連線狀態"""
        self.mgr.is_connected = False
        self.mgr.set_connection_status(True)
        assert self.mgr.is_connected == True
        
        self.mgr.set_connection_status(False)
        assert self.mgr.is_connected == False
    
    def test_max_reconnect_property(self):
        """測試 12: max_reconnect 屬性"""
        assert self.mgr.max_reconnect == 50
        
        self.mgr.max_reconnect = 100
        assert self.mgr.max_reconnect == 100
    
    def test_config_based_initialization(self):
        """測試 13: 基於配置的初始化"""
        config = {
            'reconnect': {
                'max_reconnect': 20,
                'reconnect_interval': 10
            }
        }
        mgr = ConnectionManager(self.mock_client, config)
        assert mgr.max_reconnect == 20
        assert mgr.reconnect_interval == 10
    
    @pytest.mark.asyncio
    async def test_handle_disconnect_async_login_failure(self):
        """測試 14: 登入失敗處理"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 0
        self.mgr.max_reconnect = 3
        
        # 模擬登入始終失敗
        self.mock_client.login = Mock(return_value=False)
        
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', fast_sleep):
            result = await self.mgr.handle_disconnect_async()
        
        assert result == False
        assert self.mgr.is_connected == False
        assert self.mgr.reconnect_count == 3
    
    @pytest.mark.asyncio
    async def test_handle_disconnect_async_exception(self):
        """測試 15: 登入異常處理"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 0
        self.mgr.max_reconnect = 2
        
        # 模擬登入拋出異常
        self.mock_client.login = Mock(side_effect=Exception("登入異常"))
        
        original_sleep = asyncio.sleep
        async def fast_sleep(seconds):
            await original_sleep(0.01)
        
        with patch('asyncio.sleep', fast_sleep):
            result = await self.mgr.handle_disconnect_async()
        
        assert result == False
        assert self.mgr.is_connected == False
        assert self.mgr.reconnect_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
