"""LLM 策略生成器 - 將用戶描述轉換為策略程式碼"""
import logging
from typing import Optional, Dict, Any
import re

logger = logging.getLogger(__name__)

STRATEGY_GENERATOR_PROMPT = """
你是一個期貨策略生成器。請根據用戶的策略描述，生成可在框架中執行的策略類別。

## 框架規範

### 1. 策略類別必須繼承 TradingStrategy

```python
from src.engine.framework import TradingStrategy, BarData

class MyStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        return 'hold'
```

### 2. 可用的屬性

- `self.position`: 當前部位（正=多單，負=空單，0=無部位）
- `self.entry_price`: 進場價格
- `self.context`: 字典，可儲存任意自定義狀態
- `self.symbol`: 合約代碼

### 3. 可用的 K 棒屬性與方法

- `bar.timestamp`: 時間戳
- `bar.open`, `bar.high`, `bar.low`, `bar.close`: 價格
- `bar.volume`: 成交量
- `bar.pct_change`: 從開盤到收盤的漲跌幅（小數，如 0.05 代表 5%）
- `bar.get_change_from(price)`: 相對於某價格的漲跌幅

### 4. 可用的歷史資料方法

- `self.get_bars()`: 取得所有歷史 K 棒
- `self.get_bars(10)`: 取得最近 10 根 K 棒
- `self.get_dataframe(100)`: 取得 pandas DataFrame（用於 pandas_ta）

### 5. 可用的技術指標（只能使用 pandas_ta）

使用 `self.ta(指標名稱, **參數)` 調用：

| 指標名稱 | 說明 | 參數 |
|---------|------|------|
| RSI | 相對強弱指標 | period=14 |
| MACD | 指數平滑異同移動平均線 | fast=12, slow=26, signal=9 |
| SMA | 簡單移動平均 | period=20 |
| EMA | 指數移動平均 | period=20 |
| BB | 布林帶 | period=20, std=2.0 |
| ATR | 平均真實波幅 | period=14 |
| STOCH | KD 指標 | period=14 |
| ADX | 平均趨向指標 | period=14 |
| CCI | 商品通道指標 | period=20 |
| OBV | 能量潮 | 無 |
| VWAP | 成交量加權平均價 | 無 |
| WILLR | 威廉指標 | period=14 |

### 6. 回傳值（必須是以下其中之一）

- `'buy'`: 買進開多
- `'sell'`: 賣出開空
- `'close'`: 平倉
- `'hold'`: 無動作

### 7. 範例：用戶策略 → 程式碼

**用戶策略**：「RSI 低于 30 买入，RSI 高于 70 卖出」

```python
class RSIStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        rsi = self.ta('RSI', period=14)
        
        if rsi is None or len(rsi) < 2:
            return 'hold'
        
        current_rsi = rsi.iloc[-1]
        
        if self.position == 0:
            if current_rsi < 30:
                return 'buy'
        else:
            if current_rsi > 70:
                return 'close'
        
        return 'hold'
```

**用戶策略**：「MACD 金叉買入，死叉賣出」

```python
class MACDCrossStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        macd = self.ta('MACD', fast=12, slow=26, signal=9)
        
        if macd is None or len(macd) < 4:
            return 'hold'
        
        macd_line = macd.iloc[:, 0]
        signal_line = macd.iloc[:, 2]
        
        current_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        current_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        
        if self.position == 0:
            if prev_macd <= prev_signal and current_macd > current_signal:
                return 'buy'
        else:
            if prev_macd >= prev_signal and current_macd < current_signal:
                return 'close'
        
        return 'hold'
```

**用戶策略**：「買進後，如果遇到漲停板隔日跌-6%以上就平倉」

```python
class LimitUpStrategy(TradingStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol)
    
    def on_bar(self, bar: BarData) -> str:
        bars = self.get_bars(2)
        if len(bars) < 2:
            return 'hold'
        
        yesterday = bars[-2]
        
        limit_up = yesterday.close * 1.095
        
        if self.position > 0:
            if self.context.get('was_limit_up', False):
                pct_loss = (bar.close - self.entry_price) / self.entry_price
                if pct_loss <= -0.06:
                    self.context['was_limit_up'] = False
                    return 'close'
            
            if bar.close >= limit_up:
                self.context['was_limit_up'] = True
        
        if self.position == 0:
            if bar.close >= limit_up:
                self.context['was_limit_up'] = True
                return 'buy'
        
        return 'hold'
```

### 8. 用戶策略描述

{prompt}

## 輸出格式

請生成完整的策略類別程式碼，只輸出 Python 程式碼，不要有其他說明或註解。確保：
1. 類別繼承 TradingStrategy
2. 實作 on_bar 方法
3. 只使用 self.ta() 調用技術指標
4. 回傳值為 'buy', 'sell', 'close', 'hold' 之一
"""


