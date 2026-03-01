"""Orders API Routes"""
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('orders', __name__, url_prefix='/api/orders')


@bp.route('', methods=['GET'])
def get_orders():
    """取得訂單列表
    
    Query params:
        - status: Pending/Submitted/Filled/Cancelled/Rejected (optional)
        - strategy_id: 特定策略 ID (optional)
        - date: 日期 YYYY-MM-DD，預設今日
    """
    try:
        tools = current_app.trading_tools
        order_mgr = tools.order_mgr
        
        status_filter = request.args.get('status')
        strategy_id_filter = request.args.get('strategy_id')
        date_filter = request.args.get('date')
        
        orders = []
        
        if strategy_id_filter:
            orders = order_mgr.get_orders_by_strategy(strategy_id_filter)
        elif date_filter:
            from datetime import datetime
            all_orders = order_mgr.store.get_all_orders()
            orders = [o for o in all_orders if date_filter in o.get("timestamp", "")]
        else:
            orders = order_mgr.get_today_orders()
        
        if status_filter:
            orders = [o for o in orders if o.get("status") == status_filter]
        
        # 按時間排序（由新到舊）
        orders.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        summary = {
            "total": len(orders),
            "filled": len([o for o in orders if o.get("status") == "Filled"]),
            "cancelled": len([o for o in orders if o.get("status") == "Cancelled"]),
            "rejected": len([o for o in orders if o.get("status") == "Rejected"]),
            "submitted": len([o for o in orders if o.get("status") == "Submitted"]),
            "pending": len([o for o in orders if o.get("status") == "Pending"])
        }
        
        return jsonify({
            "success": True,
            "data": orders,
            "summary": summary
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/all', methods=['GET'])
def get_all_orders():
    """取得所有歷史訂單"""
    try:
        tools = current_app.trading_tools
        order_mgr = tools.order_mgr
        
        all_orders = order_mgr.store.get_all_orders()
        
        all_orders.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return jsonify({
            "success": True,
            "data": all_orders,
            "total": len(all_orders)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/statistics', methods=['GET'])
def get_order_statistics():
    """取得訂單統計"""
    try:
        tools = current_app.trading_tools
        stats = tools.order_mgr.get_order_statistics()
        
        return jsonify({
            "success": True,
            "data": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
