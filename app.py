import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- CONFIG ---
st.set_page_config(page_title="Comco – RTA Daily Trends Dashboard", layout="wide")
DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_URL, encoding='utf-16', on_bad_lines='skip')
        st.info("Loaded successfully using encoding: utf-16")
    except Exception:
        df = pd.read_csv(DATA_URL, encoding='utf-8', on_bad_lines='skip')
        st.info("Loaded successfully using encoding: utf-8")
    return df

df = load_data()

# --- CLEANUP ---
df.columns = [col.split("\\")[-1].split(".")[-1].replace("_", " ").strip() for col in df.columns]

# Detect time column
time_col = next((c for c in df.columns if "time" in c.lower()), None)
if time_col:
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
    df = df.dropna(subset=[time_col])
    df = df.sort_values(time_col)
else:
    st.error("No valid time column found.")
    st.stop()

# Detect numeric tag columns
numeric_cols = [c for c in df.columns if df[c].dtype in ['float64', 'int64']]
if not numeric_cols:
    st.error("No numeric tags found for plotting.")
    st.stop()

# --- SIDEBAR ---
st.sidebar.header("Filters")
start_time = st.sidebar.time_input("Start Time", pd.Timestamp("00:00").time())
end_time = st.sidebar.time_input("End Time", pd.Timestamp("23:59").time())

available_tags = sorted(numeric_cols)
selected_tags = st.sidebar.multiselect("Select Tags to Display", available_tags, default=available_tags[:2])

# --- FILTER TIME RANGE ---
df["TimeOnly"] = df[time_col].dt.time
df_filtered = df[(df["TimeOnly"] >= start_time) & (df["TimeOnly"] <= end_time)]

st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.caption("Plots unmodified Feedrate, Motor Current, Setpoint, and Load values directly from CSV.")
st.markdown(f"**Data Source:** [WF with current data.csv]({DATA_URL})")

st.success(f"✅ Data loaded successfully ({len(df):,} rows).")

# --- PLOT ---
st.subheader("Raw Trend Data (Continuous Lines with Independent Scales)")

if selected_tags:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    colors = ["#00BFFF", "#FF6347", "#32CD32", "#FFD700", "#FF69B4", "#8A2BE2"]

    for i, tag in enumerate(selected_tags):
        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(x=df_filtered[time_col], y=df_filtered[tag], mode='lines', name=tag, line=dict(color=color)),
            secondary_y=(i % 2 == 1)
        )

    fig.update_layout(
        title="WeighFeeder & Motor Trend (Raw Continuous Values)",
        xaxis_title="Time",
        yaxis_title="Value (raw units)",
        legend_title="Tag",
        template="plotly_dark",
        hovermode="x unified",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("⚠️ Please select at least one tag to visualize.")
