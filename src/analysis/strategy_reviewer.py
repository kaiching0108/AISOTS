"""LLM 策略審查 - 讓 LLM 根據績效分析策略並給出建議"""
from typing import Dict, Any, Optional
from src.analysis.performance_analyzer import PerformanceAnalyzer


class StrategyReviewer:
    """讓 LLM 審查並建議策略修改"""
    
    def __init__(self, llm_provider, performance_analyzer: PerformanceAnalyzer):
        self.llm = llm_provider
        self.analyzer = performance_analyzer
    
    def review(self, strategy_id: str, strategy_info: Dict[str, Any] = None) -> str:
        """讓 LLM 審查策略
        
        Args:
            strategy_id: 策略 ID
            strategy_info: 策略資訊 (可選)
            
        Returns:
            str: LLM 審查結果和建議
        """
        analysis = self.analyzer.analyze(strategy_id, period="month")
        
        prompt = self._build_review_prompt(analysis, strategy_info)
        
        try:
            response = self.llm.chat(prompt)
            return response
        except Exception as e:
            return f"❌ LLM 審查失敗: {str(e)}"
    
    def _build_review_prompt(self, analysis: Dict[str, Any], strategy_info: Dict[str, Any] = None) -> str:
        """組建審查 prompt"""
        
        stats = analysis.get("signal_stats", {})
        goal_info = ""
        
        if strategy_info:
            goal = strategy_info.get("goal")
            goal_unit = strategy_info.get("goal_unit")
            if goal:
                unit_names = {
                    "daily": "每日",
                    "weekly": "每週", 
                    "monthly": "每月",
                    "quarterly": "每季",
                    "yearly": "每年"
                }
                unit_name = unit_names.get(goal_unit, "")
                goal_info = f"""
## 策略目標
目標: 每日賺 {goal} 元
目標單位: {unit_name}
"""
        
        prompt = f"""你是一個專業的交易策略分析師。請分析以下策略的績效並給出修改建議。

## 訊號統計
- 總訊號數：{stats.get('total_signals', 0)}
- 成交訊號：{stats.get('filled_signals', 0)}
- 勝率：{stats.get('win_rate', 0):.1f}%
- 獲利次數：{stats.get('win_count', 0)}
- 虧損次數：{stats.get('lose_count', 0)}
- 停損觸發：{stats.get('stop_loss_count', 0)}次
- 止盈觸發：{stats.get('take_profit_count', 0)}次
- 訊號反向：{stats.get('signal_reversal_count', 0)}次

## 損益統計
- 已實現損益：{stats.get('total_pnl', 0):+,.0f}元
- 平均交易損益：{stats.get('avg_pnl', 0):+,.0f}元
- 最大單次獲利：{stats.get('best_trade', 0):+,.0f}元
- 最大單次虧損：{stats.get('worst_trade', 0):+,.0f}元{goal_info}

請分析並給出建議：

1. 這個策略的問題是什麼？
2. 應該調整參數（停損/止盈/數量）還是修改交易邏輯（Prompt）？
3. 具體的修改建議是什麼？

請用以下格式回覆：

## 問題分析
[分析策略的主要問題]

## 建議類型
[參數調整 / Prompt 微調 / 重新設計]

## 具體建議
[明確的修改內容]

## 預期效果
[修改後可能帶來的效果]
"""
        return prompt
    
    def suggest_modification(
        self, 
        stats: Dict[str, Any],
        suggestion_type: str
    ) -> str:
        """根據建議類型生成具體的修改內容
        
        Args:
            stats: 統計數據
            suggestion_type: 建議類型 (parameter/prompt/redesign)
            
        Returns:
            str: 具體的修改內容
        """
        prompt = f"""根據以下統計數據，給出具體的參數調整建議：

統計數據：
- 勝率：{stats.get('win_rate', 0):.1f}%
- 停損觸發次數：{stats.get('stop_loss_count', 0)}
- 止盈觸發次數：{stats.get('take_profit_count', 0)}
- 平均交易損益：{stats.get('avg_pnl', 0):+,.0f}元
- 最大單次虧損：{stats.get('worst_trade', 0):+,.0f}元

建議類型：{suggestion_type}

請直接給出修改內容，不要其他說明。
"""
        try:
            response = self.llm.chat(prompt)
            return response
        except Exception as e:
            return f"無法生成建議: {str(e)}"
