"""設定済みモデルでLLMに問い合わせる最小CLI。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DEFAULT_MODELS_PATH, create_client_from_model_name  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="config/models.yaml で定義したモデル名を使って問い合わせます。"
    )
    parser.add_argument("model_name", help="models.yaml に定義したモデル名")
    parser.add_argument("system_prompt", help="システムメッセージ")
    parser.add_argument("user_prompt", help="ユーザープロンプト")
    parser.add_argument(
        "--config-path",
        default=str(DEFAULT_MODELS_PATH),
        help="モデル設定YAMLへのパス (既定: config/models.yaml)",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="応答をストリーミング表示",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = create_client_from_model_name(args.model_name, config_path=Path(args.config_path))
    print(f"Using model configuration: {args.model_name}")

    messages = [
        SystemMessage(content=args.system_prompt),
        HumanMessage(content=args.user_prompt),
    ]

    if args.stream:
        print("Streaming response:\n", end="")
        for chunk in client.stream(messages):
            print(chunk, end="", flush=True)
        print()
    else:
        reply = client.invoke(messages)
        print(reply.content)


if __name__ == "__main__":
    main()
