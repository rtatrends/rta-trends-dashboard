# =============================================================
# COMCO - RTA TRENDS DASHBOARD (FT-Style Multi-Panel View)
# =============================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

# ------------------------------
# Data Loader
# ------------------------------
@st.cache_data
def load_data(file):
    df = pd.read_csv(file, parse_dates=['Time'])
    df.columns = [c.strip().title() for c in df.columns]
    df = df.rename(columns={"Taggroup": "Tag_Group", "Tagname": "Tag_Name"})
    df = df.dropna(subset=['Time', 'Value'])
    df = df.sort_values('Time')
    return df

# ------------------------------
# Sidebar - Upload
# ------------------------------
st.sidebar.title("📂 Data Source")
uploaded = st.sidebar.file_uploader("Upload FactoryData CSV", type=["csv"])
if uploaded is None:
    st.warning("Please upload FactoryData_Clean_30Day.csv or Small.csv to continue.")
    st.stop()

f = load_data(uploaded)
st.sidebar.success("✅ File uploaded and loaded successfully!")

# ------------------------------
# Filters
# ------------------------------
st.sidebar.header("🔍 Filters")
min_date, max_date = f["Time"].min(), f["Time"].max()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
start_time = st.sidebar.time_input("Start", datetime.min.time())
end_time = st.sidebar.time_input("End", datetime.max.time())

# Time filter
f = f[(f["Time"].dt.date >= date_range[0]) & (f["Time"].dt.date <= date_range[1])]
f = f[(f["Time"].dt.time >= start_time) & (f["Time"].dt.time <= end_time)]

# Tag filter
tags = sorted(f["Tag_Name"].unique())
selected_tags = st.sidebar.multiselect("Select Tags", tags, default=["Feedrate", "Setpoint", "Motor_Current"])

# Equipment filter
equipments = sorted(f["Equipment"].dropna().unique()) if "Equipment" in f.columns else []
selected_equip = st.sidebar.multiselect("Select Equipment", equipments, default=equipments)

f = f[f["Tag_Name"].isin(selected_tags)]
if selected_equip:
    f = f[f["Equipment"].isin(selected_equip)]

if f.empty:
    st.warning("No data for selected filters.")
    st.stop()

# ------------------------------
# Create Panels (FT-style)
# ------------------------------
st.title("Comco - RTA Trends Dashboard")
st.markdown("**FactoryTalk-style synchronized trend panels (Feedrate, Setpoint, Motor Current)**")

# Create one shared x-axis
fig = go.Figure()

colors = {
    "Feedrate": "#1f77b4",
    "Setpoint": "#ff7f0e",
    "Motor_Current": "#2ca02c"
}

# Panel 1: Feedrate
for eq in f["Equipment"].unique():
    df_eq = f[(f["Equipment"] == eq) & (f["Tag_Name"] == "Feedrate")]
    if not df_eq.empty:
        fig.add_trace(go.Scatter(
            x=df_eq["Time"], y=df_eq["Value"],
            name=f"{eq} Feedrate", line=dict(color=colors["Feedrate"], width=1.6),
            yaxis="y1"
        ))

# Panel 2: Setpoint
for eq in f["Equipment"].unique():
    df_eq = f[(f["Equipment"] == eq) & (f["Tag_Name"] == "Setpoint")]
    if not df_eq.empty:
        fig.add_trace(go.Scatter(
            x=df_eq["Time"], y=df_eq["Value"],
            name=f"{eq} Setpoint", line=dict(color=colors["Setpoint"], width=1.3, dash="dot"),
            yaxis="y2"
        ))

# Panel 3: Motor Current
for eq in f["Equipment"].unique():
    df_eq = f[(f["Equipment"] == eq) & (f["Tag_Name"] == "Motor_Current")]
    if not df_eq.empty:
        fig.add_trace(go.Scatter(
            x=df_eq["Time"], y=df_eq["Value"],
            name=f"{eq} Motor Current", line=dict(color=colors["Motor_Current"], width=1.3, dash="dash"),
            yaxis="y3"
        ))

# Layout — 3 stacked synchronized panels
fig.update_layout(
    height=900,
    xaxis=dict(domain=[0, 1]),
    yaxis=dict(title="Feedrate", domain=[0.66, 1.0]),
    yaxis2=dict(title="Setpoint", domain=[0.33, 0.65]),
    yaxis3=dict(title="Motor Current", domain=[0.0, 0.32]),
    legend=dict(orientation="h", y=-0.2),
    hovermode="x unified",
    template="plotly_dark",
    title="RTA Trends (Feedrate, Setpoint, Current) — Time Synchronized",
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------
# Data Preview + Download
# ------------------------------
st.subheader("📋 Data Preview")
st.dataframe(f.tail(20))

csv = f.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download Filtered Data", csv, "Filtered_Data.csv", "text/csv")
