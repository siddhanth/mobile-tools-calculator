"""
Analysis Tab - Fund Comparison and Sector Valuations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import subprocess


def render_analysis_tab():
    """Render the Analysis tab content."""
    
    analysis_subtab1, analysis_subtab2 = st.tabs(["📈 Fund Comparison", "🏷️ Sector Valuations"])
    
    with analysis_subtab1:
        _render_fund_comparison()
    
    with analysis_subtab2:
        _render_sector_valuations()


def _render_fund_comparison():
    """Render the Fund Comparison sub-tab."""
    st.subheader("📈 Top Equity Funds - Strategy Comparison Report")
    st.markdown("Compare how different PE-based strategies perform across top mutual funds.")
    
    # Sub-tabs for Weekly, Daily, Monthly
    freq_tab1, freq_tab2, freq_tab3 = st.tabs(["📊 Weekly SIP Report", "📅 Daily SIP Report", "📆 Monthly SIP Report"])
    
    with freq_tab1:
        _render_weekly_report()
    
    with freq_tab2:
        _render_daily_report()
    
    with freq_tab3:
        _render_monthly_report()


def _render_weekly_report():
    """Render weekly SIP report."""
    st.markdown("### Weekly SIP (₹5,000/week)")
    
    report_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fund_comparison_data.csv")
    report_html = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fund_comparison_report.html")
    
    if os.path.exists(report_csv):
        df = pd.read_csv(report_csv)
        st.success(f"Loaded comparison data for **{len(df)} mutual funds** (5-year backtest)")
        
        _render_report_metrics(df)
        _render_report_table(df, "Weekly")
        _render_report_chart(df, "Weekly", "#ef4444")
        
        if os.path.exists(report_html):
            st.markdown("---")
            st.markdown("### 🔗 Full Interactive Report")
            st.markdown("""
                <a href="http://localhost:8502/fund_comparison_report.html" target="_blank" 
                   style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #3b82f6, #6366f1); 
                          color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    📄 Open Full HTML Report
                </a>
            """, unsafe_allow_html=True)
            st.caption("Opens in new tab with sortable table and additional details")
        
        st.download_button(
            label="📥 Download CSV Data",
            data=df.to_csv(index=False),
            file_name="fund_comparison_data.csv",
            mime="text/csv"
        )
    else:
        _render_generate_report_prompt("weekly", "generate_report.py")


def _render_daily_report():
    """Render daily SIP report."""
    st.markdown("### Daily SIP (₹1,000/day)")
    
    report_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "daily_fund_comparison_data.csv")
    report_html = os.path.join(os.path.dirname(os.path.dirname(__file__)), "daily_fund_comparison_report.html")
    
    if os.path.exists(report_csv):
        df = pd.read_csv(report_csv)
        st.success(f"Loaded daily SIP comparison data for **{len(df)} mutual funds** (5-year backtest)")
        
        _render_report_metrics(df)
        _render_report_table(df, "Daily")
        _render_report_chart(df, "Daily", "#f59e0b")
        
        if os.path.exists(report_html):
            st.markdown("---")
            st.markdown("### 🔗 Full Interactive Daily Report")
            st.markdown("""
                <a href="http://localhost:8502/daily_fund_comparison_report.html" target="_blank" 
                   style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #f59e0b, #ef4444); 
                          color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    📅 Open Full Daily Report
                </a>
            """, unsafe_allow_html=True)
        
        st.download_button(
            label="📥 Download Daily CSV Data",
            data=df.to_csv(index=False),
            file_name="daily_fund_comparison_data.csv",
            mime="text/csv",
            key="download_daily"
        )
    else:
        _render_generate_report_prompt("daily", "generate_daily_report.py")


def _render_monthly_report():
    """Render monthly SIP report."""
    st.markdown("### Monthly SIP (₹21,650/month)")
    
    report_csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monthly_fund_comparison_data.csv")
    report_html = os.path.join(os.path.dirname(os.path.dirname(__file__)), "monthly_fund_comparison_report.html")
    
    if os.path.exists(report_csv):
        df = pd.read_csv(report_csv)
        st.success(f"Loaded monthly SIP comparison data for **{len(df)} mutual funds** (5-year backtest)")
        
        _render_report_metrics(df)
        _render_report_table(df, "Monthly")
        
        if os.path.exists(report_html):
            st.markdown("---")
            st.markdown("### 🔗 Full Interactive Monthly Report")
            st.markdown("""
                <a href="http://localhost:8502/monthly_fund_comparison_report.html" target="_blank" 
                   style="display: inline-block; padding: 12px 24px; background: linear-gradient(135deg, #8b5cf6, #6366f1); 
                          color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                    📆 Open Full Monthly Report
                </a>
            """, unsafe_allow_html=True)
        
        st.download_button(
            label="📥 Download Monthly CSV Data",
            data=df.to_csv(index=False),
            file_name="monthly_fund_comparison_data.csv",
            mime="text/csv",
            key="download_monthly"
        )
    else:
        _render_generate_report_prompt("monthly", "generate_monthly_report.py")


def _render_report_metrics(df):
    """Render summary metrics for a report."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_balanced = df['balanced_return'].mean()
        st.metric("Avg Balanced Return", f"{avg_balanced:.1f}%")
    with col2:
        avg_hardcore = df['hardcore_return'].mean()
        st.metric("Avg Hardcore Return", f"{avg_hardcore:.1f}%")
    with col3:
        avg_extra = avg_hardcore - avg_balanced
        st.metric("Avg Extra Return", f"+{avg_extra:.1f}%")
    with col4:
        best_fund = df.loc[df['hardcore_return'].idxmax(), 'fund_name']
        st.metric("Best Fund", best_fund[:25] + ("..." if len(best_fund) > 25 else ""))
        st.caption(f"Full name: {best_fund}")
    
    st.divider()


