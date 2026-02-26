"""Status API Routes"""
from flask import Blueprint, jsonify, current_app

bp = Blueprint('status', __name__, url_prefix='/api')


@bp.route('/status', methods=['GET'])
def get_status():
    """取得系統狀態"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            status_text = tools.get_system_status()
        
        # 解析文字狀態為 JSON
        # 這裡需要從 get_system_status() 的回傳值解析
        # 暫時簡單處理
        return jsonify({
            "success": True,
            "message": status_text
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
