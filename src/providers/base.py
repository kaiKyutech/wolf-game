"""LangChainのチャットモデルを生成する共通インターフェース。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from langchain_core.language_models.chat_models import BaseChatModel


# LangChainのチャットモデルを生成するプロバイダ共通の抽象基底クラス
class BaseProvider(ABC):
    """LangChainチャットモデルを供給する抽象ファクトリ。"""

    @abstractmethod
    def create_chat_model(self) -> BaseChatModel:
        """設定済みのLangChainチャットモデルインスタンスを返す。"""
        # 具体的なプロバイダでチャットモデルを構築して返す責務
        raise NotImplementedError
