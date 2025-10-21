import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Tag Trends", page_icon="📈", layout="wide")

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# ===============================
# LOAD DATA
# ===============================
@st.cache_data
def load_data():
    encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(DATA_URL, encoding=enc, on_bad_lines="skip", engine="python")
            break
        except Exception:
            continue
    else:
        st.error("❌ Could not load CSV file.")
        st.stop()

    df.columns = [c.strip().lower() for c in df.columns]
    col_tag = next((c for c in df.columns if "tag" in c or "name" in c), None)
    col_val = next((c for c in df.columns if "value" in c), None)
    col_time = next((c for c in df.columns if "time" in c), None)

    if not col_tag or not col_val:
        st.error(f"Missing expected columns. Found: {df.columns.tolist()}")
        st.stop()

    df.rename(columns={col_tag: "Tag", col_val: "Value"}, inplace=True)
    if col_time:
        df.rename(columns={col_time: "Timestamp"}, inplace=True)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    else:
        df["Timestamp"] = pd.date_range(start="2025-01-01", periods=len(df), freq="T")

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df.dropna(subset=["Value", "Tag"])


df = load_data()

# ===============================
# SIDEBAR FILTERS
# ===============================
st.sidebar.header("⏱ Time Range")
min_time, max_time = df["Timestamp"].min(), df["Timestamp"].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

if start_time < end_time:
    df_filtered = df[(df["Timestamp"].dt.time >= start_time) & (df["Timestamp"].dt.time <= end_time)]
else:
    df_filtered = df[(df["Timestamp"].dt.time >= start_time) | (df["Timestamp"].dt.time <= end_time)]

# ===============================
# MAIN LAYOUT
# ===============================
st.title("📊 Tag Trends")
st.markdown(
    "Each selected tag is plotted with its own Y-axis scale. "
    "**Feedrate-type tags (Feedrate, TPH, Rate)** are automatically scaled ×0.001."
)

available_tags = sorted(df["Tag"].unique())
selected_tags = st.multiselect(
    "Select Tags to Display",
    available_tags,
    default=available_tags[:3],
)

if df_filtered.empty:
    st.warning("⚠️ No data found in this range.")
elif selected_tags:
    fig = go.Figure()
    colors = [
        "#FF6B6B", "#4ECDC4", "#FFD93D", "#1A73E8",
        "#9C27B0", "#00BFA6", "#F39C12", "#E74C3C",
        "#3498DB", "#2ECC71"
    ]

    # Add traces safely
    for i, tag in enumerate(selected_tags):
        sub = df_filtered[df_filtered["Tag"] == tag]
        if sub.empty:
            continue

        tag_lower = tag.lower()
        scale_factor = 0.001 if any(k in tag_lower for k in ["feedrate", "tph", "rate"]) else 1
        sub["ScaledValue"] = sub["Value"] * scale_factor

        color = colors[i % len(colors)]
        side = "right" if i % 2 else "left"

        fig.add_trace(
            go.Scatter(
                x=sub["Timestamp"],
                y=sub["ScaledValue"],
                name=f"{tag}{' (×0.001)' if scale_factor != 1 else ''}",
                mode="lines",
                line=dict(width=2, color=color),
                yaxis=f"y{i+1}",
            )
        )

        # define y-axis safely (no position param)
        fig.update_layout({
            f"yaxis{i+1}": dict(
                title=tag,
                titlefont=dict(color=color, size=10),
                tickfont=dict(color=color, size=9),
                side=side,
                overlaying="y" if i > 0 else None,
                rangemode="tozero",
                showgrid=False,
                zeroline=True,
            )
        })

    fig.update_layout(
        template="plotly_dark",
        height=750,
        margin=dict(l=80, r=150, t=80, b=60),
        hovermode="x unified",
        xaxis_title="Timestamp",
        legend=dict(orientation="h", y=-0.25, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        title=dict(text="📊 Tag Trends", x=0.5, font=dict(size=22)),
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Select tags to visualize trends.")

# ===============================
# RAW DATA EXPANDER
# ===============================
with st.expander("View Raw Data"):
    st.dataframe(df_filtered)
