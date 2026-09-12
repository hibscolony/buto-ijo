"""Plotly visualizations built exclusively from real inference results."""

import plotly.graph_objects as go

FOREST = "#258553"
ORANGE = "#F4A340"
RED = "#E5483F"


def risk_gauge(score: float, level: str) -> go.Figure:
    color = {"LOW": FOREST, "MODERATE": ORANGE, "HIGH": RED}.get(level, FOREST)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"font": {"size": 43, "color": "#17342A"}, "valueformat": ".1f"},
        gauge={
            "axis": {"range": [0, 100], "tickvals": [0, 30, 60, 100], "tickfont": {"size": 9, "color": "#8DA192"}, "tickwidth": 0},
            "bar": {"color": color, "thickness": .75}, "bgcolor": "#F0F5F0", "borderwidth": 0,
            "steps": [{"range": [0, 30], "color": "#E8F3E9"}, {"range": [30, 60], "color": "#FCF1DC"}, {"range": [60, 100], "color": "#FAE7E2"}],
        },
        domain={"x": [.06, .94], "y": [.06, .92]},
    ))
    fig.add_annotation(x=.5, y=.04, text="/ 100", font={"size": 12, "color": "#829B8B"}, showarrow=False, xref="paper", yref="paper")
    fig.update_layout(height=225, margin={"l": 20, "r": 20, "t": 20, "b": 0}, paper_bgcolor="rgba(0,0,0,0)", font={"family": "Segoe UI, sans-serif"})
    return fig


def distribution_donut(summary: dict) -> go.Figure:
    flagged = int(summary["flagged_claims"])
    total = int(summary["total_claims"])
    fig = go.Figure(go.Pie(
        labels=["Higher Evidentiary Risk", "Lower Evidentiary Risk"], values=[flagged, total - flagged],
        hole=.76, sort=False, direction="clockwise", rotation=0,
        marker={"colors": ["#E9917D", "#4C9967"], "line": {"color": "#FFFFFF", "width": 3}},
        textinfo="none", hovertemplate="%{label}<br>%{value} klaim · %{percent}<extra></extra>",
        domain={"x": [.05, .95], "y": [.23, 1]},
    ))
    fig.update_layout(
        height=295, margin={"l": 4, "r": 4, "t": 12, "b": 0}, paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Segoe UI, sans-serif", "color": "#637D69"},
        legend={"orientation": "h", "x": .5, "xanchor": "center", "y": -.02, "yanchor": "bottom", "font": {"size": 10}},
        annotations=[
            {"text": f"<b>{total:,}</b>", "x": .5, "y": .65, "font": {"size": 32, "color": "#17342A"}, "showarrow": False},
            {"text": "total klaim", "x": .5, "y": .49, "font": {"size": 11, "color": "#899D8E"}, "showarrow": False},
        ],
    )
    return fig


def probability_bars(greenwashing_probability: float, low_probability: float | None = None) -> go.Figure:
    p = float(greenwashing_probability)
    low = float(low_probability) if low_probability is not None else 1 - p
    fig = go.Figure(go.Bar(
        x=[low, p], y=["Lower Evidentiary Risk", "Higher Evidentiary Risk"], orientation="h",
        marker={"color": ["#4C9967", "#E58C7D"], "cornerradius": 5},
        text=[f"{low:.1%}", f"{p:.1%}"], textposition="auto",
        hovertemplate="%{y}: %{x:.2%}<extra></extra>",
    ))
    fig.update_layout(
        height=170, margin={"l": 0, "r": 30, "t": 8, "b": 20}, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font={"family": "Segoe UI, sans-serif", "size": 11, "color": "#607D69"},
        xaxis={"range": [0, 1], "tickformat": ".0%", "gridcolor": "#EDF2EC", "fixedrange": True},
        yaxis={"fixedrange": True}, bargap=.52, showlegend=False,
    )
    return fig
