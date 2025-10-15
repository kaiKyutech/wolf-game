# LangChainでプロバイダ横断のLLM呼び出しを理解するためのクイックスタート

目的は「LangChainの呼び出し構造」を把握することです。まずはローカルのOllamaを前提にしていますが、`provider`の差し替えだけで他プロバイダに展開できる形を意識しています。

---

## 1. 事前準備
```bash
# 仮想環境は任意
python3 -m venv .venv
source .venv/bin/activate

# pyproject.toml 作成前の暫定インストール例
pip install "langchain>=0.2" langchain-community langchain-core langchain-google-genai
```

- Ollamaを使う場合は、ローカルで`ollama serve`を起動しモデル（例: `ollama pull llama3.1`) を用意。
- Gemini/Claudeなど外部APIを使う場合は、後述の`provider`別設定を読み替えてください。

---

## 2. メッセージタイプとロール
LangChainはOpenAIのChat APIと似た概念で、ロールに応じたメッセージクラスを提供します。代表例は以下です。

- `SystemMessage`: モデルの振る舞いを制御するシステムプロンプト。
- `HumanMessage`: ユーザー入力。role=`user`に相当。
- `AIMessage`: モデルからの応答。role=`assistant`と同義。
- `FunctionMessage` / `ToolMessage`: ツール呼び出し結果を戻すときに使用（高度なエージェント設計向け）。

Chatモデルは`SystemMessage`と`HumanMessage`を入力に受け取り、応答として`AIMessage`を返します。Ollamaのassistantロールに対応するのは`AIMessage`で、会話履歴に格納する際は次のように使います。

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.chat_models import ChatOllama

llm = ChatOllama(model="llama3.1")
conversation = [SystemMessage(content="丁寧に回答してください")]

conversation.append(HumanMessage(content="自己紹介をお願いします"))
reply = llm.invoke(conversation)  # ここで返るのが AIMessage
conversation.append(reply)        # role=assistant のメッセージとして履歴に追加
```

この仕組みは他プロバイダでも同じです。

## 3. 最小の同期呼び出し（システム + ユーザープロンプト）
```python
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOllama(model="llama3.1", temperature=0.2)

messages = [
    SystemMessage(content="あなたは親切なアシスタントです"),
    HumanMessage(content="LangChainの役割を一言で教えてください")
]

response = llm.invoke(messages)
print(response.content)
```

- `SystemMessage` + `HumanMessage` のリストを渡すのがLangChainの基本インターフェースです。
- `invoke` は同期API。`astream` を使うとストリーム受信も可能です。

---

## 4. Gemini（Google Generative AI）を使った呼び出し
Geminiを利用する場合は `langchain-google-genai` の `ChatGoogleGenerativeAI` をラップします。APIキーは環境変数 `GEMINI_API_KEY`（または `.env` 内の `GEMINI_API_KEY`）に設定してください。

```python
from langchain_core.messages import SystemMessage, HumanMessage
from src.api import LLMClient

client = LLMClient.from_gemini_settings(model="gemini-1.5-pro", temperature=0.1)
response = client.invoke([
    SystemMessage(content="あなたは要約の専門家です"),
    HumanMessage(content="LangChainでGeminiを呼び出すポイントを簡潔にまとめて"),
])
print(response.content)
```

- `model` は `gemini-1.5-flash` などに差し替え可能。
- Google側の安全設定が必要なケースでは `safety_settings` など追加パラメータも `from_gemini_settings()` のキーワード引数経由で渡せます。

## 5. PromptTemplateを使った柔軟なプロンプト構築
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOllama

prompt = ChatPromptTemplate.from_messages([
    ("system", "あなたは要点を簡潔にまとめる専門家です"),
    ("human", "{question}")
])

chain = prompt | ChatOllama(model="llama3.1", temperature=0.3)

result = chain.invoke({"question": "LangChainのRunnableとは何ですか?"})
print(result.content)
```

- `ChatPromptTemplate` でテンプレート化し、`|` 演算子でモデルに接続すると再利用しやすい`Runnable`を構築できます。
- 他プロバイダでも同じチェーンを利用でき、差し替えるのは`ChatOllama`の部分だけです。

---

## 6. セッション（履歴）を持つ会話の例
```python
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage

llm = ChatOllama(model="llama3.1", temperature=0.6)
conversation: list = []

def chat(user_text: str):
    conversation.append(HumanMessage(content=user_text))
    reply = llm.invoke(conversation)
    conversation.append(AIMessage(content=reply.content))
    return reply.content

print(chat("こんにちは、あなたは誰?"))
print(chat("LangChainで会話履歴を扱う利点は?"))
```

- 履歴をPython側で管理し、毎回`conversation`全体を渡すだけでも基本を把握できます。
- 後で`ConversationBufferMemory`などLangChainのメモリクラスに差し替えれば管理が楽になります。

