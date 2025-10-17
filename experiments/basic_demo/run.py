"""ワンナイト人狼（基本設定）の進行フロー。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import orjson
from langchain_core.messages import HumanMessage, SystemMessage

from experiments.runner import setup_experiment_environment
from src.config import create_client_from_model_name

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_PATH = BASE_DIR / "prompts.yaml"
LOGS_DIR = BASE_DIR / "logs"
DEFAULT_LOG_NAME = "basic_demo.jsonl"


def run(config: Dict, prompts: Dict, log_path: Path, run_index: int) -> None:
    play_order = ["narrator", "seer"]

    for turn_index, agent_id in enumerate(play_order, start=1):
        model_alias = config["agents"][agent_id]
        prompt_bundle = prompts["agents"][agent_id]

        client = create_client_from_model_name(model_alias)
        messages = [
            SystemMessage(content=prompt_bundle["system_prompt"].strip()),
            HumanMessage(content=prompt_bundle["user_prompt"].strip()),
        ]

        response = client.invoke(messages)
        content = getattr(response, "content", str(response))

        print(f"{agent_id}: {content}")

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run": run_index,
            "turn_index": turn_index,
            "agent": agent_id,
            "model_name": model_alias,
            "system_prompt": messages[0].content,
            "user_prompt": messages[1].content,
            "response": content,
        }

        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(orjson.dumps(record).decode("utf-8") + "\n")


def main() -> None:
    config, prompts, log_path, run_index = setup_experiment_environment(
        CONFIG_PATH,
        PROMPTS_PATH,
        log_dir=LOGS_DIR,
        default_log_name=DEFAULT_LOG_NAME,
    )
    run(config, prompts, log_path, run_index)


if __name__ == "__main__":
    main()
