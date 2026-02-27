"""Backtest API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')


@bp.route('/<strategy_id>', methods=['POST'])
def run_backtest(strategy_id):
    """執行回測"""
    try:
        tools = current_app.trading_tools
        result = tools.backtest_strategy(strategy_id)
        
        # backtest_strategy 返回的是 dict 或 str
        if isinstance(result, dict):
            # 修復：使用 error 欄位判斷是否成功，不檢查報告內容中的 ❌ 字符
            has_error = result.get("error") is not None and result.get("error") != ""
            has_report = result.get("report") is not None and result.get("report") != ""
            
            # 修復：將相對路徑轉換為 URL 路徑
            chart_path = result.get("chart_path")
            chart_url = None
            if chart_path:
                # 將反斜線轉為正斜線，並添加前導 /
                chart_url = "/" + chart_path.replace("\\", "/")
            
            return jsonify({
                "success": not has_error and has_report,
                "report": result.get("report", ""),
                "chart_path": chart_url,
                "error": result.get("error") if has_error else None
            })
        else:
            # 字符串格式的結果
            error_markers = ["❌ 回測失敗", "錯誤", "error", "Error", "ERROR"]
            has_error = any(marker in str(result) for marker in error_markers)
            
            return jsonify({
                "success": not has_error,
                "report": result,
                "chart_path": None,
                "error": None
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "report": "",
            "chart_path": None,
            "error": str(e)
        }), 500
