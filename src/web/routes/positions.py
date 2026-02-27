"""Positions API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('positions', __name__, url_prefix='/api/positions')


@bp.route('', methods=['GET'])
def get_positions():
    """取得所有部位"""
    try:
        tools = current_app.trading_tools
        positions = tools.position_mgr.get_all_positions()
        summary = tools.position_mgr.get_positions_summary()
        
        result = []
        for pos in positions:
            result.append({
                "strategy_id": pos.get("strategy_id", ""),
                "strategy_name": pos.get("strategy_name", ""),
                "symbol": pos.get("symbol", ""),
                "direction": pos.get("direction", ""),
                "quantity": pos.get("quantity", 0),
                "entry_price": pos.get("entry_price", 0),
                "current_price": pos.get("current_price", 0),
                "pnl": pos.get("pnl", 0)
            })
        
        return jsonify({
            "success": True,
            "data": result,
            "summary": {
                "total_quantity": summary.get("total_quantity", 0),
                "total_pnl": summary.get("total_pnl", 0),
                "count": len(result)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
