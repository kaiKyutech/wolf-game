# Template (4-Player, Text Only)

テキストのみで 4 人構成のワンナイト人狼を再現する実験テンプレートです。

- `config.yaml` は `config/models.yaml` に登録した `ollama_gpt-oss:20b` を参照します。自分の Ollama 環境に合わせて `base_url` を調整すればそのまま動作します。
- デフォルト構成は議論 2 ラウンド → 3 回目に投票フェーズへ移行し、`TOTAL_MATCHES = 1` で 1 試合だけ実行します。
- 応答取得は常に 3 回まで再試行します（想定外の JSON 形式でも自動リトライ）。
- 実行すると `logs/` に `logfile_001.jsonl` 形式で連番保存されます。既存ファイルを上書きしません。

```bash
python -m experiments.template_4player.run --matches 3
```

`--matches` を省略すると 1 試合だけ実行します。

解析は `analysis/analysis.ipynb` と `analysis/viewer_app.py`（Streamlit）で行えます。

```bash
streamlit run experiments/template_4player/analysis/viewer_app.py
```

好きなモデル構成やプロンプトを複製するときは、このテンプレートをベースにしてください。
