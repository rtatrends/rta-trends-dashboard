import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Comco - RTA Trends Dashboard", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_csv("FactoryData_Clean_30Day.csv", parse_dates=['Time'])
    df['Tag_Name'] = df['Tag_Name'].fillna('Other')
    return df

# --- LOAD ---
f = load_data()

# --- SIDEBAR ---
st.sidebar.title("Filters")
date_min, date_max = f['Time'].min(), f['Time'].max()
date_range = st.sidebar.date_input("Date range", [date_min.date(), date_max.date()])
start_time = st.sidebar.time_input("Start", pd.Timestamp("00:00").time())
end_time = st.sidebar.time_input("End", pd.Timestamp("23:59").time())

tag_options = sorted(f['Tag_Name'].unique())
selected_tags = st.sidebar.multiselect("Select Tags", tag_options, default=['Feedrate'])
filter_name = st.sidebar.text_input("Filter by name or equipment")

use_cleaned = st.sidebar.checkbox("Use cleaned Feedrate (fill false dips)", True)
show_markers = st.sidebar.checkbox("Markers", False)

# --- FILTER ---
mask = (f['Time'].dt.date >= date_range[0]) & (f['Time'].dt.date <= date_range[1])
mask &= (f['Time'].dt.time >= start_time) & (f['Time'].dt.time <= end_time)
filt = f[mask]

if filter_name:
    filt = filt[filt['Name'].str.contains(filter_name, case=False, na=False)]

if selected_tags:
    filt = filt[filt['Tag_Name'].isin(selected_tags)]

# --- DISPLAY ---
st.title("Comco - RTA Trends Dashboard")
st.caption("Raw historian values • Optional filled Feedrate dips • Short tag labels only.")

if use_cleaned and 'Filled_Value' in filt.columns:
    filt['PlotValue'] = filt['Filled_Value']
else:
    filt['PlotValue'] = filt['Value']

fig = px.line(
    filt, x='Time', y='PlotValue', color='Tag_Name',
    title="Selected Trends (auto-scaled)",
    markers=show_markers
)
fig.update_layout(legend_title_text="Tag", yaxis_title="Value (raw units)", xaxis_title="Time")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(filt[['Time', 'Equipment', 'Tag_Name', 'Value', 'Filled_Value']].tail(20))
