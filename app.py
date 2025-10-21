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
        "#FF6B6B", "#4ECDC4", "#FFD93D", "#1A7
