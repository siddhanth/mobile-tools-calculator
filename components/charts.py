"""
Chart components for SIP Simulator.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List

from strategy import Strategy, SIPResult


def create_portfolio_chart(results: Dict[str, SIPResult], strategies: List[Strategy]) -> go.Figure:
    """Create portfolio value comparison chart with PE zones"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("Portfolio Value Over Time", "Nifty PE Ratio")
    )
    
    # Color mapping
    colors = {s.name: s.color for s in strategies}
    
    # Sort results by current value (descending) for tooltip order
    sorted_results = sorted(results.items(), key=lambda x: x[1].current_value, reverse=True)
    
    # Add portfolio value lines (highest value first for tooltip ordering)
    for name, result in sorted_results:
        df = result.weekly_data
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['portfolio_value'],
                mode='lines',
                name=name,
                line=dict(color=colors.get(name, '#888'), width=2),
                hovertemplate=f"<b>{name}</b><br>" +
                              "Date: %{x}<br>" +
                              "Value: ₹%{y:,.0f}<br>" +
                              "<extra></extra>"
            ),
            row=1, col=1
        )
    
    # Get PE data from first result
    first_result = list(results.values())[0]
    pe_df = first_result.weekly_data
    
    # Add PE line
    fig.add_trace(
        go.Scatter(
            x=pe_df['date'],
            y=pe_df['pe'],
            mode='lines',
            name='Nifty PE',
            line=dict(color='#8b5cf6', width=2),
            hovertemplate="PE: %{y:.1f}<extra></extra>"
        ),
        row=2, col=1
    )
    
    # Add PE threshold lines
    for pe_level, color, label in [(20, '#22c55e', 'PE 20'), 
                                    (18, '#eab308', 'PE 18'), 
                                    (16, '#ef4444', 'PE 16')]:
        fig.add_hline(
            y=pe_level, row=2, col=1,
            line=dict(color=color, dash='dash', width=1),
            annotation_text=label,
            annotation_position="right"
        )
    
    # Update layout
    fig.update_layout(
        height=600,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=60, r=40, t=80, b=40),
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(title_text="Portfolio Value (₹)", row=1, col=1)
    fig.update_yaxes(title_text="PE Ratio", row=2, col=1)
    
    return fig


def create_investment_chart(results: Dict[str, SIPResult], strategies: List[Strategy]) -> go.Figure:
    """Create cumulative investment comparison chart"""
    
    fig = go.Figure()
    colors = {s.name: s.color for s in strategies}
    
    for name, result in results.items():
        df = result.weekly_data
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['cumulative_invested'],
                mode='lines',
                name=name,
                line=dict(color=colors.get(name, '#888'), width=2),
                fill='tozeroy',
                fillcolor=f"rgba{tuple(list(int(colors.get(name, '#888888').lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.1])}"
            )
        )
    
    fig.update_layout(
        title="Cumulative Investment Over Time",
        height=400,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title="Total Invested (₹)",
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    
    return fig


def create_multiplier_breakdown(results: Dict[str, SIPResult]) -> go.Figure:
    """Create bar chart showing weeks at each multiplier level"""
    
    data = []
    for name, result in results.items():
        data.append({
            'Strategy': name,
            '1x': result.weeks_at_1x,
            '2x': result.weeks_at_2x,
            '3x': result.weeks_at_3x,
            '4x+': result.weeks_at_4x_plus
        })
    
    df = pd.DataFrame(data)
    
    fig = go.Figure()
    
    colors = ['#6b7280', '#22c55e', '#f59e0b', '#ef4444']
    for i, mult in enumerate(['1x', '2x', '3x', '4x+']):
        fig.add_trace(go.Bar(
            name=mult,
            x=df['Strategy'],
            y=df[mult],
            marker_color=colors[i]
        ))
    
    fig.update_layout(
        title="Weeks at Each Multiplier Level",
        barmode='stack',
        height=350,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title="Number of Weeks",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
    )
    
    return fig