def _render_report_table(df, freq_name):
    """Render the performance table."""
    st.markdown(f"### 📊 {freq_name} SIP Fund Performance Table")
    st.markdown("*Click column headers to sort*")
    
    display_df = df[['fund_name', 'balanced_return', 'opportunistic_return', 
                    'aggressive_return', 'hardcore_return', 'best_strategy']].copy()
    display_df.columns = ['Fund Name', 'Balanced %', 'Opportunistic %', 
                         'Aggressive %', 'Hardcore %', 'Best Strategy']
    
    for col in ['Balanced %', 'Opportunistic %', 'Aggressive %', 'Hardcore %']:
        display_df[col] = display_df[col].round(1)
    
    display_df['Extra vs Balanced'] = (display_df['Hardcore %'] - display_df['Balanced %']).round(1)
    
    st.dataframe(
        display_df.style.format({
            'Balanced %': '{:+.1f}%',
            'Opportunistic %': '{:+.1f}%',
            'Aggressive %': '{:+.1f}%',
            'Hardcore %': '{:+.1f}%',
            'Extra vs Balanced': '{:+.1f}%'
        }).background_gradient(subset=['Hardcore %'], cmap='RdYlGn'),
        use_container_width=True,
        height=500
    )


def _render_report_chart(df, freq_name, color):
    """Render the bar chart comparison."""
    st.markdown(f"### 📊 Top 15 Funds by Hardcore Strategy ({freq_name} SIP)")
    top_15 = df.nlargest(15, 'hardcore_return')
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Balanced',
        x=top_15['fund_name'].str[:25],
        y=top_15['balanced_return'],
        marker_color='#6b7280'
    ))
    fig.add_trace(go.Bar(
        name='Hardcore',
        x=top_15['fund_name'].str[:25],
        y=top_15['hardcore_return'],
        marker_color=color
    ))
    fig.update_layout(
        barmode='group',
        height=450,
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis_title="Return %",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_generate_report_prompt(freq_name, script_name):
    """Render the prompt to generate a report."""
    st.warning(f"{freq_name.title()} fund comparison report not yet generated.")
    st.info(f"""
        To generate the {freq_name} report, run this command in terminal:
        ```
        cd sip_simulator
        python3 {script_name}
        ```
        This will analyze 50+ top equity mutual funds with {freq_name} SIP.
    """)
    
    if st.button(f"🔄 Generate {freq_name.title()} Report", key=f"gen_{freq_name}"):
        with st.spinner(f"Generating {freq_name} report... This may take 2-5 minutes..."):
            result = subprocess.run(
                ["python3", script_name],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                st.success(f"{freq_name.title()} report generated! Please refresh the page.")
                st.rerun()
            else:
                st.error(f"Error generating report: {result.stderr}")


def _render_sector_valuations():
    """Render the Sector Valuations sub-tab."""
    st.subheader("🏷️ Index PE Multiple vs Nifty 50")
    st.markdown("""
    **PE Multiple** shows how expensive/cheap each index is compared to Nifty 50 (baseline = 1.0).  
    🟢 Green = Cheap (< 1.0) | 🔴 Red = Expensive (> 1.0)
    
    *Similar to [nifty-pe-ratio.com](https://nifty-pe-ratio.com/index-pe-ratio-to-nifty-pe-ratio-multiple/) matrix view*
    """)
    
    try:
        from data_fetcher import (
            get_all_sectors_pe, get_sector_pe_matrix, get_index_details,
            get_available_indices, get_index_historical_data, get_earnings_history_for_chart
        )
        
        matrix_tab, current_tab, details_tab = st.tabs(["📊 Historical Matrix", "📍 Current Valuations", "📈 Index Details & Earnings"])
        
        with matrix_tab:
            _render_pe_matrix(get_sector_pe_matrix)
        
        with current_tab:
            _render_current_valuations(get_all_sectors_pe)
        
        with details_tab:
            _render_index_details(get_available_indices, get_index_historical_data, get_earnings_history_for_chart)
            
    except Exception as e:
        st.error(f"Error loading sector valuations: {e}")
        st.info("Make sure nsepython is installed: `pip install nsepython`")


def _render_pe_matrix(get_sector_pe_matrix):
    """Render the PE Matrix view."""
    matrix_ctrl1, matrix_ctrl2 = st.columns([3, 1])
    with matrix_ctrl1:
        matrix_years = st.radio(
            "Select period:",
            options=[10, 15],
            index=0,
            horizontal=True,
            format_func=lambda x: f"{x} Years ({x * 12} months)",
            key="matrix_years"
        )
    with matrix_ctrl2:
        force_refresh = st.button("🔄 Refresh Data", key="refresh_matrix")
    
    matrix_months = matrix_years * 12
    st.markdown(f"### Index PE Multiple As Compared To Nifty 50 PE Ratio (Last {matrix_years} Years)")
    
    with st.expander("🔧 Debug Info", expanded=False):
        sector_debug = st.container()
    
    matrix_df = None
    try:
        if force_refresh:
            with st.spinner(f"Fetching {matrix_years} years of sector PE data from NSE... (this may take 1-2 minutes)"):
                with sector_debug:
                    st.write("🔄 Force refresh requested...")
                matrix_df = get_sector_pe_matrix(months=matrix_months, force_refresh=True)
            st.success("✅ Data refreshed!")
        else:
            with st.spinner("Loading sector PE data..."):
                with sector_debug:
                    st.write("📊 Loading from cache or fetching...")
                matrix_df = get_sector_pe_matrix(months=matrix_months)
        
        with sector_debug:
            if matrix_df is None:
                st.error("❌ get_sector_pe_matrix returned None")
            elif matrix_df.empty:
                st.warning("⚠️ get_sector_pe_matrix returned empty DataFrame")
            else:
                st.success(f"✅ Matrix loaded: {matrix_df.shape}")
    except Exception as e:
        with sector_debug:
            st.error(f"❌ Exception: {type(e).__name__}: {str(e)}")
        st.error(f"Failed to load sector data: {str(e)}")
    
    if matrix_df is not None and not matrix_df.empty:
        def color_multiple(val):
            if pd.isna(val) or val is None:
                return 'background-color: #374151; color: #9ca3af'
            elif val == 1.0:
                return 'background-color: #1e293b; color: #f8fafc'
            elif val <= 0.7:
                return 'background-color: #86efac; color: #14532d; font-weight: bold'
            elif val <= 0.9:
                return 'background-color: #bbf7d0; color: #166534'
            elif val <= 1.1:
                return 'background-color: #fef9c3; color: #713f12'
            elif val <= 1.5:
                return 'background-color: #fed7aa; color: #9a3412'
            else:
                return 'background-color: #fecaca; color: #991b1b; font-weight: bold'
        
        # Calculate 10-year averages
        numeric_cols = [col for col in matrix_df.columns if col != 'Month']
        avg_data = {}
        for col in numeric_cols:
            vals = pd.to_numeric(matrix_df[col], errors='coerce').dropna()
            if len(vals) > 0:
                avg_data[col] = round(vals.mean(), 2)
            else:
                avg_data[col] = None
        
        st.markdown("#### 📊 10-Year Historical Averages (PE Multiple vs Nifty 50)")
        st.caption("💡 Scroll horizontally to see all sectors →")
        avg_df = pd.DataFrame([avg_data])
        
        styled_avg = avg_df.style.applymap(
            color_multiple, 
            subset=[col for col in avg_df.columns]
        ).format(
            {col: '{:.2f}' for col in avg_df.columns},
            na_rep='-'
        )
        
        st.dataframe(styled_avg, use_container_width=True, hide_index=True)
        
        # Legend
        st.markdown("""
        <div style="display: flex; gap: 15px; flex-wrap: wrap; margin: 10px 0 20px 0;">
            <span style="background: #86efac; color: #14532d; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">≤0.7 Very Cheap</span>
            <span style="background: #bbf7d0; color: #166534; padding: 4px 8px; border-radius: 4px; font-size: 12px;">0.7-0.9 Cheap</span>
            <span style="background: #fef9c3; color: #713f12; padding: 4px 8px; border-radius: 4px; font-size: 12px;">0.9-1.1 Fair</span>
            <span style="background: #fed7aa; color: #9a3412; padding: 4px 8px; border-radius: 4px; font-size: 12px;">1.1-1.5 Expensive</span>
            <span style="background: #fecaca; color: #991b1b; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">>1.5 Very Expensive</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("#### 📅 Monthly PE Multiple History")
        st.caption("💡 Scroll horizontally to see all sectors →")
        
        styled_matrix = matrix_df.style.applymap(
            color_multiple, 
            subset=[col for col in matrix_df.columns if col != 'Month']
        ).format(
            {col: '{:.1f}' for col in matrix_df.columns if col != 'Month'},
            na_rep='-'
        )
        
        st.dataframe(styled_matrix, use_container_width=True, height=450)
    else:
        st.warning("Could not fetch matrix data. Please try again.")


def _render_current_valuations(get_all_sectors_pe):
    """Render current valuations section."""
    st.markdown("### Current PE Valuations (vs Historical Average)")
    st.markdown("*Valuation is based on each sector's own 10-year historical PE multiple trend, not just comparison to Nifty 50.*")
    
    refresh_current = st.button("🔄 Refresh Current Data", key="refresh_current")
    
    if refresh_current:
        with st.spinner("Fetching fresh sector PE data from NSE..."):
            sector_df = get_all_sectors_pe(force_refresh=True)
        st.success("✅ Data refreshed!")
    else:
        with st.spinner("Loading sector PE data..."):
            sector_df = get_all_sectors_pe()
    
    if sector_df is not None and not sector_df.empty:
        cheap_count = len(sector_df[sector_df['valuation'].str.contains('Cheap', na=False)])
        expensive_count = len(sector_df[sector_df['valuation'].str.contains('Expensive', na=False)])
        
        sum_cols = st.columns(4)
        with sum_cols[0]:
            st.metric("Total Indices", len(sector_df))
        with sum_cols[1]:
            st.metric("🟢 Cheap vs History", cheap_count)
        with sum_cols[2]:
            st.metric("🔴 Expensive vs History", expensive_count)
        with sum_cols[3]:
            nifty_pe = sector_df[sector_df['index_name'] == 'Nifty 50']['pe'].values
            st.metric("Nifty 50 PE", f"{nifty_pe[0]:.1f}" if len(nifty_pe) > 0 else "N/A")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🟢 Cheap vs Own History")
            cheap_df = sector_df[sector_df['valuation'].str.contains('Cheap', na=False)].copy()
            if not cheap_df.empty:
                for _, row in cheap_df.iterrows():
                    color = '#166534' if 'Very' in str(row['valuation']) else '#22c55e'
                    vs_hist = row.get('vs_history', 0)
                    hist_avg = row.get('hist_avg', row['pe_multiple'])
                    st.markdown(f"""
                    <div style="background: #1e293b; padding: 10px; border-radius: 6px; margin: 6px 0; border-left: 3px solid {color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #f8fafc; font-weight: bold;">{row['index_name']}</span>
                            <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{vs_hist:+.0f}%</span>
                        </div>
                        <div style="color: #9ca3af; font-size: 11px; margin-top: 4px;">
                            Current: {row['pe_multiple']:.2f}x | Hist Avg: {hist_avg:.2f}x | PE: {row['pe']:.1f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No sectors currently cheap vs their history")
        
        with col2:
            st.markdown("#### 🔴 Expensive vs Own History")
            expensive_df = sector_df[sector_df['valuation'].str.contains('Expensive', na=False)].sort_values('vs_history', ascending=False).copy()
            if not expensive_df.empty:
                for _, row in expensive_df.iterrows():
                    color = '#dc2626' if 'Very' in str(row['valuation']) else '#f97316'
                    vs_hist = row.get('vs_history', 0)
                    hist_avg = row.get('hist_avg', row['pe_multiple'])
                    st.markdown(f"""
                    <div style="background: #1e293b; padding: 10px; border-radius: 6px; margin: 6px 0; border-left: 3px solid {color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #f8fafc; font-weight: bold;">{row['index_name']}</span>
                            <span style="background: {color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{vs_hist:+.0f}%</span>
                        </div>
                        <div style="color: #9ca3af; font-size: 11px; margin-top: 4px;">
                            Current: {row['pe_multiple']:.2f}x | Hist Avg: {hist_avg:.2f}x | PE: {row['pe']:.1f}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No sectors currently expensive vs their history")
        
        st.divider()
        
        st.markdown("#### 📊 Complete Valuation Table")
        
        display_cols = ['index_name', 'pe', 'pe_multiple', 'hist_avg', 'vs_history', 'valuation']
        available_cols = [c for c in display_cols if c in sector_df.columns]
        display_df = sector_df[available_cols].copy()
        display_df.columns = ['Index', 'PE', 'Current Multiple', 'Hist Avg Multiple', 'vs History %', 'Valuation'][:len(available_cols)]
        
        def color_vs_history(val):
            try:
                v = float(val)
                if v <= -15:
                    return 'background-color: #166534; color: white'
                elif v <= -5:
                    return 'background-color: #22c55e; color: white'
                elif v >= 15:
                    return 'background-color: #dc2626; color: white'
                elif v >= 5:
                    return 'background-color: #f97316; color: white'
                else:
                    return 'background-color: #1e293b; color: #f8fafc'
            except:
                return ''
        
        if 'vs History %' in display_df.columns:
            styled_df = display_df.style.applymap(color_vs_history, subset=['vs History %'])
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.dataframe(display_df, use_container_width=True, height=400)
        
        st.markdown("""
        **Legend:**
        - **vs History %**: How current PE multiple compares to 10-year historical average
        - 🟢 **Negative %** = Trading below historical average (potentially cheap)
        - 🔴 **Positive %** = Trading above historical average (potentially expensive)
        """)
    else:
        st.warning("Could not fetch sector data.")


def _render_index_details(get_available_indices, get_index_historical_data, get_earnings_history_for_chart):
    """Render index details and earnings section."""
    st.markdown("### 📈 Index Historical Trends")
    st.markdown("*Select indices to view historical PE, PB, and Dividend Yield trends*")
    
    if 'index_data_cache' not in st.session_state:
        st.session_state['index_data_cache'] = {}
    
    available_indices = get_available_indices()
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([3, 1, 1])
    
    with ctrl_col1:
        selected_indices = st.multiselect(
            "Select Indices:",
            options=list(available_indices.keys()),
            default=["NIFTY 50", "NIFTY BANK", "NIFTY IT"],
            format_func=lambda x: available_indices[x],
            key="index_selector"
        )
    
    with ctrl_col2:
        time_period = st.selectbox(
            "Time Period:",
            options=[12, 24, 60, 120, 180],
            index=3,
            format_func=lambda x: f"{x} months ({x//12}y)" if x >= 12 else f"{x} months",
            key="trend_period"
        )
    
    with ctrl_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        force_refresh = st.button("🔄 Force Refresh", key="force_refresh_index")
    
    if selected_indices:
        indices_to_fetch = []
        trend_data = {}
        
        for idx_code in selected_indices:
            cache_key = f"{idx_code}_{time_period}"
            if force_refresh or cache_key not in st.session_state['index_data_cache']:
                indices_to_fetch.append(idx_code)
            else:
                trend_data[idx_code] = st.session_state['index_data_cache'][cache_key]
        
        if indices_to_fetch:
            status_msg = st.empty()
            status_msg.info(f"📥 Fetching data for {len(indices_to_fetch)} index(es)...")
            
            with st.spinner(f"Fetching {time_period} months of historical data from NSE..."):
                new_data = get_index_historical_data(indices_to_fetch, months=time_period)
                
                for idx_code, df in new_data.items():
                    cache_key = f"{idx_code}_{time_period}"
                    st.session_state['index_data_cache'][cache_key] = df
                    trend_data[idx_code] = df
            
            status_msg.success(f"✅ Data loaded! ({len(st.session_state['index_data_cache'])} datasets cached)")
        else:
            st.caption(f"📦 Using cached data ({len(selected_indices)} indices)")
        
        if trend_data:
            colors = ['#8b5cf6', '#f59e0b', '#22c55e', '#ef4444', '#3b82f6', '#ec4899', '#14b8a6', '#f97316']
            
            st.divider()
            
            # PE Ratio Trend Chart
            st.markdown("#### 📊 PE Ratio Trend")
            fig_pe = go.Figure()
            
            for idx, (code, df) in enumerate(trend_data.items()):
                if not df.empty:
                    color = colors[idx % len(colors)]
                    name = df['index_name'].iloc[0]
                    fig_pe.add_trace(go.Scatter(
                        x=df['date'],
                        y=df['pe'],
                        mode='lines',
                        name=name,
                        line=dict(color=color, width=2),
                        hovertemplate=f"{name}<br>Date: %{{x}}<br>PE: %{{y:.2f}}<extra></extra>"
                    ))
            
            fig_pe.update_layout(
                height=400,
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                yaxis_title="PE Ratio",
                xaxis_title="Date",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=40, r=40, t=60, b=40),
                hovermode='x unified'
            )
            st.plotly_chart(fig_pe, use_container_width=True)
            
            # Current Values Summary
            st.divider()
            st.markdown("#### 📍 Current Values")
            current_data = []
            for code, df in trend_data.items():
                if not df.empty:
                    latest = df.iloc[-1]
                    current_data.append({
                        'Index': latest['index_name'],
                        'PE Ratio': latest['pe'],
                        'PB Ratio': latest['pb'],
                        'Div Yield %': latest['div_yield'],
                        'Date': latest['date'].strftime('%d %b %Y')
                    })
            
            if current_data:
                current_df = pd.DataFrame(current_data)
                st.dataframe(
                    current_df.style.format({
                        'PE Ratio': '{:.2f}',
                        'PB Ratio': '{:.2f}',
                        'Div Yield %': '{:.2f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning("Could not fetch historical data. Please try again.")
    else:
        st.info("Please select at least one index to view trends.")

