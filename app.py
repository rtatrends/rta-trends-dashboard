
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

# ------------ Sidebar -------------
st.sidebar.title("Filters")

if df.empty or "Time" not in df.columns:
    st.sidebar.error("CSV not loaded or missing 'Time' column.")
    st.stop()

min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", (min_date, max_date))
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_dt = pd.Timestamp.combine(date_range[0], pd.Timestamp.min.time())
    end_dt   = pd.Timestamp.combine(date_range[1], pd.Timestamp.max.time())
else:
    single_date = date_range if not isinstance(date_range, (tuple, list)) else date_range[0]
    start_dt = pd.Timestamp.combine(single_date, pd.Timestamp.min.time())
    end_dt   = pd.Timestamp.combine(single_date, pd.Timestamp.max.time())

groups = sorted(df["Tag_Group"].dropna().unique()) if "Tag_Group" in df.columns else []
equipments = sorted(df["Equipment"].dropna().unique()) if "Equipment" in df.columns else []
tags = sorted(df["Tag_Name"].dropna().unique()) if "Tag_Name" in df.columns else []

sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=equipments[:6] if equipments else [])
sel_tags  = st.sidebar.multiselect("Tag(s)", tags, default=tags[:6] if tags else [])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=False)

st.sidebar.markdown("### Y-Axis Options")
overlay_mode = st.sidebar.radio("FactoryTalk overlay mode", ["Percent+MTPH (like screenshot)", "Classic multi-axis"], index=0)
lock_percent_range = st.sidebar.checkbox("Lock percent axis to -100..0 (reversed)", value=True)

# -------- Filter frame --------
mask = (
    df["Tag_Group"].isin(sel_group) &
    df["Equipment"].isin(sel_equip) &
    df["Tag_Name"].isin(sel_tags) &
    (df["Time"] >= start_dt) & (df["Time"] <= end_dt)
)
if quality_ok_only and "Quality" in df.columns:
    mask &= df["Quality"].eq("Good")

f = df.loc[mask, ["Time","Equipment","Tag_Name","Value","Tag_Group","Quality"]].copy()

# Scale feed-related to MTPH (÷1000)
if not f.empty:
    for tag in ["Feedrate", "Setpoint", "Rolling_Avg"]:
        f.loc[f["Tag_Name"] == tag, "Value"] = f.loc[f["Tag_Name"] == tag, "Value"] / 1000.0

# Helpers to route tags
def is_percent_tag(tag: str) -> bool:
    tag = str(tag)
    keys = ["PV", "CV", "OP", "Load", "Gate_Pos", "Level", "Percent", "LSH", "LSL"]
    return any(k in tag for k in keys)

def is_current(tag: str) -> bool:
    return "Current" in str(tag)

def is_speed(tag: str) -> bool:
    return "Speed" in str(tag)

def is_mtph(tag: str) -> bool:
    return tag in ["Feedrate", "Setpoint", "Rolling_Avg"]

# Colors loosely inspired by FT
COLOR_MAP = {
    "PV": "#1f77b4",        # blue
    "CV": "#ff7f0e",        # orange
    "OP": "#2ca02c",        # green
    "Load": "#d62728",      # red
    "Gate": "#8c564b",      # brown
    "Level": "#9467bd",     # purple
    "Belt_Speed": "#2ca02c",
    "Motor_Current": "#17becf",
    "Feedrate": "#1f77b4",
    "Setpoint": "#ff7f0e",
    "Rolling_Avg": "#9467bd"
}

def color_for(tag):
    if "PV" in tag: return COLOR_MAP["PV"]
    if "CV" in tag and "FY" in tag: return COLOR_MAP["CV"]
    if "OP" in tag: return COLOR_MAP["OP"]
    if "Gate_Pos" in tag: return COLOR_MAP["Gate"]
    if "Level" in tag: return COLOR_MAP["Level"]
    return COLOR_MAP.get(tag, "#cccccc")

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Overlay mode emulates the FactoryTalk panel: percent traces on a reversed left axis, MTPH feedrate on a right axis, all lines solid, true raw timestamps.")

