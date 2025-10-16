# LangChain Multi-Provider Playground

このリポジトリは、LangChain を使って複数のLLMプロバイダ（Ollama, Gemini など）を切り替えながら利用する実験環境です。基本的な使い方は以下の `sample.ipynb` で確認できます。

## 事前準備
1. Python 3.10 以上をインストール。
2. 仮想環境を作成し、 `pip install -r requirements.txt` で
3. `.env` を用意してに必要な設定を記入。（例：`OLLAMA_BASE_URL`, `GEMINI_API_KEY`）
4. `config/models.yaml` で使用するモデルのエイリアスを定義。

## ノートブックについて
ルートディレクトリにある `sample.ipynb` を開き、上から順に実行してください。
- Ollama と Gemini の呼び出し例
- ストリーミング応答の例

