"""ワンナイト人狼（基本設定）の進行フロー。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import orjson
import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import create_client_from_model_name

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_PATH = BASE_DIR / "prompts.yaml"
LOG_DIR = BASE_DIR / "logs"


def run() -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    prompts = yaml.safe_load(PROMPTS_PATH.read_text(encoding="utf-8"))

    play_order = [
        ("narrator", "Narrator"),
        ("seer", "Seer"),
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    log_name = config.get("log_filename", f"basic_demo_{timestamp}.jsonl")
    log_path = LOG_DIR / log_name
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    for index, (agent_id, label) in enumerate(play_order, start=1):
        model_alias = config["agents"][agent_id]
        prompt_bundle = prompts["agents"][agent_id]

        client = create_client_from_model_name(model_alias)
        messages = [
            SystemMessage(content=prompt_bundle["system_prompt"].strip()),
            HumanMessage(content=prompt_bundle["user_prompt"].strip()),
        ]

        response = client.invoke(messages)
        content = getattr(response, "content", str(response))

        print(f"{label}: {content}")

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn_index": index,
            "agent": agent_id,
            "model_name": model_alias,
            "system_prompt": messages[0].content,
            "user_prompt": messages[1].content,
            "response": content,
        }

        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(orjson.dumps(record).decode("utf-8") + "\n")


if __name__ == "__main__":
    run()


if __name__ == "__main__":
    run()
