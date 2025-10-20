import os, io, time, requests
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="RTA Trends Dashboard (Raw)", layout="wide")

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
sel_equip = st.sidebar.multiselect("Equipment", equipments, default=["FEB_001", "FEB_002"])
sel_tags = st.sidebar.multiselect("Tag(s)", tags, default=["Feedrate", "Setpoint", "Load", "Belt_Speed"])
quality_ok_only = st.sidebar.checkbox("Quality = Good only", value=True)
current_threshold = st.sidebar.number_input("Motor current threshold (A)", min_value=0.0, value=15.0, step=0.5)

# Filter
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

# Zoom filter (for shorter view)
start_time = st.sidebar.time_input("Start Time", pd.to_datetime("05:00").time())
end_time   = st.sidebar.time_input("End Time", pd.to_datetime("07:00").time())
f_zoom = f[(f["Time"].dt.time >= start_time) & (f["Time"].dt.time <= end_time)]

# Plot function
def plot_raw(frame, title="Raw Trend View"):
    if frame.empty:
        st.warning("No data to plot.")
        return
    COLOR_MAP = {"Feedrate":"#1f77b4","Setpoint":"#ff7f0e","Load":"#d62728","Belt_Speed":"#2ca02c"}
    fig = px.line(frame, x="Time", y="Value", color="Tag_Name", title=title, color_discrete_map=COLOR_MAP)
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Value",
        hovermode="x unified",
        height=600,
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

# Layout
st.title("📊 RTA Trends Dashboard — Raw Data")
st.caption(f"Source: {data_source} • Last updated: {last_updated}")

st.markdown("### Main Trend View")
plot_raw(f, title="Full Range — Selected Tags")

st.markdown(f"### Zoomed View ({start_time}–{end_time})")
plot_raw(f_zoom, title=f"Zoomed Raw Trend {start_time}-{end_time}")

st.markdown("### Data Preview")
st.dataframe(f.head(500), use_container_width=True)

st.caption("Showing raw data values by timestamp — no averaging or aggregation.")
