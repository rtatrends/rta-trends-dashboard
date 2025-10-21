import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(
    page_title="Comco - RTA Trends Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------
# LOAD DATA FUNCTION
# --------------------------------------
@st.cache_data
def load_data(file_path):
    df = pd.read_csv(file_path, parse_dates=['Time'])
    df['Tag_Name'] = df['Tag_Name'].fillna('Other')
    df['Equipment'] = df['Equipment'].fillna('Unknown')
    df['Tag_Group'] = df['Tag_Group'].fillna('Other')
    return df


# --------------------------------------
# LOAD CSV (AUTO OR UPLOAD)
# --------------------------------------
data_file = "FactoryData_Clean_30Day.csv"

if os.path.exists(data_file):
    df = load_data(data_file)
    st.sidebar.success("✅ Loaded FactoryData_Clean_30Day.csv")
else:
    st.sidebar.warning("⚠️ CSV not found. Please upload your dataset.")
    uploaded_file = st.sidebar.file_uploader("Upload your CSV here", type=["csv"])
    if uploaded_file:
        df = load_data(uploaded_file)
        st.sidebar.success("✅ Uploaded and loaded successfully!")
    else:
        st.stop()

# --------------------------------------
# SIDEBAR FILTERS
# --------------------------------------
st.sidebar.header("Filters")

date_min = df['Time'].min().date()
date_max = df['Time'].max().date()

date_range = st.sidebar.date_input(
    "Date range", [date_min, date_max],
    min_value=date_min, max_value=date_max
)

start_time = st.sidebar.time_input("Start", pd.to_datetime("00:00").time())
end_time = st.sidebar.time_input("End", pd.to_datetime("23:59").time())

selected_tags = st.sidebar.multiselect(
    "Select Tags",
    sorted(df['Tag_Name'].unique()),
    default=['Feedrate']
)

filter_name = st.sidebar.text_input("Filter by name or equipment", "")

quality_filter = st.sidebar.checkbox("Quality = Good only", value=False)
fill_feedrate = st.sidebar.checkbox("Use cleaned Feedrate (fill false dips)", value=False)
show_markers = st.sidebar.checkbox("Markers", value=False)

# --------------------------------------
# FILTER LOGIC
# --------------------------------------
mask = (df['Time'].dt.date >= date_range[0]) & (df['Time'].dt.date <= date_range[-1])
mask &= (df['Time'].dt.time >= start_time) & (df['Time'].dt.time <= end_time)
mask &= df['Tag_Name'].isin(selected_tags)

if quality_filter and 'Quality' in df.columns:
    mask &= df['Quality'].str.lower().eq('good')

if filter_name:
    mask &= df['Equipment'].str.contains(filter_name, case=False, na=False)

f = df.loc[mask].copy()

if f.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# --------------------------------------
# CLEAN FEEDRATE OPTION
# --------------------------------------
if fill_feedrate and 'Motor_Current' in df['Tag_Name'].unique():
    f['Value_Clean'] = f['Value']
    feed_mask = f['Tag_Name'].eq('Feedrate')
    motor_mask = f['Tag_Name'].eq('Motor_Current')

    # Fill feedrate dips only when motor running
    motor_running_times = f.loc[motor_mask & (f['Value'] > 10), 'Time']
    fill_window = pd.to_timedelta("1min")
    f.loc[feed_mask, 'Value_Clean'] = f.loc[feed_mask].apply(
        lambda row: None if ((row['Time'] - motor_running_times).abs() < fill_window).any() else row['Value'],
        axis=1
    )
    f['PlotValue'] = f['Value_Clean']
else:
    f['PlotValue'] = f['Value']

# --------------------------------------
# PLOT
# --------------------------------------
st.title("Comco - RTA Trends Dashboard")
st.caption("Raw historian values • Optional cleaned Feedrate (fills only false dips when motor is running).")

fig = px.line(
    f,
    x='Time',
    y='PlotValue',
    color='Tag_Name',
    hover_data=['Equipment', 'Tag_Group', 'Source_File'],
    markers=show_markers,
    title='Trend Data (Raw Values)',
)

fig.update_layout(
    xaxis_title="Time",
    yaxis_title="Value (raw units)",
    hovermode="x unified",
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# --------------------------------------
# DATA TABLE
# --------------------------------------
st.markdown("### 📊 Data Preview")
st.dataframe(f[['Time', 'Equipment', 'Tag_Name', 'Value', 'Tag_Group', 'Quality', 'Source_File']].sort_values('Time'))

# --------------------------------------
# DOWNLOAD OPTION
# --------------------------------------
st.download_button(
    label="⬇️ Download filtered data as CSV",
    data=f.to_csv(index=False).encode('utf-8'),
    file_name="Filtered_Trends_Data.csv",
    mime="text/csv"
)
