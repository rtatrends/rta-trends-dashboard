import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================
# CONFIG
# ==============================
st.set_page_config(
    page_title="RTA Tag Trends",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# ==============================
# LOAD DATA (robust UTF-16 safe)
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
        st.error("❌ Could not decode CSV — even after trying multiple encodings.")
        st.stop()

    # Normalize and simplify column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Handle minimal structure (Tag + Value)
    col_name = next((c for c in df.columns if "tag" in c or "name" in c), None)
    col_value = next((c for c in df.columns if "value" in c or "val" in c), None)
    col_time = next((c for c in df.columns if "time" in c), None)

    if not all([col_name, col_value]):
        st.error(f"❌ Missing required columns (tag/value). Found: {df.columns.tolist()}")
        st.stop()

    df.rename(columns={col_name: "Tag", col_value: "Value"}, inplace=True)

    if col_time:
        df.rename(columns={col_time: "Timestamp"}, inplace=True)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    else:
        # If no explicit time column, create synthetic timestamps
        df["Timestamp"] = pd.date_range(start="2025-01-01", periods=len(df), freq="T")

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Value", "Tag"])

    return df


df = load_data()

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("Filters")

tags = sorted(df["Tag"].unique().tolist())
selected_tags = st.sidebar.multiselect("Select Tags", tags, default=tags[:4])

# Time filtering if timestamps exist
if "Timestamp" in df.columns:
    min_time = df["Timestamp"].min()
    max_time = df["Timestamp"].max()
    start_time = st.sidebar.time_input("Start Time", min_time.time())
    end_time = st.sidebar.time_input("End Time", max_time.time())

    df_filtered = df[
        (df["Timestamp"].dt.time >= start_time) &
        (df["Timestamp"].dt.time <= end_time)
    ]
else:
    df_filtered = df

# ==============================
# MAIN DASHBOARD
# ==============================
st.title("📈 Tag Trends (Independent Y-Axes)")
st.markdown("Each tag plotted with its own Y-axis scale, all starting from zero.")

if selected_tags:
    fig = go.Figure()

    for tag in selected_tags:
        sub = df_filtered[df_filtered["Tag"] == tag]
        if sub.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=sub["Timestamp"],
                y=sub["Value"],
                name=tag,
                mode="lines",
                line=dict(width=1.8),
                hovertemplate="%{x}<br>%{y:.2f}<extra>%{fullData.name}</extra>",
            )
        )

    # Independent Y-axes (all from zero)
    for i, trace in enumerate(fig.data):
        fig.data[i].yaxis = f"y{i+1}"
        fig.layout[f"yaxis{i+1}"] = dict(
            title=trace.name,
            overlaying="y" if i > 0 else None,
            side="right" if i % 2 else "left",
            showgrid=False,
            zeroline=True,
            rangemode="tozero"
        )

    fig.update_layout(
        template="plotly_dark",
        height=700,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        xaxis_title="Timestamp",
        legend=dict(orientation="h", y=-0.2),
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Please select at least one tag to plot.")

# ==============================
# DATA VIEWER
# ==============================
with st.expander("View Raw Data"):
    st.dataframe(df_filtered)
