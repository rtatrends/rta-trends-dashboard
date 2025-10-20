
import os, io, time, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Comco - RTA Trends Dashboard (FactoryTalk True v5)", layout="wide")

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
    df = df.sort_values("Time").reset_index(drop=True)
    return df, source, updated

df, data_source, last_updated = load_data(RAW_CSV_URL, LOCAL_CSV)

# Sidebar filters
st.sidebar.title("Filters")
if df.empty:
    st.sidebar.error("CSV not loaded or empty.")
else:
    st.sidebar.success(f"✅ Loaded {len(df)} rows")

min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", (min_date, max_date))
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_dt = pd.Timestamp.combine(date_range[0], pd.Timestamp.min.time())
    end_dt = pd.Timestamp.combine(date_range[1], pd.Timestamp.max.time())
else:
    single_date = date_range if not isinstance(date_range, (tuple, list)) else date_range[0]
    start_dt = pd.Timestamp.combine(single_date, pd.Timestamp.min.time())
    end_dt = pd.Timestamp.combine(single_date, pd.Timestamp.max.time())

groups = sorted(df["Tag_Group"].dropna().unique())
equipments = sorted(df["Equipment"].dropna().unique())
tags = sorted(df["Tag_Name"].dropna().unique())

sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001","FEB_002"])
sel_tags = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate","Setpoint","Load","Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)

# Y-axis options
st.sidebar.subheader("Y-Axis Options")
y_mode = st.sidebar.radio("Y-axis behavior", ["Auto (default)", "Fixed (lock range)", "Manual range"], index=0)
if y_mode == "Manual range":
    y_min = st.sidebar.number_input("Y-axis Min", value=0.0)
    y_max = st.sidebar.number_input("Y-axis Max", value=300.0)
else:
    y_min, y_max = None, None

# Filter data
mask = (
    df["Tag_Group"].isin(sel_group) &
    df["Equipment"].isin(sel_equip) &
    df["Tag_Name"].isin(sel_tags) &
    (df["Time"] >= start_dt) & (df["Time"] <= end_dt)
)
if quality_ok_only and "Quality" in df.columns:
    mask &= df["Quality"].eq("Good")

f = df.loc[mask, ["Time","Equipment","Tag_Name","Value","Tag_Group","Quality"]].copy()

# Scale Feedrate and Setpoint (÷1000 for MTPH)
if not f.empty:
    for tag in ["Feedrate", "Setpoint"]:
        f.loc[f["Tag_Name"] == tag, "Value"] = f.loc[f["Tag_Name"] == tag, "Value"] / 1000

st.title("Comco - RTA Trends Dashboard (FactoryTalk True v5)")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("FactoryTalk True visualization — scaled MTPH values and solid lines.")

AXIS_MAP = {
    "Feedrate": ("y", "MTPH"), "Setpoint": ("y", "MTPH"),
    "Load": ("y2", "%"), "Belt_Speed": ("y3", "m/s"),
    "Rolling_Avg": ("y", "tph"), "Totalizer": ("y", "t"),
    "Motor_Current": ("y4", "A"), "Avg_Current": ("y4", "A"),
}
COLOR_MAP = {
    "Feedrate": "#1f77b4", "Setpoint": "#ff7f0e", "Load": "#d62728",
    "Belt_Speed": "#2ca02c", "Rolling_Avg": "#9467bd", "Totalizer": "#e377c2",
    "Motor_Current": "#17becf", "Avg_Current": "#17becf"
}

def add_traces(fig, frame, title):
    if frame.empty:
        st.warning("No data for selected filters.")
        return fig
    for (tag, equip), seg in frame.groupby(["Tag_Name","Equipment"]):
        axis_id, unit = AXIS_MAP.get(tag, ("y", ""))
        color = COLOR_MAP.get(tag, "#cccccc")
        fig.add_trace(go.Scatter(
            x=seg["Time"], y=seg["Value"], mode="lines",
            name=f"{equip} • {tag}", line=dict(color=color, width=1.5, dash="solid"),
            yaxis=axis_id,
            hovertemplate="<b>%{customdata[0]}</b><br>Tag: %{customdata[1]}<br>Time: %{x|%Y-%m-%d %H:%M:%S}<br>Value: %{y:.2f} "+unit+"<extra></extra>",
            customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1)
        ))

    yaxis_settings = dict(title="Main (MTPH)")
    if y_mode == "Fixed (lock range)":
        yaxis_settings.update(fixedrange=True)
    elif y_mode == "Manual range" and y_min is not None and y_max is not None:
        yaxis_settings.update(range=[y_min, y_max], fixedrange=True)

    fig.update_layout(
        title=title, template="plotly_dark", hovermode="x unified",
        height=650, xaxis=dict(title="Time"),
        yaxis=yaxis_settings,
        yaxis2=dict(title="Percent / Gate", overlaying="y", side="right", position=1.0),
        yaxis3=dict(title="Belt Speed (m/s)", overlaying="y", side="right", position=0.98, showgrid=False),
        yaxis4=dict(title="Current (A)", overlaying="y", side="right", position=0.96, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig

fig = go.Figure()
fig = add_traces(fig, f, "Full Range — Selected Tags (MTPH scaled, solid lines)")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)
st.caption("FactoryTalk True v5 — scaled to MTPH, solid traces, safe date handling, clean UI.")
