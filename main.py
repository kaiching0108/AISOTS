"""AI 期貨交易系統 - 主程式"""
import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, time
import signal

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import logger
from src.config import load_config, ensure_workspace, get_workspace_dir
from src.api import ShioajiClient, ConnectionManager, OrderCallbackHandler
from src.trading import StrategyManager, PositionManager, OrderManager
from src.risk import RiskManager
from src.notify import TelegramNotifier, TelegramBot
from src.agent import TradingTools, get_system_prompt
from src.agent.providers import create_llm_provider
from src.engine import StrategyRunner
from src.services.data_updater import DataUpdater
from src.services.realtime_kbar_aggregator import RealtimeKBarAggregator


class AITradingSystem:
    """AI 期貨交易系統主控制器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        # 載入配置
        self.config = load_config(config_path)
        
        # 確保工作目錄存在
        ensure_workspace()
        
        self.logger = logger
        
        # 對話歷史（用於 LLM 上下文）
        self.conversation_history: list = []
        self.max_history = 20  # 最多保存最近 20 條對話
        
        # 初始化各模組
        self.workspace = get_workspace_dir()
        
        # Shioaji API
        self.shioaji = ShioajiClient(
            api_key=self.config.shioaji.api_key,
            secret_key=self.config.shioaji.secret_key,
            simulation=self.config.shioaji.simulation,
            skip_login=getattr(self.config.shioaji, 'skip_login', False)
        )
        
        # 連線管理
        self.connection_mgr = ConnectionManager(
            self.shioaji,
            self.config.risk.model_dump()
        )
        
        # 訂單回調
        self.order_callback = OrderCallbackHandler()
        
        # 策略管理
        self.strategy_mgr = StrategyManager(self.workspace)
        
        # 部位管理
        self.position_mgr = PositionManager(self.workspace)
        
        # 下單管理
        self.order_mgr = OrderManager(self.workspace)
        
        # 風控管理
        self.risk_mgr = RiskManager(self.config.risk.model_dump())
        
        # 通知
        self.notifier = TelegramNotifier(self.config.telegram.model_dump())
        
        # Telegram Bot (接收命令)
        self.telegram_bot = TelegramBot(
            config=self.config.telegram.model_dump(),
            command_handler=self.llm_process_command,
            clear_history_callback=self.clear_conversation_history,
            notifier=self.notifier
        )
        
        # LLM Provider (lazy loading)
        self._llm_provider = None
        
        # AI 交易工具
        self.trading_tools = TradingTools(
            strategy_manager=self.strategy_mgr,
            position_manager=self.position_mgr,
            order_manager=self.order_mgr,
            risk_manager=self.risk_mgr,
            shioaji_client=self.shioaji,
            notifier=self.notifier,
            llm_provider=self.llm_provider
        )
        
        # 策略執行器
        self.strategy_runner = StrategyRunner(
            strategy_manager=self.strategy_mgr,
            position_manager=self.position_mgr,
            order_manager=self.order_mgr,
            shioaji_client=self.shioaji,
            risk_manager=self.risk_mgr,
            llm_provider=self.llm_provider,
            notifier=self.notifier,
            on_signal=self._on_strategy_signal
        )

        # 系統狀態
        self.is_running = False
        self.main_loop_task = None
        
        # 自動 LLM Review 排程器
        self.auto_review_scheduler = None
        
        # K棒數據更新服務
        self.data_updater = None
        
        # 實時 K-bar 聚合器（用於實盤）
        self.realtime_aggregator = RealtimeKBarAggregator(
            on_kbar_callback=self._on_realtime_kbar
        )
        
        # 模擬價格趨勢追蹤（用於 _simulate_price_updates）
        self._price_trend = {}  # 記錄每個 symbol 的趨勢方向: 1=上漲, -1=下跌
        self._trend_count = {}  # 記錄趨勢持續了多少根 K 棒
    
    @property
    def llm_provider(self):
        """Lazy loading LLM provider"""
        if self._llm_provider is None:
            self._llm_provider = create_llm_provider(self.config.llm)
        return self._llm_provider
    
    async def _on_strategy_signal(self, strategy, signal: str) -> None:
        """策略訊號回調
        
        Args:
            strategy: 策略對象
            signal: 交易訊號
        """
        self.logger.info(f"Strategy signal: {strategy.name} -> {signal}")
        
        # 取得部位
        position = self.position_mgr.get_position(strategy.id)
        
        # 從策略參數取得停損止盈點數（並進行型別轉換）
        stop_loss = int(strategy.params.get("stop_loss", 0)) if strategy.params.get("stop_loss") else 0
        take_profit = int(strategy.params.get("take_profit", 0)) if strategy.params.get("take_profit") else 0
        
        # 根據訊號執行
        if signal == "buy" and not position:
            result = self.trading_tools.place_order(
                strategy_id=strategy.id,
                action="Buy",
                quantity=strategy.params.get("quantity", 1),
                reason=f"策略訊號: {signal}",
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            self.notifier.send_message(result)
            
        elif signal == "sell" and position:
            result = self.trading_tools.close_position(
                strategy_id=strategy.id,
                price=0
            )
            self.notifier.send_message(result)
    
    async def initialize(self) -> bool:
        """初始化系統"""
        self.logger.info("=" * 50)
        self.logger.info("AI 期貨交易系統初始化中...")
        self.logger.info("=" * 50)
        
        # 登入 Shioaji
        if not self.shioaji.login():
            self.logger.error("Shioaji 登入失敗")
            return False
        
        # 初始化 K棒數據更新服務
        data_update_config = getattr(self.config, 'data_update', None)
        if data_update_config and data_update_config.enabled:
            self.data_updater = DataUpdater(
                shioaji_client=self.shioaji,
                workspace=self.workspace,
                config=data_update_config.model_dump() if hasattr(data_update_config, 'model_dump') else data_update_config
            )
            self.logger.info("K棒數據更新服務已初始化")
            
            # 登入時檢查並更新 K棒數據（只要連線成功就執行）
            if self.shioaji.connected:
                self.logger.info("檢查 K棒數據更新...")
                update_result = await self.data_updater.check_and_update_on_login()
                if update_result.get('symbols_updated'):
                    self.logger.info(f"K棒數據更新完成: {update_result['symbols_updated']}")
                if update_result.get('symbols_need_fetch'):
                    self.logger.info(f"需要抓取的期貨: {update_result['symbols_need_fetch']}")
        
        # 設置策略運行器參考（讓模擬模式下能獲取動態價格）
        self.shioaji.set_strategy_runner(self.strategy_runner)
        
        # 從 Shioaji 取得可用期貨代碼
        self.trading_tools.update_valid_symbols()
        
        # 同步連線狀態到 ConnectionManager（避免 _main_loop 啟動時誤判斷線）
        self.connection_mgr.is_connected = self.shioaji.connected
        logger.info(f"連線狀態同步完成：shioaji.connected={self.shioaji.connected}, connection_mgr.is_connected={self.connection_mgr.is_connected}")
        
        # 設置連線事件處理
        self.connection_mgr.setup_event_handlers()
        
        # 設置訂單回調
        self.shioaji.set_order_callback(self.order_callback.create_callback())
        
        # 綁定訂單事件
        self.order_callback.on_order_filled = self._on_order_filled
        self.order_callback.on_order_cancelled = self._on_order_cancelled
        
        # 綁定連線事件
        self.connection_mgr.on_disconnected = self._on_disconnected
        self.connection_mgr.on_reconnected = self._on_reconnected
        
        # 設置實盤報價回調（實時 K-bar 聚合）
        if not self.config.shioaji.simulation and not self.shioaji.skip_login:
            self._setup_tick_callback()
        
        # 顯示策略狀態
        strategies = self.strategy_mgr.get_all_strategies()
        self.logger.info(f"載入 {len(strategies)} 個策略:")
        for s in strategies:
            self.logger.info(f"  - {s.name} ({s.symbol}): {'啟用' if s.enabled else '停用'}")
        
        # 初始化自動 LLM Review 排程器
        if self.config.auto_review.enabled and self.config.auto_review.schedules:
            from src.analysis.auto_review_scheduler import AutoReviewScheduler
            self.auto_review_scheduler = AutoReviewScheduler(
                config=self.config,
                trading_tools=self.trading_tools,
                notifier=self.notifier
            )
            self.logger.info(f"自動 LLM Review 排程器已啟用，共 {len(self.config.auto_review.schedules)} 個排程")
        
        # 發送啟動通知
        mode = "模擬" if self.config.shioaji.simulation else "實盤"
        self.notifier.send_message(
            f"🤖 *AI 期貨交易系統啟動*\n\n"
            f"模式: {mode}\n"
            f"策略數: {len(strategies)}\n"
            f"風控: 單日最大虧損 {self.config.risk.max_daily_loss} 元"
        )
        
        return True
    
    def _on_order_filled(self, order) -> None:
        """成交回調"""
        self.logger.info(f"訂單成交: {order.order_id}")
        
        # 發送通知
        self.notifier.send_order_notification({
            "status": "Filled",
            "strategy_name": order.strategy_name,
            "symbol": order.symbol,
            "action": order.action,
            "quantity": order.quantity,
            "filled_price": order.filled_price,
            "timestamp": order.filled_time
        })
    
    def _on_order_cancelled(self, order) -> None:
        """取消回調"""
        self.logger.info(f"訂單取消: {order.order_id}")
        
        self.notifier.send_order_notification({
            "status": "Cancelled",
            "strategy_name": order.strategy_name,
            "symbol": order.symbol,
            "action": order.action,
            "quantity": order.quantity,
            "timestamp": datetime.now().isoformat()
        })
    
    def _setup_tick_callback(self) -> None:
        """設置實盤 tick 回調"""
        import shioaji as sj
        
        @sj.EvHandler(self.shioaji.api.quote.on_tick_fop_v1)
        def on_tick(tick):
            try:
                # 從 tick 提取合約代碼和價格
                if hasattr(tick, 'code') and hasattr(tick, 'close'):
                    symbol = tick.code
                    if symbol in ['TXF', 'MXF', 'TMF']:
                        price = tick.close
                        volume = tick.volume if hasattr(tick, 'volume') else 0
                        timestamp = tick.datetime
                        
                        # 處理 tick 數據
                        self.realtime_aggregator.process_tick(
                            symbol=symbol,
                            price=price,
                            volume=volume,
                            timestamp=timestamp
                        )
            except Exception as e:
                self.logger.error(f"Tick 處理錯誤: {e}")
    
    def _on_realtime_kbar(self, symbol: str, kbar_data: dict) -> None:
        """實時 K-bar 生成回調
        
        Args:
            symbol: 期貨代碼
            kbar_data: K-bar 數據
        """
        from datetime import datetime
        
        # 將 K-bar 更新到策略執行器的 market_data_cache
        self.strategy_runner.update_market_data(
            symbol=symbol,
            timestamp=datetime.fromtimestamp(kbar_data['ts']),
            open_price=kbar_data['open'],
            high=kbar_data['high'],
            low=kbar_data['low'],
            close=kbar_data['close'],
            volume=kbar_data['volume']
        )
    
    def _on_disconnected(self) -> None:
        """斷線回調"""
        self.logger.warning("Shioaji 連線中斷")
        self.notifier.send_alert("連線中斷", "Shioaji 連線已中斷，系統正在嘗試重新連線...")
    
    def _on_reconnected(self) -> None:
        """重連回調"""
        self.logger.info("Shioaji 重新連線")
        self.notifier.send_message("✅ Shioaji 重新連線成功")
    
    async def start(self) -> None:
        """啟動系統"""
        if not await self.initialize():
            self.logger.error("系統初始化失敗")
            return
        
        # 啟動 Telegram Bot
        await self.telegram_bot.start()
        
        self.is_running = True
        self.logger.info("系統啟動完成，開始執行主迴圈...")
        
        # 啟動主迴圈
        self.main_loop_task = asyncio.create_task(self._main_loop())
        
        # 等待
        try:
            await self.main_loop_task
        except asyncio.CancelledError:
            self.logger.info("主迴圈已取消")
    
    async def stop(self) -> None:
        """停止系統"""
        self.logger.info("系統正在停止...")
        self.is_running = False
        
        # 停止 Telegram Bot
        await self.telegram_bot.stop()
        
        if self.main_loop_task:
            self.main_loop_task.cancel()
            try:
                await self.main_loop_task
            except asyncio.CancelledError:
                pass
        
        # 登出
        self.shioaji.logout()
        
        # 發送停止通知
        self.notifier.send_message("🛑 AI 期貨交易系統已停止")
        
        self.logger.info("系統已停止")
    
    async def _main_loop(self) -> None:
        """主迴圈 - 定時任務"""
        check_interval = self.config.trading.check_interval
        
        # 模擬模式下，記錄上次價格更新時間
        last_price_update = datetime.now()
        price_update_interval = 60  # 每60秒更新一次價格
        
        while self.is_running:
            try:
                # 1. 檢查連線
                if not self.connection_mgr.is_connected:
                    self.logger.warning("連線中斷，嘗試重連...")
                    if not self.connection_mgr.handle_disconnect():
                        self.logger.error("重連失敗")
                        await asyncio.sleep(30)
                        continue
                
                # 模擬模式下，定時生成新價格數據
                if self.config.shioaji.simulation or self.shioaji.skip_login:
                    now = datetime.now()
                    if (now - last_price_update).seconds >= price_update_interval:
                        await self._simulate_price_updates()
                        last_price_update = now
                
                # 2. 更新部位價格
                await self._update_positions()
                
                # 3. 檢查停損止盈
                await self._check_stop_loss_take_profit()
                
                # 4. 執行策略訊號
                await self.strategy_runner.run_all_strategies()
                
                # 5. 更新當日損益
                daily_pnl = self.shioaji.get_daily_pnl()
                self.risk_mgr.update_daily_pnl(daily_pnl)
                
                # 6. 檢查是否需要強制停止
                if not self.risk_mgr.is_trading_allowed():
                    self.notifier.send_alert(
                        "風控停止",
                        f"單日虧損已達 {self.risk_mgr.max_daily_loss} 元，停止所有交易"
                    )
                
                # 7. 檢查自動 LLM Review 排程
                if self.auto_review_scheduler:
                    self.auto_review_scheduler.check_and_trigger()
                
            except Exception as e:
                self.logger.error(f"主迴圈錯誤: {e}")
                self.notifier.send_error(str(e))
            
            await asyncio.sleep(check_interval)
    
    async def _update_positions(self) -> None:
        """更新部位價格"""
        positions = self.position_mgr.get_all_positions()
        
        if not positions:
            return
        
        price_map = {}
        for pos in positions:
            # 從 strategy_runner 獲取最新市場價格（而非 get_contract().last_price）
            market_data = self.strategy_runner.get_market_data(pos.symbol)
            if market_data and market_data.close_prices:
                # 使用最新收盤價作為當前價格
                current_price = market_data.close_prices[-1]
                price_map[pos.symbol] = current_price
                logger.debug(f"停損檢查價格: {pos.symbol} @ {current_price:.2f}")
            else:
                # 如果沒有市場數據，使用部位進場價作為備選
                price_map[pos.symbol] = pos.entry_price
                logger.warning(f"無市場數據，使用進場價: {pos.symbol} @ {pos.entry_price}")
        
        # 更新並檢查是否觸發停損止盈
        triggered = self.position_mgr.update_prices(price_map)
        
        # 處理觸發
        for t in triggered:
            strategy_id = t["strategy_id"]
            exit_price = t["exit_price"]
            
            # 使用 trading_tools.close_position 進行完整平倉流程（包含訂單記錄和交易日誌）
            result_msg = self.trading_tools.close_position(strategy_id, price=exit_price)
            
            # close_position 已經發送通知，這裡只需記錄日誌
            if "平倉完成" in result_msg:
                logger.info(f"停損/止盈平倉成功: {strategy_id}, 訊息: {result_msg[:100]}...")
            else:
                logger.warning(f"停損/止盈平倉可能失敗: {strategy_id}, 訊息: {result_msg}")
    
    async def _check_stop_loss_take_profit(self) -> None:
        """檢查停損止盈"""
        # 這個功能已經整合到 _update_positions 中
        pass
    
    async def _simulate_price_updates(self) -> None:
        """模擬模式下生成新價格數據
        
        為每個已啟用策略的 symbol 生成新的 K 棒數據，
        驅動策略持續分析並產生交易訊號。
        
        注意：模擬環境下所有策略統一按 1分鐘頻率生成 K 棒，
        策略的 timeframe 參數只影響策略內部邏輯，不影響數據生成頻率。
        
        價格生成邏輯：
        - 模擬真實市場的趨勢特性（上漲/下跌有慣性）
        - 30% 概率反轉趨勢
        - 趨勢持續越久，波動越大但久了會回調
        """
        try:
            import random
            from src.api.shioaji_client import ShioajiClient
            
            # 取得所有已啟用策略
            enabled_strategies = self.strategy_mgr.get_enabled_strategies()
            
            if not enabled_strategies:
                return
            
            now = datetime.now()
            
            for strategy in enabled_strategies:
                symbol = strategy.symbol
                
                # 取得策略的 timeframe 並獲取對應波動率
                timeframe = strategy.params.get("timeframe", "1h") if strategy.params else "1h"
                base_volatility = ShioajiClient.get_timeframe_volatility(timeframe)
                
                # 取得現有市場數據
                market_data = self.strategy_runner.get_market_data(symbol)
                
                if not market_data or not market_data.close_prices:
                    continue
                
                # 取得最後一根 K 棒的收盤價作為基礎
                last_close = market_data.close_prices[-1]
                
                # ===== 趨勢模擬邏輯（根據 timeframe 調整波動率）=====
                # 檢查是否需要開始新趨勢（30% 概率反轉）
                if symbol not in self._price_trend or random.random() < 0.3:
                    # 開始新趨勢：1=上漲, -1=下跌
                    self._price_trend[symbol] = random.choice([-1, 1])
                    self._trend_count[symbol] = 0
                    self.logger.debug(f"{symbol} ({timeframe}) 開始新趨勢: {'上漲' if self._price_trend[symbol] > 0 else '下跌'}")
                
                trend = self._price_trend[symbol]
                self._trend_count[symbol] += 1
                trend_duration = self._trend_count[symbol]
                
                # 基礎變動幅度（根據 timeframe 調整：1m:0.03% ~ 1d:1.2%）
                base_change = random.uniform(base_volatility, base_volatility * 2.67)
                
                # 趨勢加成：趨勢越久，動量越大，但久了會疲態（回調）
                # 前5根：動量遞增，之後開始回調
                if trend_duration <= 5:
                    momentum = 1 + (trend_duration * 0.15)  # 最大 1.75x
                else:
                    momentum = 1.75 - ((trend_duration - 5) * 0.1)  # 開始回調
                    momentum = max(momentum, 0.5)  # 最小 0.5x
                
                # 計算價格變動百分比
                change_pct = trend * base_change * momentum
                
                # 加入隨機雜訊（±0.2%）
                noise = random.uniform(-0.002, 0.002)
                change_pct += noise
                
                # 計算新收盤價（限制為整數）
                new_close = round(last_close * (1 + change_pct))
                
                # 每10根K線或趨勢反轉時記錄波動率資訊
                if trend_duration <= 1 or trend_duration % 10 == 0:
                    self.logger.debug(f"{symbol} ({timeframe}) 波動率: {base_volatility*100:.3f}%, 趨勢: {'上漲' if trend > 0 else '下跌'} {trend_duration}根, 價格: {new_close}")
                
                # 生成 OHLC（根據趨勢方向調整，限制為整數）
                if trend > 0:  # 上漲趨勢
                    new_open = round(last_close * (1 + random.uniform(-0.001, 0.002)))
                    new_high = round(max(new_open, new_close) * (1 + random.uniform(0.001, 0.003)))
                    new_low = round(min(new_open, new_close) * (1 - random.uniform(0.001, 0.002)))
                else:  # 下跌趨勢
                    new_open = round(last_close * (1 + random.uniform(-0.002, 0.001)))
                    new_high = round(max(new_open, new_close) * (1 + random.uniform(0.001, 0.002)))
                    new_low = round(min(new_open, new_close) * (1 - random.uniform(0.002, 0.003)))
                
                new_volume = random.randint(1000, 8000)
                
                # 更新市場數據快取
                self.strategy_runner.update_market_data(
                    symbol=symbol,
                    timestamp=now,
                    open_price=new_open,
                    high=new_high,
                    low=new_low,
                    close=new_close,
                    volume=new_volume
                )
                
                self.logger.debug(f"模擬價格更新: {symbol} @ {new_close:.2f} (趨勢: {'上漲' if trend > 0 else '下跌'} {trend_duration}根)")
            
            # 收集各策略的 timeframe 資訊用於日誌
            timeframe_info = []
            for s in enabled_strategies:
                tf = s.params.get("timeframe", "1h") if s.params else "1h"
                vol = ShioajiClient.get_timeframe_volatility(tf)
                timeframe_info.append(f"{s.symbol}({tf}:{vol*100:.2f}%)")
            
            self.logger.info(f"已為 {len(enabled_strategies)} 個策略生成模擬價格更新 "
                           f"(1分鐘頻率，根據 timeframe 調整波動率: {', '.join(timeframe_info)})")
            
        except Exception as e:
            self.logger.error(f"模擬價格更新失敗: {e}")
    
    def get_help_text(self) -> str:
        """取得說明文字"""
        return """
