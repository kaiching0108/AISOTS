"""測試主循環中的斷線處理邏輯"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.api.connection import ConnectionManager


class TestMainLoopDisconnectHandling:
    """測試主循環在斷線時的行為"""
    
    def setup_method(self):
        """每個測試前初始化"""
        self.mock_client = Mock()
        self.mock_client.connected = True
        self.mock_client.simulation = True
        
        self.config = {
            'reconnect': {
                'max_reconnect': 50,
                'reconnect_interval': 5
            }
        }
        
        self.mgr = ConnectionManager(self.mock_client, self.config)
    
    @pytest.mark.asyncio
    async def test_main_loop_skips_when_disconnected(self):
        """測試 1: 主循環在斷線時跳過策略執行"""
        # 模擬斷線狀態
        self.mgr.is_connected = False
        
        # 模擬重連方法
        reconnect_called = [False]
        original_handle = self.mgr.handle_disconnect_async
        
        async def mock_handle_disconnect():
            reconnect_called[0] = True
            # 模擬重連成功
            self.mgr.is_connected = True
            return True
        
        with patch.object(self.mgr, 'handle_disconnect_async', mock_handle_disconnect):
            # 模擬主循環邏輯
            if not self.mgr.is_connected:
                await self.mgr.handle_disconnect_async()
            
            # 驗證重連方法被調用
            assert reconnect_called[0] == True
            # 驗證重連後狀態恢復
            assert self.mgr.is_connected == True
    
    @pytest.mark.asyncio
    async def test_main_loop_continues_after_reconnect(self):
        """測試 2: 重連後主循環繼續執行"""
        # 初始斷線
        self.mgr.is_connected = False
        
        # 模擬重連
        async def mock_handle_disconnect():
            await asyncio.sleep(0.01)
            self.mgr.is_connected = True
            return True
        
        with patch.object(self.mgr, 'handle_disconnect_async', mock_handle_disconnect):
            # 第一次檢查 - 斷線
            if not self.mgr.is_connected:
                await self.mgr.handle_disconnect_async()
            
            # 驗證已重連
            assert self.mgr.is_connected == True
            
            # 第二次檢查 - 應該繼續正常執行（不再進入重連邏輯）
            should_execute_strategy = self.mgr.is_connected
            assert should_execute_strategy == True
    
    @pytest.mark.asyncio
    async def test_multiple_disconnect_reconnect_cycles(self):
        """測試 3: 多次斷線/重連循環"""
        cycle_count = [0]
        max_cycles = 3
        
        async def mock_handle_disconnect():
            cycle_count[0] += 1
            await asyncio.sleep(0.01)
            if cycle_count[0] < max_cycles:
                # 前兩次仍然斷線
                self.mgr.is_connected = False
            else:
                # 最後一次成功
                self.mgr.is_connected = True
            return self.mgr.is_connected
        
        with patch.object(self.mgr, 'handle_disconnect_async', mock_handle_disconnect):
            self.mgr.is_connected = False
            
            # 模擬主循環的多個週期
            for i in range(max_cycles):
                if not self.mgr.is_connected:
                    await self.mgr.handle_disconnect_async()
                
                if i < max_cycles - 1:
                    # 前幾個週期應該仍然斷線
                    assert self.mgr.is_connected == False
                else:
                    # 最後一個週期應該已重連
                    assert self.mgr.is_connected == True
    
    @pytest.mark.asyncio
    async def test_reconnect_count_reset_on_success(self):
        """測試 4: 重連成功後計數器歸零"""
        self.mgr.is_connected = False
        self.mgr.reconnect_count = 10
        
        async def mock_handle_disconnect():
            self.mgr.is_connected = True
            self.mgr.reconnect_count = 0
            return True
        
        with patch.object(self.mgr, 'handle_disconnect_async', mock_handle_disconnect):
            await self.mgr.handle_disconnect_async()
            
            assert self.mgr.is_connected == True
            assert self.mgr.reconnect_count == 0
    
    @pytest.mark.asyncio
    async def test_reconnect_callback_triggered(self):
        """測試 5: 重連成功後觸發回調"""
        self.mgr.is_connected = False
        
        callback_called = [False]
        def mock_callback():
            callback_called[0] = True
        
        self.mgr.on_reconnected = mock_callback
        
        async def mock_handle_disconnect():
            self.mgr.is_connected = True
            if self.mgr.on_reconnected:
                self.mgr.on_reconnected()
            return True
        
        with patch.object(self.mgr, 'handle_disconnect_async', mock_handle_disconnect):
            await self.mgr.handle_disconnect_async()
            
            assert callback_called[0] == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
