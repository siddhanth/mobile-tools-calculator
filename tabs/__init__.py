"""
Tab modules for the SIP Simulator app.
Each tab is a separate module for better maintainability.
"""

from .dashboard import render_dashboard_tab
from .backtest import render_backtest_tab
from .analysis import render_analysis_tab
from .plan import render_plan_tab
from .us_markets import render_us_markets_tab

__all__ = [
    'render_dashboard_tab',
    'render_backtest_tab', 
    'render_analysis_tab',
    'render_plan_tab',
    'render_us_markets_tab',
]

