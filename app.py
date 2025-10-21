import os, io, time, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Comco - RTA Trends Dashboard (Final v8)", layout="wide")

RAW_CSV_URL = os.environ.get("RAW_CSV_URL", "").strip()
LOCAL_CSV = "Last_30_Day_Data_Group_45.csv"   # master file

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

    if "Value" in df.columns:
        df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Time", "Value"]).sort_values("Time").reset_index(drop=True)
    return df, source, updated


df, data_source, last_updated = load_data(RAW_CSV_URL, LOCAL_CSV)

if df.empty:
    st.error("CSV is empty or missing required columns.")
    st.stop()

# Sidebar filters
st.sidebar.title("Filters")

min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", (min_date, max_date))

col1, col2 = st.sidebar.columns(2)
start_t = col1.time_input("Start Time", pd.Timestamp("00:00").time())
end_t   = col2.time_input("End Time", pd.Timestamp("23:59").time())

groups = sorted(df.get("Tag_Group", pd.Series(dtype=str)).dropna().unique())
equipments = sorted(df.get("Equipment", pd.Series(dtype=str)).dropna().unique())
tags = sorted(df.get("Tag_Name", pd.Series(dtype=str)).dropna().unique())

sel_group = st.sidebar.multiselect("Tag Group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=equipments[:4])
sel_tags  = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate","Setpoint","Load","Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=False)
show_markers = st.sidebar.checkbox("Show markers", value=False)
abs_feed = st.sidebar.checkbox("Show absolute Feedrate", value=True)

# Filter
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_dt = pd.Timestamp.combine(date_range[0], start_t)
    end_dt   = pd.Timestamp.combine(date_range[1], end_t)
else:
    single_date = date_range if not isinstance(date_range, (tuple, list)) else date_range[0]
    start_dt = pd.Timestamp.combine(single_date, start_t)
    end_dt   = pd.Timestamp.combine(single_date, end_t)

mask = (df["Time"] >= start_dt) & (df["Time"] <= end_dt)
if sel_group: mask &= df["Tag_Group"].isin(sel_group)
if sel_equip: mask &= df["Equipment"].isin(sel_equip)
if sel_tags:  mask &= df["Tag_Name"].isin(sel_tags)
if quality_ok_only and "Quality" in df.columns:
    mask &= df["Quality"].eq("Good")

f = df.loc[mask, ["Time","Equipment","Tag_Name","Value","Tag_Group","Quality"]].copy()
if abs_feed:
    f.loc[f["Tag_Name"].str.lower() == "feedrate","Value"] = f.loc[f["Tag_Name"].str.lower() == "feedrate","Value"].abs()

# Plot
st.title("Comco - RTA Trends Dashboard (Final v8)")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Auto Y-axis scaling like FactoryTalk — just click, zoom, or drag to rescale.")

COLOR_MAP = {
    "Feedrate":"#1f77b4", "Setpoint":"#ff7f0e", "Load":"#d62728",
    "Belt_Speed":"#2ca02c", "Motor_Current":"#17becf",
    "Rolling_Avg":"#9467bd", "Totalizer":"#e377c2"
}

def add_traces(fig, frame):
    if frame.empty:
        st.warning("No data for selected filters.")
        return fig
    for (tag, equip), seg in frame.groupby(["Tag_Name","Equipment"]):
        color = COLOR_MAP.get(tag, "#cccccc")
        fig.add_trace(go.Scatter(
            x=seg["Time"], y=seg["Value"], mode="lines+markers" if show_markers else "lines",
            name=f"{equip} • {tag}", line=dict(width=1.5, color=color),
            marker=dict(size=3),
            hovertemplate="<b>%{customdata[0]}</b><br>Tag: %{customdata[1]}<br>Time: %{x|%Y-%m-%d %H:%M:%S}<br>Value: %{y:.2f}<extra></extra>",
            customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1)
        ))
    fig.update_layout(
        template="plotly_dark", hovermode="x unified", height=680,
        xaxis=dict(title="Time"),
        yaxis=dict(title="Value (auto-scale)", autorange=True),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig

fig = add_traces(go.Figure(), f)
st.plotly_chart(fig, use_container_width=True)
st.dataframe(f.head(1000), use_container_width=True)
