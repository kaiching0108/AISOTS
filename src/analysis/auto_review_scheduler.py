"""自動 LLM Review 排程器"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AutoReviewScheduler:
    """自動 LLM Review 排程器
    
    功能：
    - 根據 config 中的排程設定，定期觸發 LLM 策略審查
    - 跳過沒有設定 goal 的策略
    - 每天每個策略最多觸發 1 次（排程觸發）
    - 手動執行 review 不受限制
    """
    
    def __init__(self, config, trading_tools, notifier):
        """初始化排程器
        
        Args:
            config: AppConfig 物件
            trading_tools: TradingTools 物件
            notifier: TelegramNotifier 物件
        """
        self.config = config
        self.tools = trading_tools
        self.notifier = notifier
        
        self.last_review_file = Path("workspace/auto_review_last.json")
        self.last_review_times: Dict[str, str] = {}
        self.last_trigger_date: Dict[str, str] = {}
        
        self._load_state()
    
    def _load_state(self) -> None:
        """載入上次 review 時間"""
        if self.last_review_file.exists():
            try:
                data = json.loads(self.last_review_file.read_text(encoding="utf-8"))
                self.last_review_times = data.get("last_review_times", {})
                self.last_trigger_date = data.get("last_trigger_date", {})
            except Exception as e:
                logger.warning(f"載入自動 review 狀態失敗: {e}")
                self.last_review_times = {}
                self.last_trigger_date = {}
    
    def _save_state(self) -> None:
        """儲存狀態"""
        try:
            data = {
                "last_review_times": self.last_review_times,
                "last_trigger_date": self.last_trigger_date
            }
            self.last_review_file.parent.mkdir(parents=True, exist_ok=True)
            self.last_review_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"儲存自動 review 狀態失敗: {e}")
    
    def check_and_trigger(self) -> None:
        """檢查是否需要觸發 review
        
        這個方法應該在主迴圈中定時被調用。
        """
        schedules = self.config.auto_review.schedules
        
        if not schedules:
            return
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        for schedule in schedules:
            strategy_id = schedule.strategy_id
            period = schedule.period
            unit = schedule.unit
            
            try:
                if self._should_trigger(strategy_id, period, unit, today_str):
                    self._trigger_review(strategy_id)
                    
                    self.last_review_times[strategy_id] = now.isoformat()
                    self.last_trigger_date[strategy_id] = today_str
                    self._save_state()
                    
                    logger.info(f"自動觸發策略 {strategy_id} 的 LLM Review")
            except Exception as e:
                logger.error(f"檢查排程 {strategy_id} 時發生錯誤: {e}")
    
    def _should_trigger(self, strategy_id: str, period: int, unit: str, today_str: str) -> bool:
        """檢查是否應該觸發
        
        Args:
            strategy_id: 策略 ID
            period: 週期數字
            unit: 單位 (day/week/month/quarter/year)
            today_str: 今天的日期字串
            
        Returns:
            bool: 是否應該觸發
        """
        strategy = self.tools.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            logger.debug(f"策略 {strategy_id} 不存在，跳過")
            return False
        
        if not strategy.goal or strategy.goal <= 0:
            logger.debug(f"策略 {strategy_id} 沒有設定目標，跳過")
            return False
        
        if self.last_trigger_date.get(strategy_id) == today_str:
            logger.debug(f"策略 {strategy_id} 今天已經觸發過，跳過")
            return False
        
        last_time_str = self.last_review_times.get(strategy_id)
        
        if not last_time_str:
            return True
        
        try:
            last_time = datetime.fromisoformat(last_time_str)
        except Exception:
            return True
        
        interval = self._calculate_interval(period, unit)
        if not interval:
            logger.warning(f"未知的單位: {unit}")
            return False
        
        next_trigger_time = last_time + interval
        now = datetime.now()
        
        return now >= next_trigger_time
    
    def _calculate_interval(self, period: int, unit: str) -> Optional[timedelta]:
        """計算時間間隔
        
        Args:
            period: 週期數字
            unit: 單位
            
        Returns:
            timedelta 或 None
        """
        if unit == "day":
            return timedelta(days=period)
        elif unit == "week":
            return timedelta(weeks=period)
        elif unit == "month":
            return timedelta(days=30 * period)
        elif unit == "quarter":
            return timedelta(days=90 * period)
        elif unit == "year":
            return timedelta(days=365 * period)
        
        return None
    
    def _trigger_review(self, strategy_id: str) -> None:
        """觸發 review 並發送通知
        
        Args:
            strategy_id: 策略 ID
        """
        strategy = self.tools.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return
        
        try:
            result = self.tools.review_strategy(strategy_id)
            
            header = f"""🔄 *自動 LLM Review 觸發*

策略: {strategy_id} ({strategy.name})
目標: 每日賺 {strategy.goal:,} 元

---
"""
            
            full_message = header + result
            
            self.notifier.send_long_message(full_message)
            
        except Exception as e:
            logger.error(f"執行自動 review 失敗: {e}")
            error_msg = f"""❌ *自動 LLM Review 失敗*

策略: {strategy_id}
錯誤: {str(e)}
"""
            self.notifier.send_message(error_msg)
    
    def get_status(self) -> Dict[str, any]:
        """取得排程器狀態
        
        Returns:
            dict: 狀態資訊
        """
        schedules = self.config.auto_review.schedules
        
        status = {
            "enabled": self.config.auto_review.enabled,
            "schedules_count": len(schedules),
            "strategies": []
        }
        
        for schedule in schedules:
            strategy_id = schedule.strategy_id
            strategy = self.tools.strategy_mgr.get_strategy(strategy_id)
            
            info = {
                "strategy_id": strategy_id,
                "strategy_name": strategy.name if strategy else "N/A",
                "has_goal": strategy.goal > 0 if strategy and strategy.goal else False,
                "period": schedule.period,
                "unit": schedule.unit,
                "last_review": self.last_review_times.get(strategy_id, "從未"),
                "last_trigger_date": self.last_trigger_date.get(strategy_id, "從未")
            }
            status["strategies"].append(info)
        
        return status
