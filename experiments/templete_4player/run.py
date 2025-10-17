"""4人用ワンナイト人狼テンプレートの進行フロー。"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import orjson
from langchain_core.messages import HumanMessage, SystemMessage

from experiments.runner import setup_experiment_environment, strip_code_fence
from src.config import create_client_from_model_name

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.yaml"
PROMPTS_PATH = BASE_DIR / "prompts.yaml"
LOGS_DIR = BASE_DIR / "logs"
DEFAULT_LOG_NAME = "templete_4player.jsonl"
PLAY_ORDER = ["A", "B", "C", "D"]
DISCUSSION_ROUNDS = 2
VOTE_PROMPT = (
    "【投票フェーズ】\n"
    "――議論の時間が終了しました。これから追放すると思うプレイヤーを1人選んでください。\n"
    "あなたの目的は『自分が生き残ること』です。これまでの議論を踏まえ、最も怪しい人物を判断し、"
    "JSON の `vote` フィールドに追放したいプレイヤー名を必ず記入してください。"
)


def format_history(history: List[Dict[str, str]]) -> str:
    """プレイヤー共有の会話履歴（speechのみ）を文字列化。"""

    if not history:
        return "まだ発言はありません。"
    lines = [f"{entry['agent']}: {entry['speech']}" for entry in history]
    return "\n".join(lines)


def build_user_prompt(template: str, history_text: str, *, append_vote: bool = False) -> str:
    """会話履歴プレースホルダを埋め込み、必要に応じて投票指示を付与。"""

    base_template = template.rstrip()
    if append_vote:
        base_template = f"{base_template}\n\n{VOTE_PROMPT}"

    if "{conversation_history}" in base_template:
        return base_template.replace("{conversation_history}", history_text)
    return (
        f"{base_template}\n\n---\n【現在の会話履歴】\n{history_text}\n---\n"
    )

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


def run(config: Dict, prompts: Dict, log_path: Path, run_index: int) -> None:
    history: List[Dict[str, str]] = []
    votes: List[Dict[str, str]] = []
    turn_counter = 0

    # 議論フェーズ
    for round_index in range(1, DISCUSSION_ROUNDS + 1):
        for agent_id in PLAY_ORDER:
            model_alias = config["agents"][agent_id]
            prompt_bundle = prompts["agents"][agent_id]

            client = create_client_from_model_name(model_alias)
            system_prompt = prompt_bundle["system_prompt"].strip()
            user_prompt_template = prompt_bundle["user_prompt"]
            conversation_text = format_history(history)
            user_prompt = build_user_prompt(
                user_prompt_template,
                conversation_text,
                append_vote=False,
            )

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt.strip()),
            ]

            response = client.invoke(messages)
            content = getattr(response, "content", str(response))

            try:
                parsed = parse_agent_output(content, require_vote=False)
            except Exception as exc:
                print(f"ERROR: {agent_id} の応答をJSONとして解析できませんでした -> {exc}")
                print(f"RAW RESPONSE: {content}")
                raise

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

    # 投票フェーズ
    vote_round = DISCUSSION_ROUNDS + 1
    for agent_id in PLAY_ORDER:
        model_alias = config["agents"][agent_id]
        prompt_bundle = prompts["agents"][agent_id]

        client = create_client_from_model_name(model_alias)
        system_prompt = prompt_bundle["system_prompt"].strip()
        user_prompt_template = prompt_bundle["user_prompt"]
        conversation_text = format_history(history)
        user_prompt = build_user_prompt(
            user_prompt_template,
            conversation_text,
            append_vote=True,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt.strip()),
        ]

        response = client.invoke(messages)
        content = getattr(response, "content", str(response))

        try:
            parsed = parse_agent_output(content, require_vote=True)
        except Exception as exc:
            print(f"ERROR: {agent_id} の投票応答をJSONとして解析できませんでした -> {exc}")
            print(f"RAW RESPONSE: {content}")
            raise

        history.append({
            "agent": agent_id,
            "thought": parsed["thought"],
            "speech": parsed["speech"],
        })
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
            "visible_history": format_history(history),
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