class LLMGenerator:
    """LLM 策略生成器"""
    
    def __init__(self, llm_provider=None):
        self.llm_provider = llm_provider
        self._cache: Dict[str, str] = {}
    
    async def generate(self, prompt: str) -> Optional[str]:
        """生成策略程式碼"""
        
        if prompt in self._cache:
            logger.info("Using cached strategy code")
            return self._cache[prompt]
        
        if not self.llm_provider:
            logger.warning("No LLM provider, cannot generate strategy")
            return None
        
        try:
            messages = [
                {"role": "system", "content": "You are a trading strategy generator. Output ONLY valid Python code, no explanations."},
                {"role": "user", "content": STRATEGY_GENERATOR_PROMPT.format(prompt=prompt)}
            ]
            
            response = await self.llm_provider.chat(
                messages=messages,
                temperature=0.2,
                max_tokens=2000
            )
            
            code = self._extract_code(response)
            
            if code:
                logger.info("Strategy code generated successfully")
                self._cache[prompt] = code
                return code
            else:
                logger.error("Failed to extract code from LLM response")
                return None
                
        except Exception as e:
            logger.error(f"Error generating strategy: {e}")
            return None
    
    def _extract_code(self, response: str) -> Optional[str]:
        """從回應中提取程式碼"""
        
        response = response.strip()
        
        if "```python" in response:
            start = response.find("```python") + 9
            end = response.find("```", start)
            if end == -1:
                end = len(response)
            return response[start:end].strip()
        
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end == -1:
                end = len(response)
            return response[start:end].strip()
        
        if "class " in response and "on_bar" in response:
            return response
        
        return None
    
    def extract_class_name(self, code: str) -> Optional[str]:
        """從程式碼中提取類別名稱"""
        
        match = re.search(r'class\s+(\w+)\s*\(', code)
        if match:
            return match.group(1)
        
        return None
    
    def compile_strategy(self, code: str, class_name: Optional[str] = None) -> Optional[type]:
        """編譯策略類別"""
        
        try:
            if class_name is None:
                class_name = self.extract_class_name(code)
            
            if class_name is None:
                logger.error("Cannot extract class name from code")
                return None
            
            namespace = {}
            exec(code, namespace)
            
            strategy_class = namespace.get(class_name)
            
            if strategy_class is None:
                logger.error(f"Class {class_name} not found in generated code")
                return None
            
            from src.engine.framework import TradingStrategy
            if not issubclass(strategy_class, TradingStrategy):
                logger.error(f"Class must inherit from TradingStrategy")
                return None
            
            logger.info(f"Strategy class {class_name} compiled successfully")
            return strategy_class
            
        except SyntaxError as e:
            logger.error(f"Syntax error in generated code: {e}")
            return None
        except Exception as e:
            logger.error(f"Error compiling strategy: {e}")
            return None
    
    def validate_code(self, code: str) -> bool:
        """驗證策略程式碼是否正確"""
        
        class_name = self.extract_class_name(code)
        if class_name is None:
            return False
        
        strategy_class = self.compile_strategy(code, class_name)
        return strategy_class is not None
    
    def clear_cache(self) -> None:
        """清除快取"""
        self._cache.clear()
