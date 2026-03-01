"""Strategies API Routes"""
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('strategies', __name__, url_prefix='/api/strategies')


def get_strategy_data(trading_tools):
    """取得策略資料（JSON格式）"""
    strategies = trading_tools.strategy_mgr.get_all_strategies()
    strategies.sort(key=lambda s: s.id)
    
    # 一次性取得所有位置，避免重複查詢
    all_positions = {p.strategy_id: p for p in trading_tools.position_mgr.get_all_positions()}
    
    result = []
    for s in strategies:
        position = all_positions.get(s.id)
        
        result.append({
            "id": s.id,
            "name": s.name,
            "symbol": s.symbol,
            "enabled": s.enabled,
            "is_running": s.is_running,
            "direction": s.direction or "long",
            "version": s.strategy_version,
            "timeframe": s.params.get("timeframe") if s.params else None,
            "quantity": s.params.get("quantity") if s.params else None,
            "stop_loss": s.params.get("stop_loss") if s.params else None,
            "take_profit": s.params.get("take_profit") if s.params else None,
            "created_at": s.created_at.strftime("%Y-%m-%d") if s.created_at and hasattr(s.created_at, 'strftime') else (s.created_at if s.created_at else None),
            "goal": s.goal,
            "goal_unit": s.goal_unit or "daily",
            "review_period": s.review_period if s.review_period else 5,
            "review_unit": s.review_unit or "day",
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
            "strategy_code": strategy.strategy_code,
            "params": strategy.params,
            "goal": strategy.goal,
            "goal_unit": strategy.goal_unit,
            "review_period": strategy.review_period,
            "review_unit": strategy.review_unit,
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


@bp.route('/<strategy_id>/goal', methods=['POST'])
def update_strategy_goal(strategy_id):
    """更新策略目標和自動 Review 設定"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "無效的請求資料"
            }), 400
        
        tools = current_app.trading_tools
        strategy = tools.strategy_mgr.get_strategy(strategy_id)
        
        if not strategy:
            return jsonify({
                "success": False,
                "error": "Strategy not found"
            }), 404
        
        if "goal" in data:
            strategy.goal = data["goal"]
        if "goal_unit" in data:
            strategy.goal_unit = data["goal_unit"]
        if "review_period" in data:
            strategy.review_period = data["review_period"]
        if "review_unit" in data:
            strategy.review_unit = data["review_unit"]
        
        tools.strategy_mgr.save_strategy(strategy)
        
        return jsonify({
            "success": True,
            "message": "目標設定已更新"
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
        result = tools.enable_strategy(strategy_id)
        
        # 檢查是否需要確認（舊策略有部位）
        if tools._pending_enable and tools._pending_enable.get("strategy_id") == strategy_id:
            pending = tools._pending_enable
            return jsonify({
                "needs_confirmation": True,
                "title": "確認啟用",
                "message": f"舊策略 {pending['old_strategy_id']} 仍有 {pending['quantity']}口 部位",
                "position": {
                    "symbol": pending['symbol'],
                    "quantity": pending['quantity'],
                    "direction": pending['direction'],
                    "pnl": pending['pnl'],
                    "entry_price": pending['entry_price'],
                    "current_price": pending['current_price']
                },
                "risks": [
                    f"強制平倉 {pending['old_strategy_id']} ({pending['quantity']}口 {pending['symbol']})",
                    f"損益: {pending['pnl']:+,.0f}",
                    "啟用新策略"
                ]
            })
        
        return jsonify({
            "success": "找不到" not in result and "❌" not in result,
            "message": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/<strategy_id>/enable', methods=['DELETE'])
def confirm_enable_strategy(strategy_id):
    """確認啟用策略（強制平倉舊策略部位）"""
    try:
        tools = current_app.trading_tools
        result = tools.confirm_enable_with_close(strategy_id)
        
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
        position = tools.position_mgr.get_position(strategy_id)
        
        if position and position.quantity > 0:
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
        position = tools.position_mgr.get_position(strategy_id)
        
        if position and position.quantity > 0:
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
