# Experiments

人狼ゲームの実験はすべてこのディレクトリで行います。`run.py` を中心にシナリオを組み立て、`config.yaml` と `prompts.yaml` でモデル割り当てとプロンプトを差し替えていきます。

## 編集するファイル
- `run.py`
  - 実験の進行フローを書くメインファイルです。
  - `setup_experiment_environment()` で設定とログを読み込み、返ってくる `config` / `prompts` を元にターン処理を記述します。
  - `create_client_from_model_name()` と `invoke()` を使い、各エージェントの発話を生成します。
- `config.yaml`
  - `agents` のキー名をエージェントIDとして定義し、対応するモデル（`config/models.yaml` のエイリアス）を指定します。
  - ログファイル名を変えたい場合は `log_filename` を追加します。
- `prompts.yaml`
  - `agents.<agent_id>.system_prompt` / `user_prompt` にそれぞれの台詞を記述します。

## 編集しないファイル
- `logs/` ディレクトリ配下の JSONL ファイル（`run.py` が追記します）
- `runner.py` の既存ロジック（新しいユーティリティを追加したい場合のみ要調整）

## 最小の手順
1. `basic_demo/` を参考に、必要ならフォルダを複製します。
2. `config.yaml` と `prompts.yaml` のエージェントIDを揃えつつ、内容を調整します。
3. `run.py` でプレイヤー順やターンの構成を記述します。
4. `python -m experiments.<scenario>.run` を実行し、`logs/` に結果が追記されることを確認します。

実行例:
```bash
python -m experiments.basic_demo.run
```
