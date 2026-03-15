"""Status API Routes"""
from flask import Blueprint, jsonify, current_app
from datetime import datetime

bp = Blueprint('status', __name__, url_prefix='/api')


@bp.route('/status', methods=['GET'])
def get_status():
    """取得系統狀態"""
    try:
        tools = current_app.trading_tools
        status_text = tools.get_system_status()
        
        sqlite_info = tools.get_sqlite_status()
        
        # 取得連線狀態
        connection_status = "disconnected"
        reconnect_count = 0
        last_check_time = None
        
        if hasattr(current_app, 'connection_mgr') and current_app.connection_mgr:
            conn_mgr = current_app.connection_mgr
            connection_status = "connected" if conn_mgr.is_connected else "disconnected"
            reconnect_count = getattr(conn_mgr, 'reconnect_count', 0)
            last_check_time = datetime.now().isoformat()
        
        # 取得交易時段狀態
        trading_hours_status = "non_trading"
        if hasattr(current_app, 'strategy_runner') and current_app.strategy_runner:
            is_trading = current_app.strategy_runner.is_within_trading_hours()
            trading_hours_status = "trading" if is_trading else "non_trading"
        
        return jsonify({
            "success": True,
            "message": status_text,
            "sqlite": sqlite_info.get("symbols", {}),
            "sqlite_total": sqlite_info.get("total", 0),
            "sqlite_error": sqlite_info.get("error"),
            "connection": {
                "status": connection_status,
                "reconnect_count": reconnect_count,
                "last_check": last_check_time
            },
            "trading_hours": {
                "status": trading_hours_status
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
