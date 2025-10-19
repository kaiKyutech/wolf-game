# Template (4-Player, Text Only)

テキストのみで 4 人版ワンナイト人狼を実験するテンプレートです。`run.py` では議論フェーズと投票フェーズを明確に分離し、ログを連番の JSONL として保存します。追加の画像入力は使用しません。

## フォルダ構成
```
template_4player/
  ├── config.yaml        # モデル割り当て・再試行回数などの設定
  ├── prompts.yaml       # プレイヤーごとの議論/投票プロンプト定義
  ├── run.py             # 試合フロー（TOTAL_MATCHES 分を連続実行）
  ├── analysis/
  │    ├── analysis.ipynb   # 勝率など簡易集計ノートブック
  │    └── viewer_app.py    # Streamlit ログビューア
  └── logs/             # 実行結果（logfile_001.jsonl など連番）
```

## 実験の流れ
1. `config.yaml` で `agents` のモデル名や `max_retries` を調整。
2. `python -m experiments.template_4player.run` を実行すると、`TOTAL_MATCHES` 分の試合が `logs/` に記録されます（既存ログを上書きせず、連番で新規作成）。
3. `analysis/analysis.ipynb` で勝率集計、`streamlit run analysis/viewer_app.py` で run ごとの議論ログを参照できます。

## プロンプト構成
- `discussion` ブロック: `thought` / `speech` のみを返すよう指示。
- `vote` ブロック: 役職情報を再掲し、`thought` / `speech` / `vote` を必ず JSON で返すよう指示。

このテンプレートをベースに、テキストのみのシナリオを複製・改変して実験を追加してください。
