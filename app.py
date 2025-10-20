import os, io, time, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

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
    df = df.sort_values("Time").reset_index(drop=True)
    return df, source, updated

df, data_source, last_updated = load_data(RAW_CSV_URL, LOCAL_CSV)

# -------------------- Sidebar filters --------------------
st.sidebar.title("Filters")
min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

groups     = sorted(df["Tag_Group"].dropna().unique())
equipments = sorted(df["Equipment"].dropna().unique())
tags       = sorted(df["Tag_Name"].dropna().unique())

sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001","FEB_002"])
sel_tags  = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate","Setpoint","Load","Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)

# Optional fine time window
start_time = st.sidebar.time_input("Start Time", pd.to_datetime("05:00").time())
end_time   = st.sidebar.time_input("End Time",   pd.to_datetime("07:00").time())

# Filter
mask = (
    df["Tag_Group"].isin(sel_group) &
    df["Equipment"].isin(sel_equip) &
    df["Tag_Name"].isin(sel_tags) &
    (df["Time"].dt.date >= date_range[0]) &
    (df["Time"].dt.date <= date_range[-1])
)
if quality_ok_only and "Quality" in df.columns:
    mask &= df["Quality"].eq("Good")

f = df.loc[mask, ["Time","Equipment","Tag_Name","Value","Tag_Group","Quality"]].copy()
f_zoom = f[(f["Time"].dt.time >= start_time) & (f["Time"].dt.time <= end_time)]

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Use the left filters + start/end time to reproduce the FactoryTalk window. Hover any point to see exact values.")

# -------------------- Axis routing & colors --------------------
# Map Tag_Name to a y-axis id and units
AXIS_MAP = {
    # Left main axis (kg/hr / tph style)
    "Feedrate": ("y", "kg/hr"),
    "Setpoint": ("y", "kg/hr"),
    "Rolling_Avg": ("y", "tph"),
    "Totalizer": ("y", "t"),
    # Right axes
    "Load": ("y2", "%"),
    "Gate_Pos_CMD": ("y2", "%"),
    "Belt_Speed": ("y3", "m/s"),
    "Motor_Current": ("y4", "A"),
    "Avg_Current": ("y4", "A"),
    "Level_High_Switch": ("y5", "on/off"),
    "Pressure_PV": ("y6", "PV"),
}
COLOR_MAP = {
    "Feedrate": "#1f77b4",     # blue
    "Setpoint": "#ff7f0e",     # orange
    "Load": "#d62728",         # red
    "Belt_Speed": "#2ca02c",   # green
    "Rolling_Avg": "#9467bd",  # purple
    "Gate_Pos_CMD": "#8c564b", # brown
    "Motor_Current": "#17becf",# teal
    "Avg_Current": "#17becf",
    "Totalizer": "#e377c2",    # pink
    "Level_High_Switch": "#7f7f7f", # gray
    "Pressure_PV": "#bcbd22"   # olive
}
DASH_MAP = {
    # Different equipment get different dash styles so you can tell them apart
    # default solid; override for common ones
    "FEB_001": "solid",
    "FEB_002": "dash",
    "CVB_13A": "dot",
    "CVB_109": "dashdot",
    "CVB_110": "longdash",
}

def add_traces(fig, frame, title):
    if frame.empty:
        st.warning("No data for the chosen filters/time window.")
        return fig

    # Build traces per (Tag_Name, Equipment)
    for (tag, equip), seg in frame.groupby(["Tag_Name","Equipment"]):
        axis_id, unit = AXIS_MAP.get(tag, ("y", ""))
        color = COLOR_MAP.get(tag, "#ffffff")
        dash  = DASH_MAP.get(equip, "solid")
        fig.add_trace(
            go.Scatter(
                x=seg["Time"],
                y=seg["Value"],
                mode="lines",
                name=f"{equip} • {tag}",
                line=dict(color=color, dash=dash, width=1.3),
                yaxis=axis_id,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Tag: <b>%{customdata[1]}</b><br>"
                    "Time: %{x|%Y-%m-%d %H:%M:%S}<br>"
                    "Value: <b>%{y:.2f}</b> " + unit +
                    "<extra></extra>"
                ),
                customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1),
            )
        )

    # Layout with multiple right-side axes like FactoryTalk
    fig.update_layout(
        title=title,
        template="plotly_dark",
        hovermode="x unified",
        height=650,
        xaxis=dict(title="Time"),
        yaxis=dict(title="Main (kg/hr / tph / t)"),
        yaxis2=dict(title="Percent / Gate", overlaying="y", side="right", position=1.0),
        yaxis3=dict(title="Belt Speed (m/s)", overlaying="y", side="right", position=0.98, showgrid=False),
        yaxis4=dict(title="Current (A)", overlaying="y", side="right", position=0.96, showgrid=False),
        yaxis5=dict(title="Switch", overlaying="y", side="right", position=0.94, showgrid=False),
        yaxis6=dict(title="Pressure PV", overlaying="y", side="right", position=0.92, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig

# -------- Full range plot
fig_full = go.Figure()
fig_full = add_traces(fig_full, f, "Full Range — Selected Tags (Multi‑axis)")
st.plotly_chart(fig_full, use_container_width=True)

# -------- Zoomed window plot
st.markdown(f"### Zoomed Window: **{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}**")
fig_zoom = go.Figure()
fig_zoom = add_traces(fig_zoom, f_zoom, f"Zoomed Raw Trends {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}")
st.plotly_chart(fig_zoom, use_container_width=True)

# Preview
st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)

st.caption("FactoryTalk-style multi-axis viewer: distinct colors per tag, dash per equipment, true raw timestamps, hover for exact values.")
