"""BacktestEngine - backtesting.py 歷史回測引擎"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

from loguru import logger

from src.storage.kbar_manager import KBarManager


class InsufficientDataError(Exception):
    """SQLite 數據不足異常"""
    def __init__(self, available_days: int, required_days: int, symbol: str, timeframe: str):
        self.available_days = available_days
        self.required_days = required_days
        self.symbol = symbol
        self.timeframe = timeframe
        super().__init__(
            f"SQLite 數據不足：{symbol} {timeframe} 只有 {available_days} 天，需要 {required_days} 天"
        )


WORKSPACE_DIR = Path("workspace")
BACKTEST_DIR = WORKSPACE_DIR / "backtests"


def extract_indicators_from_code(code: str) -> Dict[str, Any]:
    """從策略代碼中提取需要計算的指標及其參數
    
    Args:
        code: 策略程式碼
        
    Returns:
        Dict: 需要計算的指標字典，包含指標類型和參數
        例如: {'sma': {'periods': [5, 10]}, 'rsi': {'period': 14}}
    """
    indicators = {
        'rsi': None,
        'macd': None,
        'sma': None,
        'ema': None,
        'bb': None,
        'atr': None,
        'adx': None,
        'stoch': None,
        'cci': None,
    }
    
    code_upper = code.upper()
    
    # RSI - 提取週期參數
    if 'RSI' in code_upper:
        rsi_match = re.search(r'RSI.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['rsi'] = {'period': int(rsi_match.group(1))} if rsi_match else {'period': 14}
    
    # MACD - 提取標準參數或預設值
    if 'MACD' in code_upper:
        macd_match = re.search(r'MACD.*?(?:fast|short)?[=:]\s*(\d+).*?(?:slow|long)?[=:]\s*(\d+).*?(?:signal)?[=:]\s*(\d+)', code, re.IGNORECASE)
        if macd_match:
            indicators['macd'] = {
                'fast': int(macd_match.group(1)),
                'slow': int(macd_match.group(2)),
                'signal': int(macd_match.group(3))
            }
        else:
            indicators['macd'] = {'fast': 12, 'slow': 26, 'signal': 9}
    
    # SMA - 提取所有週期參數
    if re.search(r'SMA|均線', code, re.IGNORECASE):
        sma_periods = re.findall(r'SMA.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        if sma_periods:
            indicators['sma'] = {'periods': [int(p) for p in sma_periods]}
        else:
            indicators['sma'] = {'periods': [20, 30, 60]}  # 預設值
    
    # EMA - 提取所有週期參數
    if 'EMA' in code_upper:
        ema_periods = re.findall(r'EMA.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        if ema_periods:
            indicators['ema'] = {'periods': [int(p) for p in ema_periods]}
        else:
            indicators['ema'] = {'periods': [20, 30, 60]}  # 預設值
    
    # BB - 布林帶
    if re.search(r'BB|BOLL|布林', code, re.IGNORECASE):
        bb_match = re.search(r'(?:BB|BOLL|布林).*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['bb'] = {'period': int(bb_match.group(1))} if bb_match else {'period': 20}
    
    # ATR
    if 'ATR' in code_upper:
        atr_match = re.search(r'ATR.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['atr'] = {'period': int(atr_match.group(1))} if atr_match else {'period': 14}
    
    # ADX
    if 'ADX' in code_upper:
        adx_match = re.search(r'ADX.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['adx'] = {'period': int(adx_match.group(1))} if adx_match else {'period': 14}
    
    # STOCH/KD
    if re.search(r'STOCH|KD', code, re.IGNORECASE):
        stoch_match = re.search(r'(?:STOCH|KD).*?(?:period|length|k)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['stoch'] = {'period': int(stoch_match.group(1))} if stoch_match else {'period': 14}
    
    # CCI
    if 'CCI' in code_upper:
        cci_match = re.search(r'CCI.*?(?:period|length)?[=:]\s*(\d+)', code, re.IGNORECASE)
        indicators['cci'] = {'period': int(cci_match.group(1))} if cci_match else {'period': 20}
    
    return indicators


def calculate_indicators(df: pd.DataFrame, indicators: Dict[str, Any]) -> pd.DataFrame:
    """根據指標需求計算指標，使用從策略代碼提取的參數
    
    Args:
        df: 包含 OHLCV 的 DataFrame
        indicators: 需要計算的指標字典，包含參數
        
    Returns:
        DataFrame: 包含計算後指標的 DataFrame
    """
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # RSI - 使用提取的週期參數
    if indicators.get('rsi'):
        period = indicators['rsi'].get('period', 14)
        df[f'rsi_{period}'] = ta.rsi(close, length=period)
        df['rsi'] = df[f'rsi_{period}']  # 預設欄位名
    
    # MACD - 使用提取的參數
    if indicators.get('macd'):
        params = indicators['macd']
        fast = params.get('fast', 12)
        slow = params.get('slow', 26)
        signal = params.get('signal', 9)
        macd = ta.macd(close, fast=fast, slow=slow, signal=signal)
        if macd is not None:
            df['macd'] = macd[f'MACD_{fast}_{slow}_{signal}']
            df['macd_signal'] = macd[f'MACDs_{fast}_{slow}_{signal}']
            df['macd_hist'] = macd[f'MACDh_{fast}_{slow}_{signal}']
    
    # SMA - 使用提取的所有週期參數
    if indicators.get('sma'):
        periods = indicators['sma'].get('periods', [20, 30, 60])
        for period in periods:
            df[f'sma{period}'] = ta.sma(close, length=period)
    
    # EMA - 使用提取的所有週期參數
    if indicators.get('ema'):
        periods = indicators['ema'].get('periods', [20, 30, 60])
        for period in periods:
            df[f'ema{period}'] = ta.ema(close, length=period)
    
    # BB - 布林帶
    if indicators.get('bb'):
        period = indicators['bb'].get('period', 20)
        bbands = ta.bbands(close, length=period)
        if bbands is not None:
            df[f'bb_upper_{period}'] = bbands[f'BBU_{period}_2.0']
            df[f'bb_mid_{period}'] = bbands[f'BBM_{period}_2.0']
            df[f'bb_lower_{period}'] = bbands[f'BBL_{period}_2.0']
            # 預設欄位名（向後相容）
            df['bb_upper'] = df[f'bb_upper_{period}']
            df['bb_mid'] = df[f'bb_mid_{period}']
            df['bb_lower'] = df[f'bb_lower_{period}']
    
    # ATR
    if indicators.get('atr'):
        period = indicators['atr'].get('period', 14)
        df[f'atr_{period}'] = ta.atr(high, low, close, length=period)
        df['atr'] = df[f'atr_{period}']
    
    # ADX
    if indicators.get('adx'):
        period = indicators['adx'].get('period', 14)
        df[f'adx_{period}'] = ta.adx(high, low, close, length=period)
        df['adx'] = df[f'adx_{period}']
    
    # STOCH/KD
    if indicators.get('stoch'):
        period = indicators['stoch'].get('period', 14)
        stoch = ta.stoch(high, low, close, k=period)
        if stoch is not None:
            df[f'stoch_k_{period}'] = stoch[f'STOCHk_{period}_3_3']
            df[f'stoch_d_{period}'] = stoch[f'STOCHd_{period}_3_3']
            df['stoch_k'] = df[f'stoch_k_{period}']
            df['stoch_d'] = df[f'stoch_d_{period}']
    
    # CCI
    if indicators.get('cci'):
        period = indicators['cci'].get('period', 20)
        df[f'cci_{period}'] = ta.cci(high, low, close, length=period)
        df['cci'] = df[f'cci_{period}']
    
    return df


class BacktestEngine:
    """backtesting.py 回測引擎"""
    
    # 每個 timeframe 每天的 K 棒數量
    KBARS_PER_DAY = {
        "1m": 1440,
        "5m": 288,
        "15m": 96,
        "30m": 48,
        "60m": 24,
        "1h": 24,
        "1d": 1,
    }
    
    # 最大 K 棒數量限制（避免回測太久）
    MAX_KBARS = 10000
    
    TIMEFRAME_CONFIG = {
        "1m": (7, "1週"),
        "5m": (14, "2週"),
        "15m": (30, "1個月"),
        "30m": (30, "1個月"),
        "60m": (90, "3個月"),
        "1h": (90, "3個月"),
        "1d": (365, "1年"),
    }
    
    def __init__(self, shioaji_client):
        """初始化回測引擎
        
        Args:
            shioaji_client: ShioajiClient 實例
        """
        self.client = shioaji_client
        self.kbar_manager = KBarManager(shioaji_client, WORKSPACE_DIR)
    
    def _get_timeframe_params(self, timeframe: str) -> tuple:
        """取得 timeframe 對應的參數
        
        Args:
            timeframe: K線週期
            
        Returns:
            tuple: (天數, 說明)
        """
        return self.TIMEFRAME_CONFIG.get(timeframe, (30, "1個月"))
    
    def _create_strategy_class(self, strategy_code: str, class_name: str, df: pd.DataFrame):
        """創建 backtesting.py 策略類別 - 實時計算指標（與實盤一致）
        
        Args:
            strategy_code: 策略程式碼
            class_name: 策略類別名稱
            df: OHLCV DataFrame（用於設置數據結構）
            
        Returns:
            Strategy class
        """
        from backtesting import Strategy
        from src.engine.framework import TradingStrategy, BarData
        import pandas_ta as ta_module
        
        # 編譯策略代碼
        strategy_namespace = {}
        try:
            exec_globals = {
                'TradingStrategy': TradingStrategy,
                'BarData': BarData,
                'pd': pd,
                'ta': ta_module,
                'Optional': Optional,
                'logger': logger,
            }
            exec(strategy_code, exec_globals, strategy_namespace)
            
            # 獲取策略類別
            StrategyClass = strategy_namespace.get(class_name)
            if not StrategyClass:
                for name, obj in strategy_namespace.items():
                    if isinstance(obj, type) and issubclass(obj, TradingStrategy):
                        StrategyClass = obj
                        logger.info(f"找到策略類別: {name}")
                        break
            
            if not StrategyClass:
                raise ValueError(f"找不到策略類別: {class_name}")
                
        except Exception as e:
            logger.error(f"編譯策略代碼失敗: {e}")
            raise
        
        class BacktestWrapper(Strategy):
            """包裝器：讓策略實時計算指標，與實盤行為完全一致"""
            
            def init(self):
                """初始化策略實例"""
                symbol = getattr(self.data, 'symbol', 'TMF')
                self._strategy_instance = StrategyClass(symbol)
                self._strategy_instance._bars = []
                self._strategy_instance._df_cache = None
                
                # 獲取總 K 線數量
                self._total_bars = len(self.data.Close)
                
                logger.info(f"策略實例已初始化: {StrategyClass.__name__}, 總 K 線數: {self._total_bars}")
            
            def next(self):
                """每個 K 線調用 - 執行策略邏輯"""
                # 獲取當前索引（從 0 開始）
                current_idx = len(self.data.Close) - 1
                
                # 創建 BarData
                bar = BarData(
                    timestamp=pd.Timestamp.now(),
                    symbol=self._strategy_instance.symbol,
                    open=self.data.Open[-1],
                    high=self.data.High[-1],
                    low=self.data.Low[-1],
                    close=self.data.Close[-1],
                    volume=self.data.Volume[-1]
                )
                
                # 添加到歷史
                self._strategy_instance._bars.append(bar)
                
                # 關鍵：更新 DataFrame 緩存，包含從頭到當前的所有 K 線
                # 這樣 ta() 方法就能看到完整的歷史數據
                self._update_dataframe_cache(current_idx)
                
                # 詳細日誌：記錄當前 K 線狀態
                log_prefix = f"[K線 {current_idx}/{self._total_bars}]"
                
                # 嘗試獲取指標值用於日誌
                try:
                    sma5 = self._strategy_instance.ta('SMA', period=5)
                    sma10 = self._strategy_instance.ta('SMA', period=10)
                    if sma5 is not None and sma10 is not None and len(sma5) >= 2 and len(sma10) >= 2:
                        sma5_curr = sma5.iloc[-1]
                        sma5_prev = sma5.iloc[-2]
                        sma10_curr = sma10.iloc[-1]
                        sma10_prev = sma10.iloc[-2]
                        logger.debug(f"{log_prefix} 指標: sma5={sma5_curr:.2f}({sma5_prev:.2f}), sma10={sma10_curr:.2f}({sma10_prev:.2f})")
                    else:
                        logger.debug(f"{log_prefix} 指標: sma5 or sma10 is None or insufficient data")
                except Exception as e:
                    logger.debug(f"{log_prefix} 指標計算錯誤: {e}")
                
                # 執行策略
                try:
                    signal = self._strategy_instance.on_bar(bar)
                    logger.debug(f"{log_prefix} 策略返回訊號: {signal}, position={self._strategy_instance.position}")
                except Exception as e:
                    logger.error(f"{log_prefix} 策略執行錯誤: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    signal = 'hold'
                
                # 執行交易
                position = 0
                if self.position:
                    position = 1 if self.position.size > 0 else -1
                
                # 關鍵：同步 backtesting.py 的倉位到策略實例
                # 這樣策略的 on_bar 方法才能正確檢查 self.position
                self._strategy_instance.position = position
                
                # 詳細日誌：交易決策
                if signal == 'buy' and position == 0:
                    self.buy()
                    self._strategy_instance.position = 1  # 立即同步
                    logger.info(f"{log_prefix} ✅ 執行 BUY @ {bar.close}")
                elif signal == 'sell' and position == 0:
                    self.sell()
                    self._strategy_instance.position = -1  # 立即同步
                    logger.info(f"{log_prefix} ✅ 執行 SELL @ {bar.close}")
                elif signal == 'close' and position != 0:
                    self.position.close()
                    self._strategy_instance.position = 0  # 立即同步
                    logger.info(f"{log_prefix} ✅ 執行 CLOSE @ {bar.close}")
                elif signal in ['buy', 'sell', 'close']:
                    logger.debug(f"{log_prefix} ⚠️ 訊號 {signal} 被忽略 (position={position})")
                else:
                    logger.debug(f"{log_prefix} ➖ HOLD (無訊號)")
            
            def _update_dataframe_cache(self, current_idx: int):
                """更新 DataFrame 緩存 - 包含從 0 到 current_idx 的所有 K 線"""
                # 從 backtesting.py 的數據結構重建 DataFrame
                # 注意：這裡使用完整的歷史，不是只有當前 K 線
                
                # 獲取從頭到當前的所有數據
                full_open = list(self.data.Open)[:current_idx + 1]
                full_high = list(self.data.High)[:current_idx + 1]
                full_low = list(self.data.Low)[:current_idx + 1]
                full_close = list(self.data.Close)[:current_idx + 1]
                full_volume = list(self.data.Volume)[:current_idx + 1]
                
                # 創建 DataFrame
                df = pd.DataFrame({
                    'open': full_open,
                    'high': full_high,
                    'low': full_low,
                    'close': full_close,
                    'volume': full_volume,
                })
                
                self._strategy_instance._df_cache = df
                
                # 日誌（每 100 根 K 線記錄一次）
                if current_idx % 100 == 0:
                    logger.debug(f"DataFrame 已更新: {len(df)} 根 K 線")
        
        return BacktestWrapper
    
    async def run_backtest(
        self,
        strategy_code: str,
        class_name: str,
        symbol: str,
        timeframe: str = "15m",
        initial_capital: float = 1_000_000,
        commission: float = 0,
        strategy_id: Optional[str] = None,
        strategy_version: Optional[int] = None,
        use_mock: bool = False
    ) -> dict:
        """執行歷史回測
        
        Args:
            strategy_code: 策略程式碼
            class_name: 策略類別名稱
            symbol: 期貨代碼
            timeframe: K線週期
            initial_capital: 初始資金
            commission: 已廢棄，請使用固定手續費
            strategy_id: 策略ID（用於保存圖片）
            strategy_version: 策略版本（用於保存圖片）
            use_mock: 是否使用模擬數據（True=模擬，False=使用SQLite現有數據）
            
        Returns:
            dict: {
                "passed": bool,
                "report": str,
                "metrics": {...},
                "chart_path": str,
                "error": str,
            }
        """
        try:
            from backtesting import Backtest
            
            days, period_name = self._get_timeframe_params(timeframe)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            logger.info(f"Starting backtest: {symbol} {timeframe}, period: {days} days")
            
            contract = self.client.get_contract(symbol)
            if not contract:
                return {
                    "passed": False,
                    "report": "",
                    "metrics": {},
                    "error": f"找不到合約: {symbol}"
                }
            
            # 取得合約乘數（點值）
            # Shioaji API 的 unit 欄位不是實際點值，需要使用映射表
            contract_multiplier_map = {
                "TXF": 200,  # 臺股期貨
                "MXF": 50,   # 小型臺指
                "TMF": 10,   # 微型臺指
            }
            contract_multiplier = contract_multiplier_map.get(symbol, 1)
            logger.info(f"合約乘數: {contract_multiplier}")
            
            # 計算 K 棒數量：根據 timeframe 計算每天的 K 棒數，再乘以天數
            kbars_per_day = self.KBARS_PER_DAY.get(timeframe, 96)
            
            # 先檢查 SQLite 數據是否足夠
            is_connected = getattr(self.client, 'connected', False)
            logger.info(f"SQLite 數據檢查: is_connected={is_connected}, has_kbar_db={hasattr(self.client, 'kbar_db')}, use_mock={use_mock}")
            
            available_days = None
            actual_1m_count = 0
            
            # 始終檢查 SQLite 數據（無論 use_mock 是什麼）
            if is_connected and hasattr(self.client, 'kbar_db') and self.client.kbar_db:
                # SQLite 存儲的是 1m 原始數據，需要轉換為目標 timeframe
                # 1m 數量 / kbars_per_day = 實際可用天數
                # 例如：7286 條 1m 轉換為 1d = 7286 / 1440 ≈ 5 天
                available_kbars = self.client.kbar_db.get_kbars(symbol, 0, 2147483647)
                if available_kbars:
                    actual_1m_count = len(available_kbars)
                    # 使用 1m 的每日棒數來計算（因為 SQLite 存儲的是 1m）
                    kbars_per_day_1m = self.KBARS_PER_DAY.get("1m", 1440)
                    available_days = actual_1m_count / kbars_per_day_1m
                    logger.info(f"SQLite 可用數據: {actual_1m_count} 條 1m = {available_days:.1f} 天 {timeframe} (需要 {days} 天)")
                    
                    # 數據不足時，詢問用戶（僅當 use_mock=true 時）
                    if available_days < days:
                        if use_mock:
                            # 用戶選擇使用模擬數據，但數據不足，詢問用戶
                            logger.info(f"SQLite 數據不足：只有 {available_days:.1f} 天 {timeframe}，需要 {days} 天")
                            raise InsufficientDataError(
                                available_days=int(available_days),
                                required_days=days,
                                symbol=symbol,
                                timeframe=timeframe
                            )
                        # use_mock=false：用戶選擇使用現有數據，直接使用有限範圍數據
            
            # 計算 K 棒數量
            if not use_mock and available_days and available_days < days:
                # 使用現有數據時，限制範圍為可用天數
                calculated_count = int(available_days) * kbars_per_day
                days = int(available_days)
                logger.info(f"使用現有數據：限制回測範圍為 {days} 天")
            else:
                calculated_count = days * kbars_per_day
            
            # 取計算數量和最大限制的較小值
            kbars_count = min(calculated_count, self.MAX_KBARS)
            logger.info(f"K 棒數量: {days} 天 × {kbars_per_day} 棒/天 = {calculated_count} 棒 (限制: {self.MAX_KBARS} 棒)")
            
            # 優先從本地緩存獲取 K 棒數據
            kbars_data = self.kbar_manager.get_kbars_cached(symbol, timeframe, kbars_count)
            
            if not kbars_data:
                if use_mock:
                    # 用戶選擇使用模擬數據
                    logger.info(f"使用模擬數據進行回測: {symbol} {timeframe}")
                    kbars_data = self.client._generate_mock_kbars(contract, timeframe, kbars_count)
                else:
                    # 使用 SQLite 現有數據
                    logger.info(f"使用 SQLite 現有數據: {symbol} {timeframe}")
                    if is_connected and hasattr(self.client, 'kbar_db') and self.client.kbar_db:
                        # 從 SQLite 獲取數據（自動轉換 timeframe）
                        kbars_data = self.client.kbar_db.get_kbars_with_conversion(
                            symbol, 0, 2147483647, timeframe
                        )
                        logger.info(f"從 SQLite 獲取數據: {len(kbars_data.get('ts', []))} 條 {timeframe}")
                    
                    if not kbars_data or not kbars_data.get('ts'):
                        # SQLite 也沒有數據，生成模擬數據
                        logger.warning(f"無法獲取 SQLite 數據，使用模擬數據: {symbol} {timeframe}")
                        kbars_data = self.client._generate_mock_kbars(contract, timeframe, kbars_count)
            else:
                logger.info(f"使用本地 K 棒緩存: {symbol} {timeframe}")
            
            if not kbars_data or not kbars_data.get("ts"):
                return {
                    "passed": False,
                    "report": "",
                    "metrics": {},
                    "error": "無法取得 K 棒資料"
                }
            
            df = pd.DataFrame({
                'Open': [float(x) for x in kbars_data['open']],
                'High': [float(x) for x in kbars_data['high']],
                'Low': [float(x) for x in kbars_data['low']],
                'Close': [float(x) for x in kbars_data['close']],
                'Volume': [float(x) for x in kbars_data['volume']],
            })
            
            # 不再預計算指標！策略會在回測過程中實時計算
            # 這樣確保回測結果與實盤運行完全一致
            logger.info(f"回測數據準備完成: {len(df)} 根 K 線，策略將實時計算指標")
            
            # 創建策略類別 - 實時計算指標模式
            strategy_class = self._create_strategy_class(strategy_code, class_name, df)
            
            bt = Backtest(
                df, 
                strategy_class,
                cash=initial_capital,
                commission=commission,
                exclusive_orders=True
            )
            
            stats = bt.run()
            
            chart_path = None
            report_path = None
            base_filename = None
            
            # 準備檔名（等 report 生成後再保存）
            if strategy_id and strategy_version:
                try:
                    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    base_filename = f"{strategy_id}_v{strategy_version}_{timestamp}"
                except Exception as e:
                    logger.warning(f"Failed to prepare save paths: {e}")
            
            total_return = stats.get('Return [%]', 0) or 0
            sharpe = stats.get('Sharpe Ratio', 0) or 0
            max_dd = stats.get('Max. Drawdown [%]', 0) or 0
            trade_count = stats.get('# Trades', 0) or 0
            win_rate = stats.get('Win Rate [%]', 0) or 0
            
            # 計算總損益（正確方法：使用 Equity 曲線）
            # backtesting.py 已經處理了實際權益和交易盈虧
            equity_final = stats.get('Equity Final [$]', initial_capital)
            total_pnl = equity_final - initial_capital
            
            # 計算固定手續費（大台/小台/微台）
            fixed_commission_map = {
                "TXF": 40,  # 大台
                "MXF": 20,  # 小台
                "TMF": 14,  # 微台
            }
            commission_per_trade = fixed_commission_map.get(symbol, 0)
            total_commission = trade_count * 2 * commission_per_trade  # 開倉+平倉
            
            # 淨損益 = 總損益 - 手續費（手續費已經包含在 total_pnl 中，這裡是額外計算）
            # 注意：如果回測 commission 參數不為0，手續費已扣除，這裡是額外固定手續費
            net_pnl = total_pnl - total_commission
            
            sqn = 0
            avg_trade_pct = stats.get('Avg. Trade [%]', 0) or 0
            std_trade = stats.get('Std. Trade [%]', 0) or 0
            if trade_count > 0 and avg_trade_pct and std_trade:
                if std_trade > 0:
                    sqn = (avg_trade_pct / std_trade) * (trade_count ** 0.5)
            
            won_trades = int(trade_count * win_rate / 100) if trade_count > 0 else 0
            lost_trades = trade_count - won_trades
            
            # 計算 Profit Factor（正確方法：從交易記錄計算）
            # Profit Factor = 總盈利金額 / 總虧損金額絕對值
            profit_factor = 0.0
            if trade_count > 0 and hasattr(stats, '_trades') and len(stats._trades) > 0:
                trades_df = stats._trades
                # 獲取已完成交易的盈虧
                if 'PnL' in trades_df.columns:
                    winning_trades = trades_df[trades_df['PnL'] > 0]
                    losing_trades = trades_df[trades_df['PnL'] < 0]
                    
                    total_wins = winning_trades['PnL'].sum() if len(winning_trades) > 0 else 0
                    total_losses = abs(losing_trades['PnL'].sum()) if len(losing_trades) > 0 else 0
                    
                    if total_losses > 0:
                        profit_factor = total_wins / total_losses
                    elif total_wins > 0:
                        profit_factor = float('inf')  # 只有盈利，無虧損
            
            avg_trade = total_pnl / trade_count if trade_count > 0 else 0
            
            metrics = {
                "total_return": round(total_return, 2),
                "sharpe_ratio": round(float(sharpe), 2),
                "sqn": round(float(sqn), 2),
                "win_rate": round(win_rate, 2),
                "trade_count": int(trade_count),
                "max_drawdown": round(float(max_dd), 2),
                "total_pnl": round(net_pnl, 0),
                "total_commission": round(total_commission, 0),
                "won_trades": won_trades,
                "lost_trades": lost_trades,
                "profit_factor": round(profit_factor, 2),
                "avg_trade": round(net_pnl / trade_count, 0) if trade_count > 0 else 0,
            }
            
            # 生成策略分析
            analysis = self._generate_analysis(metrics, symbol)
            
            report = self._format_report(
                class_name=class_name or "Strategy",
                symbol=symbol,
                timeframe=timeframe,
                period_name=period_name,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                initial_capital=initial_capital,
                metrics=metrics,
                stats=stats
            )
            
            # 保存圖表和文字報告
            if base_filename:
                try:
                    # 保存 HTML 圖表
                    chart_path = BACKTEST_DIR / f"{base_filename}.html"
                    bt.plot(
                        filename=str(chart_path),
                        open_browser=False
                    )
                    logger.info(f"Chart saved to: {chart_path}")
                    
                    # 保存文字報告
                    report_path = BACKTEST_DIR / f"{base_filename}.txt"
                    with open(report_path, 'w', encoding='utf-8') as f:
                        f.write(report)
                    logger.info(f"Report saved to: {report_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to save files: {e}")
                    chart_path = None
                    report_path = None
            
            logger.info(f"Backtest completed: {trade_count} trades, return: {total_return:.2f}%")
            
            # 轉換為相對路徑（從 workspace 目錄開始）
            chart_path_rel = None
            if chart_path:
                # 從絕對路徑中提取 workspace 之後的部分
                chart_path_str = str(chart_path).replace("\\", "/")
                if "workspace/" in chart_path_str:
                    chart_path_rel = chart_path_str.split("workspace/", 1)[1]
                else:
                    chart_path_rel = str(chart_path.name)
            
            report_path_rel = None
            if report_path:
                report_path_str = str(report_path).replace("\\", "/")
                if "workspace/" in report_path_str:
                    report_path_rel = report_path_str.split("workspace/", 1)[1]
                else:
                    report_path_rel = str(report_path.name)
            
            return {
                "passed": True,
                "report": report,
                "metrics": metrics,
                "chart_path": chart_path_rel,
                "report_path": report_path_rel,
                "analysis": analysis,
                "error": None,
            }
            
        except ImportError as e:
            logger.error(f"backtesting not installed: {e}")
            return {
                "passed": False,
                "report": "",
                "metrics": {},
                "chart_path": None,
                "error": "請安裝 backtesting: pip install backtesting"
            }
        except InsufficientDataError:
            # 重新抛出 InsufficientDataError，让调用方（backtest.py）处理
            raise
        except Exception as e:
            import traceback
            logger.error(f"Backtest error: {e}")
            logger.error(f"Backtest traceback: {traceback.format_exc()}")
            return {
                "passed": False,
                "report": "",
                "metrics": {},
                "chart_path": None,
                "error": f"回測過程發生錯誤: {str(e)}"
            }
    
    def _generate_analysis(self, metrics: dict, symbol: str) -> str:
        """根據回測指標生成策略分析
        
        Args:
            metrics: 回測指標字典
            symbol: 期貨代碼
            
        Returns:
            str: 格式化的分析報告
        """
        # 獲取合約乘數
        multiplier_map = {"TXF": 200, "MXF": 50, "TMF": 10}
        multiplier = multiplier_map.get(symbol, 10)
        
        total_return = metrics.get('total_return', 0)
        total_pnl = metrics.get('total_pnl', 0)
        trade_count = metrics.get('trade_count', 0)
        win_rate = metrics.get('win_rate', 0)
        max_drawdown = metrics.get('max_drawdown', 0)
        sharpe = metrics.get('sharpe_ratio', 0)
        profit_factor = metrics.get('profit_factor', 0)
        total_commission = metrics.get('total_commission', 0)
        
        # 1. 總結
        if total_pnl > 0:
            summary = f"✅ 策略在回測期間為您賺了 {total_pnl:+.0f} 元（未扣除手續費）"
        elif total_pnl == 0:
            summary = "➖ 策略在回測期間持平"
        else:
            summary = f"❌ 策略在回測期間虧損了 {total_pnl:.0f} 元"
        
        # 2. 風控評估
        risk_assessment = []
        if max_drawdown > 15:
            risk_assessment.append(f"⚠️ 最大回撤高達 {max_drawdown:.1f}%，風險較大")
        elif max_drawdown > 10:
            risk_assessment.append(f"⚡ 最大回撤 {max_drawdown:.1f}%，中等風險")
        else:
            risk_assessment.append(f"✅ 最大回撤僅 {max_drawdown:.1f}%，風險控制良好")
        
        # 3. 穩定性評估
        stability = []
        if sharpe > 1.5:
            stability.append(f"✅ 夏普比率 {sharpe:.2f}，風險調整後收益優秀")
        elif sharpe > 1.0:
            stability.append(f"⚡ 夏普比率 {sharpe:.2f}，風險調整後收益一般")
        elif sharpe > 0:
            stability.append(f"⚠️ 夏普比率 {sharpe:.2f}，風險調整後收益較差")
        else:
            stability.append(f"❌ 夏普比率 {sharpe:.2f}，策略不穩定")
        
        # 4. 交易頻率
        if trade_count == 0:
            freq_note = "⚠️ 沒有任何交易信號，可能策略條件過於嚴格"
        elif trade_count < 5:
            freq_note = f"⚠️ 交易次數僅 {trade_count} 次，可能過於保守"
        elif trade_count > 50:
            freq_note = f"⚠️ 交易次數高達 {trade_count} 次，可能過度交易"
        else:
            freq_note = f"✅ 交易次數 {trade_count} 次，頻率合理"
        
        # 5. 勝率評估
        if win_rate > 60:
            win_note = f"✅ 勝率 {win_rate:.1f}%，表現優異"
        elif win_rate > 50:
            win_note = f"⚡ 勝率 {win_rate:.1f}%，略高於一半"
        else:
            win_note = f"⚠️ 勝率 {win_rate:.1f}%，較低"
        
        # 6. 盈虧比
        if profit_factor > 1.5:
            pf_note = f"✅ 盈虧比 {profit_factor:.2f}，賺多賠少"
        elif profit_factor > 1.0:
            pf_note = f"⚡ 盈虧比 {profit_factor:.2f}，勉強持平"
        else:
            pf_note = f"❌ 盈虧比 {profit_factor:.2f}，賺少赔多"
        
        # 7. 手續費
        commission_note = f"📊 回測期間手續費合計：{total_commission:,.0f} 元"
        
        # 組裝報告
        analysis = f"""{summary}

