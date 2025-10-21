import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Comco – RTA Daily Trends Dashboard (Raw Data)",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.markdown("""
Plots **unmodified Feedrate, Motor Current, Setpoint, and Load** values directly from CSV.  
**Data Source:** [WF with current data.csv](https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv)
""")

# --- Load Data ---
url = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

try:
    df = pd.read_csv(url, encoding='utf-16', on_bad_lines='skip')
    st.info("Loaded successfully using encoding: utf-16")
except Exception:
    df = pd.read_csv(url, encoding='utf-8', on_bad_lines='skip')
    st.info("Loaded successfully using fallback encoding: utf-8")

# --- Detect time column automatically ---
time_col = None
for col in df.columns:
    if "time" in col.lower() or "date" in col.lower():
        time_col = col
        break

if time_col is None:
    st.error("No timestamp column found in data. Please check your CSV.")
    st.stop()

df[time_col] = pd.to_datetime(df[time_col], errors='coerce')
df = df.dropna(subset=[time_col])
df = df.sort_values(by=time_col)

# --- Simplify column names ---
def short_name(c):
    parts = str(c).split('|')[-1]  # remove PLC paths
    return parts.split('.')[-1] if '.' in parts else parts

rename_map = {c: short_name(c) for c in df.columns}
df = df.rename(columns=rename_map)

# --- Sidebar Filters ---
st.sidebar.header("Filters")

min_time, max_time = df[time_col].min(), df[time_col].max()
start_time = st.sidebar.time_input("Start Time", value=min_time.time())
end_time = st.sidebar.time_input("End Time", value=max_time.time())

# Filter by selected time range
df_filtered = df[(df[time_col].dt.time >= start_time) & (df[time_col].dt.time <= end_time)]

numeric_cols = [c for c in df_filtered.columns if df_filtered[c].dtype in ['float64', 'int64']]
if not numeric_cols:
    st.warning("No numeric columns found in the data.")
    st.stop()

# --- Sidebar checkboxes for tags ---
st.sidebar.subheader("Select Tags to Display")
selected_tags = []
for tag in numeric_cols:
    if st.sidebar.checkbox(tag, value=False):
        selected_tags.append(tag)

if not selected_tags:
    st.warning("Please select at least one tag to visualize.")
    st.stop()

st.success(f"Data loaded successfully ({len(df_filtered)} rows).")

# --- Plot with independent Y-axes ---
st.subheader("Raw Trend Data (Continuous Lines with Independent Scales)")

fig = go.Figure()

for i, tag in enumerate(selected_tags):
    fig.add_trace(go.Scatter(
        x=df_filtered[time_col],
        y=df_filtered[tag],
        mode='lines',
        name=tag,
        yaxis=f'y{i+1}'
    ))

# Create independent axes for each selected tag
fig.update_layout(
    height=700,
    template='plotly_dark',
    xaxis=dict(title='Time'),
    title="WeighFeeder & Motor Trends (Raw Continuous Values)"
)

# Add secondary Y axes
if len(selected_tags) > 1:
    for i, tag in enumerate(selected_tags[1:], start=2):
        fig.update_layout({
            f'yaxis{i}': dict(
                title=tag,
                overlaying='y',
                side='right',
                position=1 - (0.05 * (i - 1))
            )
        })

st.plotly_chart(fig, use_container_width=True)
