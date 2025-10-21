import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time

# ---------- CONFIG ----------
st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

DATA_PATH = "Last_30_Day_Data_Group_45.csv"  # <-- file in your repo root

# ---------- LOAD DATA ----------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_PATH, parse_dates=["Time"])
        df["Tag_Name"] = df["Tag_Name"].astype(str).str.strip()
        df["Equipment"] = df["Equipment"].astype(str).str.strip()
        df["Tag_Group"] = df["Tag_Group"].astype(str).str.strip()
        df.sort_values("Time", inplace=True)
        return df
    except Exception as e:
        st.error(f"❌ Failed to load data: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty:
    st.stop()

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("Filters")

min_date = df["Time"].min().date()
max_date = df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", [min_date, max_date])

start_time = st.sidebar.time_input("Start", time(0, 0))
end_time = st.sidebar.time_input("End", time(23, 59))

tags = st.sidebar.multiselect("Select Tags", sorted(df["Tag_Name"].unique()), ["Feedrate"])
filter_name = st.sidebar.text_input("Filter by name or equipment")

quality_good = st.sidebar.checkbox("Quality = Good only", False)
fill_feedrate = st.sidebar.checkbox("Use cleaned Feedrate (fill false dips)", False)
show_markers = st.sidebar.checkbox("Markers", False)

# ---------- FILTERING ----------
mask = (df["Time"].dt.date >= date_range[0]) & (df["Time"].dt.date <= date_range[-1])
mask &= (df["Time"].dt.time >= start_time) & (df["Time"].dt.time <= end_time)
if tags:
    mask &= df["Tag_Name"].isin(tags)
if filter_name:
    mask &= df["Equipment"].str.contains(filter_name, case=False, na=False)
if quality_good and "Quality" in df.columns:
    mask &= df["Quality"].astype(str).str.contains("Good", case=False, na=False)

filtered = df.loc[mask].copy()
if filtered.empty:
    st.warning("No matching data for selected filters.")
    st.stop()

if fill_feedrate and "Feedrate" in tags:
    filtered["Value"] = filtered.groupby("Equipment")["Value"].transform(
        lambda s: s.ffill(limit=10)
    )

# ---------- PLOT ----------
fig = px.line(
    filtered,
    x="Time",
    y="Value",
    color="Tag_Name",
    line_shape="linear",
    title="Trend Data (Raw Values)",
    markers=show_markers,
)
fig.update_layout(
    height=650,
    xaxis_title="Time",
    yaxis_title="Value (raw units)",
    legend_title="Tag",
    hovermode="x unified",
)

st.title("Comco - RTA Trends Dashboard")
st.caption(f"Source: repo data • Last updated: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}")
st.plotly_chart(fig, use_container_width=True)

# ---------- DATA PREVIEW ----------
with st.expander("📊 Data Preview"):
    st.dataframe(filtered.tail(200))

# ---------- FOOTER ----------
st.markdown("---")
st.caption("FactoryTalk-style synchronized trends • Raw + Optional cleaned Feedrate.")
