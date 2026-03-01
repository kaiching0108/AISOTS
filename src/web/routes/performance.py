"""Performance API Routes"""
from flask import Blueprint, jsonify, current_app, request

bp = Blueprint('performance', __name__, url_prefix='/api')


@bp.route('/performance', methods=['GET'])
def get_performance():
    """取得績效數據
    
    Query Parameters:
        period: 查詢週期 (today/week/month/quarter/year/all)，預設為 today
        
    Returns:
        包含當日損益（已實現 + 未實現）的績效數據
    """
    try:
        tools = current_app.trading_tools
        period = request.args.get('period', 'today')
        
        # 取得當前部位損益（未實現）
        positions_summary = tools.position_mgr.get_positions_summary()
        unrealized_pnl = positions_summary.get('total_pnl', 0)
        
        # 計算已實現損益（從所有策略的已平倉訊號）
        realized_pnl = 0
        total_trades = 0
        win_count = 0
        lose_count = 0
        
        # 取得所有策略
        strategies = tools.strategy_mgr.get_all_strategies()
        
        for strategy in strategies:
            try:
                # 使用 PerformanceAnalyzer 分析每個策略
                analyzer = tools._get_performance_analyzer()
                analysis = analyzer.analyze(strategy.id, period=period)
                stats = analysis.get('signal_stats', {})
                
                # 累加已實現損益
                pnl = stats.get('total_pnl', 0)
                if pnl:
                    realized_pnl += pnl
                    total_trades += stats.get('filled_signals', 0)
                    win_count += stats.get('win_count', 0)
                    lose_count += stats.get('lose_count', 0)
            except Exception as e:
                # 忽略單一策略分析錯誤，繼續處理其他策略
                continue
        
        # 總損益 = 已實現 + 未實現
        total_pnl = realized_pnl + unrealized_pnl
        
        return jsonify({
            "success": True,
            "period": period,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_pnl": total_pnl,
            "total_trades": total_trades,
            "win_count": win_count,
            "lose_count": lose_count,
            "win_rate": (win_count / total_trades * 100) if total_trades > 0 else 0
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('/performance/<strategy_id>', methods=['GET'])
def get_strategy_performance(strategy_id):
    """取得特定策略的績效
    
    Args:
        strategy_id: 策略 ID
        
    Query Parameters:
        period: 查詢週期 (today/week/month/quarter/year/all)，預設為 all
        
    Returns:
        特定策略的績效數據
    """
    try:
        tools = current_app.trading_tools
        period = request.args.get('period', 'all')
        
        # 檢查策略是否存在
        strategy = tools.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return jsonify({
                "success": False,
                "error": f"找不到策略: {strategy_id}"
            }), 404
        
        # 取得該策略的績效分析
        analyzer = tools._get_performance_analyzer()
        analysis = analyzer.analyze(strategy_id, period=period)
        stats = analysis.get('signal_stats', {})
        
        return jsonify({
            "success": True,
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "period": period,
            "period_display": _get_period_display(period),
            "begin_date": analysis.get('begin_date'),
            "end_date": analysis.get('end_date'),
            "total_signals": stats.get('total_signals', 0),
            "filled_signals": stats.get('filled_signals', 0),
            "win_count": stats.get('win_count', 0),
            "lose_count": stats.get('lose_count', 0),
            "win_rate": stats.get('win_rate', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "avg_pnl": stats.get('avg_pnl', 0),
            "avg_profit": stats.get('avg_profit', 0),
            "avg_loss": stats.get('avg_loss', 0),
            "best_trade": stats.get('best_trade', 0),
            "worst_trade": stats.get('worst_trade', 0),
            "max_drawdown": stats.get('max_drawdown', 0),
            "stop_loss_count": stats.get('stop_loss_count', 0),
            "take_profit_count": stats.get('take_profit_count', 0),
            "signal_reversal_count": stats.get('signal_reversal_count', 0)
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _get_period_display(period: str) -> str:
    """取得週期的顯示名稱"""
    period_names = {
        "today": "今日",
        "week": "本週",
        "month": "本月",
        "quarter": "本季",
        "year": "本年",
        "all": "全部"
    }
    return period_names.get(period, period)
