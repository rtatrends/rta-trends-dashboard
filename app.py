import os, io, time, re, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

RAW_CSV_URL = os.environ.get("RAW_CSV_URL", "").strip()
LOCAL_CSV = "Last_30_Day_Data_Group_45.csv"

@st.cache_data(show_spinner=True, ttl=300)
def load_data(raw_url: str, local_path: str):
    if raw_url:
        r = requests.get(raw_url, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content), parse_dates=["Time"])
        source = "remote (GitHub raw)"
        updated = r.headers.get("Last-Modified", "GitHub")
    else:
        df = pd.read_csv(local_path, parse_dates=["Time"])
        source = "local (repo file)"
        updated = time.ctime(os.path.getmtime(local_path)) if os.path.exists(local_path) else "unknown"
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df.dropna(subset=["Time", "Value"], inplace=True)
    df.sort_values("Time", inplace=True)
    return df, source, updated

df, data_source, last_updated = load_data(RAW_CSV_URL, LOCAL_CSV)

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Raw historian values — fully synchronized across panels.")

# --- Sidebar Filters ---
st.sidebar.header("Filters")
min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date Range", (min_date, max_date))
col1, col2 = st.sidebar.columns(2)
start_t = col1.time_input("Start", pd.Timestamp("00:00").time())
end_t = col2.time_input("End", pd.Timestamp("23:59").time())

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_dt = pd.Timestamp.combine(date_range[0], start_t)
    end_dt = pd.Timestamp.combine(date_range[1], end_t)
else:
    d = date_range if not isinstance(date_range, (tuple, list)) else date_range[0]
    start_dt = pd.Timestamp.combine(d, start_t)
    end_dt = pd.Timestamp.combine(d, end_t)

mask = (df["Time"] >= start_dt) & (df["Time"] <= end_dt)
f = df.loc[mask].copy()

# --- Auto Tag Derivation ---
def extract_tag(name):
    n = str(name).upper()
    if "FEEDRATE" in n: return "Feedrate"
    if "SETPOINT" in n: return "Setpoint"
    if "LOAD" in n: return "Load"
    if "SPEED" in n: return "Belt_Speed"
    if "CURRENT" in n: return "Motor_Current"
    if "FLOW" in n: return "Flow"
    if "GATE" in n: return "Gate_Pos_CMD"
    if "TOTAL" in n: return "Totalizer"
    return "Other"

if "Tag_Name" not in f.columns:
    f["Tag_Name"] = f["Name"].apply(extract_tag)

COLOR_MAP = {
    "Feedrate":"#1f77b4","Setpoint":"#ff7f0e","Load":"#d62728","Belt_Speed":"#2ca02c",
    "Motor_Current":"#17becf","Flow":"#9467bd","Gate_Pos_CMD":"#8c564b","Totalizer":"#e377c2"
}

# --- Build synchronized multi-panel layout ---
fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04)

line_mode = "lines"
for (tag, equip), seg in f.groupby(["Tag_Name","Name"]):
    color = COLOR_MAP.get(tag, "#aaa")
    if tag in ["Feedrate","Setpoint","Load","Belt_Speed","Totalizer"]:
        fig.add_trace(go.Scatter(x=seg["Time"], y=seg["Value"], mode=line_mode,
                                 name=f"{equip} • {tag}", line=dict(color=color, width=1.5)),
                      row=1, col=1)
    elif "CURRENT" in tag:
        fig.add_trace(go.Scatter(x=seg["Time"], y=seg["Value"], mode=line_mode,
                                 name=f"{equip} • {tag}", line=dict(color=color, width=1.5)),
                      row=2, col=1)
    elif tag in ["Flow","Gate_Pos_CMD","Totalizer"]:
        fig.add_trace(go.Scatter(x=seg["Time"], y=seg["Value"], mode=line_mode,
                                 name=f"{equip} • {tag}", line=dict(color=color, width=1.5)),
                      row=3, col=1)
    else:
        fig.add_trace(go.Scatter(x=seg["Time"], y=seg["Value"], mode=line_mode,
                                 name=f"{equip} • {tag}", line=dict(color=color, width=1.2)),
                      row=4, col=1)

# --- Axis settings ---
fig.update_layout(
    template="plotly_dark",
    height=1100,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=60, l=60, r=40, b=40),
)

for i in range(1,5):
    fig.update_yaxes(autorange=True, matches=None, title_text=f"Panel {i} Value", row=i, col=1)
    fig.update_xaxes(title_text="Time", row=i, col=1, showspikes=True, spikemode="across")

st.plotly_chart(fig, use_container_width=True)
st.dataframe(f.head(500))
