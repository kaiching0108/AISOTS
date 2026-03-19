"""K 棒数据更新服务"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from loguru import logger

from src.storage.kbar_sqlite import KBarSQLite


class DataUpdater:
    """K 棒数据更新服务"""
    
    SYMBOLS = ['TXF', 'MXF', 'TMF']
    
    DEFAULT_CONFIG = {
        'enabled': True,
        'initial_fetch': {
            'records_per_call': 5000,
            'api_calls_per_day': 20,
            'daily_limit': 60000,
            'max_total': 300000,
        },
        'storage': {
            'max_records': 600000,
            'cleanup_threshold': 700000,
        }
    }
    
    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> Dict:
        """深度合併兩個字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUpdater._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def __init__(self, shioaji_client, workspace: Path, config: Optional[Dict] = None):
        """初始化数据更新服务"""
        self.client = shioaji_client
        self.workspace = workspace
        self.config = self._deep_merge(self.DEFAULT_CONFIG, config or {})
        
        # 从配置中读取 storage 设置
        storage_config = self.config.get('storage', {})
        max_records = storage_config.get('max_records')
        cleanup_threshold = storage_config.get('cleanup_threshold')
        
        db_path = workspace / 'kbars.sqlite'
        self.db = KBarSQLite(db_path, max_records=max_records, cleanup_threshold=cleanup_threshold)
        
        logger.info(f"DataUpdater 初始化完成：{db_path}, max_records={self.db.MAX_RECORDS}, cleanup_threshold={self.db.CLEANUP_THRESHOLD}")
    
    async def check_and_update_on_login(self) -> Dict:
        """登录时检查并更新数据"""
        if not self.config.get('enabled', True):
            logger.info("DataUpdater 已禁用")
            return {'status': 'disabled'}
        
        max_total = self.config.get('initial_fetch', {}).get('max_total', 300000)
        
        symbol_counts = {}
        any_needs_fetch = False
        for symbol in self.SYMBOLS:
            count = self.db.get_count(symbol)
            symbol_counts[symbol] = count
            if count < max_total:
                any_needs_fetch = True
        
        logger.info(f"當前 1m 筆數：{symbol_counts}, max_total: {max_total}")
        
        if not any_needs_fetch:
            logger.info(f"所有 symbol 都已達到 {max_total}，無需抓取")
            return {'status': 'sufficient_data', 'symbol_counts': symbol_counts}
        
        result = {
            'symbols_updated': [],
            'symbols_need_fetch': [],
            'errors': [],
            'total_fetched': 0,
        }
        
        symbols_to_fetch = []
        for symbol in self.SYMBOLS:
            try:
                status = await self._check_and_fetch_symbol(symbol)
                if status.get('needs_fetch'):
                    symbols_to_fetch.append(symbol)
                    result['symbols_need_fetch'].append(symbol)
            except Exception as e:
                logger.error(f"檢查 symbol {symbol} 失敗：{e}")
                result['errors'].append(f"{symbol}: {str(e)}")
        
        if not symbols_to_fetch:
            logger.info("所有 symbol 數據量充足，無需抓取")
            return result
        
        daily_limit = self.config.get('initial_fetch', {}).get('daily_limit', 60000)
        today_count = self.db.get_today_fetch_count_by_type('initial')
        
        logger.info(f"Initial fetch 檢查：今日已抓取 {today_count} 筆，限制 {daily_limit} 筆")
        
        remaining = daily_limit - today_count
        
        if remaining <= 0:
            logger.info(f"今日 initial 抓取已達限制 {daily_limit}，停止抓取")
            return result
        
        quota_per_symbol = remaining // len(symbols_to_fetch)
        logger.info(f"需要抓取的 symbol: {symbols_to_fetch}, 剩餘額限：{remaining}, 每 symbol 配額：{quota_per_symbol}")
        
        total_fetched = 0
        
        for symbol in symbols_to_fetch:
            try:
                records = await self._fetch_symbol_data_with_quota(symbol, quota_per_symbol)
                if records > 0:
                    result['symbols_updated'].append(symbol)
                    result['total_fetched'] += records
                    total_fetched += records
            except Exception as e:
                logger.error(f"抓取 {symbol} 失敗：{e}")
                result['errors'].append(f"{symbol}: {str(e)}")
        
        if total_fetched > 0:
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.db.log_fetch_attempt('TXF', today_str, total_fetched, 'success', 'initial')
            logger.info(f"記錄 initial 抓取結果: {total_fetched} 筆")
        
        if self.db.get_total_count() > self.db.CLEANUP_THRESHOLD:
            self.db.cleanup_old_records()
        
        return result
    
    async def _check_and_fetch_symbol(self, symbol: str) -> Dict:
        """檢查單個期貨是否需要抓取"""
        latest = self.db.get_latest_kbar(symbol)
        oldest = self.db.get_oldest_kbar(symbol)
        
        now = datetime.now()
        
        symbol_count = self.db.get_count(symbol)
        max_total = self.config.get('initial_fetch', {}).get('max_total', 300000)
        
        if symbol_count >= max_total:
            logger.info(f"{symbol} 已達总量限制 {max_total}，無需抓取")
            return {'updated': False, 'needs_fetch': False}
        
        needs_fetch = False
        
        if latest is None:
            needs_fetch = True
            logger.info(f"{symbol}: 無本地數據，需要初始抓取")
        else:
            # 將納秒轉換為秒
            ts_sec = latest['ts'] // 1_000_000_000 if isinstance(latest['ts'], (int, float)) and latest['ts'] > 1e12 else latest['ts']
            latest_date = datetime.utcfromtimestamp(ts_sec)
            if latest_date.date() < (now - timedelta(days=1)).date():
                needs_fetch = True
                logger.info(f"{symbol}: 數據過期，最新日期 {latest_date.date()}")
        
        if not needs_fetch:
            logger.info(f"{symbol}: 數據未過期但數量不足 ({symbol_count}/{max_total})，需要補充")
        
        return {'updated': True, 'needs_fetch': True, 'records': 0}
    
    async def _fetch_symbol_data_with_quota(self, symbol: str, quota: int) -> int:
        """按配額抓取歷史期貨數據（從最舊往更早抓）
        
        Args:
            symbol: 期貨代碼
            quota: 分配給該 symbol 的抓取配額 (來自 daily_limit 自動計算)
            
        Returns:
            抓取的記錄數
        """
        if not hasattr(self.client, 'connected') or not self.client.connected:
            logger.info("Client 未連線，跳過數據抓取")
            return 0
        
        records_per_call = self.config.get('initial_fetch', {}).get('records_per_call', 5000)
        max_total = self.config.get('initial_fetch', {}).get('max_total', 300000)
        api_calls_per_day = self.config.get('initial_fetch', {}).get('api_calls_per_day', 10)
        
        logger.info(f"{symbol}: api_calls_per_day={api_calls_per_day}, records_per_call={records_per_call}")
        
        # 計算每筆 K 棒對應的天數
        # 實際統計：完整交易日約 1140 筆 (日盤 + 夜盤)
        # 考慮週末和假日，平均 22 交易日/月，換算自然日需乘以 30/22 ≈ 1.36
        records_per_trading_day = 1140
        days_per_call = records_per_call / records_per_trading_day * (30 / 22)
        
        logger.info(f"{symbol}: 目標 {records_per_call} 筆/次，估算需 {days_per_call:.1f} 天")
        
        # 從最舊日期往前抓填補歷史
        time_ranges = []
        
        oldest = self.db.get_oldest_kbar(symbol)
        if oldest:
            ts_sec = oldest['ts'] // 1_000_000_000 if isinstance(oldest['ts'], (int, float)) and oldest['ts'] > 1e12 else oldest['ts']
            current_end = datetime.utcfromtimestamp(ts_sec)
        else:
            current_end = datetime.now()
        
        for i in range(api_calls_per_day):
            start_dt = current_end - timedelta(days=days_per_call)
            time_ranges.append((start_dt, current_end))
            current_end = start_dt
        
        direction = "往前抓(initial)"
        logger.info(f"{symbol}: 預先計算 {len(time_ranges)} 組時間區間 ({direction})")
        
        total_records = 0
        call_count = 0
        
        while total_records < quota and call_count < api_calls_per_day:
            current_count = self.db.get_count(symbol)
            if current_count >= max_total:
                logger.info(f"{symbol} 已達總量限制 {max_total}，停止抓取")
                break
            
            call_count += 1
            
            start_dt, end_dt = time_ranges[call_count - 1]
            logger.info(f"{symbol}: 抓取範圍 {start_dt.strftime('%Y-%m-%d %H:%M')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}")
            
            contract = self.client.get_contract(symbol)
            if not contract:
                logger.info(f"{symbol}: 無法獲取合約對象")
                break
            
            kbars_raw = self.client.api.kbars(
                contract=contract,
                start=start_dt.strftime("%Y-%m-%d"),
                end=end_dt.strftime("%Y-%m-%d"),
                timeout=30000
            )
            
            if kbars_raw:
                ts_list = list(kbars_raw.ts)
                kbars_data = {
                    "ts": [ts // 1_000_000_000 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts) for ts in ts_list],
                    "open": list(kbars_raw.Open),
                    "high": list(kbars_raw.High),
                    "low": list(kbars_raw.Low),
                    "close": list(kbars_raw.Close),
                    "volume": list(kbars_raw.Volume),
                }
            else:
                kbars_data = None
            
            if kbars_data and kbars_data.get('ts'):
                inserted = self.db.insert_kbars(symbol, kbars_data, source='initial')
                total_records += inserted
                logger.info(f"{symbol}: 第 {call_count} 次 API，插入 {inserted} 筆，總計 {total_records}/{quota}")
            else:
                logger.info(f"{symbol}: 第 {call_count} 次 API，無數據")
        
        logger.info(f"{symbol}: 共調用 API {call_count} 次，最終抓取 {total_records}/{quota} 條")
        return total_records
    
    async def fetch_today(self) -> Dict:
        """補抓今日所有 K-bars（從 00:00 到 now）
        
        觸發時機：
        - 系統啟動時（登入後、接收 Realtime 之前）
        - 斷線重連後（重新訂閱之前）
        
        直接從 Shioaji API 補抓今日完整資料，寫入 SQLite (source='recovery')。
        不寫入 fetch_log，不消耗 initial_fetch 配額。
        """
        if not hasattr(self.client, 'connected') or not self.client.connected:
            logger.info("Client 未連線，跳過今日補抓")
            return {'status': 'not_connected'}
        
        now = datetime.now()
        start_dt = datetime.combine(now.date(), datetime.min.time())
        end_dt = now
        
        logger.info(f"補抓今日 K-bars：{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d %H:%M')}")
        
        result = {
            'symbols_recovered': [],
            'total_records': 0,
            'errors': [],
        }
        
        for symbol in self.SYMBOLS:
            try:
                contract = self.client.get_contract(symbol)
                if not contract:
                    logger.warning(f"{symbol}: 無法獲取合約對象")
                    result['errors'].append(f"{symbol}: no contract")
                    continue
                
                kbars_raw = self.client.api.kbars(
                    contract=contract,
                    start=start_dt.strftime("%Y-%m-%d"),
                    end=end_dt.strftime("%Y-%m-%d"),
                    timeout=30000
                )
                
                if kbars_raw:
                    ts_list = list(kbars_raw.ts)
                    kbars_data = {
                        "ts": [ts // 1_000_000_000 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts) for ts in ts_list],
                        "open": list(kbars_raw.Open),
                        "high": list(kbars_raw.High),
                        "low": list(kbars_raw.Low),
                        "close": list(kbars_raw.Close),
                        "volume": list(kbars_raw.Volume),
                    }
                    
                    if kbars_data.get('ts'):
                        inserted = self.db.insert_kbars(symbol, kbars_data, source='recovery')
                        result['symbols_recovered'].append(symbol)
                        result['total_records'] += inserted
                        logger.info(f"{symbol}: 補抓完成，插入 {inserted} 筆")
                    else:
                        logger.info(f"{symbol}: 補抓無數據")
                else:
                    logger.info(f"{symbol}: 補抓無數據")
                    
            except Exception as e:
                logger.error(f"{symbol} 補抓失敗：{e}")
                result['errors'].append(f"{symbol}: {str(e)}")
        
        if result['symbols_recovered']:
            logger.info(f"今日補抓完成：{result['symbols_recovered']}, 共 {result['total_records']} 筆")
        else:
            logger.info("今日補抓完成：無符號需要補抓")
        
        return result
    
    def get_status(self) -> Dict:
        """獲取更新服務狀態"""
        db_status = self.db.get_status()
        return {
            'enabled': self.config.get('enabled', True),
            'database': db_status,
        }
