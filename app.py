
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

# --- Load data from repo ---
@st.cache_data
def load_data():
    df = pd.read_csv("FactoryData_Clean_30Day.csv", parse_dates=["Time"])
    df = df.sort_values("Time")
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filters")

min_date, max_date = df["Time"].min().date(), df["Time"].max().date()
date_range = st.sidebar.date_input("Date range", value=[min_date, max_date])

start_time = st.sidebar.time_input("Start", value=datetime.strptime("00:00", "%H:%M").time())
end_time = st.sidebar.time_input("End", value=datetime.strptime("23:59", "%H:%M").time())

tag_options = sorted(df["Tag_Name"].unique())
selected_tags = st.sidebar.multiselect("Select Tags", tag_options, default=["Feedrate"])

filter_text = st.sidebar.text_input("Filter by name or equipment")

quality_good = st.sidebar.checkbox("Quality = Good only", value=False)
fill_dips = st.sidebar.checkbox("Use cleaned Feedrate (fill false dips)", value=False)
show_markers = st.sidebar.checkbox("Markers", value=False)

# --- Filter data ---
f = df.copy()

if quality_good:
    f = f[f["Quality"].str.contains("Good", case=False, na=False)]

if len(date_range) == 2:
    start_dt = pd.to_datetime(f"{date_range[0]} {start_time}")
    end_dt = pd.to_datetime(f"{date_range[1]} {end_time}")
    f = f[(f["Time"] >= start_dt) & (f["Time"] <= end_dt)]

if selected_tags:
    f = f[f["Tag_Name"].isin(selected_tags)]

if filter_text:
    f = f[f["Equipment"].str.contains(filter_text, case=False, na=False) |
          f["Tag_Name"].str.contains(filter_text, case=False, na=False)]

# --- Handle Feedrate dips (optional) ---
if fill_dips and "Feedrate" in f["Tag_Name"].unique():
    feed_df = f[f["Tag_Name"] == "Feedrate"].copy()
    feed_df["Value_Cleaned"] = feed_df["Value"]
    # Fill short 30-sec gaps where motor was running but feedrate dropped
    feed_df["Gap"] = feed_df["Time"].diff().dt.total_seconds().fillna(0)
    feed_df.loc[(feed_df["Gap"] < 90) & (feed_df["Value_Cleaned"] == 0), "Value_Cleaned"] = None
    feed_df["Value_Cleaned"] = feed_df["Value_Cleaned"].interpolate()
    f = pd.concat([f[f["Tag_Name"] != "Feedrate"], feed_df], ignore_index=True)
    f["PlotValue"] = f["Value_Cleaned"].fillna(f["Value"])
else:
    f["PlotValue"] = f["Value"]

# --- Plot ---
if not f.empty:
    fig = px.line(
        f,
        x="Time",
        y="PlotValue",
        color="Tag_Name",
        title="Trend Data (Raw Values)",
        markers=show_markers,
    )
    fig.update_traces(connectgaps=True)
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Value (raw units)",
        legend_title="Tag",
        template="plotly_dark",
        height=600,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No data found for selected filters.")

# --- Footer ---
st.markdown("---")
st.caption("Source: repo data • Last updated: " + datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
