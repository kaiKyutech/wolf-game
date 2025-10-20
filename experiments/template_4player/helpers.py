"""4人用テキストテンプレートの補助関数群。"""
from __future__ import annotations

from typing import Dict, List, Tuple

import orjson
from orjson import JSONDecodeError
from langchain_core.messages import HumanMessage

from experiments.runner import strip_code_fence

PLAY_ORDER = ["A", "B", "C", "D"]
DISCUSSION_ROUNDS = 2
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


__all__ = [
    "PLAY_ORDER",
    "DISCUSSION_ROUNDS",
    "MAX_RETRIES",
    "format_history",
    "build_user_prompt",
    "invoke_with_retries",
]