fig = go.Figure()

if f.empty:
    st.warning("No data with the chosen filters/range.")
else:
    if overlay_mode.startswith("Percent+MTPH"):
        # Left axis for % (reversed), Right axis for MTPH; others overlay on right-most axes
        for (tag, equip), seg in f.groupby(["Tag_Name","Equipment"]):
            tag_str = str(tag)
            if is_percent_tag(tag_str):
                yaxis = "y"
                unit = "%"
            elif is_mtph(tag_str):
                yaxis = "y2"
                unit = "MTPH"
            elif is_speed(tag_str):
                yaxis = "y3"; unit = "m/s"
            elif is_current(tag_str):
                yaxis = "y4"; unit = "A"
            else:
                yaxis = "y2"; unit = ""

            # Step for discrete-ish signals
            line_shape = "hv" if any(k in tag_str for k in ["Gate", "LSH", "LSL", "Switch"]) else "linear"

            fig.add_trace(go.Scatter(
                x=seg["Time"], y=seg["Value"], mode="lines",
                name=f"{equip} • {tag}",
                line=dict(color=color_for(tag_str), width=1.5, dash="solid", shape=line_shape),
                yaxis=yaxis,
                hovertemplate="<b>%{customdata[0]}</b><br>Tag: %{customdata[1]}<br>Time: %{x|%Y-%m-%d %H:%M:%S}<br>Value: %{y:.2f} "+unit+"<extra></extra>",
                customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1)
            ))

        # Layout to mimic FT
        y1 = dict(title="Percent", autorange="reversed" if lock_percent_range else True)
        if lock_percent_range:
            y1.update(range=[0, -100])  # reversed axis: 0 at top, -100 bottom if negatives; still ok for positive %

        fig.update_layout(
            template="plotly_dark", hovermode="x unified", height=680,
            xaxis=dict(title="Time"),
            yaxis=y1,
            yaxis2=dict(title="MTPH", overlaying="y", side="right", position=1.0, showgrid=False),
            yaxis3=dict(title="Belt Speed (m/s)", overlaying="y", side="right", position=0.98, showgrid=False),
            yaxis4=dict(title="Current (A)", overlaying="y", side="right", position=0.96, showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )

    else:
        # Classic multi-axis (previous behavior)
        AXIS_MAP = {
            "Feedrate": ("y2", "MTPH"), "Setpoint": ("y2", "MTPH"), "Rolling_Avg": ("y2", "MTPH"),
            "Load": ("y", "%"), "Gate_Pos_CMD": ("y", "%"),
            "Belt_Speed": ("y3", "m/s"), "Motor_Current": ("y4", "A"), "Avg_Current": ("y4", "A"),
        }
        for (tag, equip), seg in f.groupby(["Tag_Name","Equipment"]):
            axis_id, unit = AXIS_MAP.get(tag, ("y2", ""))
            fig.add_trace(go.Scatter(
                x=seg["Time"], y=seg["Value"], mode="lines",
                name=f"{equip} • {tag}", line=dict(width=1.5, dash="solid", color=color_for(str(tag))),
                yaxis=axis_id,
                hovertemplate="Equip: %{customdata[0]}<br>Tag: %{customdata[1]}<br>%{x|%Y-%m-%d %H:%M:%S}<br><b>%{y:.2f}</b> "+unit+"<extra></extra>",
                customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1)
            ))
        fig.update_layout(
            template="plotly_dark", hovermode="x unified", height=680,
            xaxis=dict(title="Time"),
            yaxis=dict(title="Percent / Gate"),
            yaxis2=dict(title="MTPH", overlaying="y", side="right", position=1.0),
            yaxis3=dict(title="Belt Speed (m/s)", overlaying="y", side="right", position=0.98, showgrid=False),
            yaxis4=dict(title="Current (A)", overlaying="y", side="right", position=0.96, showgrid=False),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
        )

st.plotly_chart(fig, use_container_width=True)

st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)
