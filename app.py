import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Comco - Daily WF Trends", layout="wide")
st.title("Comco - RTA Trends Dashboard (Daily Data)")

st.markdown(
    "Live visualization of daily WeighFeeder and motor trends "
    "(Feedrate, Load, Motor Current, Setpoint, etc.)"
)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("WF_1Day_Clean.csv", parse_dates=["Time"])
    except FileNotFoundError:
        df = pd.read_csv("WF with current data.csv", parse_dates=["Time"])
    return df

df = load_data()
st.caption(f"Source: local repo • Last updated: {datetime.now().strftime('%b %d %H:%M:%S %Y')}")
st.divider()

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

min_time, max_time = df["Time"].min(), df["Time"].max()
start_date, end_date = st.sidebar.date_input(
    "Date range",
    value=(min_time.date(), max_time.date()),
    min_value=min_time.date(),
    max_value=max_time.date(),
)

start_time = st.sidebar.time_input("Start", value=min_time.time())
end_time = st.sidebar.time_input("End", value=max_time.time())

available_tags = sorted(df["Tag_Name"].unique())
selected_tags = st.sidebar.multiselect("Select Tags", available_tags, default=["Feedrate", "Motor_Current"])

equipments = sorted(df["Equipment"].unique())
selected_eq = st.sidebar.multiselect("Filter by Equipment", equipments)

# --- FILTER DATA ---
filtered = df.copy()
filtered = filtered[
    (filtered["Time"] >= pd.Timestamp.combine(start_date, start_time))
    & (filtered["Time"] <= pd.Timestamp.combine(end_date, end_time))
]
if selected_tags:
    filtered = filtered[filtered["Tag_Name"].isin(selected_tags)]
if selected_eq:
    filtered = filtered[filtered["Equipment"].isin(selected_eq)]

if filtered.empty:
    st.warning("⚠️ No data matches your filters.")
    st.stop()

# --- PLOT ---
st.subheader("Trend Data (Raw Values)")
fig = px.line(
    filtered,
    x="Time",
    y="Value",
    color="Tag_Name",
    line_group="Equipment",
    markers=True,
    hover_data={"Equipment": True, "Value": True, "Quality": True},
    title="WeighFeeder & Motor Trend (Connected Lines)",
)

fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Value (raw units)",
    legend_title="Tag",
    template="plotly_dark",
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)

# --- DATA PREVIEW ---
st.subheader("Data Preview")
st.dataframe(filtered.sort_values("Time").head(30))
