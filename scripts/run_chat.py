"""設定ファイルで指定したプロバイダへプロンプトを送るCLI。"""
from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console

from langchain_core.messages import HumanMessage, SystemMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402  pylint: disable=wrong-import-position
    DEFAULT_MODELS_PATH,
    create_client_from_model_name,
)

app = typer.Typer(help="models.yaml の指定名でLLMに問い合わせます。")
console = Console()


@app.command()
def main(
    model_name: str = typer.Argument(..., help="config/models.yaml で定義したモデル名"),
    prompt: str = typer.Argument(..., help="ユーザープロンプト"),
    system_prompt: str = typer.Option(
        "あなたは研究支援アシスタントです。",
        "--system",
        help="先頭に付与するシステムメッセージ",
    ),
    config_path: Path = typer.Option(
        DEFAULT_MODELS_PATH,
        "--config-path",
        help="モデル設定YAMLのパス",
    ),
    stream: bool = typer.Option(False, "--stream", help="応答をストリーミング表示"),
) -> None:
    """設定ファイル上のモデル名でプロンプトを送信する。"""
    client = create_client_from_model_name(model_name, config_path=config_path)
    console.print(f"[green]設定 '{model_name}' を使用します")

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ]

    if stream:
        console.print("[bold green]ストリーミング応答[/bold green]\n", end="")
        for chunk in client.stream(messages):
            console.print(chunk, end="", highlight=False, soft_wrap=True)
        console.print()
    else:
        reply = client.invoke(messages)
        console.print(f"[bold blue]アシスタント[/bold blue] {reply.content}")


if __name__ == "__main__":
    app()
