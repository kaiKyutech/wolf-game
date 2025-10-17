# LangChain Multi-Provider Playground

このリポジトリは、LangChain を使って複数の LLM プロバイダ（Ollama, Gemini など）を切り替えながら利用する実験環境です。基本的な使い方は以下の `sample.ipynb` で確認できます。

## 事前準備
1. Python 3.12 をインストール。
2. 仮想環境を作成し、`pip install -r requirements.txt` を実行。
3. `.env` を用意し、API キー等の機密値を記入（例：`GEMINI_API_KEY`）。Ollama の `base_url` など公開設定は `config/models.yaml` に記述します。
4. `config/models.yaml` で使用するモデルのエイリアスを定義。

## ノートブックについて
ルートディレクトリにある `sample.ipynb` を開き、上から順に実行してください。
- Ollama と Gemini の呼び出し例
- ストリーミング応答の例


## CLI で試す
`config/models.yaml` の設定名を指定して以下の形式で実行できます。

```bash
python -m scripts.run_chat <model_name> "<system_prompt>" "<user_prompt>"
```

例:

```bash
python -m scripts.run_chat ollama_gemma3-27b "あなたは丁寧な研究員です" "自己紹介してください"
```

## Experiments

人狼ゲームなどシナリオベースの検証は `experiments/` フォルダで管理します。`basic_demo` を例に、`run.py` の中でどのモデルをどのエージェントへ割り当て、どの順番で `invoke()` するかを明示的に記述します。

実験の実行例:

```bash
python -m experiments.basic_demo.run
```

詳細なルールや新しいシナリオの追加方法は `experiments/README.md` を参照してください。
