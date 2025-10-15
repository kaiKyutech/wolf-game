"""モデル設定の読み込みとLLMクライアント生成。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError
from pydantic import ConfigDict

from src.api.client import LLMClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_PATH = PROJECT_ROOT / "config" / "models.yaml"


class ModelConfig(BaseModel):
    """単一モデル設定。"""

    provider: Literal["ollama", "gemini"] = Field(description="利用するプロバイダ識別子")
    model: str = Field(description="モデル名")
    base_url: Optional[str] = Field(default=None, description="Ollamaなどで利用するベースURL")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    keep_alive: Optional[str] = Field(default=None, description="Ollamaのkeep-alive設定")
    streaming: Optional[bool] = Field(default=None, description="ストリーミング応答を有効化")
    max_output_tokens: Optional[int] = Field(default=None, description="Geminiの最大出力トークン数")
    description: Optional[str] = Field(default=None, description="用途のメモ")

    model_config = ConfigDict(extra="allow")

    def to_provider_kwargs(self) -> Dict[str, object]:
        """プロバイダ生成時に渡すキーワード引数を返す。"""
        data = self.model_dump()
        data.pop("provider", None)
        data.pop("description", None)
        return {k: v for k, v in data.items() if v is not None}


class ModelRegistry(BaseModel):
    """名前とモデル設定の対応表。"""

    models: Dict[str, ModelConfig] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


def load_model_registry(config_path: Path | None = None) -> ModelRegistry:
    """YAMLファイルを読み込み、モデル名→設定の辞書を返す。"""

    path = Path(config_path or DEFAULT_MODELS_PATH).resolve()
    if not path.exists():
        raise FileNotFoundError(f"モデル設定ファイルが見つかりません: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        registry = ModelRegistry(models=raw.get("models", {}))
    except ValidationError as exc:
        raise ValueError(f"モデル設定の検証に失敗しました: {exc}") from exc
    return registry


def list_model_names(config_path: Path | None = None) -> list[str]:
    """設定ファイルに定義されたモデル名一覧を返す。"""

    return list(load_model_registry(config_path).models.keys())


def get_model_config(name: str, config_path: Path | None = None) -> ModelConfig:
    """指定名のモデル設定を取得。"""

    registry = load_model_registry(config_path)
    if name not in registry.models:
        available = ", ".join(sorted(registry.models))
        raise KeyError(f"モデル名 '{name}' は設定に存在しません。利用可能: {available}")
    return registry.models[name]


def create_client_from_model_name(name: str, *, config_path: Path | None = None) -> LLMClient:
    """設定ファイル上のモデル名からLLMClientを生成する。"""

    model_config = get_model_config(name, config_path)
    kwargs = model_config.to_provider_kwargs()
    if model_config.provider == "ollama":
        return LLMClient.from_ollama_settings(**kwargs)
    if model_config.provider == "gemini":
        return LLMClient.from_gemini_settings(**kwargs)
    raise ValueError(f"未対応のプロバイダ: {model_config.provider}")
