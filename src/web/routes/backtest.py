"""Backtest API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')


@bp.route('/<strategy_id>', methods=['POST'])
def run_backtest(strategy_id):
    """執行回測"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            result = tools.backtest_strategy(strategy_id)
        
        # backtest_strategy 返回的是 dict 或 str
        if isinstance(result, dict):
            return jsonify({
                "success": result.get("report") is not None and "❌" not in result.get("report", ""),
                "report": result.get("report", ""),
                "chart_path": result.get("chart_path")
            })
        else:
            return jsonify({
                "success": "❌" not in result and "錯誤" not in result,
                "report": result
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
