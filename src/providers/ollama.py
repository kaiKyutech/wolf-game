"""Ollama向けの設定とチャットモデル生成ロジック。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_community.chat_models import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import Field
from pydantic_settings import BaseSettings

from .base import BaseProvider


# Ollama接続に必要な設定値を環境変数と併せて管理する
class OllamaSettings(BaseSettings):
    """Ollama互換エンドポイントへ接続するための設定。"""

    model: str = Field(default="llama3.1", description="Ollamaで提供されるモデル名")
    base_url: str = Field(
        default="http://localhost:11434",
        description="OllamaサーバーのベースURL",
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    keep_alive: Optional[str] = Field(default=None, description="Ollamaのkeep-alive設定")
    streaming: bool = Field(default=False, description="デフォルトでストリーミング応答を有効にするか")

    class Config:
        env_prefix = "OLLAMA_"
        env_file = ".env"


# Ollama設定からLangChainのChatOllamaインスタンスを生成するプロバイダ
class OllamaProvider(BaseProvider):
    """設定に基づいて`ChatOllama`インスタンスを生成するファクトリ。"""

    def __init__(self, settings: Optional[OllamaSettings] = None):
        # 設定が与えられなければ環境変数を読み込んだデフォルト値を利用する
        self.settings = settings or OllamaSettings()

    def create_chat_model(self) -> BaseChatModel:
        """設定値を用いて`ChatOllama`を初期化して返す。"""
        kwargs: Dict[str, Any] = {
            "model": self.settings.model,
            "base_url": self.settings.base_url,
            "temperature": self.settings.temperature,
            "top_p": self.settings.top_p,
            "streaming": self.settings.streaming,
            "keep_alive": self.settings.keep_alive,
        }
        # Noneの値を落としてOllama側のデフォルトを尊重する
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return ChatOllama(**filtered_kwargs)
