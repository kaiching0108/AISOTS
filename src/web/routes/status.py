"""Status API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('status', __name__, url_prefix='/api')


@bp.route('/status', methods=['GET'])
def get_status():
    """取得系統狀態"""
    try:
        tools = current_app.trading_tools
        status_text = tools.get_system_status()
        
        sqlite_info = tools.get_sqlite_status()
        
        return jsonify({
            "success": True,
            "message": status_text,
            "sqlite": sqlite_info.get("symbols", {}),
            "sqlite_total": sqlite_info.get("total", 0),
            "sqlite_error": sqlite_info.get("error")
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
