import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Comco – RTA Daily Trends Dashboard (Raw Data)",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- HEADER ---
st.title("Comco – RTA Daily Trends Dashboard (Raw Data)")
st.markdown("""
Plots unmodified Feedrate, Motor Current, Setpoint, and Load values directly from CSV.  
**Data Source:** [WF with current data.csv](https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv)
""")

# --- LOAD DATA ---
@st.cache_data(ttl=3600)
def load_data():
    url = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"
    encodings = ["utf-8", "utf-16", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(url, encoding=enc, on_bad_lines="skip")
            st.info(f"Loaded successfully using encoding: `{enc}`")
            break
        except UnicodeDecodeError:
            continue
    else:
        st.error("❌ Could not decode CSV file. Try saving it as UTF-8 or UTF-16 in Excel.")
        st.stop()

    # Normalize column names
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]

    # Detect timestamp column
    time_col = next((c for c in df.columns if "time" in c.lower()), None)
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
    else:
        st.error("❌ No timestamp column found in the file.")
        st.stop()

    # Keep numeric data only
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

# --- FILTER BY TIME ---
df["TimeOnly"] = df[time_col].dt.time
filtered = df[(df["TimeOnly"] >= start_time) & (df["TimeOnly"] <= end_time)]

if filtered.empty:
    st.warning("⚠️ No data found for selected time range.")
    st.stop()

# --- SHORT LABELS ---
def short_name(tag):
    if "/" in tag or "\\" in tag:
        return tag.split("/")[-1].split("\\")[-1]
    return tag

short_labels = {col: short_name(col) for col in selected_tags}

# --- PLOTTING ---
st.subheader("Raw Trend Data (Continuous Lines with Independent Scales)")

fig = go.Figure()
colors = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf"
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
            line=dict(color=color, width=1.3),
            yaxis=y_axis,
        )
    )

# Base axis
fig.update_layout(
    xaxis=dict(title="Time"),
    yaxis=dict(title=short_labels.get(selected_tags[0], selected_tags[0])),
    template="plotly_dark",
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.2),
)

# Add extra y-axes
for i in range(1, len(selected_tags)):
    fig.update_layout({
        f"yaxis{i+1}": dict(
            title=short_labels[selected_tags[i]],
            overlaying="y",
            side="right" if i % 2 == 1 else "left",
            position=1 - (0.04 * i)
        )
    })

st.plotly_chart(fig, use_container_width=True)
st.caption("Comco RTA Dashboard • Raw historian data • Multi-axis visualization • Powered by Streamlit + Plotly")
