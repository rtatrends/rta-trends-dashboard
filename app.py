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
    encodings = ["utf-16", "utf-8", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(url, encoding=enc, on_bad_lines="skip")
            st.info(f"Loaded successfully using encoding: `{enc}`")
            break
        except UnicodeDecodeError:
            continue
    else:
        st.error("❌ Could not decode CSV file. Try saving it as UTF-8 or UTF-16.")
        st.stop()

    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    time_col = next((c for c in df.columns if "time" in c.lower()), None)
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
    else:
        st.error("❌ No timestamp column found in the file.")
        st.stop()

    num_cols = df.select_dtypes(include="number").columns.tolist()
    return df, time_col, num_cols

df, time_col, num_cols = load_data()
st.success(f"✅ Data loaded successfully ({len(df)} rows).")

# --- SIDEBAR ---
st.sidebar.header("Filters")

start_time = st.sidebar.time_input("Start Time", value=pd.Timestamp("00:00").time())
end_time = st.sidebar.time_input("End Time", value=pd.Timestamp("23:59").time())

# Checkbox selector
st.sidebar.markdown("### Select Tags to Display")
selected_tags = []
for col in num_cols:
    if st.sidebar.checkbox(col, value=("Feedrate" in col or "Current" in col)):
        selected_tags.append(col)

if not selected_tags:
    st.warning("⚠️ Please select at least one tag to visualize.")
    st.stop()

# --- FILTER BY TIME ---
df["TimeOnly"] = df[time_col].dt.time
filtered = df[(df["TimeOnly"] >= start_time) & (df["TimeOnly"] <= end_time)]

if filtered.empty:
    st.warning("⚠️ No data in this time range.")
    st.stop()

# --- SHORT LABELS ---
def short_name(tag):
    if "/" in tag or "\\" in tag:
        return tag.split("/")[-1].split("\\")[-1]
    return tag.split(".")[-1] if "." in tag else tag

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
            line=dict(color=color, width=1.2),
            yaxis=y_axis,
        )
    )

fig.update_layout(
    xaxis=dict(title="Time"),
    yaxis=dict(title=short_labels.get(selected_tags[0], selected_tags[0])),
    template="plotly_dark",
    hovermode="x unified",
    legend=dict(orientation="h", y=-0.25),
)

# Add secondary axes
for i in range(1, len(selected_tags)):
    fig.update_layout({
        f"yaxis{i+1}": dict(
            title=short_labels[selected_tags[i]],
            overlaying="y",
            side="right" if i % 2 else "left",
            position=1 - (0.05 * i)
        )
    })

st.plotly_chart(fig, use_container_width=True)
st.caption("Comco RTA Dashboard • Raw historian data • Multi-axis continuous plot • Powered by Streamlit + Plotly")
