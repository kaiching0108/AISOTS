"""規則解析器 - 使用 LLM 將策略提示轉換為 JSON 規則"""
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.logger import logger

RULE_PARSER_PROMPT = """你是一個期貨交易策略規則解析器。你的任務是將用戶的策略描述轉換為結構化的 JSON 規則。

## 可用的技術指標

1. **價格突破類**:
   - `price_breaks_high` - 價格突破 N 周期高點
   - `price_below_low` - 價格跌破 N 周期低點
   - `price_breaks_ma` - 價格突破移動平均線
   - `price_below_ma` - 價格跌破移動平均線

2. **RSI 類**:
   - `rsi_oversold` - RSI 低於超賣閾值 (預設 30)
   - `rsi_overbought` - RSI 高於超買閾值 (預設 70)
   - `rsi_cross_up` - RSI 從下往上穿越 threshold
   - `rsi_cross_down` - RSI 從上往下穿越 threshold

3. **MACD 類**:
   - `macd_cross_up` - MACD 從下往上穿越 Signal 線
   - `macd_cross_down` - MACD 從上往下穿越 Signal 線
   - `macd_histogram_positive` - MACD Histogram 為正
   - `macd_histogram_negative` - MACD Histogram 為負

4. **MA 交叉類**:
   - `ma_cross_up` - 短期 MA 從下往上穿越長期 MA (多頭訊號)
   - `ma_cross_down` - 短期 MA 從上往下穿越長期 MA (空頭訊號)

5. **成交量類**:
   - `volume_surge` - 成交量突增 (超過 N 倍平均)
   - `volume_decline` - 成交量萎縮

6. **連續漲跌類**:
   - `consecutive_up` - 連續 N 根漲停/上漲
   - `consecutive_down` - 連續 N 根跌停/下跌

7. **布林帶類**:
   - `price_at_upper_band` - 價格觸及上軌
   - `price_at_lower_band` - 價格觸及下軌
   - `price_breaks_upper` - 價格突破上軌
   - `price_breaks_lower` - 價格跌破下軌

8. **KD 指標類**:
   - `kd_oversold` - K 值低於 20 (超賣)
   - `kd_overbought` - K 值高於 80 (超買)
   - `kd_cross_up` - K 線從下往上穿越 D 線
   - `kd_cross_down` - K 線從上往下穿越 D 線

## 參數說明

- `entry_indicator`: 入場指標名稱
- `entry_params`: 入場指標參數 (如週期、閾值等)
- `exit_indicator`: 出場指標名稱
- `exit_params`: 出場指標參數
- `stop_loss_points`: 停損點數
- `take_profit_points`: 停利點數
- `position_size`: 倉位大小 (口數)
- `timeframe`: 時間週期 (1m, 5m, 15m, 30m, 1h, 1d)

## 輸出格式

請輸出 JSON 格式的規則，不要包含其他文字說明。

```json
{
  "entry_indicator": "price_breaks_high",
  "entry_params": {"period": 20},
  "exit_indicator": "price_below_low",
  "exit_params": {"period": 10},
  "stop_loss_points": 50,
  "take_profit_points": 100,
  "position_size": 2,
  "timeframe": "15m"
}
```

## 策略描述

{prompt}

## 輸出

"""

DEFAULT_RULES = {
    "entry_indicator": "price_breaks_high",
    "entry_params": {"period": 20},
    "exit_indicator": "price_below_low",
    "exit_params": {"period": 10},
    "stop_loss_points": 50,
    "take_profit_points": 100,
    "position_size": 1,
    "timeframe": "15m"
}


class RuleParser:
    """規則解析器"""
    
    def __init__(self, llm_provider=None):
        """初始化規則解析器
        
        Args:
            llm_provider: LLM provider 實例
        """
        self.llm_provider = llm_provider
    
    async def parse(self, prompt: str) -> Dict[str, Any]:
        """解析策略提示為 JSON 規則
        
        Args:
            prompt: 策略描述文字
            
        Returns:
            解析後的規則字典
        """
        if not self.llm_provider:
            logger.warning("No LLM provider, using default rules")
            return DEFAULT_RULES.copy()
        
        try:
            messages = [
                {"role": "system", "content": "You are a trading strategy rule parser. Output ONLY valid JSON, no other text."},
                {"role": "user", "content": RULE_PARSER_PROMPT.format(prompt=prompt)}
            ]
            
            response = await self.llm_provider.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            rules = self._parse_json_response(response)
            
            if rules:
                logger.info(f"Successfully parsed rules: {rules.get('entry_indicator')} -> {rules.get('exit_indicator')}")
                return rules
            else:
                logger.warning("Failed to parse LLM response, using default rules")
                return DEFAULT_RULES.copy()
                
        except Exception as e:
            logger.error(f"Error parsing rules with LLM: {e}")
            return DEFAULT_RULES.copy()
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """從 LLM 回應中解析 JSON
        
        Args:
            response: LLM 回應文字
            
        Returns:
            解析後的規則字典，失敗返回 None
        """
        try:
            response = response.strip()
            
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end == -1:
                    end = len(response)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end == -1:
                    end = len(response)
                response = response[start:end].strip()
            
            rules = json.loads(response)
            
            required_fields = ["entry_indicator", "exit_indicator"]
            for field in required_fields:
                if field not in rules:
                    logger.warning(f"Missing required field: {field}")
                    return None
            
            defaults = {
                "entry_params": {},
                "exit_params": {},
                "stop_loss_points": 50,
                "take_profit_points": 100,
                "position_size": 1,
                "timeframe": "15m"
            }
            for key, value in defaults.items():
                if key not in rules:
                    rules[key] = value
            
            return rules
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
            return None
    
    def validate_rules(self, rules: Dict[str, Any]) -> bool:
        """驗證規則格式是否正確
        
        Args:
            rules: 規則字典
            
        Returns:
            是否通過驗證
        """
        required_fields = [
            "entry_indicator",
            "exit_indicator",
            "stop_loss_points",
            "take_profit_points",
            "position_size",
            "timeframe"
        ]
        
        for field in required_fields:
            if field not in rules:
                logger.warning(f"Missing required field: {field}")
                return False
        
        valid_indicators = [
            "price_breaks_high", "price_below_low", "price_breaks_ma", "price_below_ma",
            "rsi_oversold", "rsi_overbought", "rsi_cross_up", "rsi_cross_down",
            "macd_cross_up", "macd_cross_down", "macd_histogram_positive", "macd_histogram_negative",
            "ma_cross_up", "ma_cross_down",
            "volume_surge", "volume_decline",
            "consecutive_up", "consecutive_down",
            "price_at_upper_band", "price_at_lower_band", "price_breaks_upper", "price_breaks_lower",
            "kd_oversold", "kd_overbought", "kd_cross_up", "kd_cross_down"
        ]
        
        if rules.get("entry_indicator") not in valid_indicators:
            logger.warning(f"Invalid entry indicator: {rules.get('entry_indicator')}")
            return False
        
        if rules.get("exit_indicator") not in valid_indicators:
            logger.warning(f"Invalid exit indicator: {rules.get('exit_indicator')}")
            return False
        
        return True
