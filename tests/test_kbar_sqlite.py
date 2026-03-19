"""KBarSQLite 单元测试"""
import pytest
import tempfile
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.kbar_sqlite import KBarSQLite


class TestKBarSQLite:
    """测试 SQLite 存储模块"""
    
    @pytest.fixture
    def db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
            db_path = Path(f.name)
            db = KBarSQLite(db_path)
            yield db
            if db_path.exists():
                os.unlink(str(db_path))
    
    def test_insert_kbars(self, db):
        """1.1 测试插入 K棒数据"""
        data = {
            'ts': [1700000000, 1700000060, 1700000120],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000.0, 1500.0, 2000.0],
        }
        count = db.insert_kbars('TXF', data)
        assert count == 3
    
    def test_insert_duplicate_ignored(self, db):
        """1.2 测试重复插入被忽略"""
        data = {
            'ts': [1700000000, 1700000060],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000.0, 1500.0],
        }
        count1 = db.insert_kbars('TXF', data)
        assert count1 == 2
        
        count2 = db.insert_kbars('TXF', data)
        assert count2 == 0  # 重复数据不重复插入
    
    def test_get_count(self, db):
        """1.3 测试获取指定 symbol 数量"""
        data = {
            'ts': [1700000000, 1700000060, 1700000120],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000.0, 1500.0, 2000.0],
        }
        db.insert_kbars('TXF', data)
        
        assert db.get_count('TXF') == 3
        assert db.get_count('MXF') == 0
    
    def test_get_total_count(self, db):
        """1.4 测试获取所有 symbol 总数量"""
        data1 = {
            'ts': [1700000000, 1700000060],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000.0, 1500.0],
        }
        data2 = {
            'ts': [1700000100, 1700000160],
            'open': [200.0, 201.0],
            'high': [202.0, 203.0],
            'low': [199.0, 200.0],
            'close': [201.0, 202.0],
            'volume': [3000.0, 3500.0],
        }
        db.insert_kbars('TXF', data1)
        db.insert_kbars('MXF', data2)
        
        assert db.get_total_count() == 4
    
    def test_get_kbars(self, db):
        """1.5 测试查询 K棒数据"""
        data = {
            'ts': [1700000000, 1700000060, 1700000120],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000.0, 1500.0, 2000.0],
        }
        db.insert_kbars('TXF', data)
        
        result = db.get_kbars('TXF', 0, 1700000200)
        
        assert len(result) == 3
        assert result[0]['ts'] == 1700000000
        assert result[0]['open'] == 100.0
        assert result[0]['close'] == 101.0
    
    def test_get_latest_kbar(self, db):
        """1.6 测试获取最新 K棒"""
        data = {
            'ts': [1700000000, 1700000060, 1700000120],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000.0, 1500.0, 2000.0],
        }
        db.insert_kbars('TXF', data)
        
        latest = db.get_latest_kbar('TXF')
        
        assert latest is not None
        assert latest['ts'] == 1700000120
        assert latest['close'] == 103.0
    
    def test_get_oldest_kbar(self, db):
        """1.7 测试获取最旧 K棒"""
        data = {
            'ts': [1700000000, 1700000060, 1700000120],
            'open': [100.0, 101.0, 102.0],
            'high': [102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0],
            'close': [101.0, 102.0, 103.0],
            'volume': [1000.0, 1500.0, 2000.0],
        }
        db.insert_kbars('TXF', data)
        
        oldest = db.get_oldest_kbar('TXF')
        
        assert oldest is not None
        assert oldest['ts'] == 1700000000
        assert oldest['open'] == 100.0
    
    def test_convert_1m_to_5m(self, db):
        """1.8 测试 1m 转换为 5m"""
        now = datetime(2026, 3, 3, 9, 0, 0)
        
        ts_list = []
        for i in range(10):
            ts_list.append(int((now + timedelta(minutes=i)).timestamp()))
        
        data = {
            'ts': ts_list,
            'open': [100.0 + i for i in range(10)],
            'high': [102.0 + i for i in range(10)],
            'low': [99.0 + i for i in range(10)],
            'close': [101.0 + i for i in range(10)],
            'volume': [1000.0 + i * 100 for i in range(10)],
        }
        db.insert_kbars('TXF', data)
        
        result = db.convert_1m_to_timeframe('TXF', '5m')
        
        # 10分钟数据，5分钟一段 = 2段 (09:00-09:04, 09:05-09:09)
        assert len(result['ts']) == 2
        # 转换为 Python int 进行比较
        assert int(result['ts'][0]) == ts_list[0]
        assert int(result['ts'][1]) == ts_list[5]
    
    def test_convert_1m_to_15m(self, db):
        """1.9 测试 1m 转换为 15m"""
        now = datetime(2026, 3, 3, 9, 0, 0)
        
        ts_list = []
        for i in range(20):
            ts_list.append(int((now + timedelta(minutes=i)).timestamp()))
        
        data = {
            'ts': ts_list,
            'open': [100.0 + i for i in range(20)],
            'high': [102.0 + i for i in range(20)],
            'low': [99.0 + i for i in range(20)],
            'close': [101.0 + i for i in range(20)],
            'volume': [1000.0 + i * 100 for i in range(20)],
        }
        db.insert_kbars('TXF', data)
        
        result = db.convert_1m_to_timeframe('TXF', '15m')
        
        # 20分钟数据，15分钟一段 = 2段 (09:00-09:14, 09:15-09:19)
        assert len(result['ts']) == 2
    
    def test_get_kbars_with_conversion(self, db):
        """1.10 测试带转换的 K棒查询"""
        now = datetime(2026, 3, 3, 9, 0, 0)
        
        ts_list = []
        for i in range(20):
            ts_list.append(int((now + timedelta(minutes=i)).timestamp()))
        
        data = {
            'ts': ts_list,
            'open': [100.0 + i for i in range(20)],
            'high': [102.0 + i for i in range(20)],
            'low': [99.0 + i for i in range(20)],
            'close': [101.0 + i for i in range(20)],
            'volume': [1000.0 + i * 100 for i in range(20)],
        }
        db.insert_kbars('TXF', data)
        
        result = db.get_kbars_with_conversion('TXF', 0, 9999999999, '5m')
        
        # 20分钟数据，5分钟一段 = 4段
        assert len(result['ts']) == 4
        assert int(result['ts'][0]) == ts_list[0]
        assert int(result['ts'][1]) == ts_list[5]
        assert int(result['ts'][2]) == ts_list[10]
        assert int(result['ts'][3]) == ts_list[15]
    
    def test_get_today_count(self, db):
        """1.11 测试今日抓取统计（指定 symbol）"""
        data = {
            'ts': [1700000000, 1700000060],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000.0, 1500.0],
        }
        db.insert_kbars('TXF', data)
        
        count = db.get_today_count('TXF')
        
        assert count == 2
    
    def test_get_total_today_count(self, db):
        """1.12 测试所有 symbol 今日合计"""
        data1 = {
            'ts': [1700000000],
            'open': [100.0],
            'high': [102.0],
            'low': [99.0],
            'close': [101.0],
            'volume': [1000.0],
        }
        data2 = {
            'ts': [1700000100],
            'open': [200.0],
            'high': [202.0],
            'low': [199.0],
            'close': [201.0],
            'volume': [3000.0],
        }
        db.insert_kbars('TXF', data1)
        db.insert_kbars('MXF', data2)
        
        count = db.get_total_today_count()
        
        assert count == 2
    
    def test_delete_all(self, db):
        """1.13 测试删除数据"""
        data = {
            'ts': [1700000000, 1700000060],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000.0, 1500.0],
        }
        db.insert_kbars('TXF', data)
        assert db.get_count('TXF') == 2
        
        db.delete_all('TXF')
        assert db.get_count('TXF') == 0
    
    def test_get_status(self, db):
        """1.14 测试获取状态"""
        data = {
            'ts': [1700000000, 1700000060],
            'open': [100.0, 101.0],
            'high': [102.0, 103.0],
            'low': [99.0, 100.0],
            'close': [101.0, 102.0],
            'volume': [1000.0, 1500.0],
        }
        db.insert_kbars('TXF', data)
        
        status = db.get_status()
        
        assert status['total_count'] == 2
        assert 'TXF' in status['symbols']
        assert status['symbols']['TXF']['count'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
