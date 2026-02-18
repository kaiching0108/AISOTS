"""績效分析器 - 分析策略交易績效"""
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from src.analysis.signal_recorder import SignalRecorder


class PerformanceAnalyzer:
    """分析策略績效"""
    
    def __init__(self, signal_recorder: SignalRecorder):
        self.recorder = signal_recorder
    
    def analyze(
        self, 
        strategy_id: str, 
        period: str = "month"
    ) -> Dict[str, Any]:
        """完整績效分析
        
        Args:
            strategy_id: 策略 ID
            period: 查詢週期 (today/week/month/quarter/year/all)
            
        Returns:
            dict: 績效分析結果
        """
        begin_date, end_date = self._calculate_date_range(period)
        
        signals = self._filter_by_date(
            self.recorder.get_filled_signals(strategy_id),
            begin_date,
            end_date
        )
        
        signal_stats = self._analyze_signals(signals)
        
        return {
            "strategy_id": strategy_id,
            "period": period,
            "begin_date": begin_date,
            "end_date": end_date,
            "signal_stats": signal_stats,
        }
    
    def _calculate_date_range(self, period: str) -> Tuple[Optional[str], Optional[str]]:
        """計算日期範圍
        
        Args:
            period: today/week/month/quarter/year/all
            
        Returns:
            (begin_date, end_date) in YYYY-MM-DD format
        """
        today = date.today()
        end_date = today.isoformat()
        
        if period == "today":
            begin_date = end_date
        elif period == "week":
            start = today - timedelta(days=today.weekday())
            begin_date = start.isoformat()
        elif period == "month":
            begin_date = today.replace(day=1).isoformat()
        elif period == "quarter":
            quarter_month = (today.month - 1) // 3 * 3 + 1
            begin_date = today.replace(month=quarter_month, day=1).isoformat()
        elif period == "year":
            begin_date = today.replace(month=1, day=1).isoformat()
        else:  # all
            begin_date = None
            end_date = None
            
        return begin_date, end_date
    
    def _filter_by_date(
        self, 
        signals: List[Dict[str, Any]], 
        begin_date: Optional[str], 
        end_date: Optional[str]
    ) -> List[Dict[str, Any]]:
        """按日期過濾訊號"""
        if not begin_date or not end_date:
            return signals
            
        filtered = []
        for sig in signals:
            sig_date = sig.get("timestamp", "")[:10]
            if begin_date <= sig_date <= end_date:
                filtered.append(sig)
                
        return filtered
    
    def _analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析訊號統計"""
        if not signals:
            return {
                "total_signals": 0,
                "filled_signals": 0,
                "win_count": 0,
                "lose_count": 0,
                "win_rate": 0.0,
                "stop_loss_count": 0,
                "take_profit_count": 0,
                "signal_reversal_count": 0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0
            }
        
        pnl_values = [s.get("pnl", 0) for s in signals if s.get("pnl") is not None]
        wins = [p for p in pnl_values if p > 0]
        losses = [p for p in pnl_values if p < 0]
        
        stop_loss_count = len([s for s in signals if s.get("exit_reason") == "stop_loss"])
        take_profit_count = len([s for s in signals if s.get("exit_reason") == "take_profit"])
        signal_reversal_count = len([s for s in signals if s.get("exit_reason") == "signal_reversal"])
        
        return {
            "total_signals": len(signals),
            "filled_signals": len(signals),
            "win_count": len(wins),
            "lose_count": len(losses),
            "win_rate": len(wins) / len(pnl_values) * 100 if pnl_values else 0.0,
            "stop_loss_count": stop_loss_count,
            "take_profit_count": take_profit_count,
            "signal_reversal_count": signal_reversal_count,
            "total_pnl": sum(pnl_values),
            "avg_pnl": sum(pnl_values) / len(pnl_values) if pnl_values else 0.0,
            "best_trade": max(pnl_values) if pnl_values else 0.0,
            "worst_trade": min(pnl_values) if pnl_values else 0.0
        }
    
    def format_performance_report(
        self, 
        strategy_id: str, 
        period: str = "month"
    ) -> str:
        """格式化績效報告"""
        analysis = self.analyze(strategy_id, period)
        stats = analysis["signal_stats"]
        
        period_names = {
            "today": "今日",
            "week": "本週",
            "month": "本月",
            "quarter": "本季",
            "year": "本年",
            "all": "全部"
        }
        
        period_name = period_names.get(period, period)
        begin = analysis.get("begin_date", "")
        end = analysis.get("end_date", "")
        
        if begin and end and begin != end:
            date_range = f"({begin} ~ {end})"
        elif begin:
            date_range = f"({begin})"
        else:
            date_range = ""
        
        text = f"""📈 策略績效: {strategy_id} {period_name} {date_range}
─────────────
總訊號數: {stats['total_signals']}
成交次數: {stats['filled_signals']}
獲利次數: {stats['win_count']}
虧損次數: {stats['lose_count']}
勝率: {stats['win_rate']:.1f}%

已實現損益: {stats['total_pnl']:+,.0f}元
平均交易損益: {stats['avg_pnl']:+,.0f}元
最大單次獲利: {stats['best_trade']:+,.0f}元
最大單次虧損: {stats['worst_trade']:+,.0f}元

停損觸發: {stats['stop_loss_count']}次
止盈觸發: {stats['take_profit_count']}次
訊號反向: {stats['signal_reversal_count']}次"""
        
        return text
    
    def check_goal_achieved(
        self,
        goal: float,
        goal_unit: str,
        period_profit: float,
        period_days: int
    ) -> bool:
        """檢查目標是否達成
        
        Args:
            goal: 目標數值
            goal_unit: 目標單位 (daily/weekly/monthly/quarterly/yearly)
            period_profit: 期間損益
            period_days: 期間天數
            
        Returns:
            bool: 是否達成目標
        """
        if goal is None or goal <= 0:
            return False
            
        if goal_unit == "daily":
            avg_daily = period_profit / period_days if period_days > 0 else 0
            return avg_daily >= goal
        elif goal_unit == "weekly":
            avg_weekly = period_profit / (period_days / 7) if period_days > 0 else 0
            return avg_weekly >= goal
        elif goal_unit == "monthly":
            return period_profit >= goal
        elif goal_unit == "quarterly":
            return period_profit >= goal
        elif goal_unit == "yearly":
            return period_profit >= goal
            
        return False
