"""Strategies API Routes"""
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('strategies', __name__, url_prefix='/api/strategies')


def get_strategy_data(trading_tools):
    """取得策略資料（JSON格式）"""
    strategies = trading_tools.strategy_mgr.get_all_strategies()
    
    result = []
    for s in strategies:
        position = trading_tools.position_mgr.get_position(s.id)
        
        result.append({
            "id": s.id,
            "name": s.name,
            "symbol": s.symbol,
            "enabled": s.enabled,
            "is_running": s.is_running,
            "version": s.strategy_version,
            "timeframe": s.params.get("timeframe") if s.params else None,
            "quantity": s.params.get("quantity") if s.params else None,
            "stop_loss": s.params.get("stop_loss") if s.params else None,
            "take_profit": s.params.get("take_profit") if s.params else None,
            "goal": s.goal,
            "goal_unit": s.goal_unit,
            "has_position": position is not None and position.quantity > 0 if position else False,
            "position": {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "pnl": position.pnl
            } if position and position.quantity > 0 else None
        })
    
    return result


@bp.route('', methods=['GET'])
def get_strategies():
    """取得所有策略"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            strategies = get_strategy_data(tools)
        
        return jsonify({
            "success": True,
            "data": strategies,
            "count": len(strategies)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """取得特定策略"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            strategy = tools.strategy_mgr.get_strategy(strategy_id)
            
            if not strategy:
                return jsonify({
                    "success": False,
                    "error": "Strategy not found"
                }), 404
            
            position = tools.position_mgr.get_position(strategy_id)
            
            data = {
                "id": strategy.id,
                "name": strategy.name,
                "symbol": strategy.symbol,
                "enabled": strategy.enabled,
                "is_running": strategy.is_running,
                "version": strategy.strategy_version,
                "prompt": strategy.prompt,
                "params": strategy.params,
                "goal": strategy.goal,
                "goal_unit": strategy.goal_unit,
                "position": {
                    "symbol": position.symbol,
                    "quantity": position.quantity,
                    "direction": position.direction,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "pnl": position.pnl
                } if position and position.quantity > 0 else None
            }
        
        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>/enable', methods=['POST'])
def enable_strategy(strategy_id):
    """啟用策略"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            result = tools.enable_strategy(strategy_id)
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>/disable', methods=['POST'])
def disable_strategy(strategy_id):
    """停用策略"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            # 先檢查是否有部位
            position = tools.position_mgr.get_position(strategy_id)
            
            if position and position.quantity > 0:
                # 有部位，需要確認
                return jsonify({
                    "needs_confirmation": True,
                    "title": "確認停用",
                    "message": f"此策略仍有部位，停用將強制平倉",
                    "position": {
                        "symbol": position.symbol,
                        "quantity": position.quantity,
                        "direction": position.direction
                    },
                    "risks": [
                        f"強制平倉 ({position.quantity}口 {position.symbol})",
                        "策略將被停用"
                    ]
                })
            
            result = tools.disable_strategy(strategy_id)
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>/disable', methods=['DELETE'])
def confirm_disable_strategy(strategy_id):
    """確認停用策略（強制平倉）"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            result = tools.confirm_disable_strategy(strategy_id)
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """刪除策略"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            # 先檢查是否有部位
            position = tools.position_mgr.get_position(strategy_id)
            
            if position and position.quantity > 0:
                # 有部位，需要確認
                return jsonify({
                    "needs_confirmation": True,
                    "title": "確認刪除",
                    "message": "此策略仍有部位，刪除將強制平倉",
                    "position": {
                        "symbol": position.symbol,
                        "quantity": position.quantity,
                        "direction": position.direction
                    },
                    "risks": [
                        f"強制平倉 ({position.quantity}口 {position.symbol})",
                        "策略及所有資料將被刪除"
                    ]
                })
            
            result = tools.delete_strategy_tool(strategy_id)
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>/delete', methods=['DELETE'])
def confirm_delete_strategy(strategy_id):
    """確認刪除策略（強制平倉）"""
    try:
        tools = current_app.trading_tools
        with current_app.lock:
            result = tools.confirm_delete_strategy(strategy_id)
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
