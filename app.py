import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Tag Trends", page_icon="📊", layout="wide")

DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

# --- Load data safely
@st.cache_data
def load_data():
    encodings = ["utf-16", "utf-16-le", "utf-8-sig", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(DATA_URL, encoding=enc, on_bad_lines="skip", engine="python")
            break
        except Exception:
            continue
    else:
        st.error("❌ Could not load CSV file.")
        st.stop()

    # normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    tag_col = next((c for c in df.columns if "tag" in c or "name" in c), None)
    val_col = next((c for c in df.columns if "value" in c), None)
    time_col = next((c for c in df.columns if "time" in c), None)

    if not tag_col or not val_col:
        st.error(f"Missing expected columns. Found: {df.columns.tolist()}")
        st.stop()

    df.rename(columns={tag_col: "Tag", val_col: "Value"}, inplace=True)
    if time_col:
        df.rename(columns={time_col: "Timestamp"}, inplace=True)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    else:
        df["Timestamp"] = pd.date_range("2025-01-01", periods=len(df), freq="T")

    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
    return df.dropna(subset=["Value", "Tag"])


df = load_data()

# --- Sidebar filters
st.sidebar.header("⏱ Time Range")
min_time, max_time = df["Timestamp"].min(), df["Timestamp"].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

if start_time < end_time:
    df_filtered = df[(df["Timestamp"].dt.time >= start_time) & (df["Timestamp"].dt.time <= end_time)]
else:
    df_filtered = df[(df["Timestamp"].dt.time >= start_time) | (df["Timestamp"].dt.time <= end_time)]

# --- Tag selector
st.title("📊 Tag Trends")
st.markdown("Each selected tag is plotted with its own Y-axis scale. Feedrate-type tags (Feedrate, TPH, Rate) are automatically scaled ×0.001.")

available_tags = sorted(df["Tag"].unique())
selected_tags = st.multiselect("Select Tags to Display", available_tags, default=available_tags[:3])

if df_filtered.empty:
    st.warning("⚠️ No data found in this range.")
elif not selected_tags:
    st.info("Select tags to visualize trends.")
else:
    plot_df = pd.DataFrame()
    for tag in selected_tags:
        sub = df_filtered[df_filtered["Tag"] == tag].copy()
        if sub.empty:
            continue
        scale = 0.001 if any(k in tag.lower() for k in ["feedrate", "tph", "rate"]) else 1
        sub["ScaledValue"] = sub["Value"] * scale
        sub["ScaledTag"] = f"{tag} (×{scale})" if scale != 1 else tag
        plot_df = pd.concat([plot_df, sub])

    if not plot_df.empty:
        fig = px.line(
            plot_df,
            x="Timestamp",
            y="ScaledValue",
            color="ScaledTag",
            labels={"ScaledValue": "Value", "Timestamp": "Timestamp"},
            template="plotly_dark",
        )
        fig.update_layout(height=750, hovermode="x unified", legend_title_text="Tags")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No matching data for selected tags.")

# --- Optional raw data viewer
with st.expander("View Raw Data"):
    st.dataframe(df_filtered)
