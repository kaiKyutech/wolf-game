"""ワンナイト人狼（基本設定）の進行フロー。"""
from __future__ import annotations

from pathlib import Path

from experiments.runner import ExperimentRunner

CONFIG_PATH = Path(__file__).with_name("config.yaml")


def run() -> None:
    runner = ExperimentRunner(CONFIG_PATH)
    runner.run()


if __name__ == "__main__":
    run()
