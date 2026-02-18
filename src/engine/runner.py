"""策略執行器 - 協調策略執行"""
import asyncio
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from pathlib import Path

from src.logger import logger
from src.trading.strategy import Strategy
from src.trading.strategy_manager import StrategyManager
from src.trading.position_manager import PositionManager
from src.trading.order_manager import OrderManager
from src.api.shioaji_client import ShioajiClient
from src.engine.framework import StrategyExecutor, BarData, TradingStrategy
from src.engine.rule_engine import MarketData, SIGNAL_HOLD
from src.engine.llm_generator import LLMGenerator
from src.risk.risk_manager import RiskManager


class StrategyRunner:
    """策略執行器"""
    
    def __init__(
        self,
        strategy_manager: StrategyManager,
        position_manager: PositionManager,
        order_manager: OrderManager,
        shioaji_client: ShioajiClient,
        risk_manager: RiskManager,
        llm_provider=None,
        notifier=None,
        on_signal: Optional[Callable] = None
    ):
        self.strategy_manager = strategy_manager
        self.position_manager = position_manager
        self.order_manager = order_manager
        self.client = shioaji_client
        self.risk_manager = risk_manager
        self.llm_generator = LLMGenerator(llm_provider)
        self.notifier = notifier
        self.on_signal = on_signal
        
        self.market_data_cache: Dict[str, MarketData] = {}
        self.is_running = False
        self._tasks: List[asyncio.Task] = []
        self._executors: Dict[str, StrategyExecutor] = {}
    
    def calculate_required_bars(self) -> int:
        """計算策略所需的 K 棒數量
        
        Returns:
            所需的 K 棒數量
        """
        return 100
    
    async def ensure_sufficient_data(self, strategy: Strategy) -> bool:
        """確保有足夠的 K 棒資料
        
        Args:
            strategy: 策略對象
            
        Returns:
            是否有足夠資料
        """
        
        required_bars = self.calculate_required_bars()
        
        market_data = self.market_data_cache.get(strategy.symbol)
        
        if market_data and len(market_data.close_prices) >= required_bars:
            logger.debug(f"Sufficient data for {strategy.symbol}: {len(market_data.close_prices)} >= {required_bars}")
            return True
        
        logger.info(f"Fetching historical data for {strategy.symbol}, need {required_bars} bars")
        
        try:
            contract = self.client.get_contract(strategy.symbol)
            if not contract:
                logger.warning(f"Contract not found: {strategy.symbol}")
                return False
            
            timeframe = strategy.params.get("timeframe", "15m")
            bars = self.client.get_kbars(contract, timeframe, required_bars)
            
            if not bars or not bars.get("ts"):
                logger.warning(f"No historical data for {strategy.symbol}")
                return False
            
            for i in range(len(bars["ts"])):
                self.update_market_data(
                    strategy.symbol,
                    datetime.fromtimestamp(bars["ts"][i]),
                    float(bars["open"][i]),
                    float(bars["high"][i]),
                    float(bars["low"][i]),
                    float(bars["close"][i]),
                    float(bars["volume"][i])
                )
            
            actual_bars = len(self.market_data_cache[strategy.symbol].close_prices)
            logger.info(f"Fetched {actual_bars} bars for {strategy.symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {strategy.symbol}: {e}")
            return False
    
    async def start_strategy(self, strategy_id: str) -> bool:
        """啟動策略
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            是否成功啟動
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            logger.warning(f"Strategy not found: {strategy_id}")
            return False
        
        if not strategy.enabled:
            logger.warning(f"Strategy not enabled: {strategy.name}")
            return False
        
        if strategy.is_running:
            logger.info(f"Strategy already running: {strategy.name}")
            return True
        
        if not await self.generate_strategy_code(strategy):
            logger.error(f"Failed to generate strategy code: {strategy.name}")
            return False
        
        if strategy.has_valid_strategy_code():
            if not await self.ensure_sufficient_data(strategy):
                logger.error(f"Insufficient data for strategy: {strategy.name}")
                return False
        
        try:
            contract = self.client.get_contract(strategy.symbol)
            if contract:
                self.client.subscribe_quote(contract)
                logger.info(f"Subscribed to {strategy.symbol}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {strategy.symbol}: {e}")
        
        self.strategy_manager.start_strategy(strategy_id)
        logger.info(f"Strategy started: {strategy.name}")
        return True
    
    async def stop_strategy(self, strategy_id: str) -> bool:
        """停止策略
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            是否成功停止
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            logger.warning(f"Strategy not found: {strategy_id}")
            return False
        
        if not strategy.is_running:
            logger.info(f"Strategy not running: {strategy.name}")
            return True
        
        if strategy_id in self._executors:
            del self._executors[strategy_id]
        
        try:
            contract = self.client.get_contract(strategy.symbol)
            if contract:
                self.client.unsubscribe_quote(contract)
                logger.info(f"Unsubscribed from {strategy.symbol}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from {strategy.symbol}: {e}")
        
        self.strategy_manager.stop_strategy(strategy_id)
        logger.info(f"Strategy stopped: {strategy.name}")
        return True
    
    async def execute_strategy(self, strategy: Strategy) -> bool:
        """執行策略
        
        Args:
            strategy: 策略對象
            
        Returns:
            是否成功執行
        """
        if not strategy.enabled or not strategy.is_running:
            return False
        
        if not strategy.has_valid_strategy_code():
            logger.warning(f"Strategy {strategy.name} has no valid code, skipping execution")
            return False
        
        signal = await self.execute_strategy_llm(strategy)
        
        if signal is None or signal == SIGNAL_HOLD:
            return False
        
        if self.on_signal:
            try:
                await self.on_signal(strategy, signal)
                return True
            except Exception as e:
                logger.error(f"Error executing signal callback: {e}")
                return False
        
        return False
    
    async def generate_strategy_code(self, strategy: Strategy) -> bool:
        """使用 LLM 生成策略程式碼
        
        Args:
            strategy: 策略對象
            
        Returns:
            是否成功
        """
        if strategy.has_valid_strategy_code() and not strategy.needs_regeneration():
            return True
        
        logger.info(f"Generating strategy code for: {strategy.name}")
        
        try:
            code = await self.llm_generator.generate(strategy.prompt)
            
            if not code:
                error_msg = f"LLM 生成失敗：無法產生策略程式碼 ({strategy.name})"
                logger.error(error_msg)
                await self._send_failure_notification(strategy, error_msg)
                return False
            
            class_name = self.llm_generator.extract_class_name(code)
            if not class_name:
                error_msg = f"LLM 生成失敗：無法解析類別名稱 ({strategy.name})"
                logger.error(error_msg)
                await self._send_failure_notification(strategy, error_msg)
                return False
            
            strategy_class = self.llm_generator.compile_strategy(code, class_name)
            if not strategy_class:
                error_msg = f"LLM 生成失敗：編譯策略類別失敗 ({strategy.name})"
                logger.error(error_msg)
                await self._send_failure_notification(strategy, error_msg)
                return False
            
            strategy.set_strategy_code(code, class_name)
            self.strategy_manager.store.save_strategy(strategy.to_dict())
            
            logger.info(f"Strategy code generated and saved: {class_name}")
            return True
            
        except Exception as e:
            error_msg = f"LLM 生成錯誤：{str(e)} ({strategy.name})"
            logger.error(error_msg)
            await self._send_failure_notification(strategy, error_msg)
            return False
    
    async def _send_failure_notification(self, strategy: Strategy, error_msg: str) -> None:
        """發送 LLM 失敗通知
        
        Args:
            strategy: 策略對象
            error_msg: 錯誤訊息
        """
        if self.notifier:
            try:
                await self.notifier.send_message(
                    f"⚠️ *策略生成失敗*\n"
                    f"─────────────\n"
                    f"策略: {strategy.name}\n"
                    f"錯誤: {error_msg}\n"
                    f"策略將不會執行，請檢查日誌或修改策略描述後重試。"
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    def _create_executor(self, strategy: Strategy) -> Optional[StrategyExecutor]:
        """建立策略執行器
        
        Args:
            strategy: 策略對象
            
        Returns:
            執行器或 None
        """
        if not strategy.strategy_code or not strategy.strategy_class_name:
            return None
        
        try:
            strategy_class = self.llm_generator.compile_strategy(
                strategy.strategy_code,
                strategy.strategy_class_name
            )
            
            if not strategy_class:
                return None
            
            executor = StrategyExecutor(strategy_class(strategy.symbol))
            return executor
            
        except Exception as e:
            logger.error(f"Error creating executor: {e}")
            return None
    
    async def execute_strategy_llm(self, strategy: Strategy) -> Optional[str]:
        """使用 LLM 生成的策略執行
        
        Args:
            strategy: 策略對象
            
        Returns:
            交易訊號
        """
        if strategy.id not in self._executors:
            executor = self._create_executor(strategy)
            if not executor:
                logger.error(f"Failed to create executor for: {strategy.name}")
                return None
            self._executors[strategy.id] = executor
            logger.info(f"Created executor for strategy: {strategy.name}")
        
        executor = self._executors[strategy.id]
        
        market_data = self.market_data_cache.get(strategy.symbol)
        if not market_data or not market_data.close_prices:
            return None
        
        bar = BarData(
            timestamp=market_data.timestamps[-1],
            symbol=strategy.symbol,
            open=market_data.open_prices[-1],
            high=market_data.high_prices[-1],
            low=market_data.low_prices[-1],
            close=market_data.close_prices[-1],
            volume=market_data.volumes[-1]
        )
        
        try:
            signal = await executor.execute_bar(bar)
            
            if signal and signal != SIGNAL_HOLD:
                strategy.update_last_signal(signal)
                logger.info(f"Strategy {strategy.name} generated signal: {signal}")
            
            return signal
            
        except Exception as e:
            logger.error(f"Error executing LLM strategy: {e}")
            return None
    
    async def regenerate_strategy(self, strategy_id: str) -> bool:
        """重新生成策略程式碼
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            是否成功
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            return False
        
        if strategy.id in self._executors:
            del self._executors[strategy.id]
        
        return await self.generate_strategy_code(strategy)
    
    def update_market_data(self, symbol: str, timestamp: datetime, 
                          open_price: float, high: float, low: float, 
                          close: float, volume: float) -> None:
        """更新市場數據
        
        Args:
            symbol: 合約代碼
            timestamp: 時間戳
            open_price: 開盤價
            high: 最高價
            low: 最低價
            close: 收盤價
            volume: 成交量
        """
        if symbol not in self.market_data_cache:
            self.market_data_cache[symbol] = MarketData(symbol)
        
        self.market_data_cache[symbol].add_bar(
            timestamp, open_price, high, low, close, volume
        )
        
        max_bars = 500
        md = self.market_data_cache[symbol]
        if len(md.close_prices) > max_bars:
            md.timestamps = md.timestamps[-max_bars:]
            md.open_prices = md.open_prices[-max_bars:]
            md.high_prices = md.high_prices[-max_bars:]
            md.low_prices = md.low_prices[-max_bars:]
            md.close_prices = md.close_prices[-max_bars:]
            md.volumes = md.volumes[-max_bars:]
    
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """取得市場數據"""
        return self.market_data_cache.get(symbol)
    
    async def run_all_strategies(self) -> None:
        """執行所有啟用的策略"""
        strategies = self.strategy_manager.get_enabled_strategies()
        
        for strategy in strategies:
            # 如果已啟用但尚未啟動，先啟動
            if strategy.enabled and not strategy.is_running:
                logger.info(f"Auto-starting strategy: {strategy.name}")
                await self.start_strategy(strategy.id)
            
            if strategy.is_running:
                try:
                    await self.execute_strategy(strategy)
                except Exception as e:
                    logger.error(f"Error running strategy {strategy.name}: {e}")
    
    async def start(self, check_interval: int = 60) -> None:
        """啟動策略執行循環
        
        Args:
            check_interval: 檢查間隔 (秒)
        """
        self.is_running = True
        logger.info("Strategy runner started")
        
        while self.is_running:
            try:
                await self.run_all_strategies()
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in strategy runner loop: {e}")
                await asyncio.sleep(check_interval)
    
    def stop(self) -> None:
        """停止策略執行"""
        self.is_running = False
        logger.info("Strategy runner stopped")
    
    def get_strategy_status(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """取得策略狀態
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            策略狀態字典
        """
        strategy = self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            return None
        
        position = self.position_manager.get_position(strategy_id)
        
        required_bars = self.calculate_required_bars()
        current_bars = 0
        market_data = self.market_data_cache.get(strategy.symbol)
        if market_data:
            current_bars = len(market_data.close_prices)
        
        return {
            "id": strategy.id,
            "name": strategy.name,
            "symbol": strategy.symbol,
            "enabled": strategy.enabled,
            "is_running": strategy.is_running,
            "last_signal": strategy.last_signal,
            "last_signal_time": strategy.last_signal_time,
            "rules_parsed": strategy.has_valid_rules(),
            "rules_parsed_at": strategy.rules_parsed_at,
            "current_rules": strategy.rules,
            "llm_strategy": {
                "has_code": strategy.has_valid_strategy_code(),
                "class_name": strategy.strategy_class_name,
                "generated_at": strategy.strategy_generated_at,
                "version": strategy.strategy_version,
                "needs_regeneration": strategy.needs_regeneration()
            },
            "has_position": position is not None and position.quantity > 0,
            "position": position.to_dict() if position else None,
            "market_data": {
                "required_bars": required_bars,
                "current_bars": current_bars,
                "has_sufficient_data": current_bars >= required_bars if required_bars > 0 else True
            }
        }
    
    def get_all_strategies_status(self) -> List[Dict[str, Any]]:
        """取得所有策略狀態"""
        return [
            self.get_strategy_status(s.id)
            for s in self.strategy_manager.get_all_strategies()
        ]
