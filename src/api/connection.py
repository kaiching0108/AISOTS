"""連線管理與斷線處理"""
import time
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ConnectionManager:
    """連線管理器"""
    
    def __init__(self, shioaji_client, config: dict):
        self.client = shioaji_client
        self.config = config
        self.is_connected = False
        self.reconnect_count = 0
        self.max_reconnect = 50
        self.reconnect_interval = 5  # 秒
        self.heartbeat_interval = 30  # 秒
        
        # 回調
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_reconnected: Optional[Callable] = None
    
    def setup_event_handlers(self) -> None:
        """設置連線事件處理"""
        @self.client.api.quote.on_event
        def on_event(resp_code: int, event_code: int, info: str, event: str):
            logger.info(f"Shioaji 事件: {event} (code: {event_code})")
            
            if event_code == 0:  # UP_NOTICE - 連線建立
                self.is_connected = True
                self.reconnect_count = 0
                logger.info("連線已建立")
                if self.on_connected:
                    self.on_connected()
                    
            elif event_code == 1:  # DOWN_ERROR - 連線中斷
                self.is_connected = False
                logger.warning("連線已中斷")
                if self.on_disconnected:
                    self.on_disconnected()
                self.handle_disconnect()
                
            elif event_code == 2:  # CONNECT_FAILED - 連線失敗
                logger.error(f"連線失敗: {info}")
                self.is_connected = False
    
    def handle_disconnect(self) -> bool:
        """處理斷線，嘗試重新連線"""
        logger.warning(f"正在嘗試重新連線 ({self.reconnect_count + 1}/{self.max_reconnect})...")
        
        while self.reconnect_count < self.max_reconnect:
            try:
                # 嘗試重新登入
                if self.client.login():
                    self.is_connected = True
                    self.reconnect_count = 0
                    logger.info("重新連線成功")
                    if self.on_reconnected:
                        self.on_reconnected()
                    return True
                    
            except Exception as e:
                logger.error(f"重新連線失敗: {e}")
            
            self.reconnect_count += 1
            time.sleep(self.reconnect_interval)
        
        logger.error("重新連線失敗次數過多，停止嘗試")
        return False
    
    def check_connection(self) -> bool:
        """檢查連線狀態"""
        try:
            # 嘗試取得流量資訊來測試連線
            usage = self.client.get_usage()
            if usage:
                self.is_connected = True
                return True
        except Exception as e:
            logger.warning(f"連線檢查失敗: {e}")
        
        self.is_connected = False
        return False
    
    def wait_for_connection(self, timeout: int = 60) -> bool:
        """等待連線建立"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_connected:
                return True
            time.sleep(1)
        return False
    
    def get_status(self) -> dict:
        """取得連線狀態"""
        return {
            "is_connected": self.is_connected,
            "reconnect_count": self.reconnect_count,
            "simulation_mode": self.client.simulation
        }
