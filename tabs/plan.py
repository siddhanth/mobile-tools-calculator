"""
Suggested Plan Tab - Portfolio Allocation Planner
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from pathlib import Path


# Config file path
CONFIG_FILE = Path(__file__).parent.parent / "user_config.json"

DEFAULT_CONFIG = {
    "equity_return": 13.0,
    "gold_return": 9.0,
    "debt_return": 7.5,
    "cash_return": 5.5,
    "equity_pct": 37.3,
    "gold_pct": 14.668,
    "debt_pct": 35.672,
    "cash_pct": 12.36,
    "target_irr": 12.0
}


def load_user_config() -> dict:
    """Load user config from JSON file, or return defaults."""
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_user_config(config: dict):
    """Save user config to JSON file."""
    try:
        CONFIG_FILE.write_text(json.dumps(config, indent=2))
    except Exception:
        pass


def render_plan_tab():
    """Render the Suggested Plan tab content."""
    
    st.header("📋 Portfolio Allocation Planner")
    st.markdown("*Analyze your current portfolio and get suggestions to reach your target returns*")
    
    user_config = load_user_config()
    
    def save_config_callback():
        new_config = {
            "equity_pct": st.session_state.get("plan_equity", user_config["equity_pct"]),
            "gold_pct": st.session_state.get("plan_gold", user_config["gold_pct"]),
            "debt_pct": st.session_state.get("plan_debt", user_config["debt_pct"]),
            "cash_pct": st.session_state.get("plan_cash", user_config["cash_pct"]),
            "equity_return": st.session_state.get("plan_eq_ret", user_config["equity_return"]),
            "gold_return": st.session_state.get("plan_gold_ret", user_config["gold_return"]),
            "debt_return": st.session_state.get("plan_debt_ret", user_config["debt_return"]),
            "cash_return": st.session_state.get("plan_cash_ret", user_config["cash_return"]),
            "target_irr": st.session_state.get("plan_target", user_config["target_irr"])
        }
        save_user_config(new_config)
    
    # Input Section
    st.subheader("📊 Your Current Portfolio")
    
    input_col1, input_col2 = st.columns(2)
    
    with input_col1:
        st.markdown("**Asset Allocation (%)**")
        equity_pct = st.number_input("Equity", 0.0, 100.0, user_config["equity_pct"], 0.1, 
                                     key="plan_equity", on_change=save_config_callback)
        gold_pct = st.number_input("Gold", 0.0, 100.0, user_config["gold_pct"], 0.1, 
                                   key="plan_gold", on_change=save_config_callback)
        debt_pct = st.number_input("Sovereign Debt (G-Secs, SDLs)", 0.0, 100.0, user_config["debt_pct"], 0.1, 
                                   key="plan_debt", on_change=save_config_callback)
        cash_pct = st.number_input("Cash / Liquid Funds", 0.0, 100.0, user_config["cash_pct"], 0.1, 
                                   key="plan_cash", on_change=save_config_callback)
        
        total_pct = equity_pct + gold_pct + debt_pct + cash_pct
        if abs(total_pct - 100) > 0.1:
            st.warning(f"⚠️ Total allocation is {total_pct:.1f}%. Should equal 100%.")
        else:
            st.success(f"✅ Total: {total_pct:.1f}%")
    
    with input_col2:
        st.markdown("**Expected Returns by Asset Class (%)**")
        equity_ret = st.number_input("Equity Expected Return", 8.0, 25.0, user_config["equity_return"], 0.5, 
                                     key="plan_eq_ret", on_change=save_config_callback)
        gold_ret = st.number_input("Gold Expected Return", 5.0, 15.0, user_config["gold_return"], 0.5, 
                                   key="plan_gold_ret", on_change=save_config_callback)
        debt_ret = st.number_input("Debt Expected Return", 5.0, 10.0, user_config["debt_return"], 0.5, 
                                   key="plan_debt_ret", on_change=save_config_callback)
        cash_ret = st.number_input("Cash/Liquid Return", 3.0, 8.0, user_config["cash_return"], 0.5, 
                                   key="plan_cash_ret", on_change=save_config_callback)
        
        st.markdown("**Your Target**")
        target_irr = st.number_input("Target Blended IRR (%)", 8.0, 20.0, user_config["target_irr"], 0.5, 
                                     key="plan_target", on_change=save_config_callback)
    
    st.divider()
    
    if abs(total_pct - 100) <= 0.1:
        _render_portfolio_analysis(equity_pct, gold_pct, debt_pct, cash_pct,
                                   equity_ret, gold_ret, debt_ret, cash_ret, target_irr)
    else:
        st.error(f"Please adjust allocations to total 100% (currently {total_pct:.1f}%)")


def _render_portfolio_analysis(equity_pct, gold_pct, debt_pct, cash_pct,
                                equity_ret, gold_ret, debt_ret, cash_ret, target_irr):
    """Render the portfolio analysis section."""
    
    # Current blended return
    current_irr = (
        (equity_pct / 100) * equity_ret +
        (gold_pct / 100) * gold_ret +
        (debt_pct / 100) * debt_ret +
        (cash_pct / 100) * cash_ret
    )
    
    gap = target_irr - current_irr
    
    # Display current status
    st.subheader("📈 Current Portfolio Analysis")
    
    nifty_pe = st.session_state.get('cached_nifty_pe', 22.0)
    
    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric("Current Blended IRR", f"{current_irr:.1f}%")
    with metric_cols[1]:
        st.metric("Target IRR", f"{target_irr:.1f}%")
    with metric_cols[2]:
        delta_color = "inverse" if gap > 0 else "normal"
        st.metric("Gap to Target", f"{gap:.1f}%", delta=f"{gap:.1f}%", delta_color=delta_color)
    with metric_cols[3]:
        st.metric("Nifty PE (Current)", f"{nifty_pe:.1f}")
    
    # Portfolio composition chart
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Equity', 'Gold', 'Debt', 'Cash'],
            values=[equity_pct, gold_pct, debt_pct, cash_pct],
            hole=0.4,
            marker_colors=['#22c55e', '#f59e0b', '#3b82f6', '#94a3b8']
        )])
        fig_pie.update_layout(
            title="Current Allocation",
            height=300,
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with chart_col2:
        contributions = {
            'Equity': (equity_pct / 100) * equity_ret,
            'Gold': (gold_pct / 100) * gold_ret,
            'Debt': (debt_pct / 100) * debt_ret,
            'Cash': (cash_pct / 100) * cash_ret
        }
        fig_bar = go.Figure(data=[go.Bar(
            x=list(contributions.keys()),
            y=list(contributions.values()),
            marker_color=['#22c55e', '#f59e0b', '#3b82f6', '#94a3b8'],
            text=[f"{v:.1f}%" for v in contributions.values()],
            textposition='auto'
        )])
        fig_bar.update_layout(
            title="Return Contribution by Asset",
            height=300,
            yaxis_title="Contribution to IRR (%)",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    
    # Recommendations
    st.subheader("💡 Recommendations to Reach Target")
    
    if gap <= 0:
        st.success(f"🎉 Your current allocation already meets your target of {target_irr}%!")
    else:
        _render_recommendations(equity_pct, gold_pct, debt_pct, cash_pct,
                                equity_ret, gold_ret, debt_ret, cash_ret,
                                target_irr, nifty_pe)


def _render_recommendations(equity_pct, gold_pct, debt_pct, cash_pct,
                            equity_ret, gold_ret, debt_ret, cash_ret,
                            target_irr, nifty_pe):
    """Render recommendations section."""
    
    # Calculate required equity % to reach target
    other_weighted = (gold_pct * gold_ret + debt_pct * debt_ret + cash_pct * cash_ret) / (gold_pct + debt_pct + cash_pct) if (gold_pct + debt_pct + cash_pct) > 0 else 6
    
    equity_ret_with_timing = equity_ret + 4
    
    if equity_ret > other_weighted:
        required_equity = ((target_irr - other_weighted) / (equity_ret - other_weighted)) * 100
        required_equity_timing = ((target_irr - other_weighted) / (equity_ret_with_timing - other_weighted)) * 100
    else:
        required_equity = 100
        required_equity_timing = 100
    
    required_equity = min(max(required_equity, 0), 100)
    required_equity_timing = min(max(required_equity_timing, 0), 100)
    
    rec_col1, rec_col2 = st.columns(2)
    
    with rec_col1:
        st.markdown("### Option A: Increase Equity Allocation")
        st.markdown(f"""
        To reach **{target_irr}%** with base equity returns of {equity_ret}%:
        
        | Metric | Current | Required |
        |--------|---------|----------|
        | Equity % | {equity_pct}% | **{required_equity:.0f}%** |
        | Increase needed | - | **+{required_equity - equity_pct:.0f}%** |
        
        **Suggested new allocation:**
        - Equity: {required_equity:.0f}%
        - Gold: {max(gold_pct - (required_equity - equity_pct) * 0.2, 5):.0f}%
        - Debt: {max(debt_pct - (required_equity - equity_pct) * 0.5, 10):.0f}%
        - Cash: {max(cash_pct - (required_equity - equity_pct) * 0.3, 5):.0f}%
        """)
    
    with rec_col2:
        st.markdown("### Option B: Equity + Value Timing")
        st.markdown(f"""
        Using value-based SIP (Opportunistic strategy) can add ~4% to equity returns:
        
        | Metric | Base | With Timing |
        |--------|------|-------------|
        | Equity Return | {equity_ret}% | **{equity_ret_with_timing}%** |
        | Required Equity % | {required_equity:.0f}% | **{required_equity_timing:.0f}%** |
        
        **Recommended approach:**
        - Use Opportunistic SIP (2x when PE<20, 3x when PE<18)
        - Keep "bullet cash" for dips
        - Current PE: {nifty_pe:.1f} {"✅ Good entry" if nifty_pe < 20 else "⏳ Wait for dip"}
        """)
    
    st.divider()
    
    # 10-Year Projection
    _render_projections(equity_pct, gold_pct, debt_pct, cash_pct, target_irr, nifty_pe, required_equity_timing)


def _render_projections(equity_pct, gold_pct, debt_pct, cash_pct, target_irr, nifty_pe, required_equity_timing):
    """Render year-by-year and multi-scenario projections."""
    
    st.subheader("📅 10-Year Projection")
    
    years = list(range(1, 11))
    equity_returns = [8, 15, 18, 12, -5, 25, 20, 15, 10, 5]
    gold_returns = [12, 6, 8, 10, 15, 5, 8, 10, 12, 8]
    debt_returns_yr = [7.5, 7.5, 7.0, 7.0, 7.5, 7.0, 6.5, 6.5, 6.5, 7.0]
    cash_returns_yr = [5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.0, 5.0, 5.0, 5.5]
    
    projections = []
    for i, yr in enumerate(years):
        blended = (
            (equity_pct / 100) * equity_returns[i] +
            (gold_pct / 100) * gold_returns[i] +
            (debt_pct / 100) * debt_returns_yr[i] +
            (cash_pct / 100) * cash_returns_yr[i]
        )
        projections.append({
            'Year': f'Y{yr}',
            'Equity': equity_returns[i],
            'Gold': gold_returns[i],
            'Debt': debt_returns_yr[i],
            'Cash': cash_returns_yr[i],
            'Blended': blended
        })
    
    proj_df = pd.DataFrame(projections)
    avg_blended = proj_df['Blended'].mean()
    
    st.dataframe(
        proj_df.style.format({
            'Equity': '{:.1f}%',
            'Gold': '{:.1f}%',
            'Debt': '{:.1f}%',
            'Cash': '{:.1f}%',
            'Blended': '{:.1f}%'
        }).background_gradient(subset=['Blended'], cmap='RdYlGn'),
        use_container_width=True,
        hide_index=True
    )
    
    st.info(f"📊 **10-Year Average Blended IRR: {avg_blended:.1f}%** (with current {equity_pct}% equity allocation)")
    
    # Projection chart
    fig_proj = go.Figure()
    fig_proj.add_trace(go.Scatter(
        x=proj_df['Year'],
        y=proj_df['Blended'],
        mode='lines+markers',
        name='Blended Return',
        line=dict(color='#8b5cf6', width=3),
        marker=dict(size=10)
    ))
    fig_proj.add_hline(y=target_irr, line_dash="dash", line_color="#22c55e", 
                       annotation_text=f"Target: {target_irr}%")
    fig_proj.add_hline(y=avg_blended, line_dash="dot", line_color="#f59e0b",
                       annotation_text=f"Avg: {avg_blended:.1f}%")
    fig_proj.update_layout(
        title="Projected Year-by-Year Returns",
        height=400,
        yaxis_title="Blended Return %",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig_proj, use_container_width=True)
    
    st.divider()
    
    # Multi-Scenario Projection
    _render_multi_scenario(equity_pct, gold_pct, debt_pct, cash_pct, nifty_pe, required_equity_timing)


def _render_multi_scenario(equity_pct, gold_pct, debt_pct, cash_pct, nifty_pe, required_equity_timing):
    """Render multi-scenario comparison."""
    
    st.subheader("📊 Multi-Scenario Comparison")
    st.markdown("*Compare different deployment strategies over 30 years*")
    
    OPTION_A_EQUITY = 50.0
    OPTION_B_DEPLOY = 20.0
    PROJECTION_YEARS = 30
    DIP_BOOST = 8
    
    def adjust_allocation(new_equity, current_equity, gold, debt, cash):
        equity_change = new_equity - current_equity
        other_total = gold + debt + cash
        if other_total > 0:
            gold_new = gold - (gold / other_total) * equity_change
            debt_new = debt - (debt / other_total) * equity_change
            cash_new = cash - (cash / other_total) * equity_change
            return max(0, gold_new), max(0, debt_new), max(0, cash_new)
        return gold, debt, cash
    
    # Simulated returns
    equity_cycle_1 = [8, 15, 18, 12, -5, 25, 20, 15, 10, 5]
    equity_cycle_2 = [10, 12, 20, 15, -8, 22, 18, 12, 8, 6]
    equity_cycle_3 = [7, 14, 16, 10, -3, 28, 22, 14, 11, 4]
    equity_returns_base = equity_cycle_1 + equity_cycle_2 + equity_cycle_3
    
    gold_cycle = [12, 6, 8, 10, 15, 5, 8, 10, 12, 8]
    gold_returns = gold_cycle * 3
    
    debt_cycle = [7.5, 7.5, 7.0, 7.0, 7.5, 7.0, 6.5, 6.5, 6.5, 7.0]
    debt_returns_yr = debt_cycle * 3
    
    cash_cycle = [5.5, 5.5, 5.5, 5.5, 5.5, 5.5, 5.0, 5.0, 5.0, 5.5]
    cash_returns_yr = cash_cycle * 3
    
    scenarios = {
        "Existing": {"equity_start": equity_pct, "deploy_year": None, "deploy_amount": 0},
        "Option A": {"equity_start": OPTION_A_EQUITY, "deploy_year": None, "deploy_amount": 0},
        "Option B-12": {"equity_start": equity_pct, "deploy_year": 2, "deploy_amount": OPTION_B_DEPLOY},
        "Option B-24": {"equity_start": equity_pct, "deploy_year": 3, "deploy_amount": OPTION_B_DEPLOY},
        "Option B-36": {"equity_start": equity_pct, "deploy_year": 4, "deploy_amount": OPTION_B_DEPLOY},
    }
    
    scenario_colors = {
        "Existing": "#94a3b8",
        "Option A": "#22c55e",
        "Option B-12": "#8b5cf6",
        "Option B-24": "#f59e0b",
        "Option B-36": "#ef4444",
    }
    
    scenario_results = {}
    
    for name, config in scenarios.items():
        yearly_returns = []
        cumulative_values = [100]
        
        eq = config["equity_start"]
        gl, dt, cs = adjust_allocation(eq, equity_pct, gold_pct, debt_pct, cash_pct) if eq != equity_pct else (gold_pct, debt_pct, cash_pct)
        
        for year in range(PROJECTION_YEARS):
            yr_num = year + 1
            eq_return = equity_returns_base[year]
            
            if config["deploy_year"] == yr_num:
                eq_return += DIP_BOOST
                eq += config["deploy_amount"]
                gl, dt, cs = adjust_allocation(eq, eq - config["deploy_amount"], gl, dt, cs)
            
            blended = (
                (eq / 100) * eq_return +
                (gl / 100) * gold_returns[year] +
                (dt / 100) * debt_returns_yr[year] +
                (cs / 100) * cash_returns_yr[year]
            )
            yearly_returns.append(blended)
            
            new_value = cumulative_values[-1] * (1 + blended / 100)
            cumulative_values.append(new_value)
        
        final_value = cumulative_values[-1]
        cagr = ((final_value / 100) ** (1/PROJECTION_YEARS) - 1) * 100
        
        scenario_results[name] = {
            "yearly_returns": yearly_returns,
            "cumulative_values": cumulative_values,
            "final_value": final_value,
            "cagr": cagr
        }
    
    # Cumulative Portfolio Value Chart
    st.markdown("#### 💰 Cumulative Portfolio Value (Starting with ₹100)")
    
    fig_cumulative = go.Figure()
    years_with_start = list(range(0, PROJECTION_YEARS + 1))
    
    for name, result in scenario_results.items():
        fig_cumulative.add_trace(go.Scatter(
            x=years_with_start,
            y=result["cumulative_values"],
            mode='lines+markers',
            name=f"{name} ({result['cagr']:.1f}% CAGR)",
            line=dict(color=scenario_colors[name], width=2),
            marker=dict(size=6),
            hovertemplate=f"{name}<br>Year %{{x}}: ₹%{{y:.0f}}<extra></extra>"
        ))
    
    fig_cumulative.add_hline(y=100, line_dash="dot", line_color="#64748b", line_width=1)
    
    fig_cumulative.update_layout(
        height=400,
        xaxis_title="Year",
        yaxis_title="Portfolio Value (₹)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        hovermode='x unified'
    )
    st.plotly_chart(fig_cumulative, use_container_width=True)
    
    # Summary Table
    st.markdown("#### 📊 30-Year Performance Summary")
    
    summary_data = []
    for name, result in scenario_results.items():
        summary_data.append({
            "Scenario": name,
            "30Y CAGR": f"{result['cagr']:.1f}%",
            "Final Value (₹100 → )": f"₹{result['final_value']:.0f}",
            "Total Growth": f"{(result['final_value'] - 100):.0f}%"
        })
    
    summary_df = pd.DataFrame(summary_data)
    best_idx = summary_df["30Y CAGR"].apply(lambda x: float(x.replace('%', ''))).idxmax()
    
    def highlight_best(row):
        if row.name == best_idx:
            return ['background-color: #22c55e33'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        summary_df.style.apply(highlight_best, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    best_scenario = summary_data[best_idx]["Scenario"]
    best_cagr = summary_data[best_idx]["30Y CAGR"]
    st.success(f"🏆 **Best Strategy: {best_scenario}** with {best_cagr} CAGR over 30 years")
    
    st.divider()
    
    # Implementation Strategy
    st.subheader("🎯 Implementation Strategy")
    
    st.markdown(f"""
    ### Based on Current Market Conditions (PE: {nifty_pe:.1f})
    
    | Phase | Action | Trigger | New Equity % |
    |-------|--------|---------|--------------|
    | **Phase 1** | Increase equity gradually | Now | {min(equity_pct + 5, 100)}% |
    | **Phase 2** | Deploy more via SIP | PE < 20 | {min(equity_pct + 10, 100)}% |
    | **Phase 3** | Aggressive deployment | PE < 18 | {min(equity_pct + 15, 100)}% |
    | **Phase 4** | Full deployment | PE < 16 | {min(required_equity_timing, 100):.0f}% |
    
    ### Recommended SIP Strategy
    
    Use the **Opportunistic** or **AI-Recommended** strategies from the Backtest tab:
    - **Normal (PE > 20):** 1x SIP amount
    - **Cheap (PE 18-20):** 2x SIP amount  
    - **Very Cheap (PE 16-18):** 3x SIP amount
    - **Extremely Cheap (PE < 16):** 4x SIP amount
    
    ### Action Items
    
    1. ✅ Move **{min(5, 100-equity_pct)}%** from Cash → Equity Index Fund (now)
    2. ⏳ Set up **Opportunistic SIP** for regular investing
    3. 💰 Keep **{max(5, cash_pct - 5)}%** as "Bullet Reserve" for crashes
    4. 📊 Monitor PE levels in **Dashboard** tab
    """)

