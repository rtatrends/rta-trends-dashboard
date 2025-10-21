import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import time

# -----------------------------
# Streamlit Setup
# -----------------------------
st.set_page_config(page_title="Comco – Raw WF Daily Trends", layout="wide")
st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.caption("Plots unmodified Feedrate, Motor Current, Setpoint, and Load values directly from CSV.")

# -----------------------------
# Load Raw Data
# -----------------------------
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("WF with current data.csv", encoding="utf-16", on_bad_lines="skip")
    except UnicodeError:
        df = pd.read_csv("WF with current data.csv", encoding="utf-8", on_bad_lines="skip")

    df.columns = [c.strip() for c in df.columns]
    if "Time" not in df.columns:
        st.error("❌ 'Time' column not found.")
        st.stop()

    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"])
    return df

df = load_data()
st.success(f"✅ Data loaded successfully ({len(df):,} rows).")

# -----------------------------
# Identify possible tags
# -----------------------------
feed_cols = [c for c in df.columns if "Feedrate" in c or "Feed_Rate" in c]
motor_cols = [c for c in df.columns if "Motor" in c or "MOT" in c]
setpoint_cols = [c for c in df.columns if "Setpoint" in c or "SP" in c]
load_cols = [c for c in df.columns if "Load" in c or "Rolling" in c]

# -----------------------------
# Sidebar Filters
# -----------------------------
st.sidebar.header("Filters")

start_time = st.sidebar.time_input("Start Time", value=time(0, 0))
end_time = st.sidebar.time_input("End Time", value=time(23, 59))

available_cols = [*feed_cols, *motor_cols, *setpoint_cols, *load_cols]
selected_cols = st.sidebar.multiselect(
    "Select Tags to Display", available_cols,
    default=[c for c in available_cols if "Feedrate" in c or "Motor" in c]
)

filtered = df[
    (df["Time"].dt.time >= start_time) &
    (df["Time"].dt.time <= end_time)
]

# -----------------------------
# Plot Multi-Axis Chart
# -----------------------------
st.subheader("Raw Trend Data (Continuous Lines with Independent Scales)")

if filtered.empty or not selected_cols:
    st.warning("⚠️ No data for selected filters.")
    st.stop()

fig = go.Figure()

for i, col in enumerate(selected_cols):
    axis_name = f"y{i+1}"
    fig.add_trace(go.Scatter(
        x=filtered["Time"],
        y=filtered[col],
        mode="lines",
        name=col,
        line=dict(width=1.8),
        connectgaps=True,
        yaxis=axis_name
    ))

    # Configure y-axis (overlaying each one)
    if i == 0:
        fig.update_layout(yaxis=dict(title=f"{col}", showgrid=True))
    else:
        fig.update_layout({
            f"yaxis{i+1}": dict(
                title=f"{col}",
                overlaying="y",
                side="right",
                position=1 - (i * 0.05),
                showgrid=False
            )
        })

fig.update_layout(
    template="plotly_dark",
    title="WeighFeeder & Motor Trend (Raw Continuous Values)",
    xaxis=dict(title="Time", rangeslider_visible=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    height=750
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Data Preview
# -----------------------------
with st.expander("🔍 Data Preview"):
    st.dataframe(filtered[selected_cols + ["Time"]].head(100))
