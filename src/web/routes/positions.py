"""Positions API Routes"""
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('positions', __name__, url_prefix='/api/positions')


@bp.route('', methods=['GET'])
def get_positions():
    """取得所有部位
    
    Query params:
        - strategy_id: 特定策略 ID (optional)
    """
    try:
        tools = current_app.trading_tools
        strategy_id_filter = request.args.get('strategy_id')
        
        all_positions = tools.position_mgr.get_all_positions()
        
        # 根據策略 ID 篩選
        if strategy_id_filter:
            all_positions = [p for p in all_positions 
                          if (hasattr(p, 'strategy_id') and p.strategy_id == strategy_id_filter)
                          or (hasattr(p, 'to_dict') and p.to_dict().get('strategy_id') == strategy_id_filter)]
        
        summary = tools.position_mgr.get_positions_summary()
        
        result = []
        for pos in all_positions:
            if hasattr(pos, 'to_dict'):
                pos_dict = pos.to_dict()
            else:
                pos_dict = pos
            result.append({
                "strategy_id": pos_dict.get("strategy_id", ""),
                "strategy_name": pos_dict.get("strategy_name", ""),
                "symbol": pos_dict.get("symbol", ""),
                "direction": pos_dict.get("direction", ""),
                "quantity": pos_dict.get("quantity", 0),
                "entry_price": pos_dict.get("entry_price", 0),
                "current_price": pos_dict.get("current_price", 0),
                "pnl": pos_dict.get("pnl", 0)
            })
        
        # 計算篩選後的總結
        filtered_quantity = sum(p.get("quantity", 0) for p in result)
        filtered_pnl = sum(p.get("pnl", 0) for p in result)
        
        return jsonify({
            "success": True,
            "data": result,
            "summary": {
                "total_quantity": filtered_quantity,
                "total_pnl": filtered_pnl,
                "count": len(result)
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
