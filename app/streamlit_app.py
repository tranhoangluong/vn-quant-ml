"""Dashboard portfolio (giai đoạn 5, có thể cắt nếu trễ hạn). Deploy miễn phí: Streamlit Community Cloud.

Chạy: make app
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="VN30 uncertainty-aware stock selection", layout="wide")
st.title("VN30: chọn cổ phiếu có ý thức về bất định")
st.caption("Dự án nghiên cứu, không phải khuyến nghị đầu tư.")

runs = sorted(Path("experiments").glob("*_*"))
if not runs:
    st.info("Chưa có run nào. Chạy `make all` trước.")
    st.stop()
run = st.selectbox("Run", runs[::-1], format_func=lambda p: p.name)
if (run / "backtest.parquet").exists():
    bt = pd.read_parquet(run / "backtest.parquet")
    st.line_chart((1 + bt[["gross", "net"]]).cumprod())
for f in ("metrics_forecast.json", "metrics_portfolio.json"):
    if (run / f).exists():
        st.json(json.loads((run / f).read_text()))
