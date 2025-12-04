"""
Dashboard Tab - Live Investment Recommendations and Market Sentiment
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import math

from data_fetcher import (
    get_all_indices_pe, get_all_indices_pe_pb, get_current_nifty_pe,
    get_pe_history_for_chart, get_pe_price_history_for_chart
)
from strategy import PRESET_STRATEGIES, get_current_recommendation


def render_dashboard_tab(base_amount: float = 5000):
    """Render the Dashboard tab content."""
    
    st.subheader("🔴 Live Investment Recommendation")
    
    try:
        # Use cached data for instant display, then refresh in background
        all_indices = get_all_indices_pe()  # Uses disk cache if available
        
        # Get Nifty 50 PE for the sentiment gauge
        nifty_data = all_indices.get('nifty50', {})
        current_pe = nifty_data.get('pe', 22)
        pe_thresholds = nifty_data.get('thresholds', {})
        
        # Cache for other tabs
        st.session_state['cached_nifty_pe'] = current_pe
        st.session_state['cached_all_indices'] = all_indices
        
        # Market Sentiment Gauge (inspired by ExitMantra)
        st.markdown("### 🎯 Market Sentiment Gauge")
        
        # ExitMantra-style color codes
        COLOR_PANIC = "#E53935"      # Red
        COLOR_PESSIMISM = "#FF9800"  # Orange
        COLOR_OPTIMISM = "#29B6F6"   # Light Blue
        COLOR_EUPHORIA = "#4CAF50"   # Green
        
        # PE thresholds for zones (fixed for consistency with ExitMantra)
        pe_panic = 18
        pe_pessimism = 21
        pe_optimism = 25
        
        # Determine sentiment zone
        if current_pe < pe_panic:
            sentiment = "Panic"
            sentiment_color = COLOR_PANIC
        elif current_pe < pe_pessimism:
            sentiment = "Pessimism"
            sentiment_color = COLOR_PESSIMISM
        elif current_pe < pe_optimism:
            sentiment = "Optimism"
            sentiment_color = COLOR_OPTIMISM
        else:
            sentiment = "Euphoria"
            sentiment_color = COLOR_EUPHORIA
        
        # Create gauge chart with needle
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=current_pe,
            domain={'x': [0, 1], 'y': [0, 1]},
            number={'font': {'size': 48, 'color': sentiment_color}, 'suffix': '', 'valueformat': '.1f'},
            gauge={
                'axis': {'range': [10, 40], 'tickwidth': 2, 'tickcolor': "#64748b", 
                         'tickfont': {'color': '#94a3b8', 'size': 12},
                         'tickvals': [10, 20, 30, 40]},
                'bar': {'color': 'rgba(0,0,0,0)', 'thickness': 0},  # Hide default bar
                'bgcolor': "#1e293b",
                'borderwidth': 0,
                'steps': [
                    {'range': [10, pe_panic], 'color': COLOR_PANIC},      # PANIC - Red
                    {'range': [pe_panic, pe_pessimism], 'color': COLOR_PESSIMISM},  # PESSIMISM - Orange
                    {'range': [pe_pessimism, pe_optimism], 'color': COLOR_OPTIMISM},  # OPTIMISM - Blue
                    {'range': [pe_optimism, 40], 'color': COLOR_EUPHORIA}   # EUPHORIA - Green
                ],
                'threshold': {
                    'line': {'color': "#1e293b", 'width': 6},
                    'thickness': 0.85,
                    'value': current_pe
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
        
        # Add text annotations positioned ON the colored arc segments
        radius = 0.38
        
        # PANIC - at ~25 degrees from left
        panic_angle = math.radians(155)
        gauge_fig.add_annotation(
            x=0.5 + radius * math.cos(panic_angle),
            y=0.5 + radius * math.sin(panic_angle) - 0.05,
            text="<b>PANIC</b>",
            showarrow=False,
            font=dict(size=10, color="white", family="Arial"),
            textangle=-60
        )
        
        # PESSIMISM
        pess_angle = math.radians(125)
        gauge_fig.add_annotation(
            x=0.5 + radius * math.cos(pess_angle),
            y=0.5 + radius * math.sin(pess_angle) - 0.05,
            text="<b>PESSIMISM</b>",
            showarrow=False,
            font=dict(size=9, color="white", family="Arial"),
            textangle=-30
        )
        
        # OPTIMISM
        opt_angle = math.radians(55)
        gauge_fig.add_annotation(
            x=0.5 + radius * math.cos(opt_angle),
            y=0.5 + radius * math.sin(opt_angle) - 0.05,
            text="<b>OPTIMISM</b>",
            showarrow=False,
            font=dict(size=9, color="white", family="Arial"),
            textangle=30
        )
        
        # EUPHORIA
        euph_angle = math.radians(25)
        gauge_fig.add_annotation(
            x=0.5 + radius * math.cos(euph_angle),
            y=0.5 + radius * math.sin(euph_angle) - 0.05,
            text="<b>EUPHORIA</b>",
            showarrow=False,
            font=dict(size=10, color="white", family="Arial"),
            textangle=60
        )
        
        gauge_col1, gauge_col2 = st.columns([2, 1])
        with gauge_col1:
            st.plotly_chart(gauge_fig, use_container_width=True)
        with gauge_col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%); 
                        border-radius: 12px; padding: 20px; margin-top: 20px;
                        border: 1px solid #2d4a6f;">
                <h4 style="color: #f8fafc; margin: 0 0 10px 0;">📊 Current Status</h4>
                <div style="font-size: 24px; font-weight: bold; color: {sentiment_color}; margin: 10px 0;">
                    {sentiment}
                </div>
                <div style="color: #94a3b8; font-size: 12px;">
                    <p>• PE: {current_pe:.1f} (Median: {nifty_data.get('median', 22):.1f})</p>
                    <p style="color: {COLOR_PANIC};">• Panic Zone: PE &lt; {pe_panic}</p>
                    <p style="color: {COLOR_PESSIMISM};">• Pessimism: PE {pe_panic}-{pe_pessimism}</p>
                    <p style="color: {COLOR_OPTIMISM};">• Optimism: PE {pe_pessimism}-{pe_optimism}</p>
                    <p style="color: {COLOR_EUPHORIA};">• Euphoria: PE &gt; {pe_optimism}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.caption("*Inspired by [ExitMantra](https://exitmantra.com/) Market Sentiment Gauge*")
        
        st.divider()
        
        # Display all three indices
        st.markdown("### 📊 Market Valuation Dashboard")
        st.markdown("*Valuation zones are calculated using median and standard deviation from historical data*")
        
        idx_cols = st.columns(3)
        index_names = {
            "nifty50": ("Nifty 50", "🔵"),
            "nifty_midcap": ("Nifty Midcap 50", "🟡"),
            "nifty_smallcap": ("Nifty Smallcap 250", "🟢"),
        }
        
        for i, (idx_key, (idx_name, emoji)) in enumerate(index_names.items()):
            with idx_cols[i]:
                idx_data = all_indices.get(idx_key, {})
                if 'error' in idx_data:
                    st.warning(f"{idx_name}: Data unavailable")
                else:
                    pe = idx_data.get('pe', 0)
                    zone = idx_data.get('zone', 'Unknown')
                    zone_color = idx_data.get('zone_color', '#888')
                    thresholds = idx_data.get('thresholds', {})
                    median = idx_data.get('median', 0)
                    std = idx_data.get('std', 0)
                    
                    st.markdown(f"""
                    <div class="metric-card" style="text-align: center; border-top: 4px solid {zone_color};">
                        <h3 style="color: #f8fafc; margin: 0;">{emoji} {idx_name}</h3>
                        <div style="font-size: 48px; font-weight: bold; color: {zone_color}; margin: 10px 0;">
                            {pe:.1f}
                        </div>
                        <div style="background: {zone_color}; color: white; padding: 6px 16px; border-radius: 20px; display: inline-block; font-weight: bold;">
                            {zone}
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 10px;">
                            Median: {median:.1f} | Std: {std:.1f}
                        </div>
                        <div style="font-size: 10px; color: #64748b; margin-top: 5px;">
                            P10: {thresholds.get('p10', thresholds.get('too_cheap', 0)):.0f} | 
                            P25: {thresholds.get('p25', thresholds.get('cheap', 0)):.0f} | 
                            P75: {thresholds.get('p75', thresholds.get('expensive', 0)):.0f} | 
                            P90: {thresholds.get('p90', thresholds.get('too_expensive', 0)):.0f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Combined PE + PB Valuation Section
        _render_pe_pb_section(index_names)
        
        st.divider()
        
        # Get Nifty 50 specific data for recommendations
        current_pe_info = get_current_nifty_pe()
        current_pe = current_pe_info['pe']
        pe_date = current_pe_info['date']
        days_old = current_pe_info['days_old']
        
        # Data update status
        update_col1, update_col2 = st.columns([2, 1])
        with update_col1:
            if days_old == 0:
                st.success(f"📅 Data is current: {pe_date.strftime('%d %b %Y')} (Today)")
            elif days_old == 1:
                st.info(f"📅 Last updated: {pe_date.strftime('%d %b %Y')} (Yesterday)")
            else:
                st.warning(f"📅 Last updated: {pe_date.strftime('%d %b %Y')} ({days_old} days ago)")
        with update_col2:
            with st.expander("ℹ️ How data updates"):
                st.markdown("""
                **Auto-updates:**
                - PE data fetches from NSE daily
                - Sector data cached & refreshed daily
                - Just refresh the page for latest data
                
                **No manual action needed!**
                """)
        
        st.divider()
        
        # Recommendations for each strategy
        st.subheader(f"💰 This Week's Investment (Base: ₹{base_amount:,})")
        
        recommendations = get_current_recommendation(
            current_pe, 
            base_amount,
            list(PRESET_STRATEGIES.values())
        )
        
        cols = st.columns(4)
        for i, (name, rec) in enumerate(recommendations.items()):
            with cols[i]:
                strategy = PRESET_STRATEGIES.get(name.lower().replace(" ", "_"))
                color = strategy.color if strategy else "#888"
                
                st.markdown(f"""
                <div class="metric-card" style="border-left: 4px solid {color}; text-align: center;">
                    <h4 style="color: {color}; margin: 0;">{name}</h4>
                    <div style="font-size: 32px; font-weight: bold; color: #f8fafc; margin: 10px 0;">
                        ₹{rec['investment']:,.0f}
                    </div>
                    <div style="background: {color}; color: white; padding: 4px 8px; border-radius: 4px; display: inline-block;">
                        {rec['multiplier']}x
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        st.divider()
        
        # Historical PE Trend Chart
        _render_pe_trend_chart(all_indices, index_names)
        
        # Valuation Zone Legend
        st.markdown("### 📋 Valuation Zone Definitions")
        st.markdown("""
        | Zone | Definition | Interpretation |
        |------|------------|----------------|
        | **Too Cheap** | Below 10th percentile (P10) | Extremely undervalued, rare buying opportunity |
        | **Cheap** | Between P10 and P25 | Undervalued, good entry point |
        | **Fair** | Between P25 and P75 (interquartile range) | Normal valuation, typical market |
        | **Expensive** | Between P75 and P90 | Overvalued, exercise caution |
        | **Too Expensive** | Above 90th percentile (P90) | Extremely overvalued, high risk |
        
        *Percentiles based on historical PE distribution - more robust for volatile data*
        """)
            
    except Exception as e:
        st.error(f"Could not load current PE data: {e}")
        st.info("Make sure the PE data CSV files exist in the app directory.")


def _render_pe_pb_section(index_names):
    """Render the Combined PE + PB Valuation section."""
    st.markdown("### 📈 Combined PE + PB Valuation")
    st.caption("*Combined Score = (PE Percentile × 60%) + (PB Percentile × 40%)*")
    
    try:
        pe_pb_data = get_all_indices_pe_pb()
        
        if pe_pb_data and 'error' not in pe_pb_data:
            pb_cols = st.columns(3)
            for i, (idx_key, (idx_name, emoji)) in enumerate(index_names.items()):
                idx_pb = pe_pb_data.get(idx_key, {})
                with pb_cols[i]:
                    if 'error' in idx_pb:
                        st.markdown(f"""
                        <div class="metric-card" style="text-align: center; border-top: 4px solid #666;">
                            <h4 style="color: #f8fafc; margin: 0 0 8px 0;">{emoji} {idx_name}</h4>
                            <div style="color: #94a3b8; font-size: 12px;">Data unavailable</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        combined_zone = idx_pb.get('combined_zone', 'Unknown')
                        combined_color = idx_pb.get('combined_color', '#888')
                        combined_pct = idx_pb.get('combined_percentile', 50)
                        pb = idx_pb.get('pb', 0)
                        div_yield = idx_pb.get('div_yield', 0)
                        
                        st.markdown(f"""
                        <div class="metric-card" style="text-align: center; border-top: 4px solid {combined_color};">
                            <h4 style="color: #f8fafc; margin: 0 0 8px 0;">{emoji} {idx_name}</h4>
                            <div style="display: flex; justify-content: space-around; margin-bottom: 8px;">
                                <div>
                                    <div style="font-size: 11px; color: #94a3b8;">PE</div>
                                    <div style="font-size: 18px; font-weight: bold; color: #f8fafc;">{idx_pb.get('pe', 0):.1f}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: #94a3b8;">PB</div>
                                    <div style="font-size: 18px; font-weight: bold; color: #f8fafc;">{pb:.2f}</div>
                                </div>
                                <div>
                                    <div style="font-size: 11px; color: #94a3b8;">Div%</div>
                                    <div style="font-size: 18px; font-weight: bold; color: #f8fafc;">{div_yield:.1f}</div>
                                </div>
                            </div>
                            <div style="background: {combined_color}; color: white; padding: 4px 12px; border-radius: 15px; display: inline-block; font-size: 12px; font-weight: bold;">
                                {combined_zone} ({combined_pct:.0f}%)
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            error_msg = pe_pb_data.get('error', 'Unknown error') if pe_pb_data else 'No data returned'
            st.warning(f"⚠️ Could not fetch PE/PB data: {error_msg}")
    except Exception as e:
        st.warning(f"⚠️ Error loading PE/PB data: {str(e)}")


def _render_pe_trend_chart(all_indices, index_names):
    """Render the Historical PE Trend Chart."""
    st.subheader("📈 Historical PE Trend (All Indices)")
    
    # Controls row
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1, 1, 1, 1])
    with ctrl_col1:
        chart_years = st.selectbox("Select time period:", [1, 3, 5, 10], index=3, format_func=lambda x: f"{x} Year{'s' if x > 1 else ''}")
    with ctrl_col2:
        use_log_scale = st.checkbox("📐 Log Scale", value=False, help="Use logarithmic scale for better comparison when values differ greatly")
    with ctrl_col3:
        show_index_values = st.checkbox("📈 Show Index Values", value=False, help="Show index price values alongside PE ratios")
    
    # Index visibility toggles
    st.markdown("**Show/Hide Indices:**")
    toggle_cols = st.columns(3)
    with toggle_cols[0]:
        show_nifty50 = st.checkbox("🔵 Nifty 50", value=True, key="show_nifty50")
    with toggle_cols[1]:
        show_midcap = st.checkbox("🟡 Nifty Midcap 50", value=True, key="show_midcap")
    with toggle_cols[2]:
        show_smallcap = st.checkbox("🟢 Nifty Smallcap 250", value=True, key="show_smallcap")
    
    # Debug expander for troubleshooting
    with st.expander("🔧 Debug Info (click to expand)", expanded=False):
        debug_container = st.container()
    
    try:
        # Fetch data based on whether we need index values
        if show_index_values:
            with debug_container:
                st.write("📊 Fetching PE + Price data...")
            pe_price_history = get_pe_price_history_for_chart(years=chart_years)
            with debug_container:
                if pe_price_history is None:
                    st.error("❌ pe_price_history returned None")
                elif pe_price_history.empty:
                    st.warning(f"⚠️ pe_price_history is empty")
                else:
                    st.success(f"✅ Loaded {len(pe_price_history)} rows")
                    st.write(f"Columns: {pe_price_history.columns.tolist()}")
                    value_cols = [c for c in pe_price_history.columns if 'Value' in c]
                    st.write(f"Value columns found: {value_cols}")
                    if value_cols:
                        st.write(f"Sample values: {pe_price_history[value_cols].head(2).to_dict()}")
        else:
            pe_price_history = None
        
        pe_history = get_pe_history_for_chart(years=chart_years)
        with debug_container:
            if pe_history is None:
                st.error("❌ pe_history returned None")
            elif pe_history.empty:
                st.warning("⚠️ pe_history is empty")
            else:
                st.success(f"✅ PE history: {len(pe_history)} rows, columns: {pe_history.columns.tolist()}")
        
        if pe_history is not None and not pe_history.empty:
            colors = {
                'Nifty 50': '#8b5cf6',
                'Nifty Midcap 50': '#f59e0b',
                'Nifty Smallcap 250': '#22c55e'
            }
            
            # Map checkboxes to column names
            visibility = {
                'Nifty 50': show_nifty50,
                'Nifty Midcap 50': show_midcap,
                'Nifty Smallcap 250': show_smallcap
            }
            
            if show_index_values:
                if pe_price_history is None or pe_price_history.empty:
                    st.warning("⚠️ Could not load index value data. Showing PE-only chart.")
                    show_index_values = False
                else:
                    value_cols = [c for c in pe_price_history.columns if 'Value' in c]
                    if not value_cols:
                        st.warning("⚠️ No index value columns found. Showing PE-only chart.")
                        show_index_values = False
            
            if show_index_values and pe_price_history is not None and not pe_price_history.empty:
                # Create stacked subplot chart
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.08,
                    row_heights=[0.4, 0.6],
                    subplot_titles=("📈 Index Values", "📊 PE Ratios")
                )
                
                # Top chart: Index values
                for idx_name in ['Nifty 50', 'Nifty Midcap 50', 'Nifty Smallcap 250']:
                    if not visibility.get(idx_name, True):
                        continue
                    value_col = f'{idx_name} Value'
                    if value_col in pe_price_history.columns:
                        fig.add_trace(go.Scatter(
                            x=pe_price_history['date'],
                            y=pe_price_history[value_col],
                            mode='lines',
                            name=f'{idx_name} Value',
                            line=dict(color=colors.get(idx_name, '#888'), width=2),
                            hovertemplate=f"{idx_name}<br>Date: %{{x}}<br>Value: %{{y:,.0f}}<extra></extra>"
                        ), row=1, col=1)
                
                # Bottom chart: PE ratios
                for col in pe_history.columns:
                    if col != 'date' and visibility.get(col, True):
                        fig.add_trace(go.Scatter(
                            x=pe_history['date'],
                            y=pe_history[col],
                            mode='lines',
                            name=f'{col} PE',
                            line=dict(color=colors.get(col, '#888'), width=2, dash='solid'),
                            hovertemplate=f"{col}<br>Date: %{{x}}<br>PE: %{{y:.1f}}<extra></extra>"
                        ), row=2, col=1)
                
                fig.update_layout(
                    height=650,
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=80, b=40),
                    hovermode='x unified'
                )
                fig.update_yaxes(title_text="Index Value", row=1, col=1)
                fig.update_yaxes(title_text="PE Ratio" + (" (Log)" if use_log_scale else ""), 
                                type="log" if use_log_scale else "linear", row=2, col=1)
                fig.update_xaxes(title_text="Date", row=2, col=1)
                
            else:
                # Single PE chart (original behavior)
                fig = go.Figure()
                
                for col in pe_history.columns:
                    if col != 'date' and visibility.get(col, True):
                        fig.add_trace(go.Scatter(
                            x=pe_history['date'],
                            y=pe_history[col],
                            mode='lines',
                            name=col,
                            line=dict(color=colors.get(col, '#888'), width=2),
                            hovertemplate=f"{col}<br>Date: %{{x}}<br>PE: %{{y:.1f}}<extra></extra>"
                        ))
                
                # Add median lines for visible indices
                median_info = []
                for idx_key, (idx_name, _) in index_names.items():
                    vis_key = idx_name.replace('50', ' 50').replace('250', ' 250').strip()
                    if not visibility.get(vis_key, True):
                        continue
                    idx_data = all_indices.get(idx_key, {})
                    if 'median' in idx_data:
                        median = idx_data['median']
                        color = colors.get(vis_key, '#888')
                        fig.add_hline(
                            y=median, 
                            line=dict(color=color, dash='dot', width=1)
                        )
                        median_info.append(f"<span style='color:{color}'>┈┈</span> {vis_key} Median: {median:.1f}")
                
                # Add ideal PE lines
                ideal_pe = {
                    'Nifty 50': 20,
                    'Nifty Midcap 50': 18,
                    'Nifty Smallcap 250': 15
                }
                ideal_info = []
                for idx_name_key, ideal_val in ideal_pe.items():
                    if not visibility.get(idx_name_key, True):
                        continue
                    color = colors.get(idx_name_key, '#888')
                    fig.add_hline(
                        y=ideal_val,
                        line=dict(color=color, dash='dash', width=2)
                    )
                    ideal_info.append(f"<span style='color:{color}'>──</span> {idx_name_key} Ideal: {ideal_val}")
                
                fig.update_layout(
                    height=450,
                    template="plotly_dark",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis_title="PE Ratio" + (" (Log Scale)" if use_log_scale else ""),
                    yaxis_type="log" if use_log_scale else "linear",
                    xaxis_title="Date",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=60, b=40),
                    hovermode='x unified'
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add legend for reference lines (only for PE-only view)
            if not show_index_values:
                if 'median_info' in dir() and 'ideal_info' in dir() and (median_info or ideal_info):
                    st.markdown(f"""
                    <div style="background: #1e293b; padding: 12px 15px; border-radius: 8px; margin-bottom: 10px;">
                        <div style="margin-bottom: 8px;">
                            <strong style="color: #22c55e;">🎯 Dashed Lines = Ideal PE (Good Value):</strong><br>
                            <span style="color: #94a3b8; font-size: 13px;">{' &nbsp;|&nbsp; '.join(ideal_info)}</span>
                        </div>
                        <div>
                            <strong style="color: #f8fafc;">📏 Dotted Lines = Historical Median PE:</strong><br>
                            <span style="color: #94a3b8; font-size: 13px;">{' &nbsp;|&nbsp; '.join(median_info)}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            elif show_index_values:
                st.caption("📊 *Stacked view: Top chart shows index values, bottom chart shows PE ratios*")
            
            # Add helpful tip
            st.caption("💡 Tip: Use 'Log Scale' for better comparison when PE values differ greatly across indices.")
            
            # PE Volatility Explanation
            with st.expander("❓ Why do PE values sometimes jump sharply?"):
                st.markdown("""
                **PE Ratio = Index Price ÷ Aggregate Earnings**
                
                PE can change due to several factors:
                
                | Cause | Effect on PE | Frequency |
                |-------|-------------|-----------|
                | **Quarterly Earnings** | When companies report results, the "E" changes | Every quarter |
                | **Index Rebalancing** | Stocks added/removed change aggregate earnings | Semi-annually |
                | **Corporate Actions** | Dividends, splits, mergers affect calculations | Ongoing |
                | **Price Movement** | Market buying/selling changes the numerator | Daily |
                
                **Sharp jumps** in PE usually indicate earnings updates (denominator changes), 
                not necessarily price movements. This is why PE can spike even when the index price is stable.
                
                **Example:** If earnings drop 20% but price stays flat, PE rises ~25%.
                """)
        else:
            st.warning("No PE history data available")
            
    except Exception as e:
        st.warning(f"Could not load PE trend chart: {e}")

