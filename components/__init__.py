"""
Reusable UI components for the SIP Simulator app.
"""

from .charts import (
    create_portfolio_chart,
    create_investment_chart,
    create_multiplier_breakdown
)
from .metrics import display_metrics, run_fund_comparison

__all__ = [
    'create_portfolio_chart',
    'create_investment_chart', 
    'create_multiplier_breakdown',
    'display_metrics',
    'run_fund_comparison'
]

