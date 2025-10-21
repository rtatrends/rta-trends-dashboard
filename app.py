import os, io, time, requests, re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title='Comco - RTA Trends Dashboard', layout='wide')

RAW_CSV_URL = os.environ.get('RAW_CSV_URL','').strip()
LOCAL_CSV   = 'Last_30_Day_Data_Group_45.csv'

@st.cache_data(show_spinner=True, ttl=300)
def load_data(raw_url, local_path):
    if raw_url:
        r = requests.get(raw_url, timeout=30); r.raise_for_status()
        df = pd.read_csv(io.BytesIO(r.content), parse_dates=['Time'])
        src, upd = 'remote', r.headers.get('Last-Modified','GitHub')
    else:
        df = pd.read_csv(local_path, parse_dates=['Time'])
        src, upd = 'local', time.ctime(os.path.getmtime(local_path)) if os.path.exists(local_path) else 'unknown'
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    df.dropna(subset=['Time','Value'], inplace=True)
    df.sort_values('Time', inplace=True)
    return df, src, upd

df, src, upd = load_data(RAW_CSV_URL, LOCAL_CSV)

st.title('Comco - RTA Trends Dashboard')
st.caption(f'Source: {src} • Last updated: {upd}')
st.markdown('Raw historian values • Short tag labels • Individual multi-cursor hover')

# Sidebar filters
st.sidebar.header('Filters')
min_d, max_d = df['Time'].min().date(), df['Time'].max().date()
date_range = st.sidebar.date_input('Date range', (min_d, max_d))
col1, col2 = st.sidebar.columns(2)
start_t = col1.time_input('Start', pd.Timestamp('00:00').time())
end_t   = col2.time_input('End',   pd.Timestamp('23:59').time())

if isinstance(date_range,(tuple,list)) and len(date_range)==2:
    start_dt = pd.Timestamp.combine(date_range[0], start_t)
    end_dt   = pd.Timestamp.combine(date_range[1], end_t)
else:
    d = date_range if not isinstance(date_range,(tuple,list)) else date_range[0]
    start_dt = pd.Timestamp.combine(d, start_t)
    end_dt   = pd.Timestamp.combine(d, end_t)

mask = (df['Time']>=start_dt)&(df['Time']<=end_dt)

# Short tag column
if 'Tag' not in df.columns:
    df['Tag'] = df['Name'].apply(lambda x: re.split(r'[./]', str(x))[-1])

tags = sorted(df['Tag'].unique().tolist())
sel_tags = st.sidebar.multiselect('Select Tags', tags, default=tags[:6])
search = st.sidebar.text_input('Filter by name').upper()
quality_ok = st.sidebar.checkbox('Quality = Good only', value=False)
abs_feed = st.sidebar.checkbox('Absolute Feedrate', value=False)

mask &= df['Tag'].isin(sel_tags)
if search:
    mask &= df['Name'].str.upper().str.contains(search)
if quality_ok and 'Quality' in df.columns:
    mask &= df['Quality'].astype(str).str.upper().eq('GOOD')

f = df.loc[mask].copy()
if abs_feed:
    f.loc[f['Tag'].str.lower().eq('feedrate'),'Value'] = f['Value'].abs()

COLOR_MAP = {
    'Feedrate':'#1f77b4','Setpoint':'#ff7f0e','Load':'#d62728',
    'Speed':'#2ca02c','Current':'#17becf','Flow':'#9467bd',
    'Gate_Pos_CMD':'#8c564b','Totalizer':'#e377c2'
}

fig = go.Figure()
for tag, seg in f.groupby('Tag'):
    fig.add_trace(go.Scatter(
        x=seg['Time'], y=seg['Value'], mode='lines',
        name=tag, line=dict(color=COLOR_MAP.get(tag, None), width=1.5),
        # individual per-trace hover label near the curve
        hovertemplate=f'<b>{tag}</b><br>%{{x|%Y-%m-%d %H:%M:%S}}<br>Value: %{{y:.2f}}<extra></extra>',
        hoverlabel=dict(namelength=-1)
    ))

# Individual multi-cursor style: 'x' shows a hover label per trace at the cursor x
fig.update_layout(
    template='plotly_dark',
    height=750,
    hovermode='x',                  # individual labels per trace
    hoverdistance=50,               # sensitivity for capturing nearest data on x
    spikedistance=50,
    xaxis=dict(title='Time', showspikes=True, spikemode='across', spikesnap='cursor', spikethickness=1),
    yaxis=dict(title='Value (raw units)'),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
    margin=dict(t=60,l=60,r=40,b=40)
)

st.plotly_chart(fig, use_container_width=True)
st.dataframe(f.head(500))
