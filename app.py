
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

# Sidebar
st.sidebar.title("Filters")

# Safe default date range
if not df.empty and "Time" in df.columns:
    default_start = df["Time"].min().date()
    default_end = df["Time"].max().date()
else:
    now = pd.Timestamp.now()
    default_start = (now - pd.Timedelta(days=1)).date()
    default_end = now.date()

# Date range input (safe for Streamlit Cloud)
date_range = st.sidebar.date_input(
    "Select date range", 
    (default_start, default_end)
)

# Convert to full datetime range
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_dt = pd.Timestamp.combine(date_range[0], pd.Timestamp.min.time())
    end_dt = pd.Timestamp.combine(date_range[1], pd.Timestamp.max.time())
else:
    start_dt = pd.Timestamp.combine(date_range, pd.Timestamp.min.time())
    end_dt = pd.Timestamp.combine(date_range, pd.Timestamp.max.time())

groups = sorted(df["Tag_Group"].dropna().unique()) if "Tag_Group" in df.columns else []
equipments = sorted(df["Equipment"].dropna().unique()) if "Equipment" in df.columns else []
tags = sorted(df["Tag_Name"].dropna().unique()) if "Tag_Name" in df.columns else []

# Preset tag sets
preset = st.sidebar.selectbox("Preset Tag Set", ["Custom","Weighfeeders","Motors","Conveyors","Screeners","All"])

if preset == "Weighfeeders":
    sel_group = ["WeighFeeder"]
    sel_equip = [e for e in equipments if "FEB" in e]
    sel_tags = ["Feedrate","Setpoint","Load","Belt_Speed"]
elif preset == "Motors":
    sel_group = ["Motor"]
    sel_equip = [e for e in equipments if "CVB" in e]
    sel_tags = ["Motor_Current","Avg_Current"]
elif preset == "Conveyors":
    sel_group = ["TransferTower","FlowScale"]
    sel_equip = [e for e in equipments if "CVB" in e]
    sel_tags = ["Rolling_Avg","Gate_Pos_CMD"]
elif preset == "Screeners":
    sel_group = ["Screener"]
    sel_equip = [e for e in equipments if "SNS" in e]
    sel_tags = ["Load"]
elif preset == "All":
    sel_group, sel_equip, sel_tags = groups, equipments, tags
else:
    sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
    sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001","FEB_002"])
    sel_tags = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate","Setpoint","Load","Belt_Speed"])

quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)

# Resampling
resample_choice = st.sidebar.selectbox("Resample frequency", ["None","1s","5s","15s","1min"], index=0)
resample_rule = None if resample_choice=="None" else resample_choice

# Y-axis options
st.sidebar.subheader("Y-Axis Options")
y_mode = st.sidebar.radio("Y-axis behavior", ["Auto (default)", "Fixed (lock range)", "Manual range"], index=1)
if y_mode == "Manual range":
    y_min = st.sidebar.number_input("Y-axis Min", value=0.0)
    y_max = st.sidebar.number_input("Y-axis Max", value=300000.0)
else:
    y_min, y_max = None, None

# Filtering
if not df.empty:
    mask = (
        df["Tag_Group"].isin(sel_group) &
        df["Equipment"].isin(sel_equip) &
        df["Tag_Name"].isin(sel_tags) &
        (df["Time"] >= start_dt) &
        (df["Time"] <= end_dt)
    )
    if quality_ok_only and "Quality" in df.columns:
        mask &= df["Quality"].eq("Good")

    f = df.loc[mask, ["Time","Equipment","Tag_Name","Value","Tag_Group","Quality"]].copy()

    if resample_rule:
        f = f.set_index("Time").groupby(["Equipment","Tag_Name"]).resample(resample_rule)["Value"].mean().reset_index()
else:
    f = pd.DataFrame()

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Reproduces true FactoryTalk view — full datetime filtering, raw analog values, and optional resampling.")

