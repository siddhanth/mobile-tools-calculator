"""
Metrics display components for SIP Simulator.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List

from strategy import Strategy, SIPResult, simulate_sip
from data_fetcher import (
    get_nifty_data, get_nifty_pe_data, get_mf_nav_data,
    align_data, resample_to_weekly
)


def display_metrics(results: Dict[str, SIPResult], strategies: List[Strategy]):
    """Display metric cards for each strategy"""
    
    # Find winner (highest return %)
    winner = max(results.items(), key=lambda x: x[1].absolute_return_pct)[0]
    
    cols = st.columns(len(results))
    
    for i, (name, result) in enumerate(results.items()):
        with cols[i]:
            strategy = next((s for s in strategies if s.name == name), None)
            color = strategy.color if strategy else "#888"
            is_winner = name == winner
            
            # Header with strategy name
            if is_winner:
                st.markdown(f"### 🏆 {name}")
            else:
                st.markdown(f"### {name}")
            
            # Metrics using native Streamlit
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Invested", f"₹{result.total_invested:,.0f}")
            with col2:
                st.metric("Current Value", f"₹{result.current_value:,.0f}")
            
            col3, col4 = st.columns(2)
            with col3:
                st.metric("Return", f"{result.absolute_return_pct:+.1f}%")
            with col4:
                st.metric("XIRR", f"{result.xirr:.1f}%")
            
            st.caption(f"Avg Price: ₹{result.avg_buy_price:,.2f} | Units: {result.units_held:,.2f}")


def run_fund_comparison(mf_codes: List[str], start_date: str, end_date: str, 
                        base_amount: float, strategy: Strategy):
    """Run comparison of multiple mutual funds against Nifty 50"""
    
    # Fetch PE data first
    try:
        pe_data = get_nifty_pe_data(start_date, end_date)
    except Exception as e:
        st.error(f"Could not load PE data: {e}")
        return
    
    # Fetch Nifty 50 data
    try:
        nifty_data = get_nifty_data(start_date, end_date, interval="1wk")
        nifty_aligned = align_data(nifty_data, pe_data)
        nifty_result = simulate_sip(nifty_aligned, strategy, base_amount, 
                                    price_col='nifty_close', pe_col='pe')
    except Exception as e:
        st.error(f"Could not fetch Nifty data: {e}")
        return
    
    # Fetch each MF's data and run simulation
    fund_results = {"Nifty 50": nifty_result}
    fund_colors = {"Nifty 50": "#6366f1"}  # Indigo for Nifty
    
    color_palette = ["#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]  # Green, Amber, Red, Purple, Cyan
    
    for i, code in enumerate(mf_codes):
        try:
            mf_data = get_mf_nav_data(code, start_date, end_date)
            scheme_name = mf_data.attrs.get('scheme_name', f'Fund {code}')
            # Shorten name for display
            short_name = scheme_name[:30] + "..." if len(scheme_name) > 30 else scheme_name
            
            # Resample to weekly
            mf_weekly = resample_to_weekly(mf_data, 'date', 'nav')
            mf_weekly.columns = ['date', 'close']
            
            # Align with PE data (note: align_data renames to 'nifty_close')
            mf_aligned = align_data(mf_weekly, pe_data)
            
            if len(mf_aligned) > 0:
                mf_result = simulate_sip(mf_aligned, strategy, base_amount,
                                        price_col='nifty_close', pe_col='pe')
                fund_results[short_name] = mf_result
                fund_colors[short_name] = color_palette[i % len(color_palette)]
        except Exception as e:
            st.warning(f"Could not fetch data for {code}: {e}")
    
    if len(fund_results) <= 1:
        st.error("No mutual fund data could be fetched. Please check the scheme codes.")
        return
    
    st.success(f"Comparing {len(fund_results)} investments with **{strategy.name}** strategy")
    
    # Display comparison metrics
    st.subheader("📊 Fund vs Nifty Comparison")
    
    # Sort by returns
    sorted_funds = sorted(fund_results.items(), key=lambda x: x[1].absolute_return_pct, reverse=True)
    winner = sorted_funds[0][0]
    
    # Summary table
    comparison_data = []
    for name, result in sorted_funds:
        vs_nifty = result.absolute_return_pct - nifty_result.absolute_return_pct if name != "Nifty 50" else 0
        comparison_data.append({
            "Fund": f"🏆 {name}" if name == winner else name,
            "Invested": f"₹{result.total_invested:,.0f}",
            "Current Value": f"₹{result.current_value:,.0f}",
            "Return %": f"{result.absolute_return_pct:+.1f}%",
            "XIRR": f"{result.xirr:.1f}%",
            "vs Nifty": f"{vs_nifty:+.1f}%" if name != "Nifty 50" else "—"
        })
    
    st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)
    
    # Portfolio value chart
    st.subheader("📈 Portfolio Growth Comparison")
    
    fig = go.Figure()
    
    for name, result in sorted_funds:
        df = result.weekly_data
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['portfolio_value'],
            mode='lines',
            name=name,
            line=dict(color=fund_colors.get(name, '#888'), width=2 if name == "Nifty 50" else 2.5),
            hovertemplate=f"<b>{name}</b><br>Value: ₹%{{y:,.0f}}<extra></extra>"
        ))
    
    fig.update_layout(
        height=500,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        yaxis_title="Portfolio Value (₹)",
        hovermode='x unified'
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(128,128,128,0.2)')
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Return comparison bar chart
    st.subheader("📊 Return Comparison")
    
    fig_bar = go.Figure()
    
    names = [name for name, _ in sorted_funds]
    returns = [result.absolute_return_pct for _, result in sorted_funds]
    colors = [fund_colors.get(name, '#888') for name in names]
    
    fig_bar.add_trace(go.Bar(
        x=names,
        y=returns,
        marker_color=colors,
        text=[f"{r:+.1f}%" for r in returns],
        textposition='outside'
    ))
    
    fig_bar.update_layout(
        height=400,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title="Return %",
        showlegend=False
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)

