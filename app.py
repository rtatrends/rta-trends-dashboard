import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output

app = Dash(__name__)

# Load raw CSV directly
url = "https://raw.githubusercontent.com/rtatrends/rta-trends-dashboard/refs/heads/main/WF%20with%20current%20data.csv"
df = pd.read_csv(url)

# Ensure time parsing
df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

# Create tag list dynamically
available_tags = df['Name'].unique()

app.layout = html.Div([
    html.H2("📊 Raw Trend Data (Independent Scales)"),
    
    html.Label("Select Tags to Display:"),
    dcc.Checklist(
        id="tag_selector",
        options=[{'label': tag, 'value': tag} for tag in available_tags],
        value=list(available_tags[:4]),  # default first few
        inline=True
    ),
    
    dcc.Graph(id="trend_chart")
])

@app.callback(
    Output("trend_chart", "figure"),
    Input("tag_selector", "value")
)
def update_chart(selected_tags):
    fig = go.Figure()
    for tag in selected_tags:
        sub = df[df["Name"] == tag]
        fig.add_trace(go.Scatter(
            x=sub["Timestamp"], 
            y=sub["Value"],
            name=tag,
            mode="lines"
        ))

    fig.update_layout(
        title="WeighFeeder & Motor Trends (Raw Continuous Data)",
        xaxis_title="Time",
        yaxis_title="Value",
        template="plotly_dark",
        height=600
    )

    # independent y-axes
    for i, trace in enumerate(fig.data):
        fig.data[i].yaxis = f'y{i+1}'
        fig.layout[f'yaxis{i+1}'] = dict(
            title=trace.name,
            overlaying='y' if i > 0 else None,
            side='right' if i % 2 else 'left',
            showgrid=False
        )
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
