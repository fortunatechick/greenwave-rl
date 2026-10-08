"""Live plots for the side-by-side demo.

    streamlit run demo/dashboard.py

Tails results/raw/demo_live.jsonl, written by demo/side_by_side.py.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

LIVE = Path(__file__).resolve().parents[1] / "results" / "raw" / "demo_live.jsonl"

st.set_page_config(page_title="GreenWave live", layout="wide")
st.title("GreenWave: live side-by-side")


def load() -> pd.DataFrame:
    if not LIVE.exists():
        return pd.DataFrame()
    rows = []
    for line in LIVE.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:  # a line still being written
            continue
    return pd.DataFrame(rows)


df = load()
if df.empty:
    st.info("Waiting for demo/side_by_side.py to start writing metrics...")
else:
    names = df.groupby("side")["name"].first().to_dict()
    cols = st.columns(len(names))
    for col, (side, name) in zip(cols, sorted(names.items()), strict=True):
        last = df[df["side"] == side].iloc[-1]
        col.subheader(f"{side.title()}: {name}")
        a, b, c = col.columns(3)
        a.metric("Queue (veh)", f"{last['queue']:.0f}")
        b.metric("Mean wait (s)", f"{last['mean_wait']:.1f}")
        c.metric("Longest wait (s)", f"{last['max_wait']:.0f}")

    for column, title in (("mean_wait", "Mean wait of vehicles on the approaches (s)"),
                          ("queue", "Halting vehicles on the approaches"),
                          ("max_wait", "Longest wait on any approach (s)")):  # fmt: skip
        st.caption(title)
        wide = df.pivot_table(index="t", columns="name", values=column, aggfunc="last").ffill()
        st.line_chart(wide, height=220)
    st.caption(f"Simulation time {int(df['t'].max())} s")

time.sleep(1.0)
st.rerun()
