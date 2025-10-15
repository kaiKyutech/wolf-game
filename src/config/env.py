"""プロジェクト共通の.env読み込みヘルパ。"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


@lru_cache(maxsize=1)
def load_project_dotenv(dotenv_path: Optional[Path | str] = None, *, override: bool = False) -> bool:
    """プロジェクト直下の`.env`を読み込み、環境変数へ反映する。"""

    path = Path(dotenv_path) if dotenv_path else DEFAULT_ENV_PATH
    if not path.exists():
        return False
    return load_dotenv(path, override=override)


__all__ = ["load_project_dotenv", "PROJECT_ROOT", "DEFAULT_ENV_PATH"]
