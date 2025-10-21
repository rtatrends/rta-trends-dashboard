import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Comco – RTA Daily Trends Dashboard (Raw Data)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- TITLE & INTRO ---
st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.markdown(
    """
    Plots unmodified Feedrate, Motor Current, Setpoint, and Load values directly from CSV.  
    Data source: [WF with current data.csv](https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv)
    """
)

# --- LOAD DATA ---
@st.cache_data(ttl=3600)
def load_data():
    url = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"
    df = pd.read_csv(url, encoding="utf-8", on_bad_lines="skip")
    # Normalize column names
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    # Find time column
    time_col = next((c for c in df.columns if "time" in c.lower()), None)
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
    else:
        st.error("No timestamp column found.")
        st.stop()
    # Keep only numeric columns
    num_cols = df.select_dtypes(include="number").columns.tolist()
    return df, time_col, num_cols

df, time_col, num_cols = load_data()
st.success(f"✅ Data loaded successfully ({len(df)} rows).")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filters")

start_time = st.sidebar.time_input("Start Time", value=pd.Timestamp("00:00").time())
end_time = st.sidebar.time_input("End Time", value=pd.Timestamp("23:59").time())

available_tags = num_cols
selected_tags = st.sidebar.multiselect(
    "Select Tags to Display", available_tags, default=["Feedrate"]
)

# --- DATA FILTERING ---
df["TimeOnly"] = df[time_col].dt.time
filtered = df[(df["TimeOnly"] >= start_time) & (df["TimeOnly"] <= end_time)]

if filtered.empty:
    st.warning("⚠️ No data for selected filters.")
    st.stop()

# --- SHORTEN COLUMN NAMES ---
def short_name(tag):
    # Remove long path segments like PLC paths
    if "/" in tag or "\\" in tag:
        return tag.split("/")[-1].split("\\")[-1]
    return tag

short_labels = {col: short_name(col) for col in selected_tags}

# --- PLOT MULTI-AXIS TREND ---
st.subheader("Raw Trend Data (Continuous Lines with Independent Scales)")

fig = go.Figure()
colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

for i, tag in enumerate(selected_tags):
    color = colors[i % len(colors)]
    axis_suffix = "" if i == 0 else str(i + 1)
    y_axis = "y" + axis_suffix
    fig.add_trace(
        go.Scatter(
            x=filtered[time_col],
            y=filtered[tag],
            mode="lines",
            name=short_labels[tag],
            line=dict(color=color, width=1.5),
            yaxis=y_axis,
        )
    )

# Configure axes
fig.update_layout(
    xaxis=dict(title="Time"),
    yaxis=dict(title=short_labels.get(selected_tags[0], selected_tags[0])),
    template="plotly_dark",
    hovermode="x unified",
)

# Add extra axes for multiple tags
for i in range(1, len(selected_tags)):
    fig.update_layout(
        {f"yaxis{i+1}": dict(
            title=short_labels[selected_tags[i]],
            overlaying="y",
            side="right" if i % 2 == 1 else "left",
            position=1 - (0.05 * i)
        )}
    )

st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.caption("Comco RTA Dashboard • Plots from raw historian export • Powered by Streamlit + Plotly")
