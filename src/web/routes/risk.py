"""Risk API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('risk', __name__, url_prefix='/api/risk')


@bp.route('', methods=['GET'])
def get_risk():
    """取得風控狀態"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            risk_text = tools.get_risk_status()
            risk_status = tools.risk_mgr.get_status()
        
        return jsonify({
            "success": True,
            "data": {
                "daily_pnl": risk_status.get("daily_pnl", 0),
                "max_daily_loss": risk_status.get("max_daily_loss", 0),
                "max_position": risk_status.get("max_position", 0),
                "current_position": risk_status.get("current_position", 0),
                "orders_this_minute": risk_status.get("orders_this_minute", 0),
                "max_orders_per_minute": risk_status.get("max_orders_per_minute", 0),
                "stop_loss_enabled": risk_status.get("stop_loss_enabled", True),
                "take_profit_enabled": risk_status.get("take_profit_enabled", True)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
