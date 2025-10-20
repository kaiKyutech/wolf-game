"""実験フローを共通化するためのユーティリティ。"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import orjson
import yaml
import requests
from requests import RequestException
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.config import create_client_from_model_name, get_model_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_ROOT / "data" / "logs"
DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
FAILURE_LOG_FILENAME = "failed_responses.jsonl"


class Turn(Dict[str, Any]):
    """単一ターンの定義を表す辞書ラッパー。"""


class ExperimentConfig(Dict[str, Any]):
    """実験設定全体を保持する辞書ラッパー。"""


class ExperimentRunner:
    """YAML設定を読み込み、LangChainクライアントでターン制フローを実行する。"""

    def __init__(self, config_path: Path, log_dir: Path | None = None) -> None:
        self.config_path = config_path
        self.log_dir = log_dir or DEFAULT_LOG_DIR
        self.config = self._load_config()
        self.client = self._create_client()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> ExperimentConfig:
        if not self.config_path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")
        with self.config_path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return ExperimentConfig(raw)

    def _create_client(self):
        model_name = self.config.get("model_name")
        if not model_name:
            raise ValueError("configに 'model_name' がありません。")
        return create_client_from_model_name(model_name)

    def _resolve_text(self, entry: Dict[str, Any], key: str) -> str:
        file_key = f"{key}_file"
        if file_key in entry:
            return (self.config_path.parent / entry[file_key]).read_text(encoding="utf-8")
        return entry.get(key, "")

    def _log_path(self) -> Path:
        filename = self.config.get("log_filename")
        if not filename:
            filename = f"experiment_{datetime.utcnow():%Y%m%dT%H%M%S}.jsonl"
        return self.log_dir / filename

    def _save_log(self, log_path: Path, record: Dict[str, Any]) -> None:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(orjson.dumps(record).decode("utf-8") + "\n")

    def run(self) -> None:
        prompts_file = self.config.get("prompts_file")

        if prompts_file:
            if self.config.get("system_prompt"):
                raise ValueError("configのsystem_promptとprompts_fileを同時に指定することはできません。")
            if self.config.get("turns"):
                raise ValueError("prompts_file と turns を同時に指定することはできません。")
            prompts_path = self.config_path.parent / prompts_file
            if not prompts_path.exists():
                raise FileNotFoundError(f"prompts_file が見つかりません: {prompts_path}")
            data = yaml.safe_load(prompts_path.read_text(encoding="utf-8")) or {}
            system_prompt = data.get("system_prompt")
            user_prompt = data.get("user_prompt")
            if not system_prompt:
                raise ValueError("prompts.yaml に system_prompt がありません。")
            if not user_prompt:
                raise ValueError("prompts.yaml に user_prompt がありません。")

            messages: List[BaseMessage] = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            log_path = self._log_path()
            response = self.client.invoke(messages)
            if not isinstance(response, AIMessage):
                response = AIMessage(content=str(response))

            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "turn_index": 1,
                "speaker": self.config.get("speaker", "User"),
                "prompt": user_prompt,
                "response": response.content,
                "model_name": self.config["model_name"],
                "log_file": log_path.name,
            }
            self._save_log(log_path, record)
            print(f"[Response] -> {response.content}")
            print(f"ログを保存しました: {log_path}")
            return

        system_prompt = self._resolve_text(self.config, "system_prompt")
        if not system_prompt:
            raise ValueError("system_prompt が設定されていません。")

        turns: Iterable[Turn] = self.config.get("turns", [])
        if not turns:
            raise ValueError("turns が空です。1つ以上のターンを設定するか prompts_file を指定してください。")

        messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
        log_path = self._log_path()

        for idx, turn in enumerate(turns, start=1):
            speaker = turn.get("speaker", "User")
            prompt = self._resolve_text(turn, "prompt")
            if not prompt:
                raise ValueError(f"turn {idx} に prompt がありません。")

            messages.append(HumanMessage(content=prompt))
            response = self.client.invoke(messages)
            if isinstance(response, AIMessage):
                messages.append(response)
            else:
                messages.append(AIMessage(content=str(response)))

            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "turn_index": idx,
                "speaker": speaker,
                "prompt": prompt,
                "response": messages[-1].content,
                "model_name": self.config["model_name"],
                "log_file": log_path.name,
            }
            self._save_log(log_path, record)
            print(f"[{speaker}] -> {messages[-1].content}")

        print(f"ログを保存しました: {log_path}")


def load_yaml(path: Path) -> Dict[str, Any]:
    """YAMLファイルを読み込み、辞書として返す。"""

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_next_run_index(log_path: Path) -> int:
    """既存ログを参照し、次に利用する run 番号を決定する。"""

    if not log_path.exists():
        return 1

    last_entry: str | None = None
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                last_entry = stripped

    if not last_entry:
        return 1

    try:
        record = orjson.loads(last_entry)
        return int(record.get("run", 0)) + 1
    except Exception:
        return 1


def strip_code_fence(raw: str) -> str:
    """```json ... ``` のようなコードフェンスを取り除く。"""

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def setup_experiment_environment(
    config_path: Path,
    prompts_path: Path,
    *,
    log_dir: Path | None = None,
    default_log_name: str = "experiment.jsonl",
) -> Tuple[Dict[str, Any], Dict[str, Any], Path, int]:
    """共通的な設定読込とログ設定の初期化を行う。"""

    config = load_yaml(config_path)
    prompts = load_yaml(prompts_path)

    target_dir = log_dir or config_path.parent / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)

    log_name = config.get("log_filename", default_log_name)
    log_path = target_dir / log_name
    run_index = load_next_run_index(log_path)

    return config, prompts, log_path, run_index


def load_image_base64(path: Path) -> str:
    """画像ファイルを data URI 付きの base64 文字列へ変換する。"""

    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    else:
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


def collect_image_paths(
    directory: Path,
    *,
    suffixes: Sequence[str] | None = None,
) -> List[Path]:
    """ディレクトリ内の画像ファイルを拡張子フィルタで収集する。"""

    valid = tuple(s.lower() for s in (suffixes or (".png", ".jpg", ".jpeg")))
    if not directory.exists():
        return []
    return sorted(
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in valid
    )


def create_human_message_with_images(
    text: str,
    image_paths: Sequence[Path],
) -> HumanMessage:
    """テキストと画像を混在させた HumanMessage を生成する。"""

    content: List[Dict[str, object]] = [{"type": "text", "text": text.strip()}]
    for path in image_paths:
        data_uri = load_image_base64(path)
        content.append({"type": "image_url", "image_url": {"url": data_uri}})
    return HumanMessage(content=content)


def next_sequential_log_path(
    directory: Path,
    base_name: str,
    *,
    extension: str = ".jsonl",
) -> Path:
    """directory 内で base_name_001... のような連番ファイルパスを生成する。"""

    directory.mkdir(parents=True, exist_ok=True)

    indices: list[int] = []
    pattern = f"{base_name}_*{extension}"
    for path in directory.glob(pattern):
        stem_suffix = path.stem.split("_")[-1]
        if stem_suffix.isdigit():
            indices.append(int(stem_suffix))

    next_index = max(indices) + 1 if indices else 1
    candidate = directory / f"{base_name}_{next_index:03d}{extension}"
    while candidate.exists():
        next_index += 1
        candidate = directory / f"{base_name}_{next_index:03d}{extension}"
    return candidate


def append_failure_log(log_dir: Path, record: Dict[str, Any]) -> None:
    """失敗した応答を共通ファイルに追記保存する。"""

    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / FAILURE_LOG_FILENAME
    with path.open("a", encoding="utf-8") as fh:
        fh.write(orjson.dumps(record).decode("utf-8") + "\n")


def check_ollama_endpoint(
    base_url: str,
    *,
    timeout: float = 5.0,
    verify: bool = True,
) -> Tuple[bool, str]:
    """Ollama エンドポイントの `/api/version` を叩いて疎通確認を行う。"""

    url = base_url.rstrip("/") + "/api/version"
    try:
        response = requests.get(url, timeout=timeout, verify=verify)
        response.raise_for_status()
        return True, response.text
    except RequestException as exc:
        return False, str(exc)


def collect_ollama_connection_errors(model_aliases: Iterable[str]) -> List[Tuple[str, str, str]]:
    """指定されたモデルエイリアスのうち、Ollama接続に失敗したものを収集する。"""

    failures: List[Tuple[str, str, str]] = []
    checked = set()
    for alias in sorted(model_aliases):
        if alias in checked:
            continue
        checked.add(alias)
        try:
            model_config = get_model_config(alias)
        except KeyError as exc:
            failures.append((alias, "(unknown)", f"モデル設定が見つかりません: {exc}"))
            continue
        if model_config.provider != "ollama":
            continue
        base_url = model_config.base_url or "http://localhost:11434"
        ok, detail = check_ollama_endpoint(base_url)
        if not ok:
            failures.append((alias, base_url, detail))
    return failures


__all__ = [
    "Turn",
    "ExperimentConfig",
    "ExperimentRunner",
    "load_yaml",
    "load_next_run_index",
    "strip_code_fence",
    "setup_experiment_environment",
    "load_image_base64",
    "collect_image_paths",
    "create_human_message_with_images",
    "next_sequential_log_path",
    "append_failure_log",
    "check_ollama_endpoint",
    "collect_ollama_connection_errors",
    "parse_total_matches",
]


def parse_total_matches(
    *,
    description: str,
    default: int,
) -> int:
    """共通の --matches CLI 引数を解析し、試合数を返す。"""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--matches",
        type=int,
        default=default,
        help="Number of matches to run consecutively (default: %(default)s)",
    )
    args = parser.parse_args()
    if args.matches < 1:
        parser.error("--matches must be >= 1")
    return args.matches
