import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================
# CONFIG
# ==============================
st.set_page_config(
    page_title="RTA Trends Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# ==============================
# LOAD DATA (robust + flexible)
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

    # Map likely columns
    name_col = next((c for c in df.columns if "tag" in c or "name" in c), None)
    value_col = next((c for c in df.columns if "value" in c), None)
    unit_col = next((c for c in df.columns if "unit" in c), None)
    qual_col = next((c for c in df.columns if "qual" in c), None)
    time_col = next((c for c in df.columns if "time" in c), None)

    if not all([name_col, value_col, time_col]):
        st.error("❌ Missing required columns (Name/Tag, Value, Timestamp). Check CSV headers.")
        st.write("Detected columns:", df.columns.tolist())
        st.stop()

    df.rename(columns={
        name_col: "Name",
        value_col: "Value",
        time_col: "Timestamp"
    }, inplace=True)

    if unit_col:
        df.rename(columns={unit_col: "Unit"}, inplace=True)
    else:
        df["Unit"] = ""

    if qual_col:
        df.rename(columns={qual_col: "Quality"}, inplace=True)
    else:
        df["Quality"] = ""

    # Convert types
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    df = df.dropna(subset=["Timestamp", "Value"])

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

available_tags = sorted(df["Name"].unique().tolist())
selected_tags = st.sidebar.multiselect(
    "Select Tags to Display", available_tags, default=available_tags[:4]
)

df_filtered = df[
    (df["Timestamp"].dt.time >= start_time) &
    (df["Timestamp"].dt.time <= end_time)
]

# ==============================
# MAIN DASHBOARD
# ==============================
st.title("📊 Raw Trend Data (Continuous Lines with Independent Scales)")
st.markdown("WeighFeeder & Motor Trends (Raw Continuous Data)")

if selected_tags:
    fig = go.Figure()

    # Add each tag as independent trace
    for tag in selected_tags:
        sub = df_filtered[df_filtered["Name"] == tag]
        fig.add_trace(
            go.Scatter(
                x=sub["Timestamp"],
                y=sub["Value"],
                name=tag,
                mode="lines",
                line=dict(width=1.5),
                hovertemplate="%{x}<br>%{y:.2f}<extra>%{fullData.name}</extra>",
            )
        )

    # Configure independent y-axes (like historian)
    for i, trace in enumerate(fig.data):
        fig.data[i].yaxis = f"y{i+1}"
        fig.layout[f"yaxis{i+1}"] = dict(
            title=trace.name,
            overlaying="y" if i > 0 else None,
            side="right" if i % 2 else "left",
            showgrid=False,
            zeroline=False,
        )

    fig.update_layout(
        template="plotly_dark",
        height=700,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        xaxis_title="Timestamp",
        legend=dict(orientation="h", y=-0.15)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Please select at least one tag to display.")

# ==============================
# RAW DATA TABLE
# ==============================
with st.expander("View Raw Data Table"):
    st.dataframe(df_filtered[["Timestamp", "Name", "Value", "Unit", "Quality"]])
