"""Shioaji API 封裝"""
import shioaji as sj
from shioaji.constant import Action, FuturesPriceType, OrderType, FuturesOCType
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.logger import logger


class ShioajiClient:
    """Shioaji API 客戶端封裝"""
    
    # 類常量：Timeframe 價格波動率映射表（回測與實時交易共用）
    # 基於台指期實際波動特性設定的經驗值
    TIMEFRAME_VOLATILITY = {
        "1m": 0.0003,   # 0.03%（約5-10點）
        "5m": 0.0008,   # 0.08%（約14-15點）
        "15m": 0.0015,  # 0.15%（約27點）
        "30m": 0.002,   # 0.2%（約36點）
        "1h": 0.003,    # 0.3%（約54點）
        "4h": 0.006,    # 0.6%（約108點）
        "1d": 0.012,    # 1.2%（約216點）
    }
    
    @classmethod
    def get_timeframe_volatility(cls, timeframe: str = "1h") -> float:
        """獲取指定 timeframe 的價格波動率"""
        return cls.TIMEFRAME_VOLATILITY.get(timeframe.lower(), 0.003)
    
    def __init__(self, api_key: str, secret_key: str, simulation: bool = True, skip_login: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.simulation = simulation
        self.skip_login = skip_login
        self.api = sj.Shioaji(simulation=simulation)
        self.futopt_account = None
        self.connected = False
        
        # 合約快取
        self._contracts_cache: Dict[str, Any] = {}
        
        # 模擬資料
        self._mock_positions: List[Dict[str, Any]] = []
        self._mock_orders: List[Dict[str, Any]] = []
        self._order_id_counter = 1000
        
        # 策略運行器參考（用於模擬模式下獲取動態價格）
        self._strategy_runner = None
    
    def set_strategy_runner(self, runner):
        """設置策略運行器參考（用於模擬模式下獲取動態價格）"""
        self._strategy_runner = runner
        logger.info("已設置策略運行器參考，模擬價格將使用動態趨勢價格")
    
    def login(self) -> bool:
        """登入 Shioaji"""
        # 跳過登入（模擬模式）
        if self.skip_login:
            logger.info("模擬模式：跳過 API 登入")
            self.connected = True
            self.futopt_account = "SIMULATE_ACCOUNT"
            return True
        
        try:
            logger.info("正在登入 Shioaji...")
            accounts = self.api.login(
                api_key=self.api_key,
                secret_key=self.secret_key,
                fetch_contract=True,
                contracts_timeout=30000,
            )
            
            # 取得期貨帳戶
            for acc in accounts:
                if hasattr(acc, "account_id") and acc.account_id:
                    self.futopt_account = acc
                    break
            
            if not self.futopt_account:
                logger.warning("未找到期貨帳戶")
            
            self.connected = True
            logger.info(f"登入成功 - 帳戶: {self.futopt_account}")
            return True
            
        except Exception as e:
            logger.error(f"登入失敗: {e}")
            self.connected = False
            return False
    
    def logout(self) -> bool:
        """登出"""
        try:
            self.api.logout()
            self.connected = False
            logger.info("已登出")
            return True
        except Exception as e:
            logger.error(f"登出失敗: {e}")
            return False
    
    def get_contract(self, symbol: str) -> Optional[Any]:
        """取得期貨合約
        
        Args:
            symbol: 期貨代碼（如 TXF、MXF、TMF）或完整合約代碼（如 TXFR1、TXF202503）
            
        Note:
            如果傳入基本代碼（TXF/MXF/TMF），會自動轉換為近月合約（TXFR1）
        """
        # 模擬模式：直接返回模擬合約，不進行任何網路呼叫
        if self.simulation or self.skip_login:
            if symbol not in self._contracts_cache:
                mock_contract = self._create_mock_contract(symbol)
                if mock_contract:
                    self._contracts_cache[symbol] = mock_contract
            return self._contracts_cache.get(symbol)
        
        if symbol in self._contracts_cache:
            return self._contracts_cache[symbol]
        
        try:
            # 自動轉換基本代碼為近月合約
            # 例如: TXF -> TXFR1, MXF -> MXFR1, TMF -> TMFR1
            near_month_map = {
                "TXF": "TXFR1",
                "MXF": "MXFR1", 
                "TMF": "TMFR1",
            }
            
            original_symbol = symbol
            if symbol in near_month_map:
                symbol = near_month_map[symbol]
                logger.info(f"自動使用近月合約: {original_symbol} -> {symbol}")
            
            # 嘗試解析合約代碼
            # 例如: TXFR1 -> TXF, R1 或者 TXF202503 -> TXF, 202503
            category = symbol[:3]
            month = symbol[3:]
            
            # 從 Shioaji 取得合約
            contracts = getattr(self.api.Contracts.Futures, category, None)
            if contracts:
                contract = getattr(contracts, symbol, None)
                if contract:
                    self._contracts_cache[original_symbol] = contract
                    return contract
            
            return None
            
        except Exception as e:
            logger.error(f"取得合約失敗 {symbol}: {e}")
            return None
    
    def _create_mock_contract(self, symbol: str) -> Optional[Any]:
        """建立模擬合約物件（使用動態價格）"""
        try:
            from dataclasses import dataclass
            
            @dataclass(frozen=True)
            class MockContract:
                code: str
                symbol: str
                name: str
                category: str
                delivery_month: str
                underlying: str
                limit_up: float
                limit_down: float
                margin: float
                last_price: float = 0.0
                reference: float = 0.0
                
                def __len__(self):
                    return 1
            
            category = symbol[:3] if len(symbol) >= 3 else symbol
            month = symbol[3:] if len(symbol) > 3 else ""
            
            name_map = {
                "TXF": "臺股期貨",
                "MXF": "小型臺指",
                "TMF": "微型臺指期貨"
            }
            
            # 獲取模擬價格（優先順序：strategy_runner > 部位價格 > 基礎價格）
            last_price = self._get_mock_price(symbol)
            
            return MockContract(
                code=symbol,
                symbol=symbol,
                name=name_map.get(category, category),
                category=category,
                delivery_month=month,
                underlying=category,
                limit_up=99999.0,
                limit_down=0.0,
                margin=50000.0,
                last_price=last_price,
                reference=last_price
            )
        except Exception as e:
            logger.error(f"建立模擬合約失敗 {symbol}: {e}")
            return None
    
    def _get_mock_price(self, symbol: str) -> float:
        """獲取模擬價格（優先順序：strategy_runner > 部位價格 > 基礎價格）"""
        base_price = 18000.0
        
        # 1. 優先從 strategy_runner 獲取動態價格
        if self._strategy_runner:
            try:
                market_data = self._strategy_runner.get_market_data(symbol)
                if market_data and hasattr(market_data, 'close_prices') and market_data.close_prices:
                    dynamic_price = float(market_data.close_prices[-1])
                    logger.debug(f"使用 strategy_runner 動態價格 {dynamic_price} 作為 {symbol} 的模擬價格")
                    return dynamic_price
            except Exception as e:
                logger.debug(f"從 strategy_runner 獲取價格失敗: {e}")
        
        # 2. 檢查是否有現有部位，使用進場價作為現價
        existing_position = next(
            (p for p in self._mock_positions if p['symbol'] == symbol), 
            None
        )
        if existing_position:
            position_price = existing_position.get('avg_price', base_price)
            logger.info(f"使用部位進場價 {position_price} 作為 {symbol} 的模擬價格")
            return position_price
        
        # 3. 使用基礎價格
        logger.debug(f"使用基礎價格 {base_price} 作為 {symbol} 的模擬價格")
        return base_price
    
    def _generate_simulate_trend_price(
        self,
        last_price: float,
        trend: int,
        trend_duration: int,
        base_volatility: float = 0.003
    ) -> tuple:
        """
        生成趨勢模擬價格（與 _simulate_price_updates 使用相同算法）
        
        與 main.py _simulate_price_updates 完全一致的趨勢模擬邏輯：
        - 基礎波動：0.3% ~ 0.8%
        - 趨勢加成：前5根遞增 (1.0x → 1.75x)，之後回調 (1.75x → 0.5x)
        - 隨機雜訊：±0.2%
        - 反轉概率：30%
        
        Args:
            last_price: 上一根K線收盤價
            trend: 趨勢方向 (1=上漲, -1=下跌)
            trend_duration: 趨勢持續根數
            base_volatility: 基礎波動率 (預設 0.003 = 0.3%)
            
        Returns:
            tuple: (new_price, new_trend, new_trend_duration)
        """
        import random
        
        # 基礎變動幅度 (0.3% ~ 0.8%)
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
        
        # 30% 概率反轉趨勢
        if random.random() < 0.3:
            trend = -trend
            trend_duration = 0
        
        # 計算新收盤價（限制為整數）
        new_price = round(last_price * (1 + change_pct))
        
        return new_price, trend, trend_duration + 1
    
    def get_kbars(self, contract: Any, timeframe: str = "1D", count: int = 100) -> Optional[Any]:
        """取得K線資料"""
        if self.simulation or self.skip_login:
            return self._generate_mock_kbars(contract, timeframe, count)
        
        try:
            return self.api.kbars(contract=contract, timeout=10000)
        except Exception as e:
            logger.error(f"取得K線失敗: {e}")
            return None
    
    def _generate_mock_kbars(self, contract: Any, timeframe: str, count: int) -> Optional[Dict[str, Any]]:
        """產生模擬K線資料（使用趨勢模擬算法，根據 timeframe 調整波動率）"""
        try:
            from datetime import datetime, timedelta
            import random
            
            now = datetime.now()
            intervals = {
                "1D": 1,
                "1H": 24,
                "15M": 96,
                "5M": 288,
                "1M": 1440,
                "15m": 96,
                "5m": 288,
                "1m": 1440,
                "1h": 24,
                "1d": 1
            }
            minutes = intervals.get(timeframe.lower(), 1440)
            
            # 根據 timeframe 調整價格波動率（使用類常量）
            base_volatility = ShioajiClient.get_timeframe_volatility(timeframe)
            
            timestamps = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            # 初始化趨勢狀態（固定初始價格 18000，Q1 選項A）
            current_price = 18000.0
            trend = random.choice([-1, 1])  # 隨機初始趨勢：1=上漲, -1=下跌
            trend_duration = 0
            
            logger.info(f"開始生成趨勢模擬K線: {contract.symbol if hasattr(contract, 'symbol') else 'Unknown'} {timeframe} {count}根，波動率 {base_volatility*100:.3f}%，初始價格 {current_price}")
            
            for i in range(count):
                ts = now - timedelta(minutes=minutes * (count - i))
                timestamps.append(int(ts.timestamp()))
                
                # 使用統一的趨勢模擬算法生成收盤價（根據 timeframe 調整波動率）
                new_close, trend, trend_duration = self._generate_simulate_trend_price(
                    current_price, trend, trend_duration, base_volatility
                )
                
                # 生成OHLC（與實時交易 _simulate_price_updates 一致）
                if trend > 0:  # 上漲趨勢
                    new_open = round(current_price * (1 + random.uniform(-0.001, 0.002)))
                    new_high = round(max(new_open, new_close) * (1 + random.uniform(0.001, 0.003)))
                    new_low = round(min(new_open, new_close) * (1 - random.uniform(0.001, 0.002)))
                else:  # 下跌趨勢
                    new_open = round(current_price * (1 + random.uniform(-0.002, 0.001)))
                    new_high = round(max(new_open, new_close) * (1 + random.uniform(0.001, 0.002)))
                    new_low = round(min(new_open, new_close) * (1 - random.uniform(0.002, 0.003)))
                
                volume = random.randint(1000, 8000)
                
                opens.append(new_open)
                highs.append(new_high)
                lows.append(new_low)
                closes.append(new_close)
                volumes.append(volume)
                
                # 更新當前價格為下一根K線的基礎
                current_price = new_close
                
                # 每10根K線記錄一次趨勢狀態
                if i > 0 and i % 10 == 0:
                    logger.debug(f"K線 {i}/{count}: 趨勢 {'上漲' if trend > 0 else '下跌'} {trend_duration}根，價格 {new_close}")
            
            # 記錄最終趨勢摘要
            first_price = closes[0]
            last_price = closes[-1]
            price_change = ((last_price - first_price) / first_price) * 100
            logger.info(f"趨勢模擬K線生成完成: {count}根，價格變化 {first_price} → {last_price} ({price_change:+.2f}%)")
            
            return {
                "ts": timestamps,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes
            }
            
        except Exception as e:
            logger.error(f"產生模擬K線失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_contracts_by_category(self, category: str) -> List[Any]:
        """取得某類別的所有期貨合約"""
        try:
            contracts = getattr(self.api.Contracts.Futures, category, None)
            if contracts:
                return [c for c in contracts]
            return []
        except Exception as e:
            logger.error(f"取得合約列表失敗 {category}: {e}")
            return []
    
    def get_available_futures_symbols(self) -> List[str]:
        """取得所有可用的期貨代碼"""
        symbols = []
        try:
            futures = self.api.Contracts.Futures
            if futures:
                # 使用 keys() 獲取期貨代碼列表
                symbols = list(futures.keys())
                logger.info(f"從 Shioaji 取得可用期貨代碼: {symbols}")
        except Exception as e:
            logger.warning(f"取得期貨代碼失敗: {e}")
        
        if not symbols:
            symbols = ["TXF", "MXF", "TMF"]
            logger.warning(f"使用預設期貨代碼: {symbols}")
        
        return symbols
    
    def get_futures_name_mapping(self) -> Dict[str, str]:
        """取得期貨代碼與中文名稱的對應表"""
        result = {}
        try:
            futures = self.api.Contracts.Futures
            if futures:
                for attr in dir(futures):
                    if not attr.startswith('_') and not attr.isupper():
                        contract = getattr(futures, attr, None)
                        if contract:
                            name = getattr(contract, 'name', None) or getattr(contract, 'csname', None)
                            if name:
                                result[attr] = name
                logger.info(f"從 Shioaji 取得期貨代碼對應表: {len(result)} 個")
        except Exception as e:
            logger.warning(f"取得期貨代碼對應表失敗: {e}")
        
        if not result:
            result = {
                "TXF": "臺股期貨",
                "MXF": "小型臺指",
                "TMF": "微型臺指期貨"
            }
            logger.warning(f"使用預設期貨代碼對應表: {result}")
        
        return result
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float = 0,
        price_type: str = "MKT",
        order_type: str = "ROD",
        octype: str = "Auto",
        timeout: int = 0,
        callback=None
    ) -> Optional[Any]:
        """下單"""
        if not self.connected:
            logger.error("未連線，無法下單")
            return None
        
        # 離線模式：模擬下單
        if self.skip_login:
            order_id = f"OFFLINE_{self._order_id_counter}"
            self._order_id_counter += 1
            
            # 取得模擬成交價（使用動態價格，而非固定18500）
            if price > 0:
                filled_price = price
            else:
                filled_price = self._get_mock_price(symbol)
                logger.debug(f"模擬下單使用動態價格: {symbol} @ {filled_price}")
            
            mock_trade = type('MockTrade', (), {
                'order_id': order_id,
                'status': 'F',
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'filled_price': filled_price,
                'filled_quantity': quantity,
                'order_type': order_type,
                'price_type': price_type,
                'order': type('MockOrder', (), {'seqno': None})(),
            })()
            
            self._mock_orders.append({
                'order_id': order_id,
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'filled_price': mock_trade.filled_price,
                'status': 'filled',
                'timestamp': datetime.now().isoformat()
            })
            
            # 模擬部位
            existing = next((p for p in self._mock_positions if p['symbol'] == symbol), None)
            if action == "Buy":
                if existing:
                    existing['quantity'] += quantity
                else:
                    self._mock_positions.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'avg_price': mock_trade.filled_price,
                        'action': 'Long'
                    })
            else:  # Sell
                if existing:
                    existing['quantity'] -= quantity
                    if existing['quantity'] <= 0:
                        self._mock_positions.remove(existing)
            
            logger.info(f"離線模擬下單: {symbol} {action} {quantity} @ {mock_trade.filled_price}")
            return mock_trade
        
        contract = self.get_contract(symbol)
        if not contract:
            logger.error(f"找不到合約: {symbol}")
            return None
        
        try:
            order = self.api.Order(
                action=Action.Buy if action == "Buy" else Action.Sell,
                price=price,
                quantity=quantity,
                price_type=FuturesPriceType[price_type],
                order_type=OrderType[order_type],
                octype=FuturesOCType[octype],
                account=self.futopt_account
            )
            
            # 非阻塞下單
            trade = self.api.place_order(
                contract,
                order,
                timeout=timeout,
                cb=callback
            )
            
            logger.info(f"下單成功: {symbol} {action} {quantity} @ {price}")
            return trade
            
        except Exception as e:
            logger.error(f"下單失敗: {e}")
            return None
    
    def cancel_order(self, trade: Any) -> bool:
        """取消訂單"""
        if not self.connected:
            logger.error("未連線，無法取消")
            return False
        
        # 離線模式：模擬取消
        if self.skip_login:
            logger.info(f"離線模擬取消訂單")
            return True
        
        try:
            self.api.cancel_order(trade)
            logger.info(f"取消訂單成功")
            return True
        except Exception as e:
            logger.error(f"取消訂單失敗: {e}")
            return False
    
    def get_positions(self) -> List[Any]:
        """取得目前部位"""
        if not self.connected:
            return []
        
        # 離線模式：返回模擬部位
        if self.skip_login:
            return self._mock_positions
        
        try:
            positions = self.api.list_positions(self.futopt_account)
            return positions
        except Exception as e:
            logger.error(f"取得部位失敗: {e}")
            return []
    
    def get_profit_loss(self, begin_date: str = None, end_date: str = None) -> List[Any]:
        """取得已實現損益"""
        if not self.connected:
            return []
        
        # 離線模式：返回模擬損益
        if self.skip_login:
            mock_pnl = []
            for order in self._mock_orders:
                if order.get('status') == 'filled' and order.get('pnl') is not None:
                    mock_pnl.append(order)
            return mock_pnl
        
        try:
            if not begin_date:
                begin_date = datetime.now().strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            profit_loss = self.api.list_profit_loss(
                self.futopt_account,
                begin_date=begin_date,
                end_date=end_date
            )
            return profit_loss
        except Exception as e:
            logger.error(f"取得損益失敗: {e}")
            return []
    
    def get_margin(self) -> Optional[Any]:
        """取得帳戶保證金資訊"""
        if not self.connected:
            return None
        
        try:
            margin = self.api.margin(self.futopt_account)
            return margin
        except Exception as e:
            logger.error(f"取得保證金失敗: {e}")
            return None
    
    def get_daily_pnl(self) -> float:
        """取得當日損益"""
        profit_loss = self.get_profit_loss()
        total_pnl = sum(p.pnl for p in profit_loss)
        return total_pnl
    
    def subscribe_quote(self, symbol: str, quote_type: str = "tick") -> bool:
        """訂閱報價"""
        # 模擬模式：跳過報價訂閱
        if self.simulation or self.skip_login:
            logger.debug(f"模擬模式跳過報價訂閱: {symbol}")
            return True
        
        if not self.connected:
            return False
        
        contract = self.get_contract(symbol)
        if not contract:
            return False
        
        try:
            self.api.quote.subscribe(
                contract,
                quote_type=sj.constant.QuoteType[quote_type.upper()],
                version=sj.constant.QuoteVersion.v1
            )
            return True
        except Exception as e:
            logger.error(f"訂閱報價失敗: {e}")
            return False
    
    def unsubscribe_quote(self, symbol: str, quote_type: str = "tick") -> bool:
        """取消訂閱報價"""
        # 模擬模式：跳過報價取消訂閱
        if self.simulation or self.skip_login:
            logger.debug(f"模擬模式跳過取消報價訂閱: {symbol}")
            return True
        
        if not self.connected:
            return False
        
        contract = self.get_contract(symbol)
        if not contract:
            return False
        
        try:
            self.api.quote.unsubscribe(
                contract,
                quote_type=quote_type
            )
            return True
        except Exception as e:
            logger.error(f"取消訂閱失敗: {e}")
            return False
    
    def set_order_callback(self, callback) -> None:
        """設置訂單回調"""
        self.api.set_order_callback(callback)
    
    def set_quote_callback(self, callback) -> None:
        """設置報價回調"""
        self.api.quote.set_on_tick_fop_v1_callback(callback)
    
    def get_usage(self) -> Optional[Any]:
        """取得流量使用量"""
        try:
            return self.api.usage()
        except Exception as e:
            logger.error(f"取得流量失敗: {e}")
            return None
