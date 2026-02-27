"""Config API Routes"""
import yaml
from pathlib import Path
from flask import Blueprint, jsonify, request

bp = Blueprint('config', __name__, url_prefix='/api/config')

CONFIG_PATH = "config.yaml"


def load_config_yaml():
    """載入 config.yaml"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config_yaml(data):
    """儲存 config.yaml"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def mask_sensitive(value):
    """隱藏敏感資訊"""
    if value and len(value) > 4:
        return value[:2] + "****" + value[-2:]
    return "******"


@bp.route('', methods=['GET'])
def get_config():
    """取得配置（敏感資訊脫敏）"""
    try:
        config = load_config_yaml()
        
        result = {
            "shioaji": {
                "simulation": config.get("shioaji", {}).get("simulation", True),
                "api_key": mask_sensitive(config.get("shioaji", {}).get("api_key", "")),
                "secret_key": mask_sensitive(config.get("shioaji", {}).get("secret_key", "")),
            },
            "llm": {
                "provider": config.get("llm", {}).get("provider", "custom"),
                "api_key": mask_sensitive(config.get("llm", {}).get("api_key", "")),
                "model": config.get("llm", {}).get("model", "llama3"),
                "temperature": config.get("llm", {}).get("temperature", 0.7),
                "max_tokens": config.get("llm", {}).get("max_tokens", 2000),
                "base_url": config.get("llm", {}).get("base_url", ""),
            },
            "telegram": {
                "enabled": config.get("telegram", {}).get("enabled", False),
                "bot_token": mask_sensitive(config.get("telegram", {}).get("bot_token", "")),
                "chat_id": config.get("telegram", {}).get("chat_id", ""),
            },
            "risk": {
                "max_daily_loss": config.get("risk", {}).get("max_daily_loss", 50000),
                "max_position": config.get("risk", {}).get("max_position", 10),
                "max_orders_per_minute": config.get("risk", {}).get("max_orders_per_minute", 5),
                "enable_stop_loss": config.get("risk", {}).get("enable_stop_loss", True),
                "enable_take_profit": config.get("risk", {}).get("enable_take_profit", True),
            },
            "trading": {
                "check_interval": config.get("trading", {}).get("check_interval", 60),
                "trading_hours": config.get("trading", {}).get("trading_hours", {}),
            },
            "web": {
                "enabled": config.get("web", {}).get("enabled", False),
                "host": config.get("web", {}).get("host", "127.0.0.1"),
                "port": config.get("web", {}).get("port", 5000),
            }
        }
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route('', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "無效的請求資料"
            }), 400
        
        config = load_config_yaml()
        
        if "shioaji" in data:
            shioaji_data = data["shioaji"]
            current = config.get("shioaji", {})
            if shioaji_data.get("api_key"):
                current["api_key"] = shioaji_data["api_key"]
            if shioaji_data.get("secret_key"):
                current["secret_key"] = shioaji_data["secret_key"]
            if "simulation" in shioaji_data:
                current["simulation"] = shioaji_data["simulation"]
            config["shioaji"] = current
        
        if "llm" in data:
            llm_data = data["llm"]
            current = config.get("llm", {})
            if llm_data.get("api_key"):
                current["api_key"] = llm_data["api_key"]
            if "provider" in llm_data:
                current["provider"] = llm_data["provider"]
            if "model" in llm_data:
                current["model"] = llm_data["model"]
            if "temperature" in llm_data:
                current["temperature"] = llm_data["temperature"]
            if "max_tokens" in llm_data:
                current["max_tokens"] = llm_data["max_tokens"]
            if "base_url" in llm_data:
                current["base_url"] = llm_data["base_url"]
            config["llm"] = current
        
        if "telegram" in data:
            telegram_data = data["telegram"]
            current = config.get("telegram", {})
            if telegram_data.get("bot_token"):
                current["bot_token"] = telegram_data["bot_token"]
            if "enabled" in telegram_data:
                current["enabled"] = telegram_data["enabled"]
            if "chat_id" in telegram_data:
                current["chat_id"] = telegram_data["chat_id"]
            config["telegram"] = current
        
        if "risk" in data:
            risk_data = data["risk"]
            current = config.get("risk", {})
            if "max_daily_loss" in risk_data:
                current["max_daily_loss"] = risk_data["max_daily_loss"]
            if "max_position" in risk_data:
                current["max_position"] = risk_data["max_position"]
            if "max_orders_per_minute" in risk_data:
                current["max_orders_per_minute"] = risk_data["max_orders_per_minute"]
            if "enable_stop_loss" in risk_data:
                current["enable_stop_loss"] = risk_data["enable_stop_loss"]
            if "enable_take_profit" in risk_data:
                current["enable_take_profit"] = risk_data["enable_take_profit"]
            config["risk"] = current
        
        if "trading" in data:
            trading_data = data["trading"]
            current = config.get("trading", {})
            if "check_interval" in trading_data:
                current["check_interval"] = trading_data["check_interval"]
            if "trading_hours" in trading_data:
                current["trading_hours"] = trading_data["trading_hours"]
            config["trading"] = current
        
        if "web" in data:
            web_data = data["web"]
            current = config.get("web", {})
            if "enabled" in web_data:
                current["enabled"] = web_data["enabled"]
            if "host" in web_data:
                current["host"] = web_data["host"]
            if "port" in web_data:
                current["port"] = web_data["port"]
            config["web"] = current
        
        save_config_yaml(config)
        
        return jsonify({
            "success": True,
            "message": "設定已儲存，部分設定需要重啟系統才能生效"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500