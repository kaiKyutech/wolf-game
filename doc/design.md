# LangChainベースAI人狼システム設計

## 1. 背景と目的
- LangChainを横断的に扱うAPIレイヤを整備し、システム・ユーザープロンプトや画像入力など各種LLMインタラクションを統一的に呼び出せるようにする。
- まずはローカルのOllamaで確実に動かしつつ、将来的にGeminiやClaudeなど外部プロバイダへ拡張しやすい構造を設計する。
- ワンナイト人狼はユースケースの1つとして据え、API理解の助けとなる軽量サンプルを提供する。

## 2. 対象スコープ
- LangChainの`ChatModel`/`Runnable`を共通のラッパで扱うAPIの設計と実装。
- システムプロンプト・ユーザープロンプト・ツール入力（画像など）を扱う呼び出しサンプルの整備。
- Notebook（対話的）と`.py`スクリプト（バッチ/CLI）の双方から同じAPIを利用できるようにする。
- ログ/設定管理は最小限に留め、後続の人狼シミュレーションで段階的に拡張する。
- GUIは対象外。CLI / Notebook / バッチでの操作を想定。

## 3. 初期マイルストーン（LangChain基礎API）
1. Provider非依存でシステム/ユーザープロンプトを送信できる`LLMClient`ラッパを作成。
2. NotebookとCLIサンプルから同一インターフェースで呼び出しできるデモを準備。
3. 画像やJSON出力など異なるI/Oパターンを扱うユースケースをAPIで共通化。
4. 応答ログや設定の保存フォーマット（JSONL/CSV）を整備し、追跡しやすくする。

## 4. 全体アーキテクチャ概要
```
+---------------------------+        +---------------------------+
| Notebook / プレイグラウンド |        | CLI / バッチランナー        |
+--------------+------------+        +--------------+------------+
               |                               |
               v                               v
    +----------+--------------------------------+-------+
    |      インタラクションAPI / LLMクライアント       |
    +----------+--------------------------------+-------+
               |                               |
               v                               v
+--------------+--------------+        +-------------+------------+
| プロバイダアダプタ層         |<------>| 設定・プロンプトストア        |
+--------------+--------------+        +-------------+------------+
               |
               v
         +-----+-----+
         | LangChain |
         |  モデル群  |
         +-----------+
          （Ollama など）

               ↓ （フェーズ2以降）
         +---------------------+
         | シミュレーション層   |
         | （人狼などの拡張） |
         +---------------------+
```

## 5. コンポーネント詳細
- **Config / Prompt Store**: プロンプトテンプレート、システムメッセージ、プロバイダ設定（モデル名、温度、APIキー）をYAML/JSONで管理。`config/models.yaml` でモデル名→設定を定義し、`create_client_from_model_name` で動的に切り替え。
- **プロバイダアダプタ**: `ChatOllama`に加え、`ChatGoogleGenerativeAI`（Gemini）など他プロバイダへ切り替え可能なファクトリ。統一インターフェース（`LLMClient.generate(messages, config)`）を提供。
- **インタラクションAPI**: Notebook/CLIから呼び出す公共窓口。単発呼び出しと会話セッションの双方を扱い、プロンプトや入出力の型を揃える。
- **サンプルユースケース**: シンプルなQA、システムプロンプト制御、画像キャプション生成、（拡張）ワンナイト人狼のロールプレイなどをモジュール化。
- **エージェント / シミュレーション層（フェーズ2以降）**: プレイヤーID・役職・行動方針のテンプレートからLangChainの`Runnable`グラフを構築し、ゲーム進行を制御。
- **ロガー / ストレージ**: 呼び出し履歴・設定・応答ストリームをJSON Linesで保存。オプションでSQLiteやDuckDBへの格納にも対応。
- **評価 / レポート**: API利用ログの分析、ゲームシナリオ時の勝敗や矛盾検出、プロバイダ比較などを支援。

## 6. LangChain活用・API設計方針
- インタフェース統一: `BaseLLMClient`（同期/非同期メソッド）を定義し、Notebook/CLIいずれからも同じ呼び出しパターンで利用。
- プロンプト構築: `ChatPromptTemplate` + `MessagesPlaceholder`で履歴を安全に組み立てる。ユーティリティ関数でシステム/ユーザープロンプトを柔軟に差し替え。
- マルチモーダル対応: 画像を扱う場合はLangChainの`ImageInput`やBase64エンコードをサポートする拡張を用意。
- モデル呼び出し: 初期は`ChatOllama`。Streamingが必要な場合はLangChainの`astream`を使用し、API側でコールバック or イテレータを提供。
- 出力パース: JSON形式や構造化データを返すケースは`StructuredOutputParser`や`JsonOutputParser`を利用し、API層で例外処理・再試行を実装。
- セッション管理: CLIとNotebook双方で共有できる`ConversationSession`（履歴、メタデータ、ログ書き出し）を定義。
- モデル選択: `config/models.yaml`の名前解決を通じて、環境ごとに異なるモデル構成を簡潔に切り替える。
- 記憶/RAG連携: LangChainのMemory APIとベクトルリトリーバ（FAISS/Chroma等）を組み合わせ、必要な履歴のみを取得してプロンプトに差し込む。人狼の役職別記憶制御にも転用。

