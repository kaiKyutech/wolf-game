# Template (4-Player, Multimodal)

画像も扱う 4 人構成のワンナイト人狼テンプレートです。議論・投票フローはテキスト版と同じですが、各ターンで `images/` 配下のファイルをマルチモーダル入力として渡します。

- `config.yaml` は `config/models.yaml` の `ollama_gemma3:27b` を利用します。手元の Ollama エンドポイントに合わせて `base_url` を調整してください。
- デフォルト挙動は議論 2 ラウンド → 3 回目で投票、`TOTAL_MATCHES = 1` の単一試合、リトライ上限は常に 3 回です。
- 生成されたログは `logs/` に `logfile_001.jsonl` 形式で連番保存され、画像名もレコードに含まれます。

```bash
python -m experiments.template_mm_4player.run --matches 3
```

`--matches` を省略すると 1 試合だけ実行します。

`analysis/analysis.ipynb` と `analysis/viewer_app.py`（Streamlit）でログの可視化・ドリルダウンが可能です。

```bash
streamlit run experiments/template_mm_4player/analysis/viewer_app.py
```

画像セットやプロンプトを差し替えてシナリオを拡張する際のたたき台として活用してください。
