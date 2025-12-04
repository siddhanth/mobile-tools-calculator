"""
2X in 5Y = 15% CAGR - Smart PE & PB-based Investment Strategies
A comprehensive tool for analyzing market valuations and comparing investment strategies

This is the main app entry point that orchestrates the tab modules.
"""

import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from datetime import datetime, timedelta
from pathlib import Path

from strategy import PRESET_STRATEGIES

# Import tab renderers
from tabs.dashboard import render_dashboard_tab
from tabs.backtest import render_backtest_tab
from tabs.analysis import render_analysis_tab
from tabs.plan import render_plan_tab
from tabs.us_markets import render_us_markets_tab


# Page config
st.set_page_config(
    page_title="2X in 5Y = 15% CAGR",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load authentication config
CONFIG_PATH = Path(__file__).parent / "config" / "auth_config.yaml"


def load_auth_config():
    """Load authentication configuration from YAML file."""
    with open(CONFIG_PATH) as file:
        return yaml.load(file, Loader=SafeLoader)


def get_authenticator():
    """Create and return the authenticator object."""
    config = load_auth_config()
    return stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #2d4a6f;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #4ade80;
    }
    .metric-label {
        font-size: 14px;
        color: #94a3b8;
    }
    .winner-badge {
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
    .pe-zone {
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
    }
    .pe-deep-value { background-color: #166534; color: white; }
    .pe-value { background-color: #22c55e; color: white; }
    .pe-fair { background-color: #eab308; color: black; }
    .pe-expensive { background-color: #f97316; color: white; }
    .pe-very-expensive { background-color: #dc2626; color: white; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e3a5f;
        border-radius: 8px;
        padding: 10px 20px;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #2d4a6f;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #3b82f6;
        color: white !important;
    }
    .stTabs [data-baseweb="tab"] p {
        color: white !important;
    }
    
    /* Responsive styles */
    @media (max-width: 768px) {
        /* Stack columns vertically on tablets */
        [data-testid="column"] {
            width: 100% !important;
            flex: 100% !important;
        }
        
        /* Reduce padding on mobile */
        .block-container {
            padding: 1rem !important;
        }
        
        /* Smaller headings */
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.25rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        
        /* Tabs scroll horizontally */
        [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
        }
        
        /* Smaller metrics */
        .stMetric {
            padding: 0.5rem !important;
        }
        
        /* Smaller metric cards */
        .metric-card {
            padding: 12px !important;
            margin: 5px 0 !important;
        }
        
        .metric-value {
            font-size: 20px !important;
        }
    }
    
    @media (max-width: 480px) {
        /* Extra small screens */
        h1 {
            font-size: 1.25rem !important;
        }
        h2 {
            font-size: 1.1rem !important;
        }
        
        .metric-card {
            padding: 8px !important;
        }
        
        .metric-value {
            font-size: 18px !important;
        }
        
        /* Reduce button padding */
        .stButton button {
            padding: 0.4rem 0.8rem !important;
            font-size: 0.85rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def render_login_page(authenticator):
    """Render the login page."""
    st.title("🧠 2X in 5Y = 15% CAGR")
    st.markdown("*Smart PE & PB-based Investment Strategies*")
    st.divider()
    
    st.markdown("### 🔐 Please Login to Continue")
    # v0.4.2 API: login(location='main') with keyword arguments
    authenticator.login(location='main')
    
    if st.session_state.get("authentication_status") is False:
        st.error("❌ Username or password is incorrect")
    elif st.session_state.get("authentication_status") is None:
        st.info("👆 Enter your credentials above")


def main():
    """Main application entry point."""
    
    # Initialize authenticator
    authenticator = get_authenticator()
    
    # Check authentication status
    if st.session_state.get("authentication_status") is not True:
        render_login_page(authenticator)
        return
    
    # User is authenticated - show the app
    # Title
    st.title("🧠 2X in 5Y = 15% CAGR")
    st.markdown("*Smart PE & PB-based Investment Strategies*")
    
    # Sidebar - Help info
    with st.sidebar:
        # User info and logout at top
        st.markdown(f"👤 Welcome, **{st.session_state.get('name', 'User')}**")
        authenticator.logout(button_name='Logout', location='sidebar')
        st.divider()
        
        st.header("ℹ️ About 2X in 5Y = 15% CAGR")
        
        st.markdown("""
        **2X in 5Y = 15% CAGR** helps you make smarter investment decisions based on PE and PB ratios.
        
        **📊 Dashboard**: Live India market sentiment and PE/PB valuations
        
        **🇺🇸 US Markets**: US market overview (S&P 500, NASDAQ, Russell 2000)
        
        **🔬 Backtest**: Compare strategies and simulate SIP investments
        
        **📈 Analysis**: Deep dives into fund performance and sector valuations
        
        **📋 Suggested Plan**: Portfolio allocation planner with 30-year projections
        """)
        
        with st.expander("📄 Documentation"):
            st.markdown("""
            **Specs**: See `sip_simulator/specs/` folder for detailed specifications:
            - `dashboard_spec.md` - Dashboard tab
            - `backtest_spec.md` - Backtest tab
            - `analysis_spec.md` - Analysis tab
            - `suggested_plan_spec.md` - Suggested Plan tab
            - `debug_findings.md` - Bug fixes and findings
            """)
        
        st.divider()
        
        with st.expander("📖 Strategy Types"):
            st.markdown("""
            **PE-Based**: Invest more when PE is low (cheap market)
            
            **PB-Based**: Invest more when PB is low (book value)
            
            **Combined**: Uses both PE and PB for decisions
            
            **Bullet**: Deploy cash only when market is cheap
            """)
        
        with st.expander("💡 Tips"):
            st.markdown("""
            - Use 5-10 year backtests for reliable results
            - Compare multiple strategies to find the best fit
            - Check sector valuations for sectoral opportunities
            """)
        
        st.divider()
        st.caption("Data: NSE, Yahoo Finance, mfapi.in")
    
    # Initialize default variables
    base_amount = 5000
    
    # Main content area - 5 Tab Structure
    tab_dashboard, tab_us_markets, tab_backtest, tab_analysis, tab_plan = st.tabs([
        "📊 India Dashboard", 
        "🇺🇸 US Markets",
        "🔬 Backtest", 
        "📈 Analysis", 
        "📋 Suggested Plan"
    ])
    
    # Render each tab using modular components
    with tab_dashboard:
        render_dashboard_tab(base_amount=base_amount)
    
    with tab_us_markets:
        render_us_markets_tab()
    
    with tab_backtest:
        render_backtest_tab()
    
    with tab_analysis:
        render_analysis_tab()
    
    with tab_plan:
        render_plan_tab()
    
    # Footer
    st.divider()
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 12px;">
        <p>Data Sources: India - Nifty prices from Yahoo Finance | MF NAV from mfapi.in | PE data from bundled historical data</p>
        <p>US Markets - Yahoo Finance (yfinance) | S&P 500/NASDAQ/Russell via ETF proxies (SPY, QQQ, IWM)</p>
        <p>⚠️ This is a simulation tool for educational purposes. Past performance does not guarantee future results.</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
