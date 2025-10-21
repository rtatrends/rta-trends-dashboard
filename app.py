import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import time

st.set_page_config(page_title="Comco – WF Raw Daily Trends", layout="wide")
st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.caption("Plots unmodified Feedrate, Motor Current, Setpoint, and Load values directly from CSV.")

# --- LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("WF with current data.csv", encoding="utf-16", on_bad_lines="skip")
    except UnicodeError:
        df = pd.read_csv("WF with current data.csv", encoding="utf-8", on_bad_lines="skip")

    # Clean up column names
    df.columns = [c.strip().replace("\n", " ").replace("\r", " ").replace("  ", " ") for c in df.columns]
    df.columns = [c.replace(".", "_").replace("(", "").replace(")", "").replace("/", "_") for c in df.columns]

    # Ensure Time column exists
    time_col = None
    for c in df.columns:
        if "Time" in c or "Timestamp" in c or "Date" in c:
            time_col = c
            break

    if not time_col:
        st.error("❌ No timestamp column found. Please make sure your CSV has a Time column.")
        st.stop()

    df.rename(columns={time_col: "Time"}, inplace=True)
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"])
    return df

df = load_data()
st.success(f"✅ Data loaded successfully ({len(df):,} rows).")

# --- FILTERS ---
st.sidebar.header("Filters")
start_time = st.sidebar.time_input("Start Time", value=time(0, 0))
end_time = st.sidebar.time_input("End Time", value=time(23, 59))

# Allow all columns except Time for selection
numeric_cols = [c for c in df.columns if c != "Time" and pd.api.types.is_numeric_dtype(df[c])]
if not numeric_cols:
    st.warning("⚠️ No numeric columns found for plotting.")
    st.stop()

selected_cols = st.sidebar.multiselect("Select Tags to Display", numeric_cols, default=numeric_cols[:3])

filtered = df[
    (df["Time"].dt.time >= start_time) &
    (df["Time"].dt.time <= end_time)
]

# --- PLOT ---
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
        line=dict(width=1.5),
        connectgaps=True,
        yaxis=axis_name
    ))

    if i == 0:
        fig.update_layout(yaxis=dict(title=col, showgrid=True))
    else:
        fig.update_layout({
            f"yaxis{i+1}": dict(
                title=col,
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

with st.expander("🔍 Data Preview"):
    st.dataframe(filtered[["Time"] + selected_cols].head(100))
