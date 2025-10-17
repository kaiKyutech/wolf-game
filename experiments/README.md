# Experiments

人狼ゲームの検証を行うためのシナリオ一式を配置します。LangChain 側の共通コードは `src/` 配下にあり、各実験は「どのモデルを誰に割り当て、どんなプロンプトで進行させるか」をこのディレクトリ内で完結させる方針です。

## ディレクトリ構成

```
experiments/
  ├── README.md                # この説明
  ├── runner.py                # 実験共通の補助関数（必要に応じて利用）
  └── basic_demo/              # 例: ワンナイト人狼の基本デモ
      ├── config.yaml          # エージェント→モデルの割り当て、ログ名など
      ├── prompts.yaml         # エージェントごとの system/user プロンプト
      ├── run.py               # 実験フローを明示的に記述するエントリポイント
      └── logs/                # デモ実行時の出力ログ（JSONL）
```

> **メモ:** `run.py` では実験の進行手順を直接記述します。`create_client_from_model_name()` を使ってエージェントごとに LLM を構築し、`invoke()` の呼び出し順序をそのまま読み取れるように保つことを推奨します。

## 設定ファイルのルール

- `config.yaml` と `prompts.yaml` の `agents` セクションは **同じキー名で揃える必要があります。** 例: `config.yaml` で `agents.narrator` にモデルを割り当てたら、`prompts.yaml` 内にも `agents.narrator` のプロンプトを用意してください。
- モデル名は `config/models.yaml` に定義したエイリアスを記述します。複数エージェントで同じモデルを共有したい場合は同じエイリアスを繰り返し指定すれば構いません。
- ログは各実験フォルダ直下の `logs/` に出力されます。`config.yaml` の `log_filename` を省略すると `run.py` が実行時刻入りのファイル名を自動生成します。

## 実行方法

ワンナイト人狼の基本デモを実行する場合:

```bash
python -m experiments.basic_demo.run
```

`prompts.yaml` の文面を修正したり、`config.yaml` でモデル割り当てを切り替えたりすることで、同じコードを流用した実験を繰り返せます。新しいシナリオを追加する場合は `basic_demo` をテンプレートにフォルダを複製し、`run.py` にフローを記述してください。