---

## 7. 画像入力（マルチモーダル）を扱うパターン
LangChainは`HumanMessage`の`content`に複数タイプの要素を持たせることで画像を扱えます。以下はHTTP API経由などで画像をbase64化して渡す例です（モデル側でVision対応が必要）。

```python
import base64
from pathlib import Path
from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOllama  # 視覚対応モデルが必要

img_b64 = base64.b64encode(Path("sample.png").read_bytes()).decode()

vision_message = HumanMessage(content=[
    {"type": "text", "text": "この画像の説明をしてください"},
    {"type": "image_url", "image_url": f"data:image/png;base64,{img_b64}"}
])

llm = ChatOllama(model="llava:34b", temperature=0.1)
response = llm.invoke([vision_message])
print(response.content)
```

- 画像対応のOllamaモデル（例: `llava`系）が必要です。
- GeminiやClaude Visionを使う場合も、`HumanMessage`に`image_url`と`text`を混在させる構造は同じです。

---

## 8. RAG（Retrieval Augmented Generation）の最小構成
LangChainでは`TextSplitter`で文書を分割し、`VectorStore`に格納した後、`RetrievalQA`などのチェーンでLLMと結び付けます。まずはローカルメモリ向けにFAISSを使う例です。

```python
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from langchain.chains import RetrievalQA
from langchain_community.chat_models import ChatOllama

# 1. 文書読み込み・分割
loader = TextLoader("docs/rules_werewolf.txt", encoding="utf-8")
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 2. ベクトル化してインデックス化
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vector_store = FAISS.from_documents(chunks, embedding=embeddings)
retriever = vector_store.as_retriever()

# 3. LLMと組み合わせて質問応答
llm = ChatOllama(model="llama3.1", temperature=0.2)
qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever)

answer = qa.invoke({"query": "占い師の夜の行動を教えて"})
print(answer)
```

- 埋め込みモデルもOllamaベースで統一できますが、`OpenAIEmbeddings`など外部APIも差し替え可能です。
- Werewolfの記憶制御は、この`vector_store`やLangChainの`Memory`クラスを組み合わせて「どこまで履歴を保持/検索するか」を調整します。
- 大規模運用ではベクトルDB（Chroma, Weaviate, Qdrantなど）への置き換えも簡単です。

## 9. Notebookとスクリプトで共通に使うための簡単なラッパ
CLIからは `python scripts/run_chat.py gemini_flash "プロンプト"` のように呼び出すと、models.yaml のエイリアスで切り替えられます。

```python
# src/api/simple_client.py （今後の骨組みの入口イメージ）
from typing import Sequence
from langchain_core.messages import BaseMessage
from langchain_community.chat_models import ChatOllama

class SimpleLLMClient:
    def __init__(self, model: str = "llama3.1", temperature: float = 0.2):
        self._llm = ChatOllama(model=model, temperature=temperature)

    def invoke(self, messages: Sequence[BaseMessage]):
        return self._llm.invoke(messages)
```

Notebookでは以下のように使えます。
```python
from langchain_core.messages import SystemMessage, HumanMessage
from src.api.simple_client import SimpleLLMClient

client = SimpleLLMClient()
reply = client.invoke([
    SystemMessage(content="あなたは厳格なプロンプトエンジニアです"),
    HumanMessage(content="LangChainのRunnableを説明して")
])
print(reply.content)
```

CLI `.py` スクリプトでも同じ呼び出しができるため、学習フェーズで「共通の呼び出しパターン」を体感できます。今後はこのラッパを拡張し、プロバイダごとの設定管理、ストリーミング、構造化出力などを段階的に追加していきます。

---

## 10. YAML設定でモデルを切り替える
`config/models.yaml` に複数のモデル設定を登録し、名前で呼び出せます。

```yaml
models:
  ollama_default:
    provider: ollama
    model: llama3.1
    base_url: https://example.com
  gemini_flash:
    provider: gemini
    model: gemini-1.5-flash
    temperature: 0.1
```

コードからは `create_client_from_model_name("ollama_default")` のように指定します。CLI では
`python scripts/run_chat.py gemini_flash "..."` とするだけで切り替え可能です。

```python
from src.config import create_client_from_model_name
client = create_client_from_model_name("ollama_default")
```

## 11. 次の確認ポイント
- Notebook用に `notebooks/langchain_basics/` を用意しました。ここに実際の呼び出しノートを追加します。
- 上記サンプルコードを実際に動かし、LangChainの`messages`モデルと`prompt`テンプレートの感覚を掴む。
- 画像付きリクエストやJSON出力など、実際に必要なI/O形式を試して差異を把握する。

これらを理解すると、次段階のAPI骨組み実装が見通しやすくなります。
