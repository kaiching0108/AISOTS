from flask import Blueprint, render_template, request, jsonify, Response
from functools import wraps
import asyncio
import logging
import json
import re

logger = logging.getLogger(__name__)

create_bp = Blueprint('create', __name__)


def get_trading_tools():
    """获取 trading_tools 实例"""
    from flask import current_app
    return current_app.trading_tools


def get_llm_provider():
    """获取 LLM provider 实例"""
    from flask import current_app
    return current_app.llm_provider


@create_bp.route('/strategies/create')
def create_strategy_page():
    """显示创建策略页面"""
    return render_template('create_strategy.html')


@create_bp.route('/api/strategies/preview', methods=['POST'])
def preview_strategy():
    """LLM 填充/优化下视窗参数
    
    Request Body:
    {
        "symbol": "TMF",
        "prompt": "每日赚500元",
        "timeframe": "15m",
        "stop_loss": 30,
        "take_profit": 50,
        "quantity": 1
    }
    
    Response:
    {
        "success": true,
        "data": {
            "symbol": "TMF",
            "prompt": "...",
            "timeframe": "15m",
            "stop_loss": 30,
            "take_profit": 50,
            "quantity": 1
        }
    }
    """
    try:
        data = request.get_json()
        
        symbol = data.get('symbol', 'TMF').upper()
        prompt = data.get('prompt', '')
        direction = data.get('direction', 'long')  # 預設做多
        timeframe = data.get('timeframe', '15m')
        stop_loss = int(data.get('stop_loss', 0)) if data.get('stop_loss') else None
        take_profit = int(data.get('take_profit', 0)) if data.get('take_profit') else None
        quantity = int(data.get('quantity', 1))
        
        if not prompt:
            return jsonify({
                "success": False,
                "message": "请输入策略提示词"
            }), 400
        
        # 调用 LLM 生成完整的策略描述
        trading_tools = get_trading_tools()
        
        # 交易方向說明
        direction_text = {
            "long": "只做多 (只買進開多)",
            "short": "只做空 (只賣出開空)",
            "both": "多空都做"
        }
        
        # 构建生成策略描述的 prompt
        strategy_prompt = f"""請根據以下信息設計一個期貨交易策略：

## ⚠️ 重要：可交易期貨代碼說明

| 期貨代碼 | 名稱 | 點數價值 |
|---------|------|---------|
| TXF | 臺股期貨（大台） | 1點 = 200元 |
| MXF | 小型臺指（小台） | 1點 = 50元 |
| TMF | 微型臺指期貨 | 1點 = 10元 |

⚠️ 注意：TMF 是臺灣期貨交易所的「微型臺指期貨」，不是美國國債期貨！

---

期貨代碼：{symbol}
交易方向：{direction_text.get(direction, '多空都做')}
用戶目標/描述：{prompt}
時間框架：{timeframe}
停損：{stop_loss if stop_loss else '根據策略計算'}
止盈：{take_profit if take_profit else '根據策略計算'}
交易口數：{quantity}

請設計一個完整的交易策略，必須包含：
1. 使用的技術指標（如 RSI、MACD、均線、布林通道等）
2. 具體的買入條件
3. 具體的賣出條件
4. 停損止盈的執行邏輯
5. 風險控制建議

請用繁體中文回答，直接描述策略邏輯即可，不需要代碼。"""

        # 调用 LLM
        llm_provider = get_llm_provider()
        if not llm_provider:
            # 如果没有 LLM，直接使用用户输入
            return jsonify({
                "success": True,
                "data": {
                    "symbol": symbol,
                    "prompt": prompt,
                    "timeframe": timeframe,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "quantity": quantity
                }
            })
        
        try:
            response = asyncio.run(llm_provider.chat(
                messages=[
                    {"role": "system", "content": "你是一個專業的期貨交易策略分析師。請根據用戶的需求設計完整的交易策略。"},
                    {"role": "user", "content": strategy_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            ))
            
            content = response.get("content", "") if isinstance(response, dict) else str(response)
            
            # 尝试解析 LLM 返回的参数
            import re
            
            # 提取参数
            tf_match = re.search(r'時間框架[:：]\s*(\d+[mhd])', content, re.IGNORECASE)
            sl_match = re.search(r'(?:停損|止损)[:：]\s*(\d+)', content)
            tp_match = re.search(r'(?:止盈|停利)[:：]\s*(\d+)', content)
            qty_match = re.search(r'口數[:：]\s*(\d+)', content)
            
            inferred_timeframe = tf_match.group(1) if tf_match else timeframe
            inferred_stop_loss = int(sl_match.group(1)) if sl_match else (30 if symbol in ['TXF', 'MXF'] else 15)
            inferred_take_profit = int(tp_match.group(1)) if tp_match else (50 if symbol in ['TXF', 'MXF'] else 25)
            inferred_quantity = int(qty_match.group(1)) if qty_match else quantity
            
            # 如果用户已经提供了部分参数，优先使用用户的参数
            final_timeframe = timeframe if timeframe != '15m' else inferred_timeframe
            final_stop_loss = int(stop_loss) if stop_loss else inferred_stop_loss
            final_take_profit = int(take_profit) if take_profit else inferred_take_profit
            final_quantity = int(quantity) if quantity != 1 else inferred_quantity
            
            # 使用 LLM 生成的策略描述作为 prompt
            full_prompt = content
            
            return jsonify({
                "success": True,
                "data": {
                    "symbol": symbol,
                    "suggested_name": f"策略_{symbol}",
                    "prompt": full_prompt,
                    "direction": direction,
                    "timeframe": final_timeframe,
                    "stop_loss": final_stop_loss,
                    "take_profit": final_take_profit,
                    "quantity": final_quantity
                }
            })
            
        except Exception as e:
            logger.warning(f"LLM inference failed: {e}, using user input")
            # 如果 LLM 失败，使用用户输入
            return jsonify({
                "success": True,
                "data": {
                    "symbol": symbol,
                    "prompt": prompt,
                    "direction": direction,
                    "timeframe": timeframe,
                    "stop_loss": stop_loss if stop_loss else (30 if symbol in ['TXF', 'MXF'] else 15),
                    "take_profit": take_profit if take_profit else (50 if symbol in ['TXF', 'MXF'] else 25),
                    "quantity": quantity
                }
            })
            
    except Exception as e:
        logger.error(f"Preview error: {e}")
        return jsonify({
            "success": False,
            "message": f"生成预览失败: {str(e)}"
        }), 500


@create_bp.route('/api/strategies/confirm', methods=['POST'])
def confirm_strategy():
    """确认参数，触发 LLM 生成代码 + 验证
    
    Request Body:
    {
        "symbol": "TMF",
        "prompt": "...",
        "timeframe": "15m",
        "stop_loss": 30,
        "take_profit": 50,
        "quantity": 1
    }
    
    Response:
    {
        "success": true,
        "data": {
            "strategy_id": "TMF260001",
            "name": "收益策略_TMF",
            "verification": {
                "stage1_passed": true,
                "stage1_error": null,
                "stage2_passed": true,
                "stage2_error": null,
                "trade_count": 10,
                "win_rate": 60,
                "total_return": 5.2,
                "chart_path": "/workspace/backtests/..."
            }
        }
    }
    """
    try:
        data = request.get_json()
        
        symbol = data.get('symbol', 'TMF').upper()
        prompt = data.get('prompt', '')
        direction = data.get('direction', 'long')
        timeframe = data.get('timeframe', '15m')
        stop_loss = int(data.get('stop_loss', 0)) or 30
        take_profit = int(data.get('take_profit', 0)) or 50
        quantity = int(data.get('quantity', 1))
        # 接受用户自定义的策略名称，若未提供则使用默认值
        strategy_name = data.get('name') or f"策略_{symbol}"
        
        if not prompt:
            return jsonify({
                "success": False,
                "message": "请输入策略提示词"
            }), 400
        
        trading_tools = get_trading_tools()
        
        if not trading_tools:
            return jsonify({
                "success": False,
                "message": "系统未初始化"
            }), 500
        
        # 直接设置 _pending_strategy，使用用户在界面确认的参数
        # 使用用户提供的策略名称或默认值
        params = {
            "name": strategy_name,
            "symbol": symbol,
            "direction": direction,
            "prompt": prompt,
            "timeframe": timeframe,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "quantity": quantity,
            "goal": None,
            "goal_unit": "daily"
        }
        
        # 直接设置 _pending_strategy（绕过 create_strategy_by_goal）
        trading_tools._pending_strategy = params
        trading_tools._awaiting_confirm = True
        
        # 调用 confirm_create_strategy
        result = None
        try:
            logger.info(f"Calling confirm_create_strategy with params: {params}")
            result = trading_tools.confirm_create_strategy(confirmed=True)
            logger.info(f"confirm_create_strategy returned: {result[:500] if result else 'None'}...")
        except Exception as e:
            logger.error(f"Confirm strategy error: {e}")
            return jsonify({
                "success": False,
                "message": f"確認策略失敗: {str(e)}"
            }), 500
        
        # 如果 result 為 None 或空
        if not result:
            return jsonify({
                "success": False,
                "message": "策略建立失敗: 沒有返回結果"
            }), 500
        
        # 解析结果
        # 返回格式应该是："✅ 策略已建立并通过验证\n..." 或 "❌ 驗證失敗..."
        
        # 检查是否验证通过
        verification_passed = "通過" in result or "通過驗證" in result or "已建立" in result or "已建立並通過驗證" in result
        verification_failed = "失敗" in result or "未通過" in result
        
        # 提取策略 ID
        strategy_id_match = re.search(r'ID[:：]\s*([A-Z]+\d+)', result)
        strategy_id = strategy_id_match.group(1) if strategy_id_match else None
        
        # 提取策略名称
        name_match = re.search(r'名稱[:：]\s*(.+)', result)
        strategy_name_result = name_match.group(1).strip() if name_match else strategy_name
        
        # 尝试提取具体的失败原因
        stage1_passed = verification_passed
        stage2_passed = verification_passed
        stage1_error = None
        stage2_error = None
        
        if verification_failed:
            # 解析 "Stage 1 失敗:" 或 "Stage 2 失敗:" 來判斷哪個階段失敗
            if "Stage 1" in result and "失敗" in result:
                stage1_passed = False
                stage2_passed = False
                # 提取 Stage 1 的錯誤訊息
                stage1_match = re.search(r'Stage 1 失敗[：:]\s*(.+)', result)
                if stage1_match:
                    stage1_error = stage1_match.group(1).strip()
                else:
                    # 嘗試從 "原因：" 提取
                    if "原因：" in result:
                        error_match = re.search(r'原因[：:]\s*(.+)', result)
                        if error_match:
                            stage1_error = error_match.group(1).strip()
                    if not stage1_error:
                        stage1_error = result[:200] if len(result) > 200 else result
            elif "Stage 2" in result and "失敗" in result:
                stage2_passed = False
                # Stage 1 應該通過了
                stage1_passed = True
                # 提取 Stage 2 的錯誤訊息
                stage2_match = re.search(r'Stage 2 失敗[：:]\s*(.+)', result)
                if stage2_match:
                    stage2_error = stage2_match.group(1).strip()
                else:
                    stage2_error = result[:200] if len(result) > 200 else result
            else:
                # 沒有明確的 Stage 標記，使用默認值
                stage1_error = result[:200] if len(result) > 200 else result
        
        # 构建验证结果
        verification_result = {
            "stage1_passed": stage1_passed,
            "stage1_error": stage1_error,
            "stage2_passed": stage2_passed,
            "stage2_error": stage2_error,
        }
        
        # 如果验证通过，尝试获取回测结果
        chart_path = None
        analysis = None
        if verification_passed and strategy_id:
            try:
                backtest_result = trading_tools.backtest_strategy(strategy_id)
                if isinstance(backtest_result, dict):
                    chart_path = backtest_result.get("chart_path")
                    analysis = backtest_result.get("analysis")  # 獲取分析
                    if backtest_result.get("metrics"):
                        verification_result["trade_count"] = backtest_result["metrics"].get("trade_count", 0)
                        verification_result["win_rate"] = backtest_result["metrics"].get("win_rate", 0)
                        verification_result["total_return"] = backtest_result["metrics"].get("total_return", 0)
            except Exception as e:
                logger.warning(f"Backtest after confirm failed: {e}")
        
        response_data = {
            "strategy_id": strategy_id,
            "name": strategy_name_result,
            "verification": verification_result
        }
        
        if chart_path:
            # 转换路径（支持相对路径和绝对路径）
            chart_path_str = str(chart_path).replace("\\", "/")
            
            if "workspace/" in chart_path_str:
                # 绝对路径：提取 workspace 之后部分
                chart_path_str = chart_path_str.split("workspace/")[-1]
                chart_path_str = f"/workspace/{chart_path_str}"
            elif not chart_path_str.startswith("workspace/") and not chart_path_str.startswith("/workspace/"):
                # 相对路径（如 backtests/xxx.html）：添加 /workspace/ 前缀
                chart_path_str = f"/workspace/{chart_path_str}"
            
            # 读取 HTML 文件内容
            try:
                import os
                # 尝试多个可能的路径
                possible_paths = [
                    chart_path_str.replace("/workspace/", "workspace/"),
                    chart_path_str.lstrip("/"),
                    str(chart_path)
                ]
                
                html_content = None
                for html_file_path in possible_paths:
                    if os.path.exists(html_file_path):
                        with open(html_file_path, 'r', encoding='utf-8') as f:
                            html_content = f.read()
                        logger.info(f"Successfully read HTML chart from: {html_file_path}")
                        break
                
                if html_content:
                    # 不再返回完整的 HTML 内容（太大导致 JSON 解析失败）
                    # 只返回 chart_path，让前端通过 URL 加载
                    # response_data["chart_html"] = html_content  # 已移除
                    response_data["chart_path"] = chart_path_str
                    logger.info(f"Chart path set for iframe: {chart_path_str}")
            except Exception as e:
                logger.warning(f"Failed to read HTML chart: {e}")
                # 即使读取失败，也返回 chart_path
                response_data["chart_path"] = chart_path_str
                # 即使读取失败，也返回路径供 iframe 使用
                response_data["chart_path"] = chart_path_str
        
        if analysis:
            response_data["analysis"] = analysis
        
        if verification_passed:
            return jsonify({
                "success": True,
                "data": response_data
            })
        else:
            return jsonify({
                "success": False,
                "message": "策略验证失败",
                "data": response_data
            })
            
    except Exception as e:
        logger.error(f"Confirm error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"确认策略失败: {str(e)}"
        }), 500
