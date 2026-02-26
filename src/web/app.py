"""Web Interface Flask Application"""
import threading
from flask import Flask, render_template
from loguru import logger


def create_web_app(trading_tools):
    """建立 Flask 應用
    
    Args:
        trading_tools: TradingTools 實例
        
    Returns:
        Flask 應用
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'aisots-web-secret-key'
    
    # 儲存 trading_tools 引用
    app.trading_tools = trading_tools
    
    # 執行緒鎖，保護共享狀態
    app.lock = threading.Lock()
    
    # 註冊路由
    from src.web.routes import status, strategies, positions, risk, backtest
    
    app.register_blueprint(status.bp)
    app.register_blueprint(strategies.bp)
    app.register_blueprint(positions.bp)
    app.register_blueprint(risk.bp)
    app.register_blueprint(backtest.bp)
    
    @app.route('/')
    def index():
        """首頁 - 系統總覽"""
        return render_template('index.html')
    
    @app.route('/strategies')
    def strategies_page():
        """策略列表頁面"""
        return render_template('strategies.html')
    
    @app.route('/positions')
    def positions_page():
        """部位列表頁面"""
        return render_template('positions.html')
    
    logger.info("Flask Web 應用已建立")
    
    return app


def start_web_app(trading_tools, host='127.0.0.1', port=5000):
    """啟動 Web 應用（在獨立執行緒中）
    
    Args:
        trading_tools: TradingTools 實例
        host: 綁定位址
        port: 連接埠
    """
    app = create_web_app(trading_tools)
    
    logger.info(f"啟動 Web 界面: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
