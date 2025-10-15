"""LangChainチャットモデルを扱う軽量ラッパー。"""
from __future__ import annotations

from typing import AsyncIterator, Iterable, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from ..providers.base import BaseProvider
from ..providers.ollama import OllamaProvider, OllamaSettings
from ..providers.gemini import GeminiProvider, GeminiSettings


# 共通のLLM呼び出しインターフェースを提供するラッパークラス
class LLMClient:
    """LangChainチャットモデル操作のための共通インターフェース。"""

    def __init__(self, chat_model: BaseChatModel):
        # 内部で利用するLangChainチャットモデルを保持
        self._chat_model = chat_model

    @classmethod
    def from_provider(cls, provider: BaseProvider) -> "LLMClient":
        # 任意のプロバイダからモデルを生成してLLMClientを構築
        return cls(provider.create_chat_model())

    @classmethod
    def from_ollama_settings(cls, **kwargs) -> "LLMClient":
        """キーワード引数でOllama設定を上書きしながらクライアントを構築する。"""
        settings = OllamaSettings(**kwargs)
        provider = OllamaProvider(settings=settings)
        return cls.from_provider(provider)

    @classmethod
    def from_gemini_settings(cls, **kwargs) -> "LLMClient":
        """キーワード引数でGemini設定を上書きしながらクライアントを構築する。"""
        settings = GeminiSettings(**kwargs)
        provider = GeminiProvider(settings=settings)
        return cls.from_provider(provider)

    def invoke(self, messages: Sequence[BaseMessage], **kwargs) -> BaseMessage:
        # 同期的にメッセージを送信し最終応答を取得
        return self._chat_model.invoke(messages, **kwargs)

    async def ainvoke(self, messages: Sequence[BaseMessage], **kwargs) -> BaseMessage:
        # 非同期APIでメッセージを送信し応答を得る
        return await self._chat_model.ainvoke(messages, **kwargs)

    def stream(self, messages: Sequence[BaseMessage], **kwargs) -> Iterable[str]:
        # ストリーミングで逐次トークンを受け取り文字列として返す
        for chunk in self._chat_model.stream(messages, **kwargs):
            yield getattr(chunk, "content", str(chunk))

    async def astream(
        self, messages: Sequence[BaseMessage], **kwargs
    ) -> AsyncIterator[str]:
        # 非同期ストリーミングでトークンを逐次取得
        async for chunk in self._chat_model.astream(messages, **kwargs):
            yield getattr(chunk, "content", str(chunk))


def create_default_ollama_client() -> LLMClient:
    """環境変数ベースの設定でOllamaクライアントを生成する。"""
    return LLMClient.from_provider(OllamaProvider())


def create_default_gemini_client() -> LLMClient:
    """環境変数ベースの設定でGeminiクライアントを生成する。"""
    return LLMClient.from_provider(GeminiProvider())