📋 *AI 期貨交易系統 - 命令列表*

🔍 【查詢類】
• status / 系統狀態 - 系統狀態
• positions / 部位 - 目前部位
• strategies / 策略 - 所有策略
• performance / 績效 - 當日績效
• risk / 風控 - 風控狀態
• orders / 訂單 - 訂單歷史
• price <代碼> - 查詢報價
例: price TXF
• status <ID> - 策略狀態
例: status strategy_001
• performance <ID> [period] - 策略績效
例: performance strategy_001 month
• review <ID> - LLM 審查策略
例: review strategy_001

 📦 【策略管理】
• enable <ID> - 啟用策略
例: enable strategy_001
• disable <ID> - 停用策略 (有部位會詢問)
例: disable strategy_001
• delete <ID> - 刪除策略 (有部位會詢問是否強制平倉)
例: delete TMF260001

🎯 【目標與優化】
• goal <ID> <金額> <單位> - 設定目標
例: goal strategy_001 500 daily (每日500元)
例: goal strategy_001 10000 monthly (每月10000元)
• optimize <ID> - 優化策略
例: optimize strategy_001

❓ 【其他】
• help / ? - 顯示此列表
• cancel - 取消操作
"""
    
    async def llm_process_command(self, command: str) -> str:
        """透過 LLM 處理命令"""
        import json
        import re
        
        # 檢查是否為確認關鍵詞（直接處理，避免 LLM 忘記調用工具）
        command_stripped = command.strip().lower()
        confirm_keywords = ["確認", "确定", "yes", "確定", "confirm", "ok", "好", "好啦", "okay"]
        
        if any(kw in command_stripped for kw in confirm_keywords):
            if self.trading_tools._pending_strategy is not None:
                # 有待確認的策略，直接調用確認函數
                self.logger.info(f"Directly confirming strategy (keyword detected)")
                result = self.trading_tools.confirm_create_strategy(confirmed=True)
                self._add_to_history(command, result)
                return result
            elif getattr(self.trading_tools, '_awaiting_symbol', False):
                # 正在等待期貨代碼，但用戶說了確認
                # 這表示用戶可能還沒理解需要輸入期貨代碼
                return "請輸入期貨代碼（如 TXF、MXF、TMF）來繼續建立策略"
        
        # 直接處理 enable/disable 命令
        enable_match = re.match(r'^enable\s+(\w+)$', command_stripped)
        disable_match = re.match(r'^disable\s+(\w+)$', command_stripped)
        
        if enable_match:
            strategy_id = enable_match.group(1).upper()
            self.logger.info(f"Directly enabling strategy: {strategy_id}")
            result = self.trading_tools.enable_strategy(strategy_id)
            self._add_to_history(command, result)
            return result
        
        if disable_match:
            strategy_id = disable_match.group(1).upper()
            self.logger.info(f"Directly disabling strategy: {strategy_id}")
            result = self.trading_tools.disable_strategy(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理 delete 命令
        delete_match = re.match(r'^delete\s+(\w+)$', command_stripped)
        
        if delete_match:
            strategy_id = delete_match.group(1).upper()
            self.logger.info(f"Directly deleting strategy: {strategy_id}")
            result = self.trading_tools.delete_strategy_tool(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理策略建立關鍵字
        creation_keywords = ["設計", "建立", "創建", "design", "create", "幫我設計", "幫我建立", "我想設計", "我想建立"]
        if any(kw in command_stripped for kw in creation_keywords):
            # 從命令中提取期貨代碼
            found_symbol = None
            for symbol in self.trading_tools._valid_symbols:
                if symbol in command_stripped.upper():
                    found_symbol = symbol
                    break
            
            # 提取目標描述（移除關鍵字和期貨代碼）
            goal = command
            for kw in creation_keywords:
                goal = goal.replace(kw, "")
            if found_symbol:
                goal = goal.replace(found_symbol, "").replace(found_symbol.lower(), "")
            goal = goal.strip(" ，,、.")
            
            # 如果沒找到期貨代碼，詢問用戶
            if not found_symbol:
                self.logger.info(f"Strategy creation requested but no symbol found")
                return "請問要使用哪個期貨合約？（如 TXF、MXF、TMF）"
            
            # 直接呼叫 create_strategy_by_goal
            self.logger.info(f"Directly creating strategy: goal={goal}, symbol={found_symbol}")
            result = self.trading_tools.create_strategy_by_goal(goal, found_symbol)
            self._add_to_history(command, result)
            return result
        
        # 直接處理常見命令
        # status
        if command_stripped == "status":
            result = self.trading_tools.get_system_status()
            self._add_to_history(command, result)
            return result
        
        # positions / 部位
        if command_stripped in ["positions", "部位", "持倉"]:
            result = self.trading_tools.get_positions()
            self._add_to_history(command, result)
            return result
        
        # strategies / 策略
        if command_stripped in ["strategies", "策略", "策略列表"]:
            result = self.trading_tools.get_strategies()
            self._add_to_history(command, result)
            return result
        
        # performance / 績效
        if command_stripped in ["performance", "績效", "表現"]:
            result = self.trading_tools.get_performance()
            self._add_to_history(command, result)
            return result
        
        # risk / 風控
        if command_stripped in ["risk", "風控", "風險"]:
            result = self.trading_tools.get_risk_status()
            self._add_to_history(command, result)
            return result
        
        # orders / 訂單
        if command_stripped in ["orders", "訂單", "委託"]:
            result = self.trading_tools.get_order_history(None)
            self._add_to_history(command, result)
            return result
        
        # new / 新對話
        if command_stripped in ["new", "新對話", "新會話"]:
            self.conversation_history = []
            self._add_to_history(command, "✅ 對話歷史已清除")
            return "✅ 對話歷史已清除"
        
        # help / 幫助
        if command_stripped in ["help", "幫助", "?", "？"]:
            result = """📋 *命令列表*

