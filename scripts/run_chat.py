"""Ollamaエンドポイントへ1件のプロンプトを送るCLI。"""
from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Prompt

from langchain_core.messages import HumanMessage, SystemMessage

from src.api import LLMClient

app = typer.Typer(help="LangChain経由でリモートOllamaサーバーに問い合わせます。")
console = Console()


@app.command()
def main(
    prompt: str = typer.Option(
        None,
        "-p",
        "--prompt",
        help="ユーザープロンプト。省略時は対話的に入力。",
    ),
    system_prompt: str = typer.Option(
        "あなたは研究支援アシスタントです。",
        "--system",
        help="ユーザープロンプトの前に付与するシステムメッセージ。",
    ),
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        envvar="OLLAMA_BASE_URL",
        help="OllamaサーバーのベースURL（環境変数より優先）。",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        envvar="OLLAMA_MODEL",
        help="Ollamaで使用するモデル名。",
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature",
        help="サンプリング温度。指定があれば設定を上書き。",
    ),
    stream: bool = typer.Option(
        False,
        "--stream",
        help="応答をストリーミング表示するか。",
    ),
) -> None:
    """設定されたOllamaエンドポイントへプロンプトを送信する。"""
    # コマンドライン引数または対話入力でユーザープロンプトを取得
    if prompt is None:
        prompt = Prompt.ask("ユーザープロンプト")

    overrides = {}
    if base_url:
        overrides["base_url"] = base_url
    if model:
        overrides["model"] = model
    if temperature is not None:
        overrides["temperature"] = temperature

    # 指定された設定でOllamaクライアントを準備
    client = LLMClient.from_ollama_settings(**overrides)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=prompt),
    ]

    # ストリーミング出力と一括出力の両方に対応
    if stream:
        console.print("[bold green]ストリーミング応答[/bold green]\n", end="")
        for chunk in client.stream(messages):
            console.print(chunk, end="", highlight=False, soft_wrap=True)
        console.print()  # newline after stream
    else:
        reply = client.invoke(messages)
        console.print(f"[bold blue]アシスタント[/bold blue] {reply.content}")


if __name__ == "__main__":
    app()
