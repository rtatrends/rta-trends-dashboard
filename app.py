# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==============================
# CONFIGURATION
# ==============================
st.set_page_config(
    page_title="RTA Trends Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================
# LOAD DATA
# ==============================
DATA_URL = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL)
    # Ensure timestamp column exists
    time_cols = [c for c in df.columns if 'time' in c.lower()]
    if time_cols:
        df.rename(columns={time_cols[0]: 'Timestamp'}, inplace=True)
    else:
        df['Timestamp'] = range(len(df))
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    df = df.dropna(subset=['Timestamp'])
    return df

df = load_data()

# ==============================
# SIDEBAR FILTERS
# ==============================
st.sidebar.header("Filters")

min_time = df['Timestamp'].min()
max_time = df['Timestamp'].max()

start_time = st.sidebar.time_input("Start Time", min_time.time())
end_time = st.sidebar.time_input("End Time", max_time.time())

# Tag selection
available_tags = df['Name'].unique().tolist()
selected_tags = st.sidebar.multiselect(
    "Select Tags to Display", available_tags, default=available_tags[:4]
)

# Filter by time range (hour:minute only)
df_filtered = df[
    (df['Timestamp'].dt.time >= start_time) &
    (df['Timestamp'].dt.time <= end_time)
]

# ==============================
# MAIN DASHBOARD
# ==============================
st.title("📊 Raw Trend Data (Continuous Lines with Independent Scales)")
st.markdown("WeighFeeder & Motor Trends (Raw Continuous Data)")

if selected_tags:
    fig = go.Figure()

    # Add traces for each selected tag
    for tag in selected_tags:
        sub = df_filtered[df_filtered["Name"] == tag]
        fig.add_trace(go.Scatter(
            x=sub["Timestamp"],
            y=sub["Value"],
            name=tag,
            mode="lines",
            hovertemplate="%{x}<br>%{y:.2f}<extra>%{fullData.name}</extra>"
        ))

    # Independent y-axes
    for i, trace in enumerate(fig.data):
        fig.data[i].yaxis = f'y{i+1}'
        fig.layout[f'yaxis{i+1}'] = dict(
            title=trace.name,
            overlaying='y' if i > 0 else None,
            side='right' if i % 2 else 'left',
            showgrid=False
        )

    fig.update_layout(
        template="plotly_dark",
        height=650,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified",
        xaxis_title="Timestamp"
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Please select at least one tag to display.")

# ==============================
# RAW DATA DISPLAY
# ==============================
with st.expander("View Raw Data Table"):
    st.dataframe(df_filtered[['Timestamp', 'Name', 'Value', 'Unit', 'Quality']])
