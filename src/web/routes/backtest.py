"""Backtest API Routes"""
from flask import Blueprint, jsonify, current_app
from pathlib import Path
import re
from datetime import datetime

bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')

# 獲取工作區路徑（相對於當前檔案）
WORKSPACE_DIR = Path(__file__).parent.parent.parent.parent / "workspace"


@bp.route('/<strategy_id>/check', methods=['GET'])
def check_backtest(strategy_id):
    """檢查是否存在最新的回測報告"""
    try:
        tools = current_app.trading_tools
        
        # 獲取策略資訊（使用 strategy_mgr 的方法）
        strategy = tools.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return jsonify({
                "has_report": False,
                "message": "策略不存在"
            })
        
        # 獲取策略版本（注意：Strategy 對象的屬性是 strategy_version）
        version = getattr(strategy, 'strategy_version', 1)
        strategy_name = getattr(strategy, 'name', strategy_id)
        
        # 檢查回測目錄（使用絕對路徑）
        backtest_dir = WORKSPACE_DIR / "backtests"
        if not backtest_dir.exists():
            return jsonify({
                "has_report": False,
                "message": "沒有回測記錄"
            })
        
        # 查找該策略該版本的回測檔案
        # 檔名格式: {strategy_id}_v{version}_{timestamp}.html
        pattern = f"{strategy_id}_v{version}_*.html"
        matching_files = list(backtest_dir.glob(pattern))
        
        if not matching_files:
            return jsonify({
                "has_report": False,
                "message": "沒有找到該版本的回測報告"
            })
        
        # 找出最新的 HTML 檔案
        latest_html = max(matching_files, key=lambda f: f.stat().st_mtime)
        
        # 嘗試查找對應的文字報告檔案（.txt）
        report_file = latest_html.with_suffix('.txt')
        has_text_report = report_file.exists()
        
        # 解析時間戳
        filename = latest_html.name
        timestamp_match = re.search(r'_(\d{14})\.html$', filename)
        
        if timestamp_match:
            timestamp_str = timestamp_match.group(1)
            report_time = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
            
            # 計算時間差
            time_diff = datetime.now() - report_time
            if time_diff.days > 0:
                time_ago = f"{time_diff.days} 天前"
            elif time_diff.seconds // 3600 > 0:
                time_ago = f"{time_diff.seconds // 3600} 小時前"
            else:
                time_ago = f"{time_diff.seconds // 60} 分鐘前"
        else:
            time_ago = "未知時間"
            report_time = datetime.fromtimestamp(latest_html.stat().st_mtime)
        
        # 轉換為 URL 路徑（相對於工作區）
        # 從絕對路徑中提取 workspace 之後的部分，並添加 /workspace/ 前綴
        chart_path = str(latest_html).replace("\\", "/")
        if "workspace/" in chart_path:
            chart_url = "/workspace/" + chart_path.split("workspace/", 1)[1]
        else:
            chart_url = "/workspace/backtests/" + latest_html.name
        
        # 文字報告路徑
        report_url = None
        if has_text_report:
            report_path = str(report_file).replace("\\", "/")
            if "workspace/" in report_path:
                report_url = "/workspace/" + report_path.split("workspace/", 1)[1]
            else:
                report_url = "/workspace/backtests/" + report_file.name
        
        return jsonify({
            "has_report": True,
            "chart_path": chart_url,
            "report_path": report_url,
            "has_text_report": has_text_report,
            "report_time": report_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_ago": time_ago,
            "strategy_name": strategy_name,
            "version": version
        })
        
    except Exception as e:
        return jsonify({
            "has_report": False,
            "message": f"檢查回測報告時發生錯誤: {str(e)}"
        }), 500


@bp.route('/<strategy_id>', methods=['POST'])
def run_backtest(strategy_id):
    """執行回測"""
    try:
        tools = current_app.trading_tools
        result = tools.backtest_strategy(strategy_id)
        
        # backtest_strategy 返回的是 dict 或 str
        if isinstance(result, dict):
            # 修復：使用 error 欄位判斷是否成功，不檢查報告內容中的 ❌ 字符
            has_error = result.get("error") is not None and result.get("error") != ""
            has_report = result.get("report") is not None and result.get("report") != ""
            
            # 修復：將相對路徑轉換為 URL 路徑
            chart_path = result.get("chart_path")
            chart_url = None
            if chart_path:
                # 確保路徑格式為 /workspace/...
                chart_path = chart_path.replace("\\", "/").lstrip("/")
                if not chart_path.startswith("workspace/"):
                    chart_path = "workspace/" + chart_path
                chart_url = "/" + chart_path
            
            return jsonify({
                "success": not has_error and has_report,
                "report": result.get("report", ""),
                "chart_path": chart_url,
                "error": result.get("error") if has_error else None
            })
        else:
            # 字符串格式的結果
            error_markers = ["❌ 回測失敗", "錯誤", "error", "Error", "ERROR"]
            has_error = any(marker in str(result) for marker in error_markers)
            
            return jsonify({
                "success": not has_error,
                "report": result,
                "chart_path": None,
                "error": None
            })
    except Exception as e:
        return jsonify({
            "success": False,
            "report": "",
            "chart_path": None,
            "error": str(e)
        }), 500