AXIS_MAP = {
    "Feedrate": ("y", "kg/hr"), "Setpoint": ("y", "kg/hr"), "Rolling_Avg": ("y", "tph"), "Totalizer": ("y", "t"),
    "Load": ("y2", "%"), "Gate_Pos_CMD": ("y2", "%"), "Belt_Speed": ("y3", "m/s"), "Motor_Current": ("y4", "A"),
    "Avg_Current": ("y4", "A"), "Level_High_Switch": ("y5", "on/off"), "Pressure_PV": ("y6", "PV"),
}
COLOR_MAP = {"Feedrate": "#1f77b4","Setpoint": "#ff7f0e","Load": "#d62728","Belt_Speed": "#2ca02c",
             "Rolling_Avg": "#9467bd","Gate_Pos_CMD": "#8c564b","Motor_Current": "#17becf",
             "Avg_Current": "#17becf","Totalizer": "#e377c2","Level_High_Switch": "#7f7f7f","Pressure_PV": "#bcbd22"}
DASH_MAP = {"FEB_001":"solid","FEB_002":"dash","CVB_13A":"dot","CVB_109":"dashdot","CVB_110":"longdash"}

def add_traces(fig, frame, title):
    if frame.empty:
        st.warning("No data for chosen filters/time window.")
        return fig
    for (tag, equip), seg in frame.groupby(["Tag_Name","Equipment"]):
        axis_id, unit = AXIS_MAP.get(tag, ("y", ""))
        color = COLOR_MAP.get(tag, "#ffffff")
        dash  = DASH_MAP.get(equip, "solid")
        fig.add_trace(go.Scatter(
            x=seg["Time"], y=seg["Value"], mode="lines",
            name=f"{equip} • {tag}", line=dict(color=color, dash=dash, width=1.3),
            yaxis=axis_id, customdata=np.stack([seg["Equipment"], seg["Tag_Name"]], axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>Tag: <b>%{customdata[1]}</b><br>Time: %{x|%Y-%m-%d %H:%M:%S}<br>Value: <b>%{y:.2f}</b><extra></extra>"
        ))
    yaxis_settings = dict(title="Main (kg/hr / tph / t)")
    if y_mode == "Fixed (lock range)":
        yaxis_settings.update(fixedrange=True, rangemode="tozero")
    elif y_mode == "Manual range" and y_min is not None and y_max is not None:
        yaxis_settings.update(range=[y_min, y_max], fixedrange=True)

    fig.update_layout(
        title=title, template="plotly_dark", hovermode="x unified", height=650,
        xaxis=dict(title="Time", rangeslider=dict(visible=False)),
        yaxis=yaxis_settings,
        yaxis2=dict(title="Percent / Gate", overlaying="y", side="right", position=1.0, fixedrange=(y_mode!="Auto (default)")),
        yaxis3=dict(title="Belt Speed (m/s)", overlaying="y", side="right", position=0.98, showgrid=False, fixedrange=(y_mode!="Auto (default)")),
        yaxis4=dict(title="Current (A)", overlaying="y", side="right", position=0.96, showgrid=False, fixedrange=(y_mode!="Auto (default)")),
        yaxis5=dict(title="Switch", overlaying="y", side="right", position=0.94, showgrid=False, fixedrange=(y_mode!="Auto (default)")),
        yaxis6=dict(title="Pressure PV", overlaying="y", side="right", position=0.92, showgrid=False, fixedrange=(y_mode!="Auto (default)")),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )
    return fig

fig_full = go.Figure()
fig_full = add_traces(fig_full, f, "Full Range — Selected Tags (Multi-axis)")
st.plotly_chart(fig_full, use_container_width=True)

csv = f.to_csv(index=False).encode("utf-8")
st.download_button("⬇ Download filtered CSV", csv, "filtered_trend_data.csv", "text/csv")

st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)
st.caption("FactoryTalk-True Mode v3: safe date range selector, raw analog data, full datetime filtering, resampling, tag presets, and CSV export.")
