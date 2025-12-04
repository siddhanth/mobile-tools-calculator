"""
US Markets Tab - Live US Market Overview and Valuations
Similar to Dashboard tab but for US markets (S&P 500, NASDAQ, Russell 2000)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

from us_data_fetcher import (
    get_all_us_indices_pe_pb,
    get_fear_greed_index,
    get_us_pe_history_for_chart,
    get_us_price_history_for_chart,
    get_us_sector_performance,
    get_vix_data,
    scrape_shiller_pe,
    US_PE_BENCHMARKS,
)


def render_us_markets_tab():
    """Render the US Markets tab content."""
    
    st.subheader("🇺🇸 US Markets Overview")
    
    try:
        # Market Sentiment Section
        _render_fear_greed_gauge()
        
        st.divider()
        
        # Current Valuations
        _render_us_valuations()
        
        st.divider()
        
        # VIX and Shiller PE Section
        _render_volatility_section()
        
        st.divider()
        
        # Historical Trends
        _render_us_trend_charts()
        
        st.divider()
        
        # Sector Performance
        _render_sector_performance()
        
        # Data Sources Footer
        st.markdown("---")
        st.caption("""
        **Data Sources:** Yahoo Finance (via yfinance) for index prices and ETF data | 
        Fear & Greed Index is calculated using VIX, momentum, and 52-week high proximity |
        PE ratios from ETF proxies (SPY, QQQ, IWM)
        
        ⚠️ *US market PE data is estimated from ETF data. For precise valuations, refer to official sources.*
        """)
        
    except Exception as e:
        st.error(f"Could not load US market data: {e}")
        st.info("Please check your internet connection and try again.")


def _render_fear_greed_gauge():
    """Render the Fear & Greed sentiment gauge (inspired by CNN)."""
    
    st.markdown("### 🎯 Market Sentiment (Fear & Greed)")
    
    # Get Fear & Greed data
    fg_data = get_fear_greed_index()
    score = fg_data.get('score', 50)
    sentiment = fg_data.get('sentiment', 'Neutral')
    sentiment_color = fg_data.get('color', '#eab308')
    
    # Color definitions for gauge segments
    COLOR_EXTREME_FEAR = "#dc2626"  # Red
    COLOR_FEAR = "#f97316"          # Orange  
    COLOR_NEUTRAL = "#eab308"       # Yellow
    COLOR_GREED = "#22c55e"         # Light Green
    COLOR_EXTREME_GREED = "#16a34a" # Dark Green
    
    # Create gauge chart
    gauge_fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'font': {'size': 48, 'color': sentiment_color}, 'suffix': '', 'valueformat': '.0f'},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "#64748b",
                     'tickfont': {'color': '#94a3b8', 'size': 12},
                     'tickvals': [0, 25, 50, 75, 100]},
            'bar': {'color': 'rgba(0,0,0,0)', 'thickness': 0},
            'bgcolor': "#1e293b",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 20], 'color': COLOR_EXTREME_FEAR},
                {'range': [20, 40], 'color': COLOR_FEAR},
                {'range': [40, 60], 'color': COLOR_NEUTRAL},
                {'range': [60, 80], 'color': COLOR_GREED},
                {'range': [80, 100], 'color': COLOR_EXTREME_GREED},
            ],
            'threshold': {
                'line': {'color': "#1e293b", 'width': 6},
                'thickness': 0.85,
                'value': score
            }
        }
    ))
    
    gauge_fig.update_layout(
        height=320,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#f8fafc'},
        margin=dict(l=40, r=40, t=40, b=80)
    )
    
    # Add text annotations on the arc
    radius = 0.38
    
    # EXTREME FEAR
    ef_angle = math.radians(162)
    gauge_fig.add_annotation(
        x=0.5 + radius * math.cos(ef_angle),
        y=0.5 + radius * math.sin(ef_angle) - 0.05,
        text="<b>EXTREME<br>FEAR</b>",
        showarrow=False,
        font=dict(size=8, color="white", family="Arial"),
        textangle=-70
    )
    
    # FEAR
    fear_angle = math.radians(126)
    gauge_fig.add_annotation(
        x=0.5 + radius * math.cos(fear_angle),
        y=0.5 + radius * math.sin(fear_angle) - 0.05,
        text="<b>FEAR</b>",
        showarrow=False,
        font=dict(size=9, color="white", family="Arial"),
        textangle=-40
    )
    
    # NEUTRAL
    neutral_angle = math.radians(90)
    gauge_fig.add_annotation(
        x=0.5 + radius * math.cos(neutral_angle),
        y=0.5 + radius * math.sin(neutral_angle) - 0.05,
        text="<b>NEUTRAL</b>",
        showarrow=False,
        font=dict(size=9, color="white", family="Arial"),
        textangle=0
    )
    
    # GREED
    greed_angle = math.radians(54)
    gauge_fig.add_annotation(
        x=0.5 + radius * math.cos(greed_angle),
        y=0.5 + radius * math.sin(greed_angle) - 0.05,
        text="<b>GREED</b>",
        showarrow=False,
        font=dict(size=9, color="white", family="Arial"),
        textangle=40
    )
    
    # EXTREME GREED
    eg_angle = math.radians(18)
    gauge_fig.add_annotation(
        x=0.5 + radius * math.cos(eg_angle),
        y=0.5 + radius * math.sin(eg_angle) - 0.05,
        text="<b>EXTREME<br>GREED</b>",
        showarrow=False,
        font=dict(size=8, color="white", family="Arial"),
        textangle=70
    )
    
    # Display gauge and info
    gauge_col1, gauge_col2 = st.columns([2, 1])
    
    with gauge_col1:
        st.plotly_chart(gauge_fig, use_container_width=True)
    
    with gauge_col2:
        vix = fg_data.get('vix', 20)
        momentum = fg_data.get('momentum', 0)
        high_prox = fg_data.get('high_proximity', 90)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%); 
                    border-radius: 12px; padding: 20px; margin-top: 20px;
                    border: 1px solid #2d4a6f;">
            <h4 style="color: #f8fafc; margin: 0 0 10px 0;">📊 Current Status</h4>
            <div style="font-size: 24px; font-weight: bold; color: {sentiment_color}; margin: 10px 0;">
                {sentiment}
            </div>
            <div style="color: #94a3b8; font-size: 12px;">
                <p>• Score: {score:.0f}/100</p>
                <p>• VIX: {vix:.1f}</p>
                <p>• 50-Day Momentum: {momentum:+.1f}%</p>
                <p>• 52-Week High: {high_prox:.0f}%</p>
            </div>
            <div style="font-size: 10px; color: #64748b; margin-top: 10px;">
                <p style="color: {COLOR_EXTREME_FEAR};">• Extreme Fear: 0-20</p>
                <p style="color: {COLOR_FEAR};">• Fear: 20-40</p>
                <p style="color: {COLOR_NEUTRAL};">• Neutral: 40-60</p>
                <p style="color: {COLOR_GREED};">• Greed: 60-80</p>
                <p style="color: {COLOR_EXTREME_GREED};">• Extreme Greed: 80-100</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.caption("*Calculated using VIX, market momentum, and 52-week high proximity (inspired by CNN Fear & Greed Index)*")


def _render_us_valuations():
    """Render current valuation cards for US indices."""
    
    st.markdown("### 📊 US Market Valuations")
    st.markdown("*PE ratios from ETF proxies (SPY, QQQ, IWM)*")
    
    all_indices = get_all_us_indices_pe_pb()
    
    idx_cols = st.columns(3)
    index_display = {
        "sp500": ("S&P 500", "🔵"),
        "nasdaq": ("NASDAQ", "🟣"),
        "russell2000": ("Russell 2000", "🟠"),
    }
    
    for i, (idx_key, (idx_name, emoji)) in enumerate(index_display.items()):
        with idx_cols[i]:
            idx_data = all_indices.get(idx_key, {})
            
            if 'error' in idx_data and not idx_data.get('pe'):
                st.warning(f"{idx_name}: Data unavailable")
            else:
                pe = idx_data.get('pe', 0)
                pb = idx_data.get('pb')
                div_yield = idx_data.get('div_yield', 0)
                zone = idx_data.get('zone', 'Unknown')
                zone_color = idx_data.get('zone_color', '#888')
                thresholds = idx_data.get('thresholds', {})
                median = thresholds.get('median', 0)
                price = idx_data.get('price')
                change_pct = idx_data.get('change_pct')
                
                price_display = f"${price:,.2f}" if price else "N/A"
                change_display = f"{change_pct:+.2f}%" if change_pct else ""
                change_color = "#22c55e" if change_pct and change_pct >= 0 else "#ef4444"
                
                st.markdown(f"""
                <div class="metric-card" style="text-align: center; border-top: 4px solid {zone_color};">
                    <h3 style="color: #f8fafc; margin: 0;">{emoji} {idx_name}</h3>
                    <div style="font-size: 14px; color: #94a3b8; margin: 5px 0;">
                        {price_display} <span style="color: {change_color};">{change_display}</span>
                    </div>
                    <div style="font-size: 40px; font-weight: bold; color: {zone_color}; margin: 8px 0;">
                        {pe:.1f}
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">PE Ratio</div>
                    <div style="background: {zone_color}; color: white; padding: 6px 16px; border-radius: 20px; display: inline-block; font-weight: bold; margin-top: 8px;">
                        {zone}
                    </div>
                    <div style="display: flex; justify-content: space-around; margin-top: 12px; font-size: 12px; color: #94a3b8;">
                        <div>
                            <div>PB</div>
                            <div style="font-weight: bold; color: #f8fafc;">{pb:.2f if pb else 'N/A'}</div>
                        </div>
                        <div>
                            <div>Div%</div>
                            <div style="font-weight: bold; color: #f8fafc;">{div_yield:.2f}</div>
                        </div>
                        <div>
                            <div>Med PE</div>
                            <div style="font-weight: bold; color: #f8fafc;">{median:.1f}</div>
                        </div>
                    </div>
                    <div style="font-size: 10px; color: #64748b; margin-top: 8px;">
                        P10: {thresholds.get('p10', 0):.0f} | 
                        P25: {thresholds.get('p25', 0):.0f} | 
                        P75: {thresholds.get('p75', 0):.0f} | 
                        P90: {thresholds.get('p90', 0):.0f}
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _render_volatility_section():
    """Render VIX and Shiller PE section."""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📈 VIX (Volatility Index)")
        
        vix_data = get_vix_data()
        vix_current = vix_data.get('current', 20)
        vix_color = vix_data.get('color', '#eab308')
        vix_interpretation = vix_data.get('interpretation', 'Normal')
        
        st.markdown(f"""
        <div class="metric-card" style="text-align: center; border-left: 4px solid {vix_color};">
            <div style="font-size: 48px; font-weight: bold; color: {vix_color};">
                {vix_current:.1f}
            </div>
            <div style="background: {vix_color}; color: white; padding: 4px 12px; border-radius: 15px; display: inline-block; margin: 8px 0;">
                {vix_interpretation}
            </div>
            <div style="color: #94a3b8; font-size: 12px; margin-top: 10px;">
                <p>1M Avg: {vix_data.get('avg_1m', 0):.1f} | 
                   High: {vix_data.get('high_1m', 0):.1f} | 
                   Low: {vix_data.get('low_1m', 0):.1f}</p>
            </div>
            <div style="font-size: 10px; color: #64748b; margin-top: 8px;">
                VIX &lt;12: Complacency | 12-17: Calm | 17-22: Normal | 22-30: Concern | &gt;30: Fear
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 Shiller PE (CAPE)")
        
        shiller_data = scrape_shiller_pe()
        cape = shiller_data.get('cape', 30)
        
        # Determine CAPE valuation
        if cape < 15:
            cape_zone = "Very Cheap"
            cape_color = "#22c55e"
        elif cape < 20:
            cape_zone = "Cheap"
            cape_color = "#86efac"
        elif cape < 25:
            cape_zone = "Fair"
            cape_color = "#eab308"
        elif cape < 30:
            cape_zone = "Expensive"
            cape_color = "#f97316"
        else:
            cape_zone = "Very Expensive"
            cape_color = "#ef4444"
        
        st.markdown(f"""
        <div class="metric-card" style="text-align: center; border-left: 4px solid {cape_color};">
            <div style="font-size: 48px; font-weight: bold; color: {cape_color};">
                {cape:.1f}
            </div>
            <div style="background: {cape_color}; color: white; padding: 4px 12px; border-radius: 15px; display: inline-block; margin: 8px 0;">
                {cape_zone}
            </div>
            <div style="color: #94a3b8; font-size: 12px; margin-top: 10px;">
                <p>Historical Median: {shiller_data.get('historical_median', 16.0):.1f} | 
                   Mean: {shiller_data.get('historical_mean', 17.1):.1f}</p>
            </div>
            <div style="font-size: 10px; color: #64748b; margin-top: 8px;">
                CAPE (Cyclically Adjusted PE) uses 10-year avg earnings | Source: multpl.com
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_us_trend_charts():
    """Render historical PE and price trend charts for US indices."""
    
    st.subheader("📈 Historical Trends")
    
    # Controls row
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 2])
    with ctrl_col1:
        chart_years = st.selectbox(
            "Time period:", 
            [1, 3, 5, 10], 
            index=2, 
            format_func=lambda x: f"{x} Year{'s' if x > 1 else ''}",
            key="us_chart_years"
        )
    with ctrl_col2:
        show_price_chart = st.checkbox("📈 Show Index Prices", value=True, key="us_show_prices")
    
    # Index visibility toggles
    st.markdown("**Show/Hide Indices:**")
    toggle_cols = st.columns(3)
    with toggle_cols[0]:
        show_sp500 = st.checkbox("🔵 S&P 500", value=True, key="us_show_sp500")
    with toggle_cols[1]:
        show_nasdaq = st.checkbox("🟣 NASDAQ", value=True, key="us_show_nasdaq")
    with toggle_cols[2]:
        show_russell = st.checkbox("🟠 Russell 2000", value=True, key="us_show_russell")
    
    try:
        # Get price history
        price_history = get_us_price_history_for_chart(years=chart_years)
        
        if price_history is not None and not price_history.empty:
            colors = {
                'S&P 500': '#3b82f6',       # Blue
                'NASDAQ': '#a855f7',         # Purple
                'Russell 2000': '#f97316',   # Orange
            }
            
            visibility = {
                'S&P 500': show_sp500,
                'NASDAQ': show_nasdaq,
                'Russell 2000': show_russell,
            }
            
            if show_price_chart:
                # Create price chart
                fig = go.Figure()
                
                for idx_name in ['S&P 500', 'NASDAQ', 'Russell 2000']:
                    if not visibility.get(idx_name, True):
                        continue
                    value_col = f'{idx_name} Value'
                    if value_col in price_history.columns:
                        fig.add_trace(go.Scatter(
                            x=price_history['date'],
                            y=price_history[value_col],
                            mode='lines',
                            name=idx_name,
                            line=dict(color=colors.get(idx_name, '#888'), width=2),
                            hovertemplate=f"{idx_name}<br>Date: %{{x}}<br>Value: %{{y:,.0f}}<extra></extra>"
                        ))
                
                fig.update_layout(
                    title="US Index Values Over Time",
                    height=450,
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="Index Value",
                    xaxis_title="Date",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=60, b=40),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # PE Trend Chart (estimated)
            pe_history = get_us_pe_history_for_chart(years=chart_years)
            
            if pe_history is not None and not pe_history.empty:
                st.markdown("#### Estimated PE Trends")
                st.caption("*Note: PE values are estimated from price movements and historical benchmarks*")
                
                fig_pe = go.Figure()
                
                for idx_name in ['S&P 500', 'NASDAQ', 'Russell 2000']:
                    if not visibility.get(idx_name, True):
                        continue
                    if idx_name in pe_history.columns:
                        fig_pe.add_trace(go.Scatter(
                            x=pe_history['date'],
                            y=pe_history[idx_name],
                            mode='lines',
                            name=idx_name,
                            line=dict(color=colors.get(idx_name, '#888'), width=2),
                            hovertemplate=f"{idx_name}<br>Date: %{{x}}<br>Est. PE: %{{y:.1f}}<extra></extra>"
                        ))
                
                # Add median lines
                for idx_name in ['S&P 500', 'NASDAQ', 'Russell 2000']:
                    if not visibility.get(idx_name, True):
                        continue
                    idx_key = idx_name.lower().replace(' ', '').replace('&', '')
                    if idx_key == 'sp500':
                        idx_key = 'sp500'
                    elif idx_key == 'nasdaq':
                        idx_key = 'nasdaq'
                    else:
                        idx_key = 'russell2000'
                    
                    benchmarks = US_PE_BENCHMARKS.get(idx_key, {})
                    median = benchmarks.get('median', 20)
                    
                    fig_pe.add_hline(
                        y=median,
                        line=dict(color=colors.get(idx_name, '#888'), dash='dot', width=1),
                        annotation_text=f"{idx_name} Median",
                        annotation_position="right"
                    )
                
                fig_pe.update_layout(
                    height=400,
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="Estimated PE Ratio",
                    xaxis_title="Date",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=40, b=40),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_pe, use_container_width=True)
        else:
            st.warning("Could not load historical data")
    
    except Exception as e:
        st.warning(f"Could not load trend charts: {e}")


