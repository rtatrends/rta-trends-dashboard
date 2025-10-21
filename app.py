import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ------------------------------------
# CONFIG
# ------------------------------------
st.set_page_config(
    page_title="RTA Tag Trends",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# ------------------------------------
# LOAD DATA
# ------------------------------------
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
        st.error("❌ Unable to decode CSV file.")
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

# ------------------------------------
# TIME FILTER
# ------------------------------------
st.sidebar.header("⏱ Time Range")
min_time = df["Timestamp"].min()
max_time = df["Timestamp"].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

# Handle midnight wrap-around
if start_time < end_time:
    df_filtered = df[
        (df["Timestamp"].dt.time >= start_time)
        & (df["Timestamp"].dt.time <= end_time)
    ]
else:
    df_filtered = df[
        (df["Timestamp"].dt.time >= start_time)
        | (df["Timestamp"].dt.time <= end_time)
    ]

# ------------------------------------
# MAIN SECTION
# ------------------------------------
st.title("📊 Tag Trends")
st.markdown(
    "Each selected tag is plotted with its own Y-axis. "
    "Feedrate-type tags are automatically scaled ×0.001 for clarity."
)

available_tags = sorted(df["Tag"].unique().tolist())
selected_tags = st.multiselect(
    "Select Tags to Display",
    available_tags,
    default=available_tags[:4],
    max_selections=10,
)

if df_filtered.empty:
    st.warning("⚠️ No data found for this time range. Adjust Start/End times.")
elif selected_tags:
    fig = go.Figure()
    colors = [
        "#FF6B6B", "#4ECDC4", "#FFD93D", "#1A73E8",
        "#9C27B0", "#00BFA6", "#F39C12", "#E74C3C",
        "#3498DB", "#2ECC71"
    ]

    yaxes_config = {}

    # Build traces
    for i, tag in enumerate(selected_tags):
        sub = df_filtered[df_filtered["Tag"] == tag]
        if sub.empty:
            continue

        tag_lower = tag.lower()
        scale_factor = 0.001 if any(k in tag_lower for k in ["feedrate", "tph", "rate"]) else 1
        sub["ScaledValue"] = sub["Value"] * scale_factor

        color = colors[i % len(colors)]
        fig.add_trace(
            go.Scatter(
                x=sub["Timestamp"],
                y=sub["ScaledValue"],
                name=f"{tag}{' (×0.001)' if scale_factor != 1 else ''}",
                mode="lines",
                line=dict(width=2, color=color),
                hovertemplate="%{x}<br><b>%{y:.2f}</b><extra>%{fullData.name}</extra>",
            )
        )

        # Prepare axis definition (defer adding until after loop)
        side = "right" if i % 2 else "left"
        offset = (i // 2) * 70
        yaxes_config[f"yaxis{i+1}"] = dict(
            title=tag,
            titlefont=dict(size=10, color=color),
            tickfont=dict(size=9, color=color),
            overlaying="y" if i > 0 else None,
            side=side,
            anchor="free",
            position=1.0 - (offset / 1000) if side == "right" else (offset / 1000),
            rangemode="tozero",
            showgrid=False,
            zeroline=True,
        )
        fig.data[i].y axis = f"y{i+1}"

    # Apply all axes at once
    fig.update_layout(yaxes_conf
