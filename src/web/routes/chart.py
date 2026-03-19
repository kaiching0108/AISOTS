"""Chart API Routes - K棒圖表資料"""
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timezone
from pathlib import Path

bp = Blueprint('chart', __name__, url_prefix='/api/chart')

# 預先載入資料庫
_kbar_db = None
_signal_recorder = None


def get_kbar_db():
    """取得 KBar SQLite 資料庫"""
    global _kbar_db
    if _kbar_db is None:
        try:
            from src.storage.kbar_sqlite import KBarSQLite
            db_path = Path('workspace/kbars.sqlite')
            print(f"Checking for kbar database at: {db_path.absolute()}")
            print(f"Exists: {db_path.exists()}")
            if db_path.exists():
                _kbar_db = KBarSQLite(db_path)
                print(f"KBar database loaded successfully")
        except Exception as e:
            print(f"Failed to load kbar_db: {e}")
            import traceback
            traceback.print_exc()
    return _kbar_db


def get_signal_recorder():
    """取得訊號記錄器"""
    global _signal_recorder
    if _signal_recorder is None:
        try:
            from src.analysis.signal_recorder import SignalRecorder
            _signal_recorder = SignalRecorder(Path('workspace'))
        except Exception as e:
            print(f"Failed to load signal_recorder: {e}")
    return _signal_recorder