def _render_sector_performance():
    """Render US sector ETF performance table."""
    
    st.subheader("📊 Sector Performance (ETFs)")
    
    try:
        sector_df = get_us_sector_performance()
        
        if sector_df is not None and not sector_df.empty:
            # Style the dataframe
            def color_returns(val):
                if pd.isna(val):
                    return ''
                if val > 0:
                    return 'color: #22c55e'
                elif val < 0:
                    return 'color: #ef4444'
                return ''
            
            # Display columns
            display_df = sector_df[['symbol', 'sector', 'price', 'pe', '1d_return', '1w_return', '1m_return', 'ytd_return']].copy()
            display_df.columns = ['Symbol', 'Sector', 'Price', 'PE', '1D %', '1W %', '1M %', 'YTD %']
            
            # Sort by YTD return
            display_df = display_df.sort_values('YTD %', ascending=False)
            
            st.dataframe(
                display_df.style.map(
                    color_returns, 
                    subset=['1D %', '1W %', '1M %', 'YTD %']
                ),
                use_container_width=True,
                hide_index=True
            )
            
            # Sector performance bar chart
            st.markdown("#### YTD Sector Returns")
            
            fig = go.Figure()
            
            colors_list = ['#22c55e' if x >= 0 else '#ef4444' for x in display_df['YTD %']]
            
            fig.add_trace(go.Bar(
                x=display_df['Sector'],
                y=display_df['YTD %'],
                marker_color=colors_list,
                text=[f"{x:+.1f}%" for x in display_df['YTD %']],
                textposition='outside'
            ))
            
            fig.update_layout(
                height=400,
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_title="YTD Return %",
                xaxis_tickangle=-45,
                margin=dict(l=40, r=40, t=20, b=100),
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sector performance data not available")
    
    except Exception as e:
        st.warning(f"Could not load sector data: {e}")


# Valuation Zone Legend
def _render_valuation_legend():
    """Render valuation zone definitions."""
    
    st.markdown("### 📋 Valuation Zone Definitions")
    st.markdown("""
    | Zone | S&P 500 PE | Interpretation |
    |------|------------|----------------|
    | **Very Cheap** | < 13 | Extremely undervalued, rare opportunity |
    | **Cheap** | 13-15.5 | Undervalued, good entry point |
    | **Fair** | 15.5-23 | Normal valuation |
    | **Expensive** | 23-28 | Overvalued, exercise caution |
    | **Very Expensive** | > 28 | Extremely overvalued, high risk |
    
    *Based on historical S&P 500 PE distribution*
    """)



