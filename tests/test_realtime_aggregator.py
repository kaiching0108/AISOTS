"""实时 K-bar 聚合器单元测试"""
import pytest
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.realtime_kbar_aggregator import RealtimeKBarAggregator


class TestRealtimeKBarAggregator:
    """测试实时 K-bar 聚合器"""
    
    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return RealtimeKBarAggregator()
    
    def test_process_tick_initial(self, aggregator):
        """4.1 测试初始 tick 处理"""
        ts = datetime(2026, 3, 3, 9, 0, 0)
        
        result = aggregator.process_tick('TXF', 100.0, 10, ts)
        
        assert result is None  # 未形成完整 K-bar
        
        bar = aggregator.get_current_bar('TXF')
        assert bar is not None
        assert bar['open'] == 100.0
        assert bar['close'] == 100.0
        assert bar['volume'] == 10
    
    def test_process_tick_same_minute(self, aggregator):
        """4.2 测试同一分钟内 tick 聚合"""
        ts = datetime(2026, 3, 3, 9, 0, 0)
        
        aggregator.process_tick('TXF', 100.0, 10, ts)
        aggregator.process_tick('TXF', 101.0, 20, ts)
        aggregator.process_tick('TXF', 99.0, 30, ts)
        
        bar = aggregator.get_current_bar('TXF')
        
        assert bar['open'] == 100.0
        assert bar['high'] == 101.0
        assert bar['low'] == 99.0
        assert bar['close'] == 99.0
        assert bar['volume'] == 60  # 10 + 20 + 30
    
    def test_process_tick_new_minute_generates_bar(self, aggregator):
        """4.3 测试跨分钟生成新 K-bar"""
        ts1 = datetime(2026, 3, 3, 9, 0, 0)
        ts2 = datetime(2026, 3, 3, 9, 1, 0)  # 新的一分钟
        
        aggregator.process_tick('TXF', 100.0, 10, ts1)
        result = aggregator.process_tick('TXF', 102.0, 20, ts2)
        
        assert result is not None  # 生成了新的 K-bar
        assert result['ts'] == int(ts1.timestamp())
        assert result['open'] == 100.0
        assert result['high'] == 100.0
        assert result['low'] == 100.0
        assert result['close'] == 100.0
        assert result['volume'] == 10
        
        bar = aggregator.get_current_bar('TXF')
        assert bar['ts'] == int(ts2.timestamp())
        assert bar['open'] == 102.0
    
    def test_process_tick_multiple_symbols(self, aggregator):
        """4.4 测试多 symbol 独立处理"""
        ts = datetime(2026, 3, 3, 9, 0, 0)
        
        aggregator.process_tick('TXF', 100.0, 10, ts)
        aggregator.process_tick('MXF', 200.0, 20, ts)
        
        txf_bar = aggregator.get_current_bar('TXF')
        mxf_bar = aggregator.get_current_bar('MXF')
        
        assert txf_bar['open'] == 100.0
        assert mxf_bar['open'] == 200.0
    
    def test_get_1m_bars(self, aggregator):
        """4.5 测试获取 1m K-bar 列表"""
        ts1 = datetime(2026, 3, 3, 9, 0, 0)
        ts2 = datetime(2026, 3, 3, 9, 1, 0)
        ts3 = datetime(2026, 3, 3, 9, 2, 0)
        ts4 = datetime(2026, 3, 3, 9, 3, 0)  # 添加第四个时间点触发第三根完成
        
        aggregator.process_tick('TXF', 100.0, 10, ts1)
        aggregator.process_tick('TXF', 101.0, 10, ts2)
        aggregator.process_tick('TXF', 102.0, 10, ts3)
        aggregator.process_tick('TXF', 103.0, 10, ts4)  # 触发第三根完成
        
        bars = aggregator.get_1m_bars('TXF', count=10)
        
        assert len(bars) == 3
    
    def test_convert_to_5m(self, aggregator):
        """4.6 测试转换为 5m"""
        for i in range(10):
            ts = datetime(2026, 3, 3, 9, i, 0)
            aggregator.process_tick('TXF', 100.0 + i, 10, ts)
        
        bars_5m = aggregator.convert_to_timeframe('TXF', '5m', count=10)
        
        assert len(bars_5m) == 2
    
    def test_convert_to_15m(self, aggregator):
        """4.7 测试转换为 15m"""
        for i in range(20):
            ts = datetime(2026, 3, 3, 9, i, 0)
            aggregator.process_tick('TXF', 100.0 + i, 10, ts)
        
        bars_15m = aggregator.convert_to_timeframe('TXF', '15m', count=10)
        
        assert len(bars_15m) == 2
    
    def test_convert_to_1h(self, aggregator):
        """4.8 测试转换为 1h"""
        # 产生 70 分钟的数据（超过 1 小时）
        for i in range(70):
            hour = 9 + (i // 60)  # 超过 60 分钟后小时递增
            minute = i % 60
            ts = datetime(2026, 3, 3, hour, minute, 0)
            aggregator.process_tick('TXF', 100.0 + i, 10, ts)
        
        bars_1h = aggregator.convert_to_timeframe('TXF', '1h', count=10)
        
        assert len(bars_1h) == 2
    
    def test_get_current_bar_none(self, aggregator):
        """4.9 测试获取不存在的 current bar"""
        bar = aggregator.get_current_bar('TXF')
        assert bar is None
    
    def test_clear_symbol(self, aggregator):
        """4.10 测试清除指定 symbol 数据"""
        ts = datetime(2026, 3, 3, 9, 0, 0)
        
        aggregator.process_tick('TXF', 100.0, 10, ts)
        assert aggregator.get_current_bar('TXF') is not None
        
        aggregator.clear('TXF')
        assert aggregator.get_current_bar('TXF') is None
    
    def test_clear_all(self, aggregator):
        """4.11 测试清除所有数据"""
        ts = datetime(2026, 3, 3, 9, 0, 0)
        
        aggregator.process_tick('TXF', 100.0, 10, ts)
        aggregator.process_tick('MXF', 200.0, 20, ts)
        
        aggregator.clear()
        
        assert aggregator.get_current_bar('TXF') is None
        assert aggregator.get_current_bar('MXF') is None
    
    def test_callback_on_new_bar(self, aggregator):
        """4.12 测试新 K-bar 生成回调"""
        callback_results = []
        
        def callback(symbol, bar):
            callback_results.append((symbol, bar))
        
        agg = RealtimeKBarAggregator(on_kbar_callback=callback)
        
        ts1 = datetime(2026, 3, 3, 9, 0, 0)
        ts2 = datetime(2026, 3, 3, 9, 1, 0)
        
        agg.process_tick('TXF', 100.0, 10, ts1)
        agg.process_tick('TXF', 102.0, 20, ts2)
        
        assert len(callback_results) == 1
        assert callback_results[0][0] == 'TXF'
        assert callback_results[0][1]['close'] == 100.0
    
    def test_bars_limit(self, aggregator):
        """4.13 测试 K-bar 列表限制"""
        for i in range(1005):
            ts = datetime(2026, 3, 3, 9, i % 60, 0)
            aggregator.process_tick('TXF', 100.0 + i, 10, ts)
        
        bars = aggregator.get_1m_bars('TXF', count=2000)
        
        assert len(bars) == 1000  # 限制最多 1000 条


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
