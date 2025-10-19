"""OpenAI向け設定とチャットモデル生成ロジック。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .base import BaseProvider


class OpenAISettings(BaseSettings):
    """OpenAI API への接続設定。"""

    model: str = Field(default="gpt-4o-mini", description="利用するOpenAIモデル名")
    api_key: str = Field(..., env="OPENAI_API_KEY", description="OpenAI APIキー")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="出力トークン上限")

    model_config = SettingsConfigDict(env_prefix="OPENAI_", extra="ignore")


class OpenAIProvider(BaseProvider):
    """設定に基づいて ChatOpenAI インスタンスを生成するファクトリ。"""

    def __init__(self, settings: Optional[OpenAISettings] = None):
        self.settings = settings or OpenAISettings()

    def create_chat_model(self) -> BaseChatModel:
        kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "api_key": self.settings.api_key,
            "temperature": self.settings.temperature,
        }
        if self.settings.max_tokens is not None:
            kwargs["max_tokens"] = self.settings.max_tokens
        return ChatOpenAI(**kwargs)
