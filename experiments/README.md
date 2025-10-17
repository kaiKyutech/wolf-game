# Experiments

各種人狼シナリオや検証をこのディレクトリ配下に追加していきます。

推奨構成:
```
experiments/
  └── one_night_default/
      ├── README.md
      ├── config.yaml
      ├── prompts/
      ├── run.py
      └── notes.ipynb
```

共通ロジックは `src/` のモジュールを利用し、実験ごとの設定・プロンプト・結果はここに閉じ込める想定です。

## 実行例
ワンナイト人狼の基本実験を実行するには、プロジェクトルートで以下を実行します。

```bash
python -m experiments.one_night_default.run
```

必要に応じて `config.yaml` を編集し、プロンプトやログ出力名を調整してください。
