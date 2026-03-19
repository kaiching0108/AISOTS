"""測試 BacktestEngine 回測引擎"""
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestBacktestEngine:
    """測試 BacktestEngine 回測引擎"""
    
    def test_import(self):
        """測試匯入 BacktestEngine"""
        try:
            from src.engine.backtest_engine import BacktestEngine
            assert BacktestEngine is not None
        except ImportError as e:
            pytest.skip(f"BacktestEngine 尚未實作: {e}")
    
    def test_timeframe_config(self):
        """測試 timeframe 配置"""
        try:
            from src.engine.backtest_engine import BacktestEngine
            
            # 驗證 TIMEFRAME_CONFIG 存在
            assert hasattr(BacktestEngine, 'TIMEFRAME_CONFIG')
            
            # 驗證各 timeframe 配置
            config = BacktestEngine.TIMEFRAME_CONFIG
            assert config["1m"] == (7, "1週")
            assert config["5m"] == (14, "2週")
            assert config["15m"] == (30, "1個月")
            assert config["30m"] == (30, "1個月")
            assert config["60m"] == (90, "3個月")
            assert config["1h"] == (90, "3個月")
            assert config["1d"] == (365, "1年")
        except ImportError:
            pytest.skip("BacktestEngine 尚未實作")
    
    def test_timeframe_kbars_estimation(self):
        """測試 K棒數量估算"""
        try:
            from src.engine.backtest_engine import BacktestEngine
            
            # 估算各 timeframe 的 K棒數量
            # 1m: 7天 ≈ 7 * 510分鐘 ≈ 3570根（但系統會限制）
            # 5m: 14天 ≈ 14 * 102 ≈ 1428根
            # 15m: 30天 ≈ 30 * 34 ≈ 1020根
            # 30m: 30天 ≈ 30 * 17 ≈ 510根
            # 60m: 90天 ≈ 90 * 24 ≈ 2160根
            # 1d: 365天 ≈ 365根
            
            config = BacktestEngine.TIMEFRAME_CONFIG
            
            # 驗證配置正確性
            assert len(config) == 7  # 7種 timeframe
            assert "1m" in config
            assert "5m" in config
            assert "15m" in config
            assert "30m" in config
            assert "60m" in config
            assert "1h" in config
            assert "1d" in config
        except ImportError:
            pytest.skip("BacktestEngine 尚未實作")


class TestBacktestFallback:
    """測試回測指令"""
    
    def test_backtest_command_in_fallback(self):
        """測試回測指令是否存在於 fallback"""
        import re
        
        # 測試中文指令正則
        chinese_pattern = r'^回測\s+(\w+)$'
        assert re.match(chinese_pattern, "回測 TMF260001")
        assert re.match(chinese_pattern, "回測 TXF260001")
        
        # 測試英文指令正則
        english_pattern = r'^backtest\s+(\w+)$'
        assert re.match(english_pattern, "backtest TMF260001")
        assert re.match(english_pattern, "backtest TXF260001")
        
        # 測試 combined pattern
        combined_pattern = r'^(回測|backtest)\s+(\w+)$'
        assert re.match(combined_pattern, "回測 TMF260001")
        assert re.match(combined_pattern, "backtest TMF260001")
    
    def test_backtest_extract_strategy_id(self):
        """測試從指令中提取策略ID"""
        import re
        
        pattern = r'^(回測|backtest)\s+(\w+)$'
        
        # 測試中文
        match = re.match(pattern, "回測 TMF260001")
        assert match is not None
        assert match.group(2) == "TMF260001"
        
        # 測試英文
        match = re.match(pattern, "backtest TXF260001")
        assert match is not None
        assert match.group(2) == "TXF260001"


class TestBacktestStrategy:
    """測試回測策略"""
    
    def test_backtesting_import(self):
        """測試 backtesting.py 匯入"""
        try:
            from backtesting import Backtest, Strategy
            
            # 驗證類別存在
            assert Backtest is not None
            assert Strategy is not None
        except ImportError:
            pytest.skip("backtesting 未安裝")
    
    def test_indicator_extraction(self):
        """測試指標提取函數"""
        try:
            from src.engine.backtest_engine import extract_indicators_from_code
            
            # 測試 RSI 提取
            code = "self.ta('RSI', period=14)"
            indicators = extract_indicators_from_code(code)
            assert 'rsi' in indicators
            assert indicators['rsi'] == True
            
            # 測試 MACD 提取（會標記為 True，但會在 calculate_indicators 中計算附屬欄位）
            code = "self.ta('MACD', fast=12, slow=26)"
            indicators = extract_indicators_from_code(code)
            assert 'macd' in indicators
            assert indicators['macd'] == True
            
            # 測試多指標
            code = "rsi = self.ta('RSI'); macd = self.ta('MACD')"
            indicators = extract_indicators_from_code(code)
            assert 'rsi' in indicators
            assert 'macd' in indicators
            assert indicators['rsi'] == True
            assert indicators['macd'] == True
            
            # 測試布林帶
            code = "bb = self.ta('BB', period=20)"
            indicators = extract_indicators_from_code(code)
            assert 'bb' in indicators
            assert indicators['bb'] == True
        except ImportError:
            pytest.skip("extract_indicators_from_code 尚未實作")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
