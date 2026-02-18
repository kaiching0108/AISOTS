"""LLM Provider 實現 - 支援多種 LLM 服務"""
import os
import json
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
import httpx

from src.logger import logger


class BaseProvider(ABC):
    """LLM Provider 基類"""
    
    def __init__(self, config):
        self.config = config
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """發送聊天請求"""
        pass
    
    @abstractmethod
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        """發送聊天請求並使用工具"""
        pass


class CustomProvider(BaseProvider):
    """自定義 Provider - 支援 Ollama 或其他 OpenAI 相容端點"""
    
    def __init__(self, config):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434/v1"
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """發送聊天請求"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"Custom provider HTTP error: {e}")
            raise
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        """發送聊天請求並使用工具 (含 function calling)"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "tools": tools if tools else None
        }
        
        # 移除 None 值
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            message = result["choices"][0]["message"]
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
            
        except httpx.HTTPError as e:
            logger.error(f"Custom provider HTTP error: {e}")
            raise
    
    async def close(self):
        """關閉客戶端"""
        await self.client.aclose()


class OpenRouterProvider(BaseProvider):
    """OpenRouter Provider - 支援多種模型"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ai-futures-trading",
            "X-Title": "AI Futures Trading System"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"OpenRouter provider error: {e}")
            raise
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/ai-futures-trading",
            "X-Title": "AI Futures Trading System"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "tools": tools if tools else None
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            
            message = result["choices"][0]["message"]
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
            
        except httpx.HTTPError as e:
            logger.error(f"OpenRouter provider error: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()


class OpenAIProvider(BaseProvider):
    """OpenAI Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("OPENAI_API_KEY", "")
        self.base_url = config.base_url or "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI provider error: {e}")
            raise
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "tools": tools if tools else None
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = await self.client.post(
                "/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            message = result["choices"][0]["message"]
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
            
        except httpx.HTTPError as e:
            logger.error(f"OpenAI provider error: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()


class AnthropicProvider(BaseProvider):
    """Anthropic Claude Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.client = httpx.AsyncClient(
            base_url="https://api.anthropic.com",
            timeout=120.0,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # 轉換 messages 格式
        system_message = ""
        filtered_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        
        payload = {
            "model": self.model,
            "messages": filtered_messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "system": system_message
        }
        
        try:
            response = await self.client.post(
                "/v1/messages",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return result["content"][0]["text"]
            
        except httpx.HTTPError as e:
            logger.error(f"Anthropic provider error: {e}")
            raise
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        # Anthropic 不支援 tools，fallback 到 chat
        content = await self.chat(messages, **kwargs)
        return {
            "content": content,
            "tool_calls": []
        }
    
    async def close(self):
        await self.client.aclose()


class DeepSeekProvider(BaseProvider):
    """DeepSeek Provider"""
    
    def __init__(self, config):
        super().__init__(config)
        self.api_key = config.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.client = httpx.AsyncClient(
            base_url="https://api.deepseek.com",
            timeout=120.0,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        
        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            return result["choices"][0]["message"]["content"]
            
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek provider error: {e}")
            raise
    
    async def chat_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict], **kwargs) -> Dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "tools": tools if tools else None
        }
        
        payload = {k: v for k, v in payload.items() if v is not None}
        
        try:
            response = await self.client.post(
                "/v1/chat/completions",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
            message = result["choices"][0]["message"]
            
            return {
                "content": message.get("content", ""),
                "tool_calls": message.get("tool_calls", [])
            }
            
        except httpx.HTTPError as e:
            logger.error(f"DeepSeek provider error: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()


class ProviderFactory:
    """LLM Provider 工廠"""
    
    _providers = {
        "custom": CustomProvider,
        "openrouter": OpenRouterProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "deepseek": DeepSeekProvider,
    }
    
    @classmethod
    def create(cls, config) -> BaseProvider:
        """建立 Provider 實例"""
        provider_name = config.provider.lower()
        
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            logger.warning(f"Unknown provider: {provider_name}, using custom")
            provider_class = CustomProvider
        
        logger.info(f"Creating LLM provider: {provider_name}")
        return provider_class(config)
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """取得可用的 providers"""
        return list(cls._providers.keys())


def create_llm_provider(config) -> BaseProvider:
    """建立 LLM Provider 的便捷函數"""
    return ProviderFactory.create(config)
