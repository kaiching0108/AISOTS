"""交易日誌 API Routes"""
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('trade_logs', __name__, url_prefix='/api/trade-logs')


@bp.route('', methods=['GET'])
def get_trade_logs():
    """取得交易日誌
    
    Query Parameters:
        limit: 返回條數上限 (預設50, 最大100)
        event_type: 過濾事件類型 (可選)
        strategy_id: 過濾策略ID (可選)
    """
    try:
        tools = current_app.trading_tools
        
        # 取得查詢參數
        limit = min(int(request.args.get('limit', 50)), 100)
        event_type = request.args.get('event_type') or None
        strategy_id = request.args.get('strategy_id') or None
        
        # 取得日誌
        logs = tools.trade_log_store.get_recent_logs(
            limit=limit,
            event_type=event_type,
            strategy_id=strategy_id
        )
        
        # 格式化時間顯示
        formatted_logs = []
        for log in logs:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(log['timestamp'])
                formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                formatted_time = log['timestamp']
            
            formatted_logs.append({
                **log,
                "formatted_time": formatted_time,
                "event_type_display": _get_event_type_display(log['event_type'])
            })
        
        return jsonify({
            "success": True,
            "data": formatted_logs,
            "count": len(formatted_logs),
            "filters": {
                "event_type": event_type,
                "strategy_id": strategy_id
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/event-types', methods=['GET'])
def get_event_types():
    """取得可用的事件類型"""
    try:
        tools = current_app.trading_tools
        types = tools.trade_log_store.get_event_types()
        
        return jsonify({
            "success": True,
            "data": [
                {"value": t, "label": _get_event_type_display(t)} 
                for t in types
            ]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/stats', methods=['GET'])
def get_stats():
    """取得日誌統計"""
    try:
        tools = current_app.trading_tools
        stats = tools.trade_log_store.get_stats()
        
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _get_event_type_display(event_type: str) -> str:
    """取得事件類型的中文顯示名稱"""
    mapping = {
        "ORDER_SUCCESS": "下單成功",
        "CLOSE_POSITION": "平倉",
        "RISK_BLOCKED": "風控擋單",
        "ORDER_FAILED": "下單失敗",
        "SYSTEM": "系統訊息"
    }
    return mapping.get(event_type, event_type)