📈 風控評估
{chr(10).join(risk_assessment)}

📊 穩定性
{chr(10).join(stability)}

🎯 交易頻率
{freq_note}

🏆 勝率
{win_note}

💰 盈虧比
{pf_note}

💸 手續費
{commission_note}

---
💡 提醒：過去表現不代表未來收益，請謹慎評估風險后再實際交易。"""
        
        return analysis
    
    def _format_report(
        self,
        class_name: str,
        symbol: str,
        timeframe: str,
        period_name: str,
        start_date: str,
        end_date: str,
        initial_capital: float,
        metrics: dict,
        stats
    ) -> str:
        """格式化回測報告
        
        Args:
            class_name: 策略類別名稱
            symbol: 期貨代碼
            timeframe: K線週期
            period_name: 期間名稱
            start_date: 開始日期
            end_date: 結束日期
            initial_capital: 初始資金
            metrics: 指標字典
            stats: backtesting.py 統計物件
            
        Returns:
            str: 格式化報告
        """
        sqn_rating = ""
        sqn = metrics.get('sqn', 0)
        if sqn >= 7:
            sqn_rating = "Holy Grail"
        elif sqn >= 5:
            sqn_rating = "Superb"
        elif sqn >= 3:
            sqn_rating = "Excellent"
        elif sqn >= 2.5:
            sqn_rating = "Good"
        elif sqn >= 2:
            sqn_rating = "Average"
        elif sqn >= 1.6:
            sqn_rating = "Below Average"
        else:
            sqn_rating = "Poor"
        
        best_trade = stats['Best Trade [%]'] if stats['Best Trade [%]'] else 0
        worst_trade = stats['Worst Trade [%]'] if stats['Worst Trade [%]'] else 0
        
        report = f"""📊 歷史回測報告 ({class_name})
══════════════════════════════════════════
📅 回測期間: {start_date} ~ {end_date} ({period_name})
📈 初始資金: {initial_capital:,.0f} NTD
─────────────────────────────────────────
💰 總損益: {metrics['total_pnl']:+,.0f} ({metrics['total_return']:+,.1f}%)
💵 最大資金回撤: {metrics['max_drawdown']:,.1f}%
📊 Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
📊 SQN: {metrics['sqn']:.2f} ({sqn_rating})
📊 交易次數: {metrics['trade_count']}
✅ 獲利交易: {metrics['won_trades']}
❌ 虧損交易: {metrics['lost_trades']}
📈 勝率: {metrics['win_rate']:.1f}%
📊 獲利因子: {metrics['profit_factor']:.2f}
📊 平均交易: {metrics['avg_trade']:+,.0f}
📊 手續費: -{metrics.get('total_commission', 0):,} 元
📊 最大單筆獲利: {best_trade:+.1f}%
📊 最大單筆虧損: {worst_trade:+.1f}%
─────────────────────────────────────────
⚠️ 過去績效不代表未來結果，僅供參考"""
        
        return report
