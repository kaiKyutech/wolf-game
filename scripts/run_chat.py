"""設定済みモデルでLLMに問い合わせる最小CLI。"""
from __future__ import annotations

import argparse

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import DEFAULT_MODELS_PATH, create_client_from_model_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="config/models.yaml で定義したモデル名を使って問い合わせます。"
    )
    parser.add_argument("model_name", help="models.yaml に定義したモデル名")
    parser.add_argument("system_prompt", help="システムメッセージ")
    parser.add_argument("user_prompt", help="ユーザープロンプト")    
    parser.add_argument(
        "--stream",
        action="store_true",
        help="応答をストリーミング表示",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = create_client_from_model_name(args.model_name)
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
