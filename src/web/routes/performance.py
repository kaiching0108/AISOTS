"""Performance API Routes"""
from flask import Blueprint, jsonify, current_app, request

bp = Blueprint('performance', __name__, url_prefix='/api')


@bp.route('/performance', methods=['GET'])
def get_performance():
    """取得總績效數據（全部策略）
    
    Query Parameters:
        period: 查詢週期 (today/week/month/quarter/year/all)，預設為 all
        
    Returns:
        包含全部策略的已實現損益（未含未實現）的績效數據
    """
    try:
        tools = current_app.trading_tools
        period = request.args.get('period', 'all')
        
        # 計算已實現損益（從所有策略的已平倉訊號）
        all_pnl_values = []
        total_trades = 0
        win_count = 0
        lose_count = 0
        total_wins = 0
        total_losses = 0
        
        # 收集所有策略的信號數據
        all_signals = []
        all_pnl_values = []
        
        # 取得所有策略
        strategies = tools.strategy_mgr.get_all_strategies()
        analyzer = tools._get_performance_analyzer()
        
        # 各策略績效明細
        strategy_performances = []
        
        for strategy in strategies:
            try:
                analysis = analyzer.analyze(strategy.id, period=period)
                stats = analysis.get('signal_stats', {})
                
                trades = stats.get('filled_signals', 0)
                if trades > 0:
                    # 收集各策略的績效
                    strategy_performances.append({
                        "strategy_id": strategy.id,
                        "strategy_name": strategy.name,
                        "total_trades": trades,
                        "win_rate": stats.get('win_rate', 0),
                        "profit_factor": stats.get('profit_factor', 0),
                        "total_pnl": stats.get('total_pnl', 0)
                    })
                
                # 累加總數據
                total_trades += trades
                win_count += stats.get('win_count', 0)
                lose_count += stats.get('lose_count', 0)
                
                # 收集 pnl 值用於計算 profit_factor 和 equity_curve
                equity_curve = stats.get('equity_curve', [])
                all_signals.extend(equity_curve)
                
                # 收集單筆交易PnL用於計算 profit_factor
                trade_dist = stats.get('trade_distribution', [])
                all_pnl_values.extend(trade_dist)
                
                # 計算總獲利和總虧損
                for pnl in trade_dist:
                    if pnl > 0:
                        total_wins += pnl
                    elif pnl < 0:
                        total_losses += abs(pnl)
                        
            except Exception as e:
                # 忽略單一策略分析錯誤，繼續處理其他策略
                continue
        
        # 計算 profit_factor
        profit_factor = 0
        if total_losses > 0:
            profit_factor = total_wins / total_losses
        elif total_wins > 0:
            profit_factor = float('inf')
        
        # 計算總損益
        total_pnl = sum(all_pnl_values) if all_pnl_values else 0
        
        # 計算 equity_curve（按日期排序並合併）
        equity_curve = {}
        for item in all_signals:
            date = item.get('date', '')
            pnl = item.get('pnl', 0)
            if date:
                equity_curve[date] = equity_curve.get(date, 0) + pnl
        
        # 轉換為排序後的列表
        equity_curve_list = [
            {"date": k, "pnl": round(v, 2)} 
            for k, v in sorted(equity_curve.items())
        ]
        
        return jsonify({
            "success": True,
            "period": period,
            "total_trades": total_trades,
            "win_count": win_count,
            "lose_count": lose_count,
            "win_rate": (win_count / total_trades * 100) if total_trades > 0 else 0,
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else 0,
            "total_pnl": round(total_pnl, 2) if total_pnl else 0,
            "realized_pnl": round(total_pnl, 2) if total_pnl else 0,
            "unrealized_pnl": 0,
            "equity_curve": equity_curve_list,
            "trade_distribution": [round(p, 2) for p in all_pnl_values] if all_pnl_values else [],
            "strategy_performances": strategy_performances
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
            "profit_factor": stats.get('profit_factor', 0),
            "total_pnl": stats.get('total_pnl', 0),
            "avg_pnl": stats.get('avg_pnl', 0),
            "avg_profit": stats.get('avg_profit', 0),
            "avg_loss": stats.get('avg_loss', 0),
            "best_trade": stats.get('best_trade', 0),
            "worst_trade": stats.get('worst_trade', 0),
            "max_drawdown": stats.get('max_drawdown', 0),
            "stop_loss_count": stats.get('stop_loss_count', 0),
            "take_profit_count": stats.get('take_profit_count', 0),
            "signal_reversal_count": stats.get('signal_reversal_count', 0),
            "equity_curve": stats.get('equity_curve', []),
            "trade_distribution": stats.get('trade_distribution', [])
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
