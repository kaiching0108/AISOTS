"""BacktestEngine - backtesting.py 歷史回測引擎"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import pandas_ta as ta

from loguru import logger


def extract_indicators_from_code(code: str) -> Dict[str, bool]:
    """從策略代碼中提取需要計算的指標
    
    Args:
        code: 策略程式碼
        
    Returns:
        Dict: 需要計算的指標字典
    """
    indicators = {
        'rsi': False,
        'macd': False,
        'sma': False,
        'ema': False,
        'bb': False,
        'atr': False,
        'adx': False,
        'stoch': False,
        'cci': False,
    }
    
    code_upper = code.upper()
    
    if 'RSI' in code_upper:
        indicators['rsi'] = True
    
    if 'MACD' in code_upper:
        indicators['macd'] = True
    
    if re.search(r'SMA|均線', code, re.IGNORECASE):
        indicators['sma'] = True
    
    if 'EMA' in code_upper:
        indicators['ema'] = True
    
    if re.search(r'BB|BOLL|布林', code, re.IGNORECASE):
        indicators['bb'] = True
    
    if 'ATR' in code_upper:
        indicators['atr'] = True
    
    if 'ADX' in code_upper:
        indicators['adx'] = True
    
    if re.search(r'STOCH|KD', code, re.IGNORECASE):
        indicators['stoch'] = True
    
    if 'CCI' in code_upper:
        indicators['cci'] = True
    
    return indicators


def calculate_indicators(df: pd.DataFrame, indicators: Dict[str, bool]) -> pd.DataFrame:
    """根據指標需求計算指標
    
    Args:
        df: 包含 OHLCV 的 DataFrame
        indicators: 需要計算的指標字典
        
    Returns:
        DataFrame: 包含計算後指標的 DataFrame
    """
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']
    
    if indicators.get('rsi'):
        df['rsi'] = ta.rsi(close, length=14)
    
    if indicators.get('macd'):
        macd = ta.macd(close)
        if macd is not None:
            df['macd'] = macd['MACD_12_26_9']
            df['macd_signal'] = macd['MACDs_12_26_9']
            df['macd_hist'] = macd['MACDh_12_26_9']
    
    if indicators.get('sma'):
        df['sma20'] = ta.sma(close, length=20)
        df['sma30'] = ta.sma(close, length=30)
        df['sma60'] = ta.sma(close, length=60)
    
    if indicators.get('ema'):
        df['ema20'] = ta.ema(close, length=20)
        df['ema30'] = ta.ema(close, length=30)
        df['ema60'] = ta.ema(close, length=60)
    
    if indicators.get('bb'):
        bbands = ta.bbands(close, length=20)
        if bbands is not None:
            df['bb_upper'] = bbands['BBU_20_2.0']
            df['bb_mid'] = bbands['BBM_20_2.0']
            df['bb_lower'] = bbands['BBL_20_2.0']
    
    if indicators.get('atr'):
        df['atr'] = ta.atr(high, low, close, length=14)
    
    if indicators.get('adx'):
        df['adx'] = ta.adx(high, low, close, length=14)
    
    if indicators.get('stoch'):
        stoch = ta.stoch(high, low, close)
        if stoch is not None:
            df['stoch_k'] = stoch['STOCHk_14_3_3']
            df['stoch_d'] = stoch['STOCHd_14_3_3']
    
    if indicators.get('cci'):
        df['cci'] = ta.cci(high, low, close, length=20)
    
    return df


class BacktestEngine:
    """backtesting.py 回測引擎"""
    
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
    
    def _get_timeframe_params(self, timeframe: str) -> tuple:
        """取得 timeframe 對應的參數
        
        Args:
            timeframe: K線週期
            
        Returns:
            tuple: (天數, 說明)
        """
        return self.TIMEFRAME_CONFIG.get(timeframe, (30, "1個月"))
    
    def _create_strategy_class(self, strategy_code: str, indicators_dict: Dict[str, pd.Series]):
        """根據策略代碼和指標創建 backtesting.py 策略類別
        
        Args:
            strategy_code: 策略程式碼
            indicators_dict: 指標字典
            
        Returns:
            Strategy class
        """
        from backtesting import Strategy
        
        # 提取關鍵邏輯
        has_rsi = indicators_dict.get('rsi') is not None
        has_macd = indicators_dict.get('macd') is not None
        has_sma = indicators_dict.get('sma20') is not None
        has_bb = indicators_dict.get('bb_upper') is not None
        
        # 根據策略代碼判斷訊號邏輯
        code_lower = strategy_code.lower()
        
        class GeneratedStrategy(Strategy):
            def init(self):
                # 綁定預先計算的指標
                if has_rsi:
                    self.rsi = self.I(lambda: indicators_dict['rsi'])
                if has_macd:
                    self.macd = self.I(lambda: indicators_dict['macd'])
                    self.macd_signal = self.I(lambda: indicators_dict['macd_signal'])
                if has_sma:
                    self.sma20 = self.I(lambda: indicators_dict['sma20'])
                    self.sma30 = self.I(lambda: indicators_dict['sma30'])
                    self.sma60 = self.I(lambda: indicators_dict['sma60'])
                if has_bb:
                    self.bb_upper = self.I(lambda: indicators_dict['bb_upper'])
                    self.bb_mid = self.I(lambda: indicators_dict['bb_mid'])
                    self.bb_lower = self.I(lambda: indicators_dict['bb_lower'])
            
            def next(self):
                # 根據策略代碼中的邏輯生成訊號
                position = 0
                if self.position:
                    position = 1 if self.position.size > 0 else -1
                
                signal = self._generate_signal(position)
                
                if signal == 'buy' and position == 0:
                    self.buy()
                elif signal == 'sell' and position == 0:
                    self.sell()
                elif signal == 'close' and position != 0:
                    self.position.close()
        
        #訊 添加號生成邏輯
        def generate_signal(self, position):
            # RSI 策略邏輯
            if has_rsi and hasattr(self, 'rsi'):
                rsi_val = self.rsi[-1]
                if pd.notna(rsi_val):
                    if rsi_val < 30 and position == 0:
                        return 'buy'
                    elif rsi_val > 70 and position > 0:
                        return 'close'
            
            # MACD 策略邏輯
            if has_macd and hasattr(self, 'macd') and hasattr(self, 'macd_signal'):
                macd_val = self.macd[-1]
                signal_val = self.macd_signal[-1]
                if pd.notna(macd_val) and pd.notna(signal_val):
                    # 金叉
                    if macd_val > signal_val and position == 0:
                        return 'buy'
                    # 死叉
                    elif macd_val < signal_val and position > 0:
                        return 'close'
            
            # SMA 策略邏輯
            if has_sma and hasattr(self, 'sma20') and hasattr(self, 'sma60'):
                sma20 = self.sma20[-1]
                sma60 = self.sma60[-1]
                if pd.notna(sma20) and pd.notna(sma60):
                    if sma20 > sma60 and position == 0:
                        return 'buy'
                    elif sma20 < sma60 and position > 0:
                        return 'close'
            
            # 布林帶策略邏輯
            if has_bb and hasattr(self, 'bb_lower') and hasattr(self, 'bb_upper'):
                close_price = self.data.Close[-1]
                bb_lower = self.bb_lower[-1]
                bb_upper = self.bb_upper[-1]
                if pd.notna(bb_lower) and pd.notna(bb_upper):
                    if close_price < bb_lower and position == 0:
                        return 'buy'
                    elif close_price > bb_upper and position > 0:
                        return 'close'
            
            return 'hold'
        
        GeneratedStrategy._generate_signal = generate_signal
        
        return GeneratedStrategy
    
    async def run_backtest(
        self,
        strategy_code: str,
        class_name: str,
        symbol: str,
        timeframe: str = "15m",
        initial_capital: float = 1_000_000,
        commission: float = 0  # 固定手續費另行計算
    ) -> dict:
        """執行歷史回測
        
        Args:
            strategy_code: 策略程式碼
            class_name: 策略類別名稱
            symbol: 期貨代碼
            timeframe: K線週期
            initial_capital: 初始資金
            commission: 已廢棄，請使用固定手續費
            
        Returns:
            dict: {
                "passed": bool,
                "report": str,
                "metrics": {...},
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
            
            kbars_data = self.client.get_kbars(
                contract, 
                timeframe, 
                count=days * 500
            )
            
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
            
            indicators_requested = extract_indicators_from_code(strategy_code)
            df = calculate_indicators(df, indicators_requested)
            
            # 準備指標字典
            indicators_dict = {}
            if indicators_requested.get('rsi') and 'rsi' in df.columns:
                indicators_dict['rsi'] = df['rsi'].values
            if indicators_requested.get('macd'):
                indicators_dict['macd'] = df['macd'].values if 'macd' in df.columns else df['Close'].values
                indicators_dict['macd_signal'] = df['macd_signal'].values if 'macd_signal' in df.columns else df['Close'].values
            if indicators_requested.get('sma'):
                indicators_dict['sma20'] = df['sma20'].values if 'sma20' in df.columns else df['Close'].values
                indicators_dict['sma30'] = df['sma30'].values if 'sma30' in df.columns else df['Close'].values
                indicators_dict['sma60'] = df['sma60'].values if 'sma60' in df.columns else df['Close'].values
            if indicators_requested.get('bb'):
                indicators_dict['bb_upper'] = df['bb_upper'].values if 'bb_upper' in df.columns else df['Close'].values
                indicators_dict['bb_mid'] = df['bb_mid'].values if 'bb_mid' in df.columns else df['Close'].values
                indicators_dict['bb_lower'] = df['bb_lower'].values if 'bb_lower' in df.columns else df['Close'].values
            
            strategy_class = self._create_strategy_class(strategy_code, indicators_dict)
            
            bt = Backtest(
                df, 
                strategy_class,
                cash=initial_capital,
                commission=commission,
                exclusive_orders=True
            )
            
            stats = bt.run()
            
            total_return = stats['Return [%]'] if stats['Return [%]'] else 0
            sharpe = stats['Sharpe Ratio'] if stats['Sharpe Ratio'] else 0
            max_dd = stats['Max. Drawdown [%]'] if stats['Max. Drawdown [%]'] else 0
            trade_count = stats['# Trades'] if stats['# Trades'] else 0
            win_rate = stats['Win Rate [%]'] if stats['Win Rate [%]'] else 0
            
            # 計算總損益（乘以合約乘數）
            total_pnl = initial_capital * total_return / 100 * contract_multiplier
            
            # 計算固定手續費（大台/小台/微台）
            fixed_commission_map = {
                "TXF": 40,  # 大台
                "MXF": 20,  # 小台
                "TMF": 14,  # 微台
            }
            commission_per_trade = fixed_commission_map.get(symbol, 0)
            total_commission = trade_count * 2 * commission_per_trade  # 開倉+平倉
            
            # 淨損益 = 總損益 - 手續費
            net_pnl = total_pnl - total_commission
            
            sqn = 0
            if trade_count > 0 and stats['Avg. Trade [%]']:
                avg_trade_pct = stats['Avg. Trade [%]']
                if stats['Std. Trade [%)']:
                    std_trade = stats['Std. Trade [%)']
                    if std_trade > 0:
                        sqn = (avg_trade_pct / std_trade) * (trade_count ** 0.5)
            
            won_trades = int(trade_count * win_rate / 100) if trade_count > 0 else 0
            lost_trades = trade_count - won_trades
            
            profit_factor = 0.0
            if won_trades > 0 and lost_trades > 0:
                avg_win = total_pnl / won_trades if won_trades > 0 else 0
                avg_loss = abs(total_pnl / lost_trades) if lost_trades > 0 else 1
                profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
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
            
            logger.info(f"Backtest completed: {trade_count} trades, return: {total_return:.2f}%")
            
            return {
                "passed": True,
                "report": report,
                "metrics": metrics,
                "error": None,
            }
            
        except ImportError as e:
            logger.error(f"backtesting not installed: {e}")
            return {
                "passed": False,
                "report": "",
                "metrics": {},
                "error": "請安裝 backtesting: pip install backtesting"
            }
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {
                "passed": False,
                "report": "",
                "metrics": {},
                "error": f"回測過程發生錯誤: {str(e)}"
            }
    
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