## 7. プロジェクト構成案
```
langchain-1014-v2/
├── doc/
│   └── design.md
├── notebooks/
│   ├── playground.ipynb         # LangChainお試し
│   ├── api_demo.ipynb           # 共通APIのNotebookデモ
│   └── gemini_client.ipynb      # Geminiアクセスのサンプル
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py            # 共通LLMクライアント
│   ├── config/
│   │   ├── __init__.py          # 設定ローダの公開
│   │   └── models.py            # YAMLベースのモデル辞書
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── ollama.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── templates.py         # システム/ユーザープロンプト管理
│   ├── sessions/
│   │   ├── __init__.py
│   │   └── conversation.py      # 履歴・ログ管理
│   ├── use_cases/
│   │   ├── __init__.py
│   │   ├── basic_chat.py        # シンプルな会話サンプル
│   │   ├── multimodal.py        # 画像入力など
│   │   └── werewolf_demo.py     # 応用ユースケース
│   └── utils/
│       ├── __init__.py
│       └── logging.py
├── scripts/
│   ├── run_chat.py              # CLIからAPIを呼び出す例
│   └── run_multimodal.py
└── data/
    └── logs/
```
- `pyproject.toml`でライブラリ（langchain, langchain-community, pydantic, typer等）を管理予定。

## 8. 参考ユースケース（ワンナイト人狼）
API基盤が整った後の応用例。API層で複数プロバイダを扱う運用に慣れるための発展課題として位置付ける。
1. エクスペリメント設定読み込み（モデル、温度、ゲーム回数）。
2. `AgentFactory`がプレイヤーA-Dを生成し、役職情報を渡す。
3. 夜フェーズ: 役職固有のアクションを実行し、内部状態を更新。
4. 議論フェーズ: ターン制でメッセージ生成。LangChainが各エージェントのthought/speech JSONを返す。
5. 投票フェーズ: 各エージェントに最終判断プロンプトを与え、投票先を取得。
6. 勝敗判定後、`Logger`に記録し、`Eval`が集計。
7. バッチ実行では上記を指定回数ループし、結果をCSV/JSONでまとめる。

## 9. 拡張計画
- **プロバイダ**: Gemini/Claude等を追加する際はProvider Adapterにクラスを拡張し、APIキー管理を`.env` / Vaultで行う。
- **自動評価**: LLMジャッジによるロールプレイ品質評価、ロジック矛盾検出をLangChainの別チェーンで実装。
- **RAG/記憶強化**: 役職別メモリや過去ゲームログをベクトルDBに蓄積し、必要な情報のみをリトリーブして推論に利用。
- **ツール利用**: 外部検索やメモリを使う高度な戦略エージェントをLangChain Agent Toolとして追加。
- **分散実行**: 多数試行に向けて、PrefectやAirflowなどのジョブオーケストレータと連携する余地を残す。

## 10. リスクと対策
- **プロバイダAPI差異**: パラメータ名や制約の違いをアダプタ層で吸収し、共通設定クラスでバリデーションを行う。
- **モデル応答フォーマット崩れ**: `StructuredOutputParser`で厳格にパースし、再プロンプトやRetryチェーンを導入。
- **LLMの幻覚によるルール逸脱**: システムメッセージでルールと禁止事項を強調し、違反検出ロジックをEvalで追加する。
- **コスト/性能差**: プロバイダごとにメトリクスを記録し、比較分析を可能にする。
- **状態爆発**: ゲーム履歴を最小限の構造体で保持し、LangChainの`trim_messages`等でトークンを制御。


## 11. 必要ライブラリとツール
- **Python 3.10+**: `Enum`/`match`構文や型ヒントの活用を想定。
- **langchain**: プロンプトチェーン/ランナブルの基盤。
- **langchain-community**: `ChatOllama`などコミュニティ実装のLLMクライアント。
- **langchain-core** (自動依存だが明示的にPin推奨): 低レベルRunnable/APIを安定運用。
- **langchain-ollama** (必要に応じて): Ollamaエンドポイント用の軽量依存。
- **langchain-google-genai**: Geminiとの連携を提供。
- **pyyaml**: YAML設定(`config/models.yaml`)の読み書き。
- **python-dotenv**: Notebook/CLIで`.env`を自動読み込み。
- **pydantic** / **pydantic-settings**: 設定管理やモデルバリデーション。
- **typer**: CLIエントリポイント作成。
- **rich**: 進捗やログの整形表示。
- **orjson** または **ujson**: 高速JSONシリアライズ（ログ出力）。
- **pytest** + **pytest-asyncio**: ゲームロジックの単体テスト。
- **ruff**: Lint/フォーマット統合で可読性維持。

## 12. 次のステップ
1. `pyproject.toml`を作成し、LangChain + Ollama依存とAPIラッパ（YAML設定ローダ含む）の骨組みを実装。
2. `src/providers/ollama.py`および共通`llm_client.py`を整備し、Notebook/CLIから同じメソッドで呼び出すデモを用意。
3. マルチモーダル入力（例: 画像説明）と構造化出力（JSON応答）のサンプルを追加。
4. 後続のワンナイト人狼シナリオに向けたサンプルノートブックを準備し、API利用例として整理。
