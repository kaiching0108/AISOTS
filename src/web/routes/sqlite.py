"""SQLite Data API Routes"""
import asyncio
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, current_app
from loguru import logger

bp = Blueprint('sqlite', __name__, url_prefix='/api/sqlite')


@bp.route('/fetch-missing', methods=['POST'])
def fetch_missing():
    """手動獲取缺失的數據"""
    try:
        tools = current_app.trading_tools
        api = tools.api

        if not hasattr(api, 'connected') or not api.connected:
            return jsonify({
                "success": False,
                "error": "API 未連線"
            }), 400

        result = asyncio.run(_fetch_missing_data(api))

        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


async def _fetch_missing_data(api):
    """異步獲取缺失數據"""
    from src.storage.kbar_sqlite import KBarSQLite
    from pathlib import Path
    from datetime import datetime, timedelta

    workspace = Path(__file__).parent.parent.parent.parent / 'workspace'
    db_path = workspace / 'kbars.sqlite'
    db = KBarSQLite(db_path)

    symbols = db.get_all_symbols()
    results = {
        "symbols_updated": [],
        "total_fetched": 0,
        "dates_checked": 0,
        "no_data_dates": [],
        "errors": []
    }

    for symbol in symbols:
        try:
            # 取得所有已確認的日期
            confirmed_dates = db.get_confirmed_dates(symbol)
            
            # 取得工作日缺口日期
            workday_check = db.check_workday_gaps(symbol)
            workday_gap_dates = workday_check.get("workday_gap_dates", [])
            
            # 取得每日數據不足日期
            trading_check = db.check_trading_hours_completeness(symbol)
            incomplete_dates = [s["date"] for s in trading_check.get("incomplete_details", [])]
            suspicious_dates = incomplete_dates  # 保持變數名稱兼容
            
            # 合併所有需要處理的日期，並過濾已確認的日期
            all_dates = list(set(workday_gap_dates + suspicious_dates))
            all_dates = [d for d in all_dates if d not in confirmed_dates]
            
            if not all_dates:
                logger.info(f"{symbol}: 所有缺口日期已確認")
                results["symbols_updated"].append(symbol)
                continue
            
            # 按日期排序
            all_dates.sort()
            
            logger.info(f"{symbol}: 需要處理的日期: {all_dates}")
            
            # 處理每個日期
            for gap_date in all_dates:
                gap_dt = datetime.strptime(gap_date, "%Y-%m-%d")
                results["dates_checked"] += 1
                
                try:
                    contract = api.get_contract(symbol.replace('R1', ''))
                    if contract:
                        start_date = gap_dt.strftime("%Y-%m-%d")
                        end_date = (gap_dt + timedelta(days=1)).strftime("%Y-%m-%d")
                        
                        logger.info(f"補抓 {symbol}: {start_date} ~ {end_date}")
                        
                        kbars = api.api.kbars(
                            contract=contract,
                            start=start_date,
                            end=end_date,
                            timeout=30000
                        )
                        
                        if kbars and hasattr(kbars, 'ts') and len(kbars.ts) > 0:
                            result_data = {
                                "ts": [
                                    ts // 1_000_000_000 if isinstance(ts, (int, float)) and ts > 1e12 else int(ts)
                                    for ts in kbars.ts
                                ],
                                "open": list(kbars.Open),
                                "high": list(kbars.High),
                                "low": list(kbars.Low),
                                "close": list(kbars.Close),
                                "volume": list(kbars.Volume),
                            }
                            
                            ts_list = result_data["ts"]
                            if ts_list:
                                first_ts = ts_list[0]
                                if isinstance(first_ts, (int, float)) and first_ts > 1e12:
                                    first_ts_sec = first_ts // 1_000_000_000
                                else:
                                    first_ts_sec = int(first_ts)
                                
                                actual_date = datetime.utcfromtimestamp(first_ts_sec).strftime("%Y-%m-%d")
                                
                                if actual_date != gap_date:
                                    db.log_fetch_attempt(symbol, gap_date, 0, 'no_data')
                                    results["no_data_dates"].append(gap_date)
                                    logger.info(f"補抓無資料: {symbol} {gap_date} (API 返回 {actual_date}，該日可能是假日)")
                                else:
                                    db.insert_kbars(symbol, result_data)
                                    results["total_fetched"] += len(result_data.get("close", []))
                                    
                                    # 获取当天日期（台北时间），当天不写入 success
                                    today = datetime.now().strftime("%Y-%m-%d")
                                    if gap_date == today:
                                        logger.info(f"補抓成功: {symbol} {gap_date}, 取得 {len(result_data['ts'])} 筆 (當天不寫入 success)")
                                    else:
                                        db.log_fetch_attempt(symbol, gap_date, len(result_data["ts"]), 'success')
                                        logger.info(f"補抓成功: {symbol} {gap_date}, 取得 {len(result_data['ts'])} 筆")
                        else:
                            db.log_fetch_attempt(symbol, gap_date, 0, 'no_data')
                            results["no_data_dates"].append(gap_date)
                            logger.info(f"補抓無資料: {symbol} {gap_date} (API 無返回數據，可能是假日)")
                except Exception as e:
                    logger.error(f"補抓失敗 {symbol} {gap_date}: {e}")
                    results["errors"].append(f"{symbol}: {gap_date} - {str(e)}")
            
            results["symbols_updated"].append(symbol)

        except Exception as e:
            results["errors"].append(f"{symbol}: {str(e)}")

    return results
