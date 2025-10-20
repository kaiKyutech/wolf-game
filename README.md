# AI人狼ゲーム

このリポジトリは、LangChain を使って複数の LLM プロバイダ（Ollama, Gemini, OpenAI, Anthropic など）を切り替えながら、人狼ゲームの実験フローを構築・検証するための環境です。今後の利用は `experiments/` ディレクトリを基点に進めます。

## 事前準備
1. Python 3.12 をインストール。
2. 仮想環境を作成し、`pip install -r requirements.txt` を実行。
3. `.env` を用意し、API キー等の機密値を記入（例：`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`）。Ollama の `base_url` など公開設定は `config/models.yaml` に記述します。
4. `config/models.yaml` で使用するモデルのエイリアスを定義。

## Experiments へ進む
人狼ゲーム関連の実装・運用は `experiments/` 以下にまとめています。まずは `experiments/README.md` を確認してください。

- `experiments/template_4player/`: テキストのみの 4 人版ワンナイト人狼テンプレート。
- `experiments/template_mm_4player/`: 画像入力も扱うマルチモーダル版テンプレート。

各テンプレートには設定ファイル、連番ログ保存、解析ノートブック／Streamlit ビューアなどが揃っています。実験手順やログの扱いも `experiments/README.md` に記載しています。
