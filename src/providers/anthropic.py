"""Anthropic Claude向けの設定とチャットモデル生成ロジック。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import BaseProvider


class AnthropicSettings(BaseSettings):
    """Anthropic Claude API への接続設定。"""

    model: str = Field(default="claude-3-haiku-20240307", description="利用するClaudeモデル名")
    api_key: str = Field(..., env="ANTHROPIC_API_KEY", description="Anthropic APIキー")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_output_tokens: Optional[int] = Field(default=1024, description="最大出力トークン数")

    model_config = SettingsConfigDict(env_prefix="ANTHROPIC_", extra="ignore")


class AnthropicProvider(BaseProvider):
    """設定に基づいて ChatAnthropic インスタンスを生成するファクトリ。"""

    def __init__(self, settings: Optional[AnthropicSettings] = None):
        self.settings = settings or AnthropicSettings()

    def create_chat_model(self) -> BaseChatModel:
        kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "api_key": self.settings.api_key,
            "temperature": self.settings.temperature,
        }
        if self.settings.max_output_tokens is not None:
            kwargs["max_output_tokens"] = self.settings.max_output_tokens
        return ChatAnthropic(**kwargs)
