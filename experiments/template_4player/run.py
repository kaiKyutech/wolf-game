"""テキストのみ4人用ワンナイト人狼テンプレートの進行フロー。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import orjson
from orjson import JSONDecodeError
from langchain_core.messages import HumanMessage, SystemMessage

from experiments.runner import (
    append_failure_log,
    check_ollama_endpoint,
    next_sequential_log_path,
    parse_total_matches,
    setup_experiment_environment,
    strip_code_fence,
)
from src.config import create_client_from_model_name, get_model_config

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_PATH = BASE_DIR / "prompts.yaml"
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE_BASE = "logfile"
PLAY_ORDER = ["A", "B", "C", "D"]
DISCUSSION_ROUNDS = 2
DEFAULT_TOTAL_MATCHES = 1
MAX_RETRIES = 3


def format_history(history: List[Dict[str, str]]) -> str:
    """プレイヤー共有の会話履歴（speechのみ）を文字列化。"""

    if not history:
        return "まだ発言はありません。"
    lines = [f"{entry['agent']}: {entry['speech']}" for entry in history]
    return "\n".join(lines)


def build_user_prompt(template: str, history_text: str) -> str:
    """会話履歴プレースホルダを埋め込む。"""

    base_template = template.rstrip()
    if "{conversation_history}" in base_template:
        return base_template.replace("{conversation_history}", history_text)
    return (
        f"{base_template}\n\n---\n【現在の会話履歴】\n{history_text}\n---\n"
    )

def invoke_with_retries(
    client,
    messages: List[HumanMessage],
    *,
    require_vote: bool,
    max_retries: int,
    agent_id: str,
    model_alias: str,
) -> Tuple[Dict[str, str] | None, str | None, Exception | None]:
    """LLM呼び出しとJSONパースを指定回数まで再試行する。"""

    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.invoke(messages)
            content = getattr(response, "content", str(response))
            parsed = parse_agent_output(content, require_vote=require_vote)
            return parsed, content, None
        except (ValueError, JSONDecodeError) as exc:
            last_exc = exc
            print(
                f"Retryable parse error (attempt {attempt}/{max_retries}): {exc}"
            )
        except Exception as exc:
            last_exc = exc
            print(
                f"Retryable invocation error (attempt {attempt}/{max_retries}): {exc}"
            )
            if "getaddrinfo failed" in str(exc).lower():
                print(
                    f"HINT: モデル '{model_alias}' の接続先を解決できません。"
                    " config/models.yaml の base_url を確認してください。"
                )
    return None, None, last_exc


def parse_agent_output(raw_content: str, *, require_vote: bool = False) -> Dict[str, str]:
    """エージェントのJSON出力を辞書化する。"""

    sanitized = strip_code_fence(raw_content)
    data = orjson.loads(sanitized)
    thought = str(data.get("thought", "")).strip()
    speech = str(data.get("speech", "")).strip()
    if not speech:
        raise ValueError("JSONに'speech'が含まれていません。")
    vote = str(data.get("vote", "")).strip()
    if require_vote and not vote:
        raise ValueError("投票フェーズなのに'vote'が指定されていません。")
    return {"thought": thought, "speech": speech, "vote": vote}


def run(config: Dict, prompts: Dict, log_path: Path, run_index: int) -> bool:
    history: List[Dict[str, str]] = []
    votes: List[Dict[str, str]] = []
    discussion_history_snapshot: List[Dict[str, str]] = []
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

    discussion_history_snapshot = list(history)
    history_text = format_history(discussion_history_snapshot)

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
        success = run(config, prompts, log_path, run_index)
        if not success:
            print(f"=== Run #{run_index} failed. Moving to next match. ===")


if __name__ == "__main__":
    main()