🔍 基本查詢
• status - 系統狀態
• positions / 部位 - 目前部位
• strategies / 策略 - 所有策略
• performance - 當日績效
• risk / 風控 - 風控狀態

📦 策略管理
• enable <ID> - 啟用策略
• disable <ID> - 停用策略

❓ 輸入文字描述讓 AI 幫你操作"""
            self._add_to_history(command, result)
            return result
        
        # 直接處理 enable/disable 命令
        enable_match = re.match(r'^enable\s+(\w+)$', command_stripped)
        disable_match = re.match(r'^disable\s+(\w+)$', command_stripped)
        
        if enable_match:
            strategy_id = enable_match.group(1).upper()
            self.logger.info(f"Directly enabling strategy: {strategy_id}")
            result = self.trading_tools.enable_strategy(strategy_id)
            self._add_to_history(command, result)
            return result
        
        if disable_match:
            strategy_id = disable_match.group(1).upper()
            self.logger.info(f"Directly disabling strategy: {strategy_id}")
            result = self.trading_tools.disable_strategy(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理 delete 命令
        delete_match = re.match(r'^delete\s+(\w+)$', command_stripped)
        
        if delete_match:
            strategy_id = delete_match.group(1).upper()
            self.logger.info(f"Directly deleting strategy: {strategy_id}")
            result = self.trading_tools.delete_strategy_tool(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理 confirm delete 命令
        confirm_delete_match = re.match(r'^confirm delete\s+(\w+)$', command_stripped)
        
        if confirm_delete_match:
            strategy_id = confirm_delete_match.group(1).upper()
            self.logger.info(f"Confirming delete strategy: {strategy_id}")
            result = self.trading_tools.confirm_delete_strategy(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理 confirm enable 命令（啟用新策略並強制平倉舊策略部位）
        confirm_enable_match = re.match(r'^confirm enable\s+(\w+)$', command_stripped)
        
        if confirm_enable_match:
            strategy_id = confirm_enable_match.group(1).upper()
            self.logger.info(f"Confirming enable strategy with close: {strategy_id}")
            result = self.trading_tools.confirm_enable_with_close(strategy_id)
            self._add_to_history(command, result)
            return result
        
        # 直接處理常見命令
        # status
        if command_stripped == "status":
            result = self.trading_tools.get_system_status()
            self._add_to_history(command, result)
            return result
        
        # positions / 部位
        if command_stripped in ["positions", "部位", "持倉"]:
            result = self.trading_tools.get_positions()
            self._add_to_history(command, result)
            return result
        
        # strategies / 策略
        if command_stripped in ["strategies", "策略", "策略列表"]:
            result = self.trading_tools.get_strategies()
            self._add_to_history(command, result)
            return result
        
        # performance / 績效
        if command_stripped in ["performance", "績效", "表現"]:
            result = self.trading_tools.get_performance()
            self._add_to_history(command, result)
            return result
        
        # risk / 風控
        if command_stripped in ["risk", "風控", "風險"]:
            result = self.trading_tools.get_risk_status()
            self._add_to_history(command, result)
            return result
        
        # orders / 訂單
        if command_stripped in ["orders", "訂單", "委託"]:
            result = self.trading_tools.get_order_history(None)
            self._add_to_history(command, result)
            return result
        
        # new / 新對話
        if command_stripped in ["new", "新對話", "新會話"]:
            self.conversation_history = []
            self._add_to_history(command, "✅ 對話歷史已清除")
            return "✅ 對話歷史已清除"
        
        # help / 幫助
        if command_stripped in ["help", "幫助", "?", "？"]:
            result = """📋 *命令列表*

