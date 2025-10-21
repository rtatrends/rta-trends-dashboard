import os, io, time, re, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

RAW_CSV_URL = os.environ.get("RAW_CSV_URL","").strip()
LOCAL_CSV   = "Last_30_Day_Data_Group_45.csv"

@st.cache_data(show_spinner=True, ttl=300)
def load_data(raw_url, local_path):
    if raw_url:
        r = requests.get(raw_url, timeout=30); r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content), parse_dates=["Time"])
        src, upd = "remote", r.headers.get("Last-Modified","GitHub")
    else:
        df = pd.read_csv(local_path, parse_dates=["Time"])
        src, upd = "local", time.ctime(os.path.getmtime(local_path)) if os.path.exists(local_path) else "unknown"
    for col in ["Value","Value_Raw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=["Time"], inplace=True)
    df.sort_values("Time", inplace=True)
    if "Tag" not in df.columns:
        df["Tag"] = df["Name"].apply(lambda s: re.split(r"[./]", str(s))[-1])
    if "Equipment" not in df.columns:
        def extract_equipment(name: str) -> str:
            u = str(name).upper()
            for eq in ["FEB_001","FEB_002","CVB_13A","CVB_109","CVB_110","SNS_001","SNS_002","C13A","C13B"]:
                if eq in u: return eq
            m = re.search(r"[A-Z]{2,4}_\d{1,3}[A-Z]?", u)
            return m.group(0) if m else "Other"
        df["Equipment"] = df["Name"].apply(extract_equipment)
    return df, src, upd

df, src, upd = load_data(RAW_CSV_URL, LOCAL_CSV)

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {src} • Last updated: {upd}")
st.markdown("Raw historian values • Short tag labels • Optional cleaned Feedrate (fills only false dips when motor is running).")

# Sidebar
st.sidebar.header("Filters")
min_d, max_d = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d))
col1, col2 = st.sidebar.columns(2)
start_t = col1.time_input("Start", pd.Timestamp("00:00").time())
end_t   = col2.time_input("End",   pd.Timestamp("23:59").time())

start_dt = pd.Timestamp.combine(date_range[0], start_t)
end_dt   = pd.Timestamp.combine(date_range[-1], end_t)

tags = sorted(df["Tag"].dropna().unique().tolist())
default_tags = [t for t in ["Feedrate","Setpoint","Load","Speed","Current","Flow","Totalizer"] if t in tags] or tags[:6]
sel_tags = st.sidebar.multiselect("Select Tags", tags, default=default_tags)

search = st.sidebar.text_input("Filter by name or equipment").upper()
quality_ok = st.sidebar.checkbox("Quality = Good only", value=False)
use_clean_feed = st.sidebar.checkbox("Use cleaned Feedrate (fill false dips)", value=True)
show_markers = st.sidebar.checkbox("Markers", value=False)

mask = (df["Time"] >= start_dt) & (df["Time"] <= end_dt) & (df["Tag"].isin(sel_tags))
if search:
    mask &= (df["Name"].str.upper().str.contains(search) | df["Equipment"].str.upper().str.contains(search))
if quality_ok and "Quality" in df.columns:
    mask &= df["Quality"].astype(str).str.upper().eq("GOOD")

f = df.loc[mask].copy()

if use_clean_feed and "Value_Raw" in f.columns:
    is_feed = f["Tag"].str.upper().eq("FEEDRATE")
    f.loc[is_feed, "PlotValue"] = f.loc[is_feed, "Value"]
    f.loc[~is_feed, "PlotValue"] = f.loc[~is_feed, "Value"].fillna(f.loc[~is_feed, "Value_Raw"])
else:
    f["PlotValue"] = f["Value_Raw"].fillna(f["Value"])

COLOR_MAP = {
    "Feedrate":"#1f77b4","Setpoint":"#ff7f0e","Load":"#d62728",
    "Speed":"#2ca02c","Current":"#17becf","Flow":"#9467bd",
    "Gate_Pos_CMD":"#8c564b","Totalizer":"#e377c2"
}

fig = go.Figure()
line_mode = "lines+markers" if show_markers else "lines"
for tag, seg in f.groupby("Tag"):
    fig.add_trace(go.Scatter(
        x=seg["Time"], y=seg["PlotValue"], mode=line_mode,
        name=tag, line=dict(color=COLOR_MAP.get(tag), width=1.6),
        hovertemplate=f"<b>{tag}</b><br>%{{x|%Y-%m-%d %H:%M:%S}}<br>Value: %{{y:.2f}}<extra></extra>"
    ))

fig.update_layout(
    template="plotly_dark",
    height=760,
    hovermode="x",
    hoverdistance=50,
    xaxis=dict(title="Time", showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1),
    yaxis=dict(title="Value (raw units)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(t=60,l=60,r=40,b=40)
)

st.plotly_chart(fig, use_container_width=True)

st.sidebar.download_button(
    label="⬇ Download filtered data",
    data=f[["Time","Name","Tag","Equipment","PlotValue"]].rename(columns={"PlotValue":"Value"}).to_csv(index=False).encode("utf-8"),
    file_name="Filtered_RTA_Trends.csv",
    mime="text/csv"
)
