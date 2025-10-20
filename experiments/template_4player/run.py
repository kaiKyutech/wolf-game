"""テキストのみ4人用ワンナイト人狼テンプレートの実行エントリ。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import orjson
from langchain_core.messages import HumanMessage, SystemMessage

from experiments.runner import (
    append_failure_log,
    check_ollama_endpoint,
    next_sequential_log_path,
    parse_total_matches,
    setup_experiment_environment,
)
from src.config import create_client_from_model_name, get_model_config

from .helpers import (
    DISCUSSION_ROUNDS,
    MAX_RETRIES,
    PLAY_ORDER,
    build_user_prompt,
    format_history,
    invoke_with_retries,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_PATH = BASE_DIR / "prompts.yaml"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE_BASE = "logfile"
DEFAULT_TOTAL_MATCHES = 1


def main() -> None:
    total_matches = parse_total_matches(
        description="Run the 4-player text-only One Night Werewolf simulation",
        default=DEFAULT_TOTAL_MATCHES,
    )

    config, prompts, _, _ = setup_experiment_environment(
        CONFIG_PATH,
        PROMPTS_PATH,
        log_dir=LOGS_DIR,
        default_log_name=f"{LOG_FILE_BASE}.jsonl",
    )

    ollama_failures: List[Tuple[str, str, str]] = []
    agent_models = set(config.get("agents", {}).values())
    for model_alias in sorted(agent_models):
        try:
            model_config = get_model_config(model_alias)
        except KeyError as exc:
            ollama_failures.append(
                (model_alias, "(unknown)", f"モデル設定が見つかりません: {exc}")
            )
            continue
        if model_config.provider != "ollama":
            continue
        base_url = model_config.base_url or "http://localhost:11434"
        ok, detail = check_ollama_endpoint(base_url)
        if not ok:
            ollama_failures.append((model_alias, base_url, detail))

    if ollama_failures:
        print("ERROR: Ollama エンドポイントへの接続確認に失敗しました。")
        for alias, url, detail in ollama_failures:
            print(f" - {alias}: base_url={url} -> {detail}")
        print(
            "config/models.yaml の base_url が最新のトンネル URL か、"
            "証明書エラーが発生していないかを確認してください。"
        )
        return

    log_path = next_sequential_log_path(LOGS_DIR, LOG_FILE_BASE)
    for run_index in range(1, total_matches + 1):
        print(f"=== Starting run #{run_index} (log: {log_path.name}) ===")
        success = run(
            config,
            prompts,
            log_path,
            run_index,
        )
        if not success:
            print(f"=== Run #{run_index} failed. Moving to next match. ===")


def run(config: Dict, prompts: Dict, log_path: Path, run_index: int) -> bool:
    """1試合分の進行を実行する。成功ならTrue。"""

    history: List[Dict[str, str]] = []
    votes: List[Dict[str, str]] = []
    turn_counter = 0
    max_retries = MAX_RETRIES
    clients = {
        agent_id: create_client_from_model_name(config["agents"][agent_id])
        for agent_id in PLAY_ORDER
    }

    # 議論フェーズ
    for round_index in range(1, DISCUSSION_ROUNDS + 1):
        for agent_id in PLAY_ORDER:
            model_alias = config["agents"][agent_id]
            agent_prompts = prompts["agents"][agent_id]
            prompt_bundle = agent_prompts["discussion"]

            client = clients[agent_id]
            system_prompt = prompt_bundle["system_prompt"].strip()
            user_prompt_template = prompt_bundle["user_prompt"]
            conversation_text = format_history(history)
            user_prompt = build_user_prompt(
                user_prompt_template,
                conversation_text,
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=[{"type": "text", "text": user_prompt.strip()}])
            ]

            parsed, content, error = invoke_with_retries(
                client,
                messages,
                require_vote=False,
                max_retries=max_retries,
                agent_id=agent_id,
                model_alias=model_alias,
            )
            if parsed is None:
                print(
                    f"WARNING: {agent_id} の議論応答を取得できなかったためこの試合を中断します。"
                )
                record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "run": run_index,
                    "round": round_index,
                    "phase": "discussion",
                    "turn_index": turn_counter + 1,
                    "agent": agent_id,
                    "model_name": model_alias,
                    "error": str(error),
                    "raw_response": content,
                }
                with log_path.open("a", encoding="utf-8") as fh:
                    fh.write(orjson.dumps(record).decode("utf-8") + "\n")

                failure_record = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "run": run_index,
                    "round": round_index,
                    "phase": "discussion",
                    "agent": agent_id,
                    "model_name": model_alias,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "raw_response": content,
                    "error": str(error),
                }
                append_failure_log(LOGS_DIR, failure_record)
                return False

            history.append({
                "agent": agent_id,
                "thought": parsed["thought"],
                "speech": parsed["speech"],
            })
            turn_counter += 1

            print(f"{agent_id}: {parsed['speech']}")

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run": run_index,
                "round": round_index,
                "phase": "discussion",
                "turn_index": turn_counter,
                "agent": agent_id,
                "model_name": model_alias,
                "vote": parsed["vote"],
                "thought": parsed["thought"],
                "speech": parsed["speech"],
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_response": content,
                "visible_history": format_history(history),
            }

            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(orjson.dumps(record).decode("utf-8") + "\n")

    history_text = format_history(list(history))

    # 投票フェーズ
    vote_round = DISCUSSION_ROUNDS + 1
    for agent_id in PLAY_ORDER:
        model_alias = config["agents"][agent_id]
        agent_prompts = prompts["agents"][agent_id]
        prompt_bundle = agent_prompts["vote"]

        client = clients[agent_id]
        system_prompt = prompt_bundle["system_prompt"].strip()
        user_prompt_template = prompt_bundle["user_prompt"]
        user_prompt = build_user_prompt(
            user_prompt_template,
            history_text,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=[{"type": "text", "text": user_prompt.strip()}]),
        ]

        parsed, content, error = invoke_with_retries(
            client,
            messages,
            require_vote=True,
            max_retries=max_retries,
            agent_id=agent_id,
            model_alias=model_alias,
        )
        if parsed is None:
            print(
                f"WARNING: {agent_id} の投票応答を取得できなかったためこの試合を中断します。"
            )
            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run": run_index,
                "round": vote_round,
                "phase": "vote",
                "turn_index": turn_counter + 1,
                "agent": agent_id,
                "model_name": model_alias,
                "error": str(error),
                "raw_response": content,
            }
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(orjson.dumps(record).decode("utf-8") + "\n")

            failure_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run": run_index,
                "round": vote_round,
                "phase": "vote",
                "agent": agent_id,
                "model_name": model_alias,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_response": content,
                "error": str(error),
            }
            append_failure_log(LOGS_DIR, failure_record)
            return False

        votes.append({"agent": agent_id, "vote": parsed["vote"]})
        turn_counter += 1

        print(f"{agent_id}: {parsed['speech']} (vote: {parsed['vote']})")

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run": run_index,
            "round": vote_round,
            "phase": "vote",
            "turn_index": turn_counter,
            "agent": agent_id,
            "model_name": model_alias,
            "vote": parsed["vote"],
            "thought": parsed["thought"],
            "speech": parsed["speech"],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw_response": content,
            "visible_history": history_text,
        }

        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(orjson.dumps(record).decode("utf-8") + "\n")

    tally: Dict[str, int] = {}
    for entry in votes:
        target = entry["vote"]
        tally[target] = tally.get(target, 0) + 1

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run": run_index,
        "round": vote_round,
        "phase": "vote_summary",
        "votes": votes,
        "tally": tally,
    }

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(orjson.dumps(summary).decode("utf-8") + "\n")

    return True


if __name__ == "__main__":
    main()
