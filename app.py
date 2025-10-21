import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ----- PAGE CONFIG -----
st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

st.title("Comco - RTA Trends Dashboard")
st.caption("Live visualization of last 30 days factory trends (Feedrate, Load, Motor Current, Setpoint, etc.)")

# ----- LOAD DATA -----
@st.cache_data
def load_data():
    file_path = "Last_30_Day_Data_Group_45.csv"
    if not os.path.exists(file_path):
        st.error("❌ File not found. Please ensure Last_30_Day_Data_Group_45.csv is in the root directory.")
        st.stop()

    df = pd.read_csv(file_path, parse_dates=["Time"], low_memory=False)
    df = df.sort_values("Time")
    df["Tag_Name"] = df["Tag_Name"].fillna("Unknown")
    return df

df = load_data()

st.caption(f"Source: repo data • Last updated: {pd.Timestamp.now().strftime('%a %b %d %H:%M:%S %Y')}")

# ----- SIDEBAR FILTERS -----
st.sidebar.header("Filters")

date_range = st.sidebar.date_input(
    "Date range",
    value=(df["Time"].min().date(), df["Time"].max().date())
)
start_time = st.sidebar.time_input("Start", pd.Timestamp("00:00:00").time())
end_time = st.sidebar.time_input("End", pd.Timestamp("23:59:00").time())

tag_options = sorted(df["Tag_Name"].dropna().unique())
selected_tags = st.sidebar.multiselect("Select Tags", tag_options, default=["Feedrate"])
name_filter = st.sidebar.text_input("Filter by equipment or name", "")

use_clean = st.sidebar.checkbox("Use cleaned Feedrate (fills dips)", value=True)
show_markers = st.sidebar.checkbox("Show markers", value=False)

# ----- FILTER DATA -----
mask = (
    (df["Time"].dt.date >= date_range[0])
    & (df["Time"].dt.date <= date_range[1])
    & (df["Time"].dt.time >= start_time)
    & (df["Time"].dt.time <= end_time)
)

filtered = df[mask]

if name_filter:
    filtered = filtered[filtered["Name"].str.contains(name_filter, case=False, na=False)]

filtered = filtered[filtered["Tag_Name"].isin(selected_tags)]

if filtered.empty:
    st.warning("⚠️ No data found for selected filters.")
    st.stop()

# ----- PLOT -----
fig = px.line(
    filtered,
    x="Time",
    y="Value",
    color="Tag_Name",
    line_shape="linear",
    title="Trend Data (Raw Values)",
)

fig.update_traces(mode="lines+markers" if show_markers else "lines")
fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Value (raw units)",
    legend_title="Tag",
    hovermode="x unified",
    template="plotly_dark"
)

st.plotly_chart(fig, use_container_width=True)

# ----- DATA PREVIEW -----
st.subheader("Data Preview")
st.dataframe(filtered.head(50))
