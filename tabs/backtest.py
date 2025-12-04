"""
Backtest Tab - Strategy Comparison and SIP Simulation
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List

from data_fetcher import (
    get_index_data, get_index_pe_data, get_mf_nav_data, align_data,
    TOP_EQUITY_FUNDS, FUND_AUM
)
from strategy import (
    Strategy, PETier, PRESET_STRATEGIES, AI_STRATEGIES,
    PB_SIP_PRESETS, AI_PB_STRATEGIES, AI_COMBINED_STRATEGIES,
    BULLET_PRESETS, AI_BULLET_PRESETS, PB_BULLET_PRESETS, COMBINED_BULLET_PRESETS,
    simulate_sip, simulate_bullet_deployment, compare_strategies
)
from components.charts import (
    create_portfolio_chart, create_investment_chart, create_multiplier_breakdown
)
from components.metrics import display_metrics


def render_backtest_tab():
    """Render the Backtest tab content."""
    
    # Create 2 sub-tabs for Backtest
    backtest_comparison_tab, backtest_simulation_tab = st.tabs(["📊 Strategy Comparison", "🔄 SIP Simulation"])
    
    with backtest_comparison_tab:
        _render_strategy_comparison()
    
    with backtest_simulation_tab:
        _render_sip_simulation()


def _render_strategy_comparison():
    """Render the Strategy Comparison sub-tab."""
    st.subheader("📋 All Strategies Comparison")
    st.markdown("*Compare all SIP and Bullet Deployment strategies side-by-side*")
    
    # Configuration
    sum_col1, sum_col2 = st.columns([1, 3])
    
    with sum_col1:
        st.markdown("#### ⚙️ Settings")
        
        # Asset type selection
        sum_asset_type = st.radio(
            "Asset Type:",
            options=["Index", "Mutual Fund"],
            horizontal=True,
            key="sum_asset_type"
        )
    
    sum_instrument = None
    sum_mf_code = None
    
    if sum_asset_type == "Index":
        sum_instrument = st.selectbox(
            "Select Index:",
            options=["Nifty 50", "Nifty Midcap 50", "Nifty Smallcap 250"],
            index=0,
            key="sum_instrument"
        )
    else:
        # Mutual Fund selection
        fund_options = []
        for code, name in TOP_EQUITY_FUNDS.items():
            aum = FUND_AUM.get(code, 0)
            aum_str = f"₹{aum:,} Cr" if aum > 0 else ""
            display_name = f"{name} ({aum_str})" if aum_str else name
            fund_options.append((display_name, code, name, aum))
        
        fund_options.sort(key=lambda x: x[3], reverse=True)
        display_names = [f[0] for f in fund_options]
        
        mf_choice_idx = st.selectbox(
            "Select Fund (sorted by AUM):",
            options=range(len(display_names)),
            format_func=lambda i: display_names[i],
            index=0,
            key="sum_mf_select"
        )
        
        sum_mf_code = fund_options[mf_choice_idx][1]
        sum_instrument = fund_options[mf_choice_idx][2]
        selected_aum = fund_options[mf_choice_idx][3]
        
        if selected_aum > 0:
            st.caption(f"📊 AUM: ₹{selected_aum:,} Crores")
        
        with st.expander("Or enter custom AMFI code"):
            custom_code = st.text_input("AMFI Code:", key="sum_custom_mf")
            if custom_code:
                sum_mf_code = custom_code
                sum_instrument = f"MF ({custom_code})"
    
    with sum_col1:
        sum_amount = st.number_input("Weekly Amount (₹):", value=5000, min_value=100, max_value=1000000, step=1000, key="sum_amount")
        sum_period = st.selectbox("Period:", options=[1, 3, 5, 10], index=2, format_func=lambda x: f"{x} Year{'s' if x > 1 else ''}", key="sum_period")
        run_summary = st.button("🚀 Compare All Strategies", type="primary", use_container_width=True, key="run_summary")
    
    with sum_col2:
        if run_summary:
            _run_strategy_comparison(sum_asset_type, sum_instrument, sum_mf_code, sum_amount, sum_period)
        else:
            st.info("👈 Set your weekly amount and period, then click 'Compare All Strategies' to see results")


def _run_strategy_comparison(asset_type, instrument, mf_code, amount, period):
    """Run all strategy comparisons."""
    with st.spinner(f"Running all strategy simulations on {instrument}..."):
        with st.expander("🔧 Debug Info (click to expand)", expanded=False):
            debug_sc = st.container()
        
        try:
            sum_end = datetime.now()
            sum_start = sum_end - timedelta(days=period * 365)
            
            with debug_sc:
                st.write(f"📋 Asset Type: {asset_type}")
                st.write(f"📋 Instrument: {instrument}")
                st.write(f"📋 Period: {sum_start.date()} to {sum_end.date()}")
            
            if asset_type == "Index":
                instrument_map = {
                    "Nifty 50": "nifty50",
                    "Nifty Midcap 50": "nifty_midcap",
                    "Nifty Smallcap 250": "nifty_smallcap",
                }
                
                index_key = instrument_map[instrument]
                with debug_sc:
                    st.write(f"📋 Index Key: {index_key}")
                
                index_data = get_index_data(index_key, sum_start.strftime("%Y-%m-%d"), sum_end.strftime("%Y-%m-%d"))
                pe_data = get_index_pe_data(index_key)
                price_col = 'nifty_close'
                
                with debug_sc:
                    st.write(f"📊 Index data: {index_data.shape if index_data is not None else 'None'}")
                    st.write(f"📊 PE data: {pe_data.shape if pe_data is not None else 'None'}")
            else:
                with debug_sc:
                    st.write(f"📋 MF Code: {mf_code}")
                mf_data = get_mf_nav_data(mf_code, sum_start.strftime("%Y-%m-%d"), sum_end.strftime("%Y-%m-%d"))
                if mf_data is None or mf_data.empty:
                    st.error(f"Could not fetch data for {instrument}")
                    return
                
                pe_data = get_index_pe_data("nifty50")
                index_data = mf_data.rename(columns={'nav': 'close'})
                price_col = 'nifty_close'
            
            if index_data is None or pe_data is None:
                st.error(f"Could not fetch data for {instrument}.")
                return
            
            aligned = align_data(index_data, pe_data)
            
            if aligned is None or aligned.empty:
                st.error("Could not align data.")
                return
            
            all_results = []
            errors = []
            
            def safe_simulate(func, *args, strategy_name="Unknown", strategy_type="Unknown", **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    errors.append(f"{strategy_type}: {strategy_name} - {str(e)}")
                    return None
            
            # Run all preset SIP strategies
            for key, strategy in PRESET_STRATEGIES.items():
                result = safe_simulate(
                    simulate_sip, aligned, strategy, amount, 
                    strategy_name=strategy.name, strategy_type="SIP",
                    price_col='nifty_close', pe_col='pe'
                )
                if result:
                    all_results.append({
                        'Strategy': f"📊 {strategy.name}",
                        'Type': 'SIP',
                        'Invested': result.total_invested,
                        'Value': result.current_value,
                        'Return %': result.absolute_return_pct,
                        'XIRR %': result.xirr,
                        'Avg Buy': result.avg_buy_price
                    })
            
            # Run AI-recommended SIP strategies
            for key, strategy in AI_STRATEGIES.items():
                result = safe_simulate(
                    simulate_sip, aligned, strategy, amount,
                    strategy_name=strategy.name, strategy_type="AI-SIP",
                    price_col='nifty_close', pe_col='pe'
                )
                if result:
                    all_results.append({
                        'Strategy': f"🤖 {strategy.name}",
                        'Type': 'AI-SIP',
                        'Invested': result.total_invested,
                        'Value': result.current_value,
                        'Return %': result.absolute_return_pct,
                        'XIRR %': result.xirr,
                        'Avg Buy': result.avg_buy_price
                    })
            
            # Run all preset Bullet strategies
            for key, config in BULLET_PRESETS.items():
                result = simulate_bullet_deployment(aligned, config, amount, price_col='nifty_close', pe_col='pe')
                total_value = result.current_value + result.cash_remaining
                ret_pct = ((total_value - result.total_accumulated) / result.total_accumulated * 100) if result.total_accumulated > 0 else 0
                all_results.append({
                    'Strategy': f"🎯 {config.name}",
                    'Type': 'Bullet',
                    'Invested': result.total_deployed,
                    'Value': total_value,
                    'Return %': ret_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.current_value / result.units_held if result.units_held > 0 else 0
                })
            
            # Run AI-recommended Bullet strategies
            for key, config in AI_BULLET_PRESETS.items():
                result = simulate_bullet_deployment(aligned, config, amount, price_col='nifty_close', pe_col='pe')
                total_value = result.current_value + result.cash_remaining
                ret_pct = ((total_value - result.total_accumulated) / result.total_accumulated * 100) if result.total_accumulated > 0 else 0
                all_results.append({
                    'Strategy': f"🤖 {config.name}",
                    'Type': 'AI-Bullet',
                    'Invested': result.total_deployed,
                    'Value': total_value,
                    'Return %': ret_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.current_value / result.units_held if result.units_held > 0 else 0
                })
            
            # Run PB-based SIP strategies
            for key, strategy in PB_SIP_PRESETS.items():
                result = simulate_sip(aligned, strategy, amount, price_col='nifty_close', pe_col='pe')
                all_results.append({
                    'Strategy': f"📊 {strategy.name}",
                    'Type': 'PB-SIP',
                    'Invested': result.total_invested,
                    'Value': result.current_value,
                    'Return %': result.absolute_return_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.avg_buy_price
                })
            
            # Run AI PB-based SIP strategies
            for key, strategy in AI_PB_STRATEGIES.items():
                result = simulate_sip(aligned, strategy, amount, price_col='nifty_close', pe_col='pe')
                all_results.append({
                    'Strategy': f"🤖 {strategy.name}",
                    'Type': 'AI-PB-SIP',
                    'Invested': result.total_invested,
                    'Value': result.current_value,
                    'Return %': result.absolute_return_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.avg_buy_price
                })
            
            # Run PB-based Bullet strategies
            for key, config in PB_BULLET_PRESETS.items():
                result = simulate_bullet_deployment(aligned, config, amount, price_col='nifty_close', pe_col='pe')
                total_value = result.current_value + result.cash_remaining
                ret_pct = ((total_value - result.total_accumulated) / result.total_accumulated * 100) if result.total_accumulated > 0 else 0
                all_results.append({
                    'Strategy': f"🎯 {config.name}",
                    'Type': 'PB-Bullet',
                    'Invested': result.total_deployed,
                    'Value': total_value,
                    'Return %': ret_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.current_value / result.units_held if result.units_held > 0 else 0
                })
            
            # Run Combined PE+PB Bullet strategies
            for key, config in COMBINED_BULLET_PRESETS.items():
                result = simulate_bullet_deployment(aligned, config, amount, price_col='nifty_close', pe_col='pe')
                total_value = result.current_value + result.cash_remaining
                ret_pct = ((total_value - result.total_accumulated) / result.total_accumulated * 100) if result.total_accumulated > 0 else 0
                all_results.append({
                    'Strategy': f"🔄 {config.name}",
                    'Type': 'Combined-Bullet',
                    'Invested': result.total_deployed,
                    'Value': total_value,
                    'Return %': ret_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.current_value / result.units_held if result.units_held > 0 else 0
                })
            
            # Run AI Combined strategies
            for key, strategy in AI_COMBINED_STRATEGIES.items():
                result = simulate_sip(aligned, strategy, amount, price_col='nifty_close', pe_col='pe')
                all_results.append({
                    'Strategy': f"🤖 {strategy.name}",
                    'Type': 'AI-Combined',
                    'Invested': result.total_invested,
                    'Value': result.current_value,
                    'Return %': result.absolute_return_pct,
                    'XIRR %': result.xirr,
                    'Avg Buy': result.avg_buy_price
                })
            
            # Show any errors that occurred
            if errors:
                with st.expander(f"⚠️ {len(errors)} strategies failed (click to see details)", expanded=False):
                    for err in errors:
                        st.warning(err)
            
            st.success(f"✅ Compared {len(all_results)} strategies across PE, PB, and Combined types")
            
            # Create summary table
            summary_df = pd.DataFrame(all_results)
            summary_df = summary_df.sort_values('XIRR %', ascending=False)
            
            st.markdown(f"### 📊 Strategy Comparison Results - {instrument}")
            
            def highlight_best(s):
                if s.name in ['Return %', 'XIRR %']:
                    is_max = s == s.max()
                    return ['background-color: #22c55e33' if v else '' for v in is_max]
                return ['' for _ in s]
            
            st.dataframe(
                summary_df.style.apply(highlight_best).format({
                    'Invested': '₹{:,.0f}',
                    'Value': '₹{:,.0f}',
                    'Return %': '{:.1f}%',
                    'XIRR %': '{:.1f}%',
                    'Avg Buy': '₹{:,.0f}'
                }),
                use_container_width=True,
                hide_index=True,
                height=500
            )
            
            # Best strategy callout
            best = summary_df.iloc[0]
            st.success(f"🏆 **Best Strategy by XIRR:** {best['Strategy']} with {best['XIRR %']:.1f}% XIRR")
            
            st.divider()
            
            # Strategy descriptions
            _render_strategy_guide()
                    
        except Exception as e:
            st.error(f"Error: {e}")
            import traceback
            st.code(traceback.format_exc())


def _render_sip_simulation():
    """Render the SIP Simulation sub-tab."""
    st.subheader("🔄 SIP Simulation")
    st.markdown("*Simulate SIP investments with different strategies and frequencies*")
    
    # Simulation Controls
    sim_col1, sim_col2, sim_col3, sim_col4 = st.columns([1, 1, 1, 1])
    with sim_col1:
        sim_asset = st.selectbox("Asset:", ["Nifty 50", "Nifty Midcap 50", "Nifty Smallcap 250"], key="sim_asset")
    with sim_col2:
        sim_amount = st.number_input("Weekly Amount (₹):", value=5000, min_value=100, step=500, key="sim_amount")
    with sim_col3:
        sim_period = st.selectbox("Period:", [1, 3, 5, 10], index=2, format_func=lambda x: f"{x} Year{'s' if x > 1 else ''}", key="sim_period")
    with sim_col4:
        st.write("")
        run_sip_sim = st.button("🚀 Run Simulation", type="primary", key="run_sip_sim")
    
    # Strategy selection
    sip_strategies = _get_selected_strategies()
    
    st.divider()
    
    # Frequency selector
    freq_subtab1, freq_subtab2, freq_subtab3 = st.tabs(["📊 Weekly SIP", "📅 Daily SIP", "📆 Monthly SIP"])
    
    with freq_subtab1:
        if run_sip_sim and len(sip_strategies) >= 1:
            _run_sip_simulation(sim_asset, sim_amount, sim_period, sip_strategies)
        else:
            st.info("Select strategies above and click 'Run Simulation' to see results")
            
            # Show strategy reference tables
            _render_strategy_tables()
    
    with freq_subtab2:
        st.markdown("### 📅 Daily SIP Backtest")
        st.markdown("*Same strategies with daily investments instead of weekly*")
        st.info("Daily SIP simulation uses the same strategies but with daily frequency. Run weekly simulation first to see the comparison.")
    
    with freq_subtab3:
        st.markdown("### 📆 Monthly SIP Backtest")
        st.markdown("*Same strategies with monthly investments*")
        st.info("Monthly SIP simulation uses the same strategies but with monthly frequency. Run weekly simulation first to see the comparison.")


def _get_selected_strategies() -> List[Strategy]:
    """Get user-selected strategies for simulation."""
    with st.expander("📊 Select Strategies", expanded=False):
        sip_strategies = []
        
        strat_type = st.radio(
            "Strategy Type:",
            ["PE-Based", "PB-Based", "Combined PE+PB", "AI Recommended", "Custom"],
            horizontal=True,
            key="sip_strat_type"
        )
        
        st.markdown("---")
        
        if strat_type == "PE-Based":
            sip_strat_col1, sip_strat_col2 = st.columns(2)
            with sip_strat_col1:
                st.markdown("**Preset Strategies:**")
                for key, strategy in PRESET_STRATEGIES.items():
                    if st.checkbox(strategy.name, value=(key in ["balanced", "opportunistic"]), key=f"sip_{key}"):
                        sip_strategies.append(strategy)
            with sip_strat_col2:
                st.markdown("**AI PE Strategies:**")
                for key, strategy in AI_STRATEGIES.items():
                    if st.checkbox(strategy.name, value=False, key=f"sip_ai_{key}"):
                        sip_strategies.append(strategy)
        
        elif strat_type == "PB-Based":
            sip_strat_col1, sip_strat_col2 = st.columns(2)
            with sip_strat_col1:
                st.markdown("**PB Preset Strategies:**")
                for key, strategy in PB_SIP_PRESETS.items():
                    if st.checkbox(strategy.name, value=(key == "pb_conservative"), key=f"sip_pb_{key}"):
                        sip_strategies.append(strategy)
            with sip_strat_col2:
                st.markdown("**AI PB Strategies:**")
                for key, strategy in AI_PB_STRATEGIES.items():
                    if st.checkbox(strategy.name, value=False, key=f"sip_ai_pb_{key}"):
                        sip_strategies.append(strategy)
        
        elif strat_type == "Combined PE+PB":
            st.markdown("**Combined PE+PB Strategies (AI Recommended):**")
            for key, strategy in AI_COMBINED_STRATEGIES.items():
                if st.checkbox(strategy.name, value=(key == "combined_balanced"), key=f"sip_combined_{key}"):
                    sip_strategies.append(strategy)
        
        elif strat_type == "Custom":
            st.markdown("### 🛠️ Build Your Custom Strategy")
            st.caption("Define PE thresholds and investment multipliers")
            
            custom_name = st.text_input("Strategy Name:", value="My Custom Strategy", key="custom_strat_name")
            num_tiers = st.slider("Number of Tiers:", min_value=1, max_value=10, value=3, key="custom_num_tiers")
            
            custom_tiers = []
            tier_cols = st.columns(num_tiers)
            
            for i, col in enumerate(tier_cols):
                with col:
                    st.markdown(f"**Tier {i+1}**")
                    pe_thresh = st.number_input(f"PE ≤", min_value=5.0, max_value=50.0, value=float(22 - i * 2), step=0.5, key=f"custom_pe_{i}")
                    mult = st.number_input(f"Multiplier", min_value=1.0, max_value=20.0, value=float(i + 1), step=0.5, key=f"custom_mult_{i}")
                    custom_tiers.append(PETier(pe_threshold=pe_thresh, multiplier=mult))
            
            custom_strategy = Strategy(
                name=custom_name,
                tiers=custom_tiers,
                description=f"Custom strategy with {num_tiers} tiers",
                color="#FF6B6B"
            )
            sip_strategies.append(custom_strategy)
            
            st.markdown("**Strategy Preview:**")
            tier_preview = " → ".join([f"PE≤{t.pe_threshold}: {t.multiplier}x" for t in sorted(custom_tiers, key=lambda x: x.pe_threshold, reverse=True)])
            st.code(tier_preview)
        
        else:  # AI Recommended
            st.markdown("**Top AI Recommended Strategies:**")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("PE-Based")
                for key, strategy in list(AI_STRATEGIES.items())[:2]:
                    if st.checkbox(strategy.name, value=True, key=f"sip_ai_top_{key}"):
                        sip_strategies.append(strategy)
            with col2:
                st.caption("PB-Based")
                for key, strategy in list(AI_PB_STRATEGIES.items())[:2]:
                    if st.checkbox(strategy.name, value=False, key=f"sip_ai_pb_top_{key}"):
                        sip_strategies.append(strategy)
        
        if len(sip_strategies) == 0:
            sip_strategies = [PRESET_STRATEGIES["balanced"], PRESET_STRATEGIES["opportunistic"]]
            st.info("No strategies selected. Using default: Balanced and Opportunistic")
    
    return sip_strategies


def _run_sip_simulation(asset, amount, period, strategies):
    """Run SIP simulation with selected parameters."""
    with st.spinner("Fetching data and running simulation..."):
        try:
            sim_end = datetime.now()
            sim_start = sim_end - timedelta(days=365 * period)
            
            asset_map = {
                "Nifty 50": "nifty50",
                "Nifty Midcap 50": "nifty_midcap",
                "Nifty Smallcap 250": "nifty_smallcap"
            }
            index_key = asset_map.get(asset, "nifty50")
            
            index_data = get_index_data(index_key, sim_start.strftime("%Y-%m-%d"), sim_end.strftime("%Y-%m-%d"))
            pe_data = get_index_pe_data(index_key)
            
            if index_data is not None and pe_data is not None:
                aligned = align_data(index_data, pe_data)
                
                if aligned is not None and len(aligned) > 0:
                    st.success(f"Loaded {len(aligned)} weeks of data for **{asset}**")
                    
                    results = compare_strategies(
                        aligned, 
                        strategies, 
                        amount,
                        price_col='nifty_close',
                        pe_col='pe'
                    )
                    
                    # Display metrics
                    st.subheader("📈 Strategy Comparison")
                    display_metrics(results, strategies)
                    
                    # Charts
                    st.subheader("📊 Portfolio Growth")
                    st.plotly_chart(
                        create_portfolio_chart(results, strategies),
                        use_container_width=True
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.plotly_chart(
                            create_investment_chart(results, strategies),
                            use_container_width=True
                        )
                    with col2:
                        st.plotly_chart(
                            create_multiplier_breakdown(results),
                            use_container_width=True
                        )
                    
                    # Detailed data
                    with st.expander("📋 Detailed Weekly Data"):
                        for name, result in results.items():
                            st.markdown(f"**{name}**")
                            st.dataframe(
                                result.weekly_data[['date', 'price', 'pe', 'multiplier', 'weekly_investment', 'portfolio_value']].tail(20),
                                use_container_width=True
                            )
                else:
                    st.error("Could not align data")
            else:
                st.error("Could not fetch data")
                
        except Exception as e:
            st.error(f"Error: {e}")


def _render_strategy_tables():
    """Render strategy reference tables."""
    st.subheader("📖 Available Strategies")
    
    # Preset Strategies
    st.markdown("**Preset Strategies:**")
    strategy_data = []
    for key, s in PRESET_STRATEGIES.items():
        row = {"Strategy": s.name, "Description": s.description}
        for tier in s.tiers:
            row[f"PE ≤ {tier.pe_threshold}"] = f"{tier.multiplier}x"
        strategy_data.append(row)
    
    preset_df = pd.DataFrame(strategy_data)
    # Sort PE columns from smaller to higher PE values
    pe_cols = [c for c in preset_df.columns if c.startswith("PE ≤")]
    pe_cols_sorted = sorted(pe_cols, key=lambda x: float(x.replace("PE ≤ ", "")))
    ordered_cols = ["Strategy", "Description"] + pe_cols_sorted
    preset_df = preset_df[[c for c in ordered_cols if c in preset_df.columns]]
    st.table(preset_df)
    
    # AI-Recommended Strategies
    with st.expander("🤖 AI-Recommended Strategies", expanded=False):
        ai_strategy_data = []
        for key, s in AI_STRATEGIES.items():
            row = {"Strategy": s.name, "Description": s.description}
            for tier in s.tiers:
                row[f"PE ≤ {tier.pe_threshold}"] = f"{tier.multiplier}x"
            ai_strategy_data.append(row)
        
        ai_df = pd.DataFrame(ai_strategy_data)
        # Sort PE columns from smaller to higher PE values
        pe_cols = [c for c in ai_df.columns if c.startswith("PE ≤")]
        pe_cols_sorted = sorted(pe_cols, key=lambda x: float(x.replace("PE ≤ ", "")))
        ordered_cols = ["Strategy", "Description"] + pe_cols_sorted
        ai_df = ai_df[[c for c in ordered_cols if c in ai_df.columns]]
        st.table(ai_df)


def _render_strategy_guide():
    """Render the strategy guide section."""
    st.markdown("### 📖 Strategy Guide")
    
    with st.expander("📈 PE-Based Strategies", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **📊 PE SIP Presets**
            - **Balanced**: 1x always
            - **Opportunistic**: 2x/3x/4x at PE ≤20/18/16
            - **Aggressive**: 3x/6x/12x
            - **Hardcore**: 3x/8x/16x
            """)
        with col2:
            st.markdown("""
            **🎯 PE Bullet Presets**
            - **Conservative**: 20%/40%/75% at PE ≤18/16/14
            - **Moderate**: 25%/50%/100% at PE ≤20/18/16
            - **Aggressive**: 33%/66%/100% at PE ≤22/20/18
            """)
    
    with st.expander("📊 PB-Based Strategies"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **📊 PB SIP Presets**
            - **PB Balanced**: 1x always
            - **PB Opportunistic**: 2x/3x/4x at PB ≤3.0/2.5/2.0
            - **PB Aggressive**: 3x/6x/12x at PB thresholds
            - **PB Hardcore**: 3x/8x/16x at PB thresholds
            """)
        with col2:
            st.markdown("""
            **🎯 PB Bullet Presets**
            - **PB Conservative**: 20%/40%/75% at PB ≤3.0/2.5/2.0
            - **PB Moderate**: 25%/50%/100%
            - **PB Aggressive**: 33%/66%/100%
            - **PB Deep Value**: 50%/80%/100%
            """)
    
    with st.expander("🔄 Combined PE+PB Strategies"):
        st.markdown("""
        **Combined strategies use BOTH PE and PB:**
        - **Dual Value**: Both PE AND PB must be cheap (2x/4x/6x)
        - **Stricter Value**: Very strict - both at low levels (3x/8x/15x)
        - **Either Value**: Deploy when EITHER is cheap (OR logic)
        - **Weighted Value**: Gradual 60% PE + 40% PB weighted signal
        """)
    
    with st.expander("🤖 AI-Recommended Strategies"):
        st.markdown("""
        **🤖 AI-Recommended Strategies**
        - **Gradual Builder**: Smooth 1.5x→4x scaling
        - **Value Accumulator**: Reduce at high PE (0.5x→5x)
        - **Crash Catcher**: Normal + 10-20x at crashes
        - **Momentum Value**: 0.5x→8x extreme swings
        - **Value Hunter**: Deploy 30%/60%/100%
        """)