🔍 基本查詢
• status - 系統狀態
• positions / 部位 - 目前部位
• strategies / 策略 - 所有策略
• performance - 當日績效
• risk / 風控 - 風控狀態

📦 策略管理
• enable <ID> - 啟用策略
• disable <ID> - 停用策略

❓ 輸入文字描述讓 AI 幫你操作"""
            self._add_to_history(command, result)
            return result
        
        # 檢查是否正在等待期貨代碼輸入（_awaiting_symbol=True）
        # 如果用戶直接回覆期貨代碼，直接處理
        if self.trading_tools._awaiting_symbol and self.trading_tools._pending_strategy is None:
            # 提取可能的期貨代碼
            user_input = command.strip().upper()
            valid_symbols = self.trading_tools._valid_symbols if hasattr(self.trading_tools, '_valid_symbols') else []
            
            # 檢查用戶輸入是否包含有效的期貨代碼
            found_symbol = None
            for symbol in valid_symbols:
                if symbol in user_input:
                    found_symbol = symbol
                    break
            
            if found_symbol:
                # 直接調用 create_strategy_by_goal
                self.logger.info(f"Directly processing futures code: {found_symbol}")
                goal = self.trading_tools._current_goal or "建立策略"
                result = self.trading_tools.create_strategy_by_goal(goal, found_symbol)
                self._add_to_history(command, result)
                return result
        
        # 取得 system prompt
        system_prompt = get_system_prompt(self.config)
        
        # 建立 messages（包含對話歷史）
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # 添加對話歷史
        messages.extend(self.conversation_history)
        
        # 添加當前用戶訊息
        messages.append({"role": "user", "content": command})
        
        # 取得 tools 定義
        tools = self.trading_tools.get_tool_definitions()
        
        try:
            self.logger.info(f"LLM processing command: {command}")
            
            # 呼叫 LLM
            response = await self.llm_provider.chat_with_tools(
                messages=messages,
                tools=tools,
                temperature=0.7
            )
            
            # 獲取 LLM 回覆內容
            content = response.get("content", "")
            tool_calls = response.get("tool_calls", [])
            
            self.logger.info(f"LLM response - content: {content[:100] if content else 'None'}, tool_calls: {len(tool_calls)}")
            
            # 檢查是否有 tool calls
            tool_calls = response.get("tool_calls", [])
            
            if tool_calls:
                # 執行第一個 tool call
                tool_call = tool_calls[0]
                function_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                
                self.logger.info(f"LLM tool call - function: {function_name}, arguments: {arguments}")
                
                # 執行工具
                result = self.trading_tools.execute_tool(function_name, arguments)
                
                # 添加到歷史
                self._add_to_history(command, result)
                return result
            else:
                # 沒有 tool call，直接回覆
                result = content if content else "無法理解指令，輸入 help 查看"
                
                # 添加到歷史
                self._add_to_history(command, result)
                return result
                
        except Exception as e:
            self.logger.error(f"LLM 處理失敗: {e}")
            # Fallback 到原有邏輯
            return self.fallback_handle_command(command)
    
    def _add_to_history(self, user_message: str, assistant_message: str) -> None:
        """添加對話到歷史記錄"""
        self.conversation_history.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        # 限制歷史長度
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_conversation_history(self) -> None:
        """清除對話歷史"""
        self.conversation_history = []
        self.logger.info("對話歷史已清除")
    
    def fallback_handle_command(self, command: str) -> str:
        """Fallback 命令處理 (當 LLM 失敗時)"""
        command = command.strip()
        command_lower = command.lower()
        
        # 檢查是否在建立策略 Q&A 流程中
        if self.trading_tools._awaiting_create_input:
            return self.trading_tools.handle_create_input(command)
        
        # 建立策略 Q&A 流程
        if command_lower == "create":
            return self.trading_tools.start_create_flow()
        
        # 解析命令
        if command_lower in ["status", "狀態", "系統狀態"]:
            return self.trading_tools.get_system_status()
        
        elif command_lower in ["positions", "部位", "持倉"]:
            return self.trading_tools.get_positions()
        
        elif command_lower in ["strategies", "策略"]:
            return self.trading_tools.get_strategies()
        
        elif command_lower in ["performance", "績效"]:
            return self.trading_tools.get_performance()
        
        elif command.startswith("performance "):
            parts = command.split(" ", 1)[1]
            args = parts.split()
            
            strategy_id = args[0] if args else ""
            
            if not strategy_id:
                return "請提供策略 ID：performance <ID> [period]"
            
            if len(args) >= 2:
                period = args[1]
            else:
                period = "all"
            
            return self.trading_tools.get_strategy_performance(strategy_id, period)
        
        elif command_lower in ["risk", "風控"]:
            return self.trading_tools.get_risk_status()
        
        elif command_lower in ["orders", "訂單"]:
            return self.trading_tools.get_order_history()
        
        elif command.startswith("enable "):
            strategy_id = command.split(" ", 1)[1]
            return self.trading_tools.enable_strategy(strategy_id)
        
        elif command.startswith("disable "):
            strategy_id = command.split(" ", 1)[1]
            return self.trading_tools.disable_strategy(strategy_id)
        
        elif command.startswith("confirm disable "):
            strategy_id = command.split(" ", 1)[1]
            return self.trading_tools.confirm_disable_strategy(strategy_id)
        
        elif command.startswith("回測 ") or command.startswith("backtest "):
            parts = command.split(" ", 1)
            strategy_id = parts[1].upper()
            result = self.trading_tools.backtest_strategy(strategy_id)
            
            if isinstance(result, dict):
                report = result.get("report", "")
                chart_path = result.get("chart_path")
                
                if chart_path and self.notifier:
                    self.notifier.send_message(report)
                    self.notifier.send_photo(chart_path, caption="📈 回測圖表")
                    return "📊 回測報告已發送"
                else:
                    return report
            else:
                return result
        
        elif command_lower in ["cancel", "取消"]:
            return "已取消操作"
        
        elif command_lower in ["確認", "确定", "yes", "確定"]:
            # 確認建立策略
            if self.trading_tools._pending_strategy:
                return self.trading_tools.confirm_create_strategy(confirmed=True)
            return "沒有待確認的策略"
        
        elif command_lower in ["否", "no", "不要"]:
            # 取消建立策略
            if self.trading_tools._pending_strategy:
                return self.trading_tools.confirm_create_strategy(confirmed=False)
            return "沒有待取消的操作"
        
        elif command.startswith("price "):
            symbol = command.split(" ", 1)[1].upper()
            return self.trading_tools.get_market_data(symbol)
        
        elif command.startswith("status "):
            strategy_id = command.split(" ", 1)[1]
            return self.trading_tools.get_strategy_status(strategy_id)
        
        elif command.startswith("review "):
            strategy_id = command.split(" ", 1)[1]
            return self.trading_tools.review_strategy(strategy_id)
        
        elif command.startswith("optimize "):
            strategy_id = command.split(" ", 1)[1]
            result = self.trading_tools.optimize_strategy(strategy_id)
            if "正在進行 LLM 策略審查" in result:
                return self.trading_tools._process_optimization_review()
            return result
        
        elif command in ["confirm optimize", "確認優化"]:
            if self.trading_tools._pending_optimization and self.trading_tools._pending_optimization.get("stage") == "confirm":
                return self.trading_tools.confirm_optimize(confirmed=True)
            return "❌ 沒有待確認的優化，請先輸入「optimize <策略ID>」"
        
        elif command.startswith("goal "):
            parts = command.split(" ", 1)[1]
            args = parts.split()
            
            if len(args) < 3:
                return "請提供完整參數：goal <ID> <目標金額> <單位>\n例如：goal strategy_001 500 daily"
            
            strategy_id = args[0]
            try:
                goal = float(args[1])
            except ValueError:
                return "目標金額必須是數字"
            
            goal_unit = args[2].lower()
            
            return self.trading_tools.set_strategy_goal(strategy_id, goal, goal_unit)
        
        else:
            return "無法理解指令，輸入 help 查看"


def parse_args():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description="AI 期貨交易系統")
    parser.add_argument("command", nargs="?", default="start", help="命令: start (預設)")
    parser.add_argument("--simulate", action="store_true", help="模擬模式（跳過 API 登入）")
    return parser.parse_args()


async def main():
    """主函數"""
    args = parse_args()
    
    # 建立系統
    system = AITradingSystem(config_path="config.yaml")
    
    # 模擬模式
    if args.simulate:
        system.shioaji.skip_login = True
    
    # Web 界面（可選）
    web_config = getattr(system.config, 'web', None)
    if web_config and web_config.enabled:
        import threading
        from src.web.app import create_web_app
        
        web_app = create_web_app(
            system.trading_tools, 
            system.llm_provider,
            system.data_updater  # 傳遞 DataUpdater
        )
        web_thread = threading.Thread(
            target=web_app.run,
            kwargs={
                "host": web_config.host,
                "port": web_config.port,
                "debug": False,
                "use_reloader": False
            }
        )
        web_thread.daemon = True
        web_thread.start()
        logger.info(f"Web 界面已啟動: http://{web_config.host}:{web_config.port}")
    
    # 處理信號
    def signal_handler(sig, frame):
        print("\n收到停止信號，正在關閉...")
        asyncio.create_task(system.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 啟動
    if not await system.initialize():
        print("系統初始化失敗")
        return
    
    # Telegram 模式
    system.is_running = True
    await system.telegram_bot.start()
    system.main_loop_task = asyncio.create_task(system._main_loop())
    
    try:
        await system.main_loop_task
    except asyncio.CancelledError:
        pass
    
    # 停止系統
    await system.stop()


if __name__ == "__main__":
    asyncio.run(main())
