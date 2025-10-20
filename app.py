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

# Sidebar filters
st.sidebar.title("Filters")
min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

groups = sorted(df["Tag_Group"].dropna().unique())
equipments = sorted(df["Equipment"].dropna().unique())
tags = sorted(df["Tag_Name"].dropna().unique())

sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001","FEB_002"])
sel_tags = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate","Setpoint","Load","Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)

# Add absolute value toggle
abs_values = st.sidebar.checkbox("📈 Show absolute TPH (ignore negative direction)", value=True)

# Time window
start_time = st.sidebar.time_input("Start Time", pd.to_datetime("05:00").time())
end_time   = st.sidebar.time_input("End Time",   pd.to_datetime("07:00").time())

# Y-axis options
st.sidebar.subheader("Y-Axis Options")
y_mode = st.sidebar.radio("Y-axis behavior", ["Auto (default)", "Fixed (lock range)", "Manual range"], index=1)
if y_mode == "Manual range":
    y_min = st.sidebar.number_input("Y-axis Min", value=0.0)
    y_max = st.sidebar.number_input("Y-axis Max", value=300000.0)
else:
    y_min, y_max = None, None

# Filtering
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

# Apply absolute values if checkbox is ON
if abs_values:
    abs_tags = ["Feedrate", "Setpoint", "Load", "Rolling_Avg"]
    f.loc[f["Tag_Name"].isin(abs_tags), "Value"] = f.loc[f["Tag_Name"].isin(abs_tags), "Value"].abs()
    f_zoom.loc[f_zoom["Tag_Name"].isin(abs_tags), "Value"] = f_zoom.loc[f_zoom["Tag_Name"].isin(abs_tags), "Value"].abs()

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")
st.markdown("Use filters + time window to reproduce FactoryTalk view. Hover for exact values.")

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

st.markdown(f"### Zoomed Window: **{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}**")
fig_zoom = go.Figure()
fig_zoom = add_traces(fig_zoom, f_zoom, f"Zoomed Raw Trends {start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}")
st.plotly_chart(fig_zoom, use_container_width=True)

st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)
st.caption("Added 'Show absolute TPH' option — converts Feedrate, Setpoint, Load, and Rolling_Avg to positive values when checked.")
