"""実験フローを共通化するためのユーティリティ。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import orjson
import yaml
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from src.config import create_client_from_model_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = PROJECT_ROOT / "data" / "logs"
DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)


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


__all__ = [
    "Turn",
    "ExperimentConfig",
    "ExperimentRunner",
    "load_yaml",
    "load_next_run_index",
    "setup_experiment_environment",
]
