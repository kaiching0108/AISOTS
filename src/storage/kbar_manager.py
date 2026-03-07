"""K棒數據管理器模組 - 負責定期更新和緩存管理"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from loguru import logger

from src.storage.kbar_store import KBarStore


class KBarManager:
    """K棒數據管理器 - 負責定期更新和緩存管理"""
    
    # 刷新間隔（天）
    REFRESH_INTERVAL_DAYS = 90
    
    # 支持的期貨標的
    SUPPORTED_SYMBOLS = ["TXF", "MXF", "TMF"]
    
    def __init__(self, client: Any, workspace_dir: Path):
        """初始化K棒管理器
        
        Args:
            client: ShioajiClient 實例
            workspace_dir: 工作目錄路徑
        """
        self.client = client
        self.workspace_dir = workspace_dir
        self.store = KBarStore(workspace_dir)
        logger.info("KBarManager 初始化完成")
    
    async def refresh(self, symbol: str) -> Dict:
        """刷新指定標的的所有時間週期K棒數據
        
        Args:
            symbol: 期貨代碼（如 TXF、MXF、TMF）
            
        Returns:
            刷新結果字典
        """
        if symbol not in self.SUPPORTED_SYMBOLS:
            logger.warning(f"不支持的期貨標的: {symbol}")
            return {"success": False, "error": f"不支持的標的: {symbol}"}
        
        logger.info(f"開始刷新 K棒數據: {symbol}")
        
        results = {}
        
        for timeframe, count in KBarStore.RECOMMENDED_COUNTS.items():
            try:
                # 獲取合約
                contract = self.client.get_contract(symbol)
                if not contract:
                    logger.error(f"無法獲取合約: {symbol}")
                    results[timeframe] = {"success": False, "error": "無法獲取合約"}
                    continue
                
                # 調用 API 獲取 K 棒數據（1m）
                kbars_data = self.client.get_kbars(contract, timeframe, count)
                
                if not kbars_data:
                    logger.warning(f"無法獲取 K 棒數據：{symbol}/{timeframe}")
                    results[timeframe] = {"success": False, "error": "API 返回空數據"}
                    continue
                
                # 轉換時間週期（1d、5m、15m 等需要转换，因為 API 只給回 1m）
                if timeframe != '1m':
                    import pandas as pd
                    minutes = {'5m': 5, '15m': 15, '30m': 30, '1h': 60, '1d': 1440}[timeframe]
                    df = pd.DataFrame(kbars_data)
                    # API 的 ts_str 是納秒，轉為秒後計算
                    ts_sec = [ts / 1e9 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts) for ts in kbars_data['ts']]
                    df['datetime'] = pd.to_datetime(ts_sec, unit='s')
                    df.set_index('datetime', inplace=True)
                    resampled = df.resample(f'{minutes}min', label='right', closed='right').agg({
                        'open': 'first', 'high': 'max', 'low': 'min',
                        'close': 'last', 'volume': 'sum',
                    }).dropna()
                    kbars_data = {
                        'ts': [int(t.timestamp()) for t in resampled.index],
                        'open': list(resampled['open'].values),
                        'high': list(resampled['high'].values),
                        'low': list(resampled['low'].values),
                        'close': list(resampled['close'].values),
                        'volume': list(resampled['volume'].values),
                    }
                
                # 保存到本地緩存
                success = self.store.save(symbol, timeframe, kbars_data)
                
                if success:
                    bar_count = len(kbars_data.get('close', []))
                    results[timeframe] = {"success": True, "bars": bar_count}
                    if timeframe == '1d':
                        logger.info(f"K 棒數據 [1d]: {symbol}/{timeframe}, {bar_count} 根")
                    elif timeframe in ['5m', '15m', '30m', '1h']:
                        logger.info(f"K 棒數據 [{timeframe}]: {symbol}/{timeframe}, {bar_count} 根")
                    else:
                        # API 失敗
                        results[timeframe] = {"success": False, "error": "保存失敗"}
                
                # 避免觸發 API 頻率限制（5 秒 50 次，這裡每次等待 0.5 秒）
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"刷新 K棒數據失敗: {symbol}/{timeframe}, error: {e}")
                results[timeframe] = {"success": False, "error": str(e)}
        
        # 統計結果
        success_count = sum(1 for r in results.values() if r.get("success"))
        total_count = len(results)
        
        logger.info(
            f"K棒數據刷新完成: {symbol}, "
            f"成功 {success_count}/{total_count}"
        )
        
        return {
            "success": success_count == total_count,
            "symbol": symbol,
            "results": results,
            "summary": f"{success_count}/{total_count} 個時間週期"
        }
    
    async def refresh_all(self) -> Dict:
        """刷新所有支持標的的所有時間週期K棒數據
        
        Returns:
            刷新結果字典
        """
        logger.info("開始刷新所有 K棒數據")
        
        results = {}
        
        for symbol in self.SUPPORTED_SYMBOLS:
            result = await self.refresh(symbol)
            results[symbol] = result
            # 每個標的之間稍作等待
            await asyncio.sleep(1)
        
        # 統計結果
        success_count = sum(1 for r in results.values() if r.get("success"))
        
        logger.info(
            f"所有 K棒數據刷新完成: "
            f"成功 {success_count}/{len(self.SUPPORTED_SYMBOLS)} 個標的"
        )
        
        return {
            "success": success_count == len(self.SUPPORTED_SYMBOLS),
            "results": results
        }
    
    def needs_refresh(self, symbol: str) -> bool:
        """檢查是否需要刷新
        
        Args:
            symbol: 期貨代碼
            
        Returns:
            是否需要刷新
        """
        if symbol not in self.SUPPORTED_SYMBOLS:
            return False
        
        # 檢查每個時間週期
        for timeframe in KBarStore.RECOMMENDED_COUNTS:
            cached = self.store.load(symbol, timeframe)
            
            if not cached:
                logger.info(f"需要刷新: {symbol}/{timeframe} - 緩存不存在")
                return True
            
            # 檢查是否過期
            if self._is_expired(cached):
                logger.info(
                    f"需要刷新: {symbol}/{timeframe} - "
                    f"緩存於 {cached.get('last_updated')} 已過期"
                )
                return True
        
        return False
    
    def _is_expired(self, cached: Dict) -> bool:
        """檢查緩存是否過期
        
        Args:
            cached: 緩存數據
            
        Returns:
            是否過期
        """
        try:
            last_updated_str = cached.get('last_updated')
            if not last_updated_str:
                return True
            
            last_updated = datetime.fromisoformat(last_updated_str)
            days_since_update = (datetime.now() - last_updated).days
            
            return days_since_update > self.REFRESH_INTERVAL_DAYS
            
        except Exception as e:
            logger.warning(f"檢查緩存過期失敗: {e}")
            return True
    
    async def check_and_refresh(self, symbol: str) -> Optional[Dict]:
        """檢查並自動刷新（如果需要）
        
        Args:
            symbol: 期貨代碼
            
        Returns:
            刷新結果，若不需要刷新則返回 None
        """
        if self.needs_refresh(symbol):
            logger.info(f"自動觸發 K棒數據刷新: {symbol}")
            return await self.refresh(symbol)
        
        logger.info(f"K棒數據已是最新: {symbol}")
        return None
    
    async def check_and_refresh_all(self) -> Dict:
        """檢查並自動刷新所有標的
        
        Returns:
            刷新結果字典
        """
        results = {}
        
        for symbol in self.SUPPORTED_SYMBOLS:
            result = await self.check_and_refresh(symbol)
            if result:
                results[symbol] = result
        
        return results
    
    def get_status(self) -> Dict:
        """獲取緩存狀態
        
        Returns:
            緩存狀態字典
        """
        store_status = self.store.get_status()
        
        # 添加刷新建議
        refresh_needed = []
        for symbol in self.SUPPORTED_SYMBOLS:
            if self.needs_refresh(symbol):
                refresh_needed.append(symbol)
        
        store_status["refresh_needed"] = refresh_needed
        store_status["refresh_interval_days"] = self.REFRESH_INTERVAL_DAYS
        
        return store_status
    
    def get_kbars_cached(
        self, 
        symbol: str, 
        timeframe: str, 
        count: int
    ) -> Optional[Dict]:
        """從本地緩存獲取K棒數據
        
        Args:
            symbol: 期貨代碼
            timeframe: 時間週期
            count: 需要獲取的數量
            
        Returns:
            K棒數據字典，若緩存不存在或無效則返回 None
        """
        cached = self.store.load(symbol, timeframe)
        
        if not cached or not cached.get('data'):
            logger.debug(f"緩存不存在: {symbol}/{timeframe}")
            return None
        
        # 取最後 count 根
        data = cached['data']
        
        if len(data) < count:
            logger.warning(
                f"緩存數據不足: {symbol}/{timeframe}, "
                f"需要 {count} 根，本地只有 {len(data)} 根"
            )
            # 返回現有數據
            needed_data = data
        else:
            needed_data = data[-count:]
        
        # 轉換為 KBar API 格式
        return self.store.convert_to_kbars_format(needed_data)
    
    def delete_cache(self, symbol: str, timeframe: Optional[str] = None) -> bool:
        """刪除緩存
        
        Args:
            symbol: 期貨代碼
            timeframe: 時間週期，若為 None則刪除該標的所有緩存
            
        Returns:
            是否刪除成功
        """
        return self.store.delete(symbol, timeframe)
