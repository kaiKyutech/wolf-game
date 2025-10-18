# Experiments

このディレクトリには、LangChain を使った人狼ゲーム実験のテンプレートがまとまっています。
主に以下の2パターンを用意しています。

- `template_4player/`: テキストのみで4人プレイの議論 → 投票をシミュレート。
- `template_mm_4player/`: テキスト + 画像（images/ 配下のPNG/JPEG）を参照させるマルチモーダル版。議論と投票を2フェーズに分け、投票フェーズでは必ず1名に投票するようプロンプトを強化しています。

## 実行手順

各テンプレートの `run.py` は、`TOTAL_MATCHES`（デフォルト1）だけ連続試合を回し、`logs/` に `logfile_001.jsonl`, `logfile_002.jsonl` … のように連番で保存します。

```bash
python -m experiments.template_mm_4player.run
```

設定は `config.yaml` で行います。モデル割り当て（`agents`）、再試行回数（`max_retries`、デフォルト3）、プロンプトファイル（`prompts.yaml`）などが指定できます。

## 分析ツール

各テンプレートの `analysis/` ディレクトリに、解析向けツールを揃えています。

- `analysis.ipynb`: `../logs/*.jsonl` を読み込み、試合ごとの `vote_summary` から簡易的な勝率や投票傾向を確認するノートブック。
- `viewer_app.py`: Streamlit アプリ。`streamlit run experiments/template_mm_4player/analysis/viewer_app.py` で起動し、run ごとの議論ログ・thought・vote・サマリーを折りたたみ形式で閲覧できます。

ノートブック側で深入り（ワード単位の分析など）を行い、Streamlit で異常な試合の生データを簡単に掘り下げる運用を想定しています。ログファイルが追加されるたびにノートブック/Streamlit を再実行すれば最新状況を反映できます。
