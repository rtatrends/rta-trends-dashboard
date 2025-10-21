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
# LOAD DATA
# ==============================
@st.cache_data
def load_data():
    encodings = ["utf-8", "utf-8-sig", "latin1", "ISO-8859-1"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(DATA_URL, encoding=enc, on_bad_lines="skip", engine="python")
            break
        except Exception:
            continue
    if df is None:
        st.error("❌ Could not load the CSV file.")
        st.stop()

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]

    # Expected columns: bytime, name, value
    col_time = next((c for c in df.columns if "time" in c), None)
    col_name = next((c for c in df.columns if "name" in c or "tag" in c), None)
    col_value = next((c for c in df.columns if "value" in c), None)

    if not all([col_time, col_name, col_value]):
        st.error("❌ Missing required columns (bytime/name/value). Found columns: " + str(df.columns.tolist()))
        st.stop()

    df.rename(columns={col_time: "Timestamp", col_name: "Tag", col_value: "Value"}, inplace=True)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Timestamp", "Tag", "Value"])

    return df


df = load_data()

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("Filters")

min_time = df["Timestamp"].min()
max_time = df["Timestamp"].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

tags = sorted(df["Tag"].unique().tolist())
selected_tags = st.sidebar.multiselect("Select Tags", tags, default=tags[:4])

# Filter by time
df_filtered = df[
    (df["Timestamp"].dt.time >= start_time) &
    (df["Timestamp"].dt.time <= end_time)
]

# ==============================
# MAIN DASHBOARD
# ==============================
st.title("📈 Tag Trend Data (Independent Y-Axes)")
st.markdown("Each tag plotted with independent Y-scale, all starting from zero.")

if selected_tags:
    fig = go.Figure()

    # Plot each selected tag
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

    # Independent y-axes for each tag
    for i, trace in enumerate(fig.data):
        fig.data[i].yaxis = f"y{i+1}"
        fig.layout[f"yaxis{i+1}"] = dict(
            title=trace.name,
            overlaying="y" if i > 0 else None,
            side="right" if i % 2 else "left",
            showgrid=False,
            zeroline=True,
            rangemode="tozero"  # start y-axis at 0
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
