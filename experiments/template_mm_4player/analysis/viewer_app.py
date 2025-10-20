"""Streamlitアプリ: ログの会話・投票をざっと閲覧するビューア。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = EXPERIMENT_DIR / "logs"
DEFAULT_LOG_PATH = LOG_DIR / "templete_4player.jsonl"


def load_records(log_path: Path) -> List[dict]:
    records: List[dict] = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def main() -> None:
    st.set_page_config(page_title="Werewolf Log Viewer", layout="wide")
    st.title("Template MM 4-Player Log Viewer")

    if not LOG_DIR.exists():
        st.error(f"ログディレクトリが見つかりません: {LOG_DIR}")
        return

    log_files = sorted(LOG_DIR.glob("*.jsonl"))
    if not log_files:
        st.error("ログファイルが存在しません。")
        return

    default_index = 0
    for idx, path in enumerate(log_files):
        if path == DEFAULT_LOG_PATH:
            default_index = idx
            break

    selected_path = st.sidebar.selectbox(
        "ログファイル", log_files, index=default_index, format_func=lambda p: p.name
    )

    try:
        records = load_records(selected_path)
    except json.JSONDecodeError as exc:
        st.error(f"JSONの読み込みに失敗しました: {exc}")
        return

    if not records:
        st.warning("レコードが存在しません。")
        return

    df = pd.DataFrame(records)
    if "run" not in df.columns:
        st.error("ログに 'run' 列がありません。")
        return

    runs = sorted(df["run"].dropna().unique())
    selected_run = st.sidebar.selectbox("Run番号", runs, format_func=lambda x: int(x))

    run_df = df[df["run"] == selected_run].sort_values("turn_index")
    st.subheader(f"Run #{int(selected_run)}")

    discussion_rows = run_df[run_df.get("phase") == "discussion"]
    vote_rows = run_df[run_df.get("phase") == "vote"]
    summary_rows = run_df[run_df.get("phase") == "vote_summary"]

    with st.expander("議論フェーズ", expanded=True):
        if discussion_rows.empty:
            st.write("議論フェーズのログがありません。")
        else:
            for _, row in discussion_rows.iterrows():
                st.markdown(
                    f"### Turn {int(row.get('turn_index', -1))} — {row.get('agent', '?')}"
                )
                if row.get("speech"):
                    st.markdown(f"**Speech:** {row['speech']}")
                if row.get("thought"):
                    st.markdown("**Thought:**")
                    st.write(row["thought"])
                if row.get("images"):
                    st.caption(f"Images: {', '.join(row['images'])}")
                if row.get("system_prompt") or row.get("user_prompt"):
                    prompt_key = f"disc_prompt_{row.get('run', 0)}_{row.get('turn_index', -1)}_{row.get('agent', '?')}"
                    if st.checkbox("プロンプト (System/User) を表示", key=prompt_key):
                        if row.get("system_prompt"):
                            st.caption("System Prompt")
                            st.code(row["system_prompt"], language="markdown")
                        if row.get("user_prompt"):
                            st.caption("User Prompt")
                            st.code(row["user_prompt"], language="markdown")
                st.divider()

    with st.expander("投票フェーズ", expanded=True):
        if vote_rows.empty:
            st.write("投票フェーズのログがありません。")
        else:
            for _, row in vote_rows.iterrows():
                st.markdown(
                    f"#### {row.get('agent', '?')} — Vote: {row.get('vote', 'N/A')}"
                )
                if row.get("speech"):
                    st.markdown(f"**Speech:** {row['speech']}")
                if row.get("thought"):
                    st.markdown("**Thought:**")
                    st.write(row["thought"])
                prompt_key = f"vote_prompt_{row.get('run', 0)}_{row.get('turn_index', -1)}_{row.get('agent', '?')}"
                if st.checkbox("プロンプト (System/User) を表示", key=prompt_key):
                    if row.get("system_prompt"):
                        st.caption("System Prompt")
                        st.code(row["system_prompt"], language="markdown")
                    if row.get("user_prompt"):
                        st.caption("User Prompt")
                        st.code(row["user_prompt"], language="markdown")
                st.divider()

    if not summary_rows.empty:
        st.subheader("投票サマリー")
        summary = summary_rows.iloc[0]
        tally = summary.get("tally") or {}
        summary_df = pd.DataFrame(
            [
                {"target": target, "count": count}
                for target, count in tally.items()
            ]
        )
        if not summary_df.empty:
            summary_df["rate"] = summary_df["count"] / summary_df["count"].sum()
            st.table(summary_df)
        else:
            st.write("tally 情報がありません。")

    st.sidebar.markdown("---")
    st.sidebar.markdown("ログが更新された場合は再実行してください。")


if __name__ == "__main__":
    main()
