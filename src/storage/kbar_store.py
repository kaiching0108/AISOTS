"""K棒數據持久化存儲模組"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from loguru import logger


class KBarStore:
    """K棒數據持久化存儲"""
    
    # 各 timeframe 建議抓取數量
    RECOMMENDED_COUNTS = {
        "1m": 3000,
        "5m": 1000,
        "15m": 800,
        "30m": 500,
        "1h": 1500,
        "1d": 300,
    }
    
    # 最大存儲上限
    MAX_BARS = 10000
    
    def __init__(self, workspace_dir: Path):
        self.workspace = workspace_dir
        self.kbars_dir = workspace_dir / "kbars"
        self.kbars_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, symbol: str, timeframe: str) -> Path:
        """獲取緩存文件路徑"""
        return self.kbars_dir / symbol / f"{timeframe}.json"
    
    def load(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """從本地加載K棒數據
        
        Args:
            symbol: 期貨代碼（如 TXF、MXF、TMF）
            timeframe: 時間週期（如 1m、15m、1h、1d）
            
        Returns:
            緩存數據字典，若不存在則返回 None
        """
        path = self.get_cache_path(symbol, timeframe)
        
        if not path.exists():
            logger.debug(f"K棒緩存不存在: {symbol}/{timeframe}")
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            if not cached or not cached.get('data'):
                logger.warning(f"K棒緩存為空: {symbol}/{timeframe}")
                return None
            
            logger.info(
                f"載入K棒緩存: {symbol}/{timeframe}, "
                f"共 {len(cached['data'])} 根, "
                f"更新於 {cached.get('last_updated', 'unknown')}"
            )
            return cached
            
        except json.JSONDecodeError as e:
            logger.error(f"K棒緩存JSON解析失敗: {path}, error: {e}")
            return None
        except Exception as e:
            logger.error(f"載入K棒緩存失敗: {path}, error: {e}")
            return None
    
    def save(self, symbol: str, timeframe: str, kbars_data: Dict) -> bool:
        """保存K棒數據到本地（完全覆蓋）
        
        Args:
            symbol: 期貨代碼
            timeframe: 時間週期
            kbars_data: K棒數據字典，必須包含 ts, open, high, low, close, volume
            
        Returns:
            是否保存成功
        """
        try:
            # 轉換為內部格式
            data = self._convert_to_internal_format(kbars_data)
            
            # 裁剪超過 MAX_BARS（取最新的）
            if len(data) > self.MAX_BARS:
                data = data[-self.MAX_BARS:]
                logger.info(f"K棒數據裁剪至 {self.MAX_BARS} 根")
            
            cache = {
                "symbol": symbol,
                "timeframe": timeframe,
                "last_updated": datetime.now().isoformat(),
                "max_bars": self.MAX_BARS,
                "data": data
            }
            
            # 寫入文件
            path = self.get_cache_path(symbol, timeframe)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            
            logger.info(
                f"K棒緩存保存成功: {symbol}/{timeframe}, "
                f"共 {len(data)} 根"
            )
            return True
            
        except Exception as e:
            logger.error(f"保存K棒緩存失敗: {symbol}/{timeframe}, error: {e}")
            return False
    
    def delete(self, symbol: str, timeframe: Optional[str] = None) -> bool:
        """刪除K棒緩存
        
        Args:
            symbol: 期貨代碼
            timeframe: 時間週期，若為 None 則刪除該標的所有緩存
            
        Returns:
            是否刪除成功
        """
        try:
            if timeframe:
                path = self.get_cache_path(symbol, timeframe)
                if path.exists():
                    path.unlink()
                    logger.info(f"刪除K棒緩存: {symbol}/{timeframe}")
            else:
                symbol_dir = self.kbars_dir / symbol
                if symbol_dir.exists():
                    import shutil
                    shutil.rmtree(symbol_dir)
                    logger.info(f"刪除K棒緩存目錄: {symbol}")
            
            return True
        except Exception as e:
            logger.error(f"刪除K棒緩存失敗: {symbol}/{timeframe}, error: {e}")
            return False
    
    def get_status(self) -> Dict:
        """獲取所有標的緩存狀態
        
        Returns:
            緩存狀態字典
        """
        status = {
            "total_symbols": 0,
            "total_timeframes": 0,
            "symbols": {}
        }
        
        if not self.kbars_dir.exists():
            return status
        
        for symbol_dir in self.kbars_dir.iterdir():
            if not symbol_dir.is_dir():
                continue
            
            symbol = symbol_dir.name
            status["total_symbols"] += 1
            status["symbols"][symbol] = {}
            
            for cache_file in symbol_dir.glob("*.json"):
                timeframe = cache_file.stem
                cached = self.load(symbol, timeframe)
                
                if cached:
                    data_count = len(cached.get('data', []))
                    last_updated = cached.get('last_updated', 'unknown')
                    status["symbols"][symbol][timeframe] = {
                        "count": data_count,
                        "last_updated": last_updated
                    }
                    status["total_timeframes"] += 1
        
        return status
    
    def exists(self, symbol: str, timeframe: str) -> bool:
        """檢查緩存是否存在
        
        Args:
            symbol: 期貨代碼
            timeframe: 時間週期
            
        Returns:
            緩存是否存在
        """
        return self.get_cache_path(symbol, timeframe).exists()
    
    def _convert_to_internal_format(self, kbars_data: Dict) -> List[Dict]:
        """將 KBar API 數據轉換為內部存儲格式
        
        Args:
            kbars_data: K棒數據字典，包含 ts, open, high, low, close, volume
            
        Returns:
            內部格式的 K棒列表
        """
        data = []
        timestamps = kbars_data.get('ts', [])
        opens = kbars_data.get('open', [])
        highs = kbars_data.get('high', [])
        lows = kbars_data.get('low', [])
        closes = kbars_data.get('close', [])
        volumes = kbars_data.get('volume', [])
        
        for i in range(len(timestamps)):
            ts = timestamps[i]
            
            # 將 timestamp 轉換為可讀字符串
            try:
                ts_dt = datetime.utcfromtimestamp(ts)
                ts_str = ts_dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                ts_str = str(ts)
            
            data.append({
                "ts": ts,
                "ts_str": ts_str,
                "open": float(opens[i]) if i < len(opens) else 0,
                "high": float(highs[i]) if i < len(highs) else 0,
                "low": float(lows[i]) if i < len(lows) else 0,
                "close": float(closes[i]) if i < len(closes) else 0,
                "volume": float(volumes[i]) if i < len(volumes) else 0,
            })
        
        return data
    
    def convert_to_kbars_format(self, data: List[Dict]) -> Dict:
        """將內部格式轉換為 KBar API 格式
        
        Args:
            data: 內部格式的 K棒列表
            
        Returns:
            KBar API 格式的字典
        """
        return {
            "ts": [bar["ts"] for bar in data],
            "open": [bar["open"] for bar in data],
            "high": [bar["high"] for bar in data],
            "low": [bar["low"] for bar in data],
            "close": [bar["close"] for bar in data],
            "volume": [bar["volume"] for bar in data],
        }
