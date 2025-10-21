import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================
# PAGE CONFIG
# ==============================
st.set_page_config(
    page_title="RTA Tag Trends (Scaled)",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# ==============================
# LOAD DATA
# ==============================
@st.cache_data
def load_data():
    encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8", "latin1"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(DATA_URL, encoding=enc, on_bad_lines="skip", engine="python")
            if df is not None:
                break
        except Exception:
            continue
    if df is None:
        st.error("❌ Could not decode CSV file.")
        st.stop()

    df.columns = [c.strip().lower() for c in df.columns]

    col_name = next((c for c in df.columns if "tag" in c or "name" in c), None)
    col_value = next((c for c in df.columns if "value" in c), None)
    col_time = next((c for c in df.columns if "time" in c), None)

    if not all([col_name, col_value]):
        st.error(f"❌ Missing required columns (tag/value). Found: {df.columns.tolist()}")
        st.stop()

    df.rename(columns={col_name: "Tag", col_value: "Value"}, inplace=True)
    if col_time:
        df.rename(columns={col_time: "Timestamp"}, inplace=True)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    else:
        df["Timestamp"] = pd.date_range(start="2025-01-01", periods=len(df), freq="T")

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Value", "Tag"])

    return df


df = load_data()

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("⏱ Time Range")
min_time = df["Timestamp"].min()
max_time = df["Timestamp"].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

df_filtered = df[
    (df["Timestamp"].dt.time >= start_time) &
    (df["Timestamp"].dt.time <= end_time)
]

# ==============================
# MAIN GRAPH SECTION
# ==============================
st.title("📊 Tag Trends (Independent Y-Axes, Scaled)")
st.markdown("Each tag plotted with its own Y-axis scale (auto-scaled for high-magnitude tags).")

available_tags = sorted(df["Tag"].unique().tolist())

# Let user select tags
selected_tags = st.multiselect("Select Tags", available_tags, default=available_tags[:4])

if selected_tags:
    fig = go.Figure()
    colors = [
        "#FF6B6B", "#4ECDC4", "#FFD93D", "#1A73E8",
        "#9C27B0", "#00BFA6", "#F39C12", "#E74C3C",
        "#3498DB", "#2ECC71"
    ]

    for i, tag in enumerate(selected_tags):
        sub = df_filtered[df_filtered["Tag"] == tag]
        if sub.empty:
            continue

        # Detect if tag has large magnitude (like Feedrate)
        scale_factor = 1
        if sub["Value"].max() > 50000:  # auto-detect high scale tags
            scale_factor = 0.001  # scale down for visual clarity

        sub["ScaledValue"] = sub["Value"] * scale_factor

        # Plot scaled data
        fig.add_trace(
            go.Scatter(
                x=sub["Timestamp"],
                y=sub["ScaledValue"],
                name=f"{tag} ({'×0.001' if scale_factor!=1 else 'raw'})",
                mode="lines",
                line=dict(width=2, color=colors[i % len(colors)]),
                hovertemplate="%{x}<br><b>%{y:.2f}</b><extra>%{fullData.name}</extra>",
            )
        )

    # Configure independent Y axes
    for i, trace in enumerate(fig.data):
        side = "right" if i % 2 else "left"
        offset = (i // 2) * 70

        fig.layout[f"yaxis{i+1}"] = dict(
            title=trace.name,
            titlefont=dict(size=10, color=trace.line.color),
            tickfont=dict(size=9, color=trace.line.color),
            overlaying="y" if i > 0 else None,
            side=side,
            anchor="free",
            position=1.0 - (offset / 1000) if side == "right" else (offset / 1000),
            rangemode="tozero",
            showgrid=False,
            zeroline=True,
        )
        trace.yaxis = f"y{i+1}"

    fig.update_layout(
        template="plotly_dark",
        height=750,
        margin=dict(l=80, r=120, t=80, b=60),
        hovermode="x unified",
        xaxis_title="Timestamp",
        legend=dict(
            orientation="h",
            y=-0.25,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)"
        ),
        title=dict(
            text="📈 Tag Trends (Independent Y-Axes with Auto-Scaling)",
            x=0.5,
            xanchor="center",
            font=dict(size=22, color="#FFFFFF")
        )
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select one or more tags to view their trends.")

# ==============================
# RAW DATA
# ==============================
with st.expander("View Raw Data"):
    st.dataframe(df_filtered)
