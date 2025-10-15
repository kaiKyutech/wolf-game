"""Google Gemini向けの設定とチャットモデル生成ロジック。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import Field
from pydantic_settings import BaseSettings

from .base import BaseProvider


# Gemini接続に必要な設定値を環境変数と併せて管理する
class GeminiSettings(BaseSettings):
    """Google Gemini API への接続設定。"""

    model: str = Field(default="gemini-1.5-pro", description="利用するGeminiモデル名")
    api_key: str = Field(..., env="GEMINI_API_KEY", description="Google Generative AI APIキー")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    max_output_tokens: Optional[int] = Field(default=None, description="最大出力トークン数")

    class Config:
        env_prefix = "GEMINI_"
        env_file = ".env"
        validate_assignment = True


# Gemini設定からLangChainのChatGoogleGenerativeAIインスタンスを生成するプロバイダ
class GeminiProvider(BaseProvider):
    """設定に基づいて`ChatGoogleGenerativeAI`を生成するファクトリ。"""

    def __init__(self, settings: Optional[GeminiSettings] = None):
        # 設定が与えられなければ環境変数から読み込む
        self.settings = settings or GeminiSettings()

    def create_chat_model(self) -> BaseChatModel:
        """設定値を用いて`ChatGoogleGenerativeAI`を初期化して返す。"""
        kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "google_api_key": self.settings.api_key,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
        }
        if self.settings.max_output_tokens is not None:
            kwargs["max_output_tokens"] = self.settings.max_output_tokens
        return ChatGoogleGenerativeAI(**kwargs)