@bp.route('/kbars', methods=['GET'])
def get_kbars():
    """取得 K 棒資料
    
    Query Parameters:
        symbol: 期貨代碼 (TXF/MXF/TMF)
        timeframe: 時間週期 (1m/5m/15m/30m/60m/1h/1d)
        limit: 回傳數量 (預設 300)
        start_ts: 開始時間戳 (可選)
        end_ts: 結束時間戳 (可選)
    """
    try:
        symbol = request.args.get('symbol', 'TXF').upper()
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 300))
        start_ts = request.args.get('start_ts', type=int)
        end_ts = request.args.get('end_ts', type=int)
        
        kbar_db = get_kbar_db()
        
        if not kbar_db:
            return jsonify({
                "success": False,
                "error": f"KBar database not found. Path: workspace/kbars.sqlite"
            }), 500
        
        if end_ts is None:
            end_ts = 2147483647
        if start_ts is None:
            # 根據週期計算時間範圍
            timeframe_seconds = {
                '1m': 60,
                '5m': 300,
                '15m': 900,
                '30m': 1800,
                '60m': 3600,
                '1h': 3600,
                '1d': 86400,
            }.get(timeframe, 900)
            
            latest = kbar_db.get_latest_kbar(symbol)
            if latest:
                start_ts = latest['ts'] - (limit * timeframe_seconds)
            else:
                start_ts = 0
        
        kbars = kbar_db.get_kbars_with_conversion(symbol, start_ts, end_ts, timeframe)
        
        if not kbars or not kbars.get('ts'):
            return jsonify({
                "success": True,
                "data": {
                    "candlestick": [],
                    "volume": []
                },
                "message": "No data available"
            })
        
        ts_list = kbars.get('ts', [])
        open_list = kbars.get('open', [])
        high_list = kbars.get('high', [])
        low_list = kbars.get('low', [])
        close_list = kbars.get('close', [])
        volume_list = kbars.get('volume', [])
        
        candlestick = []
        volume = []
        
        count = min(len(ts_list), limit)
        
        # Lightweight Charts 需要 UTC 时间的秒數timestamp
        for i in range(count):
            # 使用 Unix timestamp (秒) - Lightweight Charts 支援
            ts = int(ts_list[i])
            
            candlestick.append({
                "time": ts,
                "open": round(open_list[i], 2),
                "high": round(high_list[i], 2),
                "low": round(low_list[i], 2),
                "close": round(close_list[i], 2)
            })
            
            vol = volume_list[i] if i < len(volume_list) else 0
            volume.append({
                "time": ts,
                "value": int(vol),
                "open": round(open_list[i], 2),
                "close": round(close_list[i], 2)
            })
        
        return jsonify({
            "success": True,
            "data": {
                "candlestick": candlestick,
                "volume": volume
            },
            "meta": {
                "symbol": symbol,
                "timeframe": timeframe,
                "count": len(candlestick)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/signals', methods=['GET'])
def get_signals():
    """取得策略訊號
    
    Query Parameters:
        strategy_id: 策略 ID
        start_ts: 起始時間戳（可選，用於過濾）
        end_ts: 結束時間戳（可選，用於過濾）
    """
    try:
        strategy_id = request.args.get('strategy_id')
        start_ts = request.args.get('start_ts', type=int)
        end_ts = request.args.get('end_ts', type=int)
        
        if not strategy_id:
            return jsonify({
                "success": False,
                "error": "strategy_id is required"
            }), 400
        
        signal_recorder = get_signal_recorder()
        
        if not signal_recorder:
            return jsonify({
                "success": False,
                "error": "Signal recorder not available"
            }), 500
        
        signals = signal_recorder.get_signals(strategy_id)
        
        markers = []
        
        for sig in signals:
            ts = sig.get('timestamp')
            if not ts:
                continue
            
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                ts_sec = int(dt.timestamp())
            except:
                continue
            
            # 前端傳入的 start_ts/end_ts 是毫秒，轉換成秒再比對
            if start_ts is not None and ts_sec < (start_ts // 1000):
                continue
            if end_ts is not None and ts_sec > (end_ts // 1000):
                continue
            
            signal_type = sig.get('signal', '')
            price = sig.get('price', 0)
            status = sig.get('status', 'pending')
            
            if status == 'pending':
                if signal_type == 'buy':
                    markers.append({
                        "time": ts_sec,
                        "position": "belowBar",
                        "color": "#3fb950",
                        "shape": "arrowUp",
                        "text": f"BUY {price:.0f}"
                    })
                elif signal_type == 'sell':
                    markers.append({
                        "time": ts_sec,
                        "position": "aboveBar",
                        "color": "#f85149",
                        "shape": "arrowDown",
                        "text": f"SELL {price:.0f}"
                    })
                elif signal_type == 'close':
                    markers.append({
                        "time": ts_sec,
                        "position": "aboveBar",
                        "color": "#d29922",
                        "shape": "circle",
                        "text": f"CLOSE {price:.0f}"
                    })
            elif status == 'filled':
                exit_reason = sig.get('exit_reason', '')
                if 'stop_loss' in exit_reason:
                    color = "#f85149"
                    shape = "circle"
                elif 'take_profit' in exit_reason:
                    color = "#3fb950"
                    shape = "circle"
                else:
                    color = "#8b949e"
                    shape = "circle"
                
                markers.append({
                    "time": ts_sec,
                    "position": "aboveBar",
                    "color": color,
                    "shape": shape,
                    "text": f"{signal_type.upper()} {price:.0f}"
                })
        
        return jsonify({
            "success": True,
            "data": {
                "markers": markers,
                "count": len(markers)
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/symbols', methods=['GET'])
def get_symbols():
    """取得所有可用的期貨代碼"""
    try:
        kbar_db = get_kbar_db()
        if not kbar_db:
            return jsonify({
                "success": False,
                "error": "KBar database not available"
            }), 500
        
        symbols = kbar_db.get_all_symbols()
        
        symbol_names = {
            "TXFR1": "TXF (台指期)",
            "MXFR1": "MXF (小台指)",
            "TMFR1": "TMF (微型台指)",
            "TXF": "TXF (台指期)",
            "MXF": "MXF (小台指)",
            "TMF": "TMF (微型台指)"
        }
        
        result = []
        for sym in symbols:
            base = kbar_db.get_base_code(sym)
            result.append({
                "code": base,
                "name": symbol_names.get(base, base)
            })
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/strategies', methods=['GET'])
def get_strategies():
    """取得所有策略"""
    try:
        tools = getattr(current_app, 'trading_tools', None)
        if not tools or not hasattr(tools, 'strategy_mgr'):
            return jsonify({
                "success": False,
                "error": "Strategy manager not available"
            }), 500
        
        strategies = tools.strategy_mgr.get_all_strategies()
        
        result = []
        for s in strategies:
            result.append({
                "id": s.id,
                "name": s.name,
                "symbol": s.symbol,
                "timeframe": s.params.get("timeframe") if s.params else None,
                "enabled": s.enabled
            })
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
