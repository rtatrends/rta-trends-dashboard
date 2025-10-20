import os, io, time, requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="RTA Trends Dashboard", layout="wide")

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

st.sidebar.title("Filters")

min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

groups = sorted(df["Tag_Group"].dropna().unique())
equipments = sorted(df["Equipment"].dropna().unique())
tags = sorted(df["Tag_Name"].dropna().unique())

sel_group = st.sidebar.multiselect("Tag group", groups, default=groups)
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001", "FEB_002"])
sel_tags = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate", "Setpoint", "Load", "Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)
granularity = st.sidebar.selectbox("Resample", ["raw","1min","5min","15min","hour","day"], index=0)
current_threshold = st.sidebar.number_input("Motor current threshold (A)", min_value=0.0, value=15.0, step=0.5)

mask = (
    df["Tag_Group"].isin(sel_group)
    & df["Equipment"].isin(sel_equip)
    & df["Tag_Name"].isin(sel_tags)
    & (df["Time"].dt.date >= date_range[0])
    & (df["Time"].dt.date <= date_range[-1])
)
if quality_ok_only and "Quality" in df.columns:
    mask &= df["Quality"].eq("Good")

f = df.loc[mask, ["Time","Tag_Group","Equipment","Tag_Name","Value","Quality","Source_File"]].copy()

def resample_frame(frame, rule):
    if rule == "raw" or frame.empty:
        return frame
    rule_map = {"1min":"1min","5min":"5min","15min":"15min","hour":"H","day":"D"}
    out = (
        frame.set_index("Time")
        .groupby(["Tag_Group","Equipment","Tag_Name"])
        .resample(rule_map[rule])
        .Value.mean()
        .reset_index()
    )
    out["Quality"] = "N/A"
    out["Source_File"] = "mixed"
    return out

f = resample_frame(f, granularity)

def plot_trend(frame, title="Trend View"):
    if frame.empty:
        st.warning("No data to plot.")
        return
    wide = frame.pivot(index="Time", columns="Tag_Name", values="Value")
    COLOR_MAP = {"Feedrate":"#1f77b4","Setpoint":"#ff7f0e","Load":"#d62728","Belt_Speed":"#2ca02c"}
    fig = px.line(wide, x=wide.index, y=wide.columns, title=title, color_discrete_map=COLOR_MAP)
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode="x unified",
        height=500,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

def kpi_avg(frame, tag):
    try:
        return frame.loc[frame["Tag_Name"].eq(tag), "Value"].mean()
    except Exception:
        return np.nan

st.title("📊 RTA Trends Dashboard")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Overview", "WeighFeeder", "Flow & Gate", "Motors", "Totals & Sensors", "Data QA"]
)

with tab1:
    st.subheader("Overview")
    col1,col2,col3,col4 = st.columns(4)
    avg_feedrate = kpi_avg(f,"Feedrate")
    avg_setpoint = kpi_avg(f,"Setpoint")
    avg_load     = kpi_avg(f,"Load")
    avg_current  = kpi_avg(f,"Motor_Current")
    eff = (avg_feedrate / avg_setpoint * 100) if (avg_setpoint and avg_setpoint != 0) else np.nan
    col1.metric("Avg Feedrate (MTPH)", f"{(avg_feedrate or 0):.2f}")
    col2.metric("Avg Setpoint (MTPH)", f"{(avg_setpoint or 0):.2f}")
    col3.metric("Avg Load (%)", f"{(avg_load or 0):.2f}")
    col4.metric("Avg Motor Current (A)", f"{(avg_current or 0):.2f}")
    st.markdown("### Production Trend (Feedrate vs Setpoint)")
    plot_trend(f[f["Tag_Name"].isin(["Feedrate","Setpoint"])], title="Feedrate vs Setpoint")

with tab2:
    st.subheader("WeighFeeder — Raw Zoomable Trends")
    wf = f[f["Tag_Group"].eq("WeighFeeder")]
    start_time = st.time_input("Start Time", pd.to_datetime("05:00").time())
    end_time   = st.time_input("End Time", pd.to_datetime("07:00").time())
    f_zoom = wf[(wf["Time"].dt.time >= start_time) & (wf["Time"].dt.time <= end_time)]
    plot_trend(f_zoom[f_zoom["Tag_Name"].isin(["Feedrate","Setpoint","Load","Belt_Speed"])],
               title=f"Zoomed Trend {start_time}-{end_time}")

with tab3:
    st.subheader("Flow Scale & Gate")
    flow = f[f["Tag_Group"].isin(["FlowScale","TransferTower"])]
    plot_trend(flow[flow["Tag_Name"].isin(["Rolling_Avg","Gate_Pos_CMD"])], title="Flow & Gate Trends")

with tab4:
    st.subheader("Motors — Currents & Thresholds")
    motors = f[f["Tag_Name"].eq("Motor_Current")]
    plot_trend(motors, title="Motor Currents by Equipment")

with tab5:
    st.subheader("Totalizer / Screeners / Sensors")
    sensors = f[f["Tag_Name"].isin(["Totalizer","Level_High_Switch","Avg_Current","Motor_Current"])]
    plot_trend(sensors, title="Sensor and Totalizer Trends")

with tab6:
    st.subheader("Data Quality & Source Audit")
    if "Quality" in f.columns:
        bad = df[(df["Quality"]!="Good") & (df["Time"].dt.date.between(date_range[0], date_range[-1]))]
        st.metric("Non-Good rows", len(bad))
        st.dataframe(bad.tail(200), use_container_width=True)
    src = df.groupby("Source_File").size().reset_index(name="rows").sort_values("rows", ascending=False)
    st.dataframe(src, use_container_width=True)

st.caption("Tip: adjust date & time to zoom into sections like FactoryTalk trends. Resample only if data is too dense.")
