import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Comco – RTA Daily Trends Dashboard (Raw Data)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Title and Description ---
st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.markdown("""
Plots **unmodified Feedrate, Motor Current, Setpoint, and Load** values directly from CSV.  
**Data Source:** [WF with current data.csv](https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv)
""")

# --- Load CSV from GitHub ---
url = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

try:
    df = pd.read_csv(url, encoding="utf-16", on_bad_lines="skip")
    st.info("✅ Loaded successfully using encoding: utf-16")
except Exception:
    df = pd.read_csv(url, encoding="utf-8", on_bad_lines="skip")
    st.info("✅ Loaded successfully using fallback encoding: utf-8")

# --- Detect timestamp column ---
time_col = None
for c in df.columns:
    if "time" in c.lower() or "date" in c.lower():
        time_col = c
        break

if time_col is None:
    st.error("❌ No timestamp column found in CSV.")
    st.stop()

df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
df = df.dropna(subset=[time_col]).sort_values(by=time_col)

# --- Clean Column Names ---
def clean_col(col):
    col = str(col)
    col = col.split("|")[-1]
    col = col.split(".")[-1]
    col = col.strip()
    return col

rename_map = {c: clean_col(c) for c in df.columns}
df = df.rename(columns=rename_map)

# --- Convert numeric-like columns ---
for c in df.columns:
    if c != time_col:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")

# --- Sidebar Filters ---
st.sidebar.header("Filters")
min_time, max_time = df[time_col].min(), df[time_col].max()
start_time = st.sidebar.time_input("Start Time", value=min_time.time())
end_time = st.sidebar.time_input("End Time", value=max_time.time())

df_filtered = df[(df[time_col].dt.time >= start_time) & (df[time_col].dt.time <= end_time)]

# --- Detect Numeric Tags ---
numeric_cols = [c for c in df_filtered.columns if df_filtered[c].dtype in ["float64", "int64"] and c != time_col]
if not numeric_cols:
    st.warning("⚠️ No numeric columns detected. Check file format.")
    st.stop()

# --- Sidebar Tag Selection ---
st.sidebar.subheader("Select Tags to Display")

# Category-color mapping
color_map = {
    "Feedrate": "#1f77b4",  # blue
    "Setpoint": "#ff7f0e",  # orange
    "Load": "#2ca02c",      # green
    "Motor": "#d62728",     # red
    "Belt": "#9467bd",      # purple
    "Average": "#bcbd22",   # yellow
    "Other": "#7f7f7f"      # gray
}

selected_tags = []
for tag in numeric_cols:
    if st.sidebar.checkbox(tag, value=("feed" in tag.lower() or "current" in tag.lower())):
        selected_tags.append(tag)

if not selected_tags:
    st.warning("⚠️ Please select at least one tag to visualize.")
    st.stop()

st.success(f"✅ Data loaded successfully ({len(df_filtered)} rows, {len(numeric_cols)} numeric tags detected).")

# --- Plot: Multi-Axis Line Chart ---
st.subheader("📊 Raw Trend Data (Continuous Lines with Independent Scales)")

fig = go.Figure()

for i, tag in enumerate(selected_tags):
    # choose color based on tag keywords
    color = color_map["Other"]
    for key in color_map.keys():
        if key.lower() in tag.lower():
            color = color_map[key]
            break

    fig.add_trace(go.Scatter(
        x=df_filtered[time_col],
        y=df_filtered[tag],
        mode="lines",
        name=tag,
        line=dict(color=color, width=2),
        yaxis=f"y{i+1}"
    ))

# --- Configure Layout ---
fig.update_layout(
    height=750,
    template="plotly_dark",
    xaxis=dict(title="Time"),
    title="WeighFeeder & Motor Trends (Raw Continuous Data)",
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2)
)

# --- Independent Scales ---
if len(selected_tags) > 1:
    for i, tag in enumerate(selected_tags[1:], start=2):
        fig.update_layout({
            f"yaxis{i}": dict(
                title=tag,
                overlaying="y",
                side="right",
                position=1 - (0.05 * (i - 1)),
                showgrid=False
            )
        })

st.plotly_chart(fig, use_container_width=True)
