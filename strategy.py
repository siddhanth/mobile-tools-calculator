"""
Strategy Module
Defines SIP strategies with PE-based multipliers
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from scipy import optimize
from datetime import datetime


@dataclass
class PETier:
    """Represents a PE threshold and its corresponding multiplier"""
    pe_threshold: float  # Invest at this multiplier when PE <= threshold
    multiplier: float
    
    def __repr__(self):
        return f"PE ≤ {self.pe_threshold}: {self.multiplier}x"


@dataclass
class PBTier:
    """Represents a PB threshold and its corresponding multiplier"""
    pb_threshold: float  # Invest at this multiplier when PB <= threshold
    multiplier: float
    
    def __repr__(self):
        return f"PB ≤ {self.pb_threshold}: {self.multiplier}x"


@dataclass 
class Strategy:
    """Represents a complete investment strategy"""
    name: str
    tiers: List[PETier] = field(default_factory=list)
    description: str = ""
    color: str = "#000000"
    
    def get_multiplier(self, pe_value: float) -> float:
        """
        Get the investment multiplier for a given PE value
        
        Tiers are checked from lowest PE threshold to highest.
        Returns the multiplier for the lowest matching threshold.
        """
        if not self.tiers:
            return 1.0
        
        # Sort tiers by PE threshold (ascending)
        sorted_tiers = sorted(self.tiers, key=lambda t: t.pe_threshold)
        
        # Find the applicable tier (lowest threshold that PE is below)
        for tier in sorted_tiers:
            if pe_value <= tier.pe_threshold:
                return tier.multiplier
        
        # If PE is above all thresholds, return 1x (base investment)
        return 1.0
    
    def __repr__(self):
        tiers_str = ", ".join(str(t) for t in self.tiers)
        return f"{self.name}: [{tiers_str}]"


# Preset Strategies
PRESET_STRATEGIES = {
    "balanced": Strategy(
        name="Balanced",
        tiers=[],  # No tiers = always 1x
        description="Regular SIP - Fixed amount every week regardless of market conditions",
        color="#6B7280"  # Gray
    ),
    "opportunistic": Strategy(
        name="Opportunistic",
        tiers=[
            PETier(pe_threshold=20, multiplier=2),
            PETier(pe_threshold=18, multiplier=3),
            PETier(pe_threshold=16, multiplier=4),
        ],
        description="Moderate increase during dips: 2x at PE≤20, 3x at PE≤18, 4x at PE≤16",
        color="#10B981"  # Green
    ),
    "aggressive": Strategy(
        name="Aggressive",
        tiers=[
            PETier(pe_threshold=20, multiplier=3),
            PETier(pe_threshold=18, multiplier=6),
            PETier(pe_threshold=16, multiplier=12),
        ],
        description="Strong increase during dips: 3x at PE≤20, 6x at PE≤18, 12x at PE≤16",
        color="#F59E0B"  # Amber
    ),
    "hardcore": Strategy(
        name="Hardcore",
        tiers=[
            PETier(pe_threshold=20, multiplier=3),
            PETier(pe_threshold=18, multiplier=8),
            PETier(pe_threshold=16, multiplier=16),
        ],
        description="Maximum aggression: 3x at PE≤20, 8x at PE≤18, 16x at PE≤16",
        color="#EF4444"  # Red
    ),
}


# ============== AI-RECOMMENDED STRATEGIES ==============
# These strategies are designed based on historical PE patterns and optimization

AI_STRATEGIES = {
    "gradual_builder": Strategy(
        name="Gradual Builder",
        tiers=[
            PETier(pe_threshold=24, multiplier=1.5),
            PETier(pe_threshold=22, multiplier=2),
            PETier(pe_threshold=20, multiplier=2.5),
            PETier(pe_threshold=18, multiplier=3),
            PETier(pe_threshold=16, multiplier=4),
        ],
        description="Smooth scaling: 1.5x→2x→2.5x→3x→4x as PE drops from 24→16",
        color="#06B6D4"  # Cyan
    ),
    "value_accumulator": Strategy(
        name="Value Accumulator",
        tiers=[
            PETier(pe_threshold=28, multiplier=0.5),  # Reduce in expensive markets
            PETier(pe_threshold=24, multiplier=0.75),
            PETier(pe_threshold=22, multiplier=1),
            PETier(pe_threshold=20, multiplier=2),
            PETier(pe_threshold=18, multiplier=3),
            PETier(pe_threshold=16, multiplier=5),
        ],
        description="Reduce exposure when expensive (0.5x at PE>24), increase when cheap (5x at PE≤16)",
        color="#8B5CF6"  # Purple
    ),
    "crash_catcher": Strategy(
        name="Crash Catcher",
        tiers=[
            PETier(pe_threshold=22, multiplier=1),
            PETier(pe_threshold=18, multiplier=4),
            PETier(pe_threshold=15, multiplier=10),
            PETier(pe_threshold=13, multiplier=20),
        ],
        description="Normal SIP, but massive deployment during crashes: 10x at PE≤15, 20x at PE≤13",
        color="#DC2626"  # Dark Red
    ),
    "steady_climber": Strategy(
        name="Steady Climber",
        tiers=[
            PETier(pe_threshold=25, multiplier=0.8),
            PETier(pe_threshold=22, multiplier=1.2),
            PETier(pe_threshold=20, multiplier=1.5),
            PETier(pe_threshold=18, multiplier=2),
            PETier(pe_threshold=16, multiplier=2.5),
        ],
        description="Conservative scaling: Slightly reduce in expensive, moderate increase in cheap",
        color="#059669"  # Emerald
    ),
    "momentum_value": Strategy(
        name="Momentum Value",
        tiers=[
            PETier(pe_threshold=26, multiplier=0.5),  # Very expensive - minimal
            PETier(pe_threshold=23, multiplier=0.75),
            PETier(pe_threshold=21, multiplier=1.5),
            PETier(pe_threshold=19, multiplier=3),
            PETier(pe_threshold=17, multiplier=5),
            PETier(pe_threshold=15, multiplier=8),
        ],
        description="Aggressive value timing: 0.5x when PE>26, scales to 8x at PE≤15",
        color="#7C3AED"  # Violet
    ),
}


# ============== PB-BASED STRATEGIES ==============
# These strategies use Price-to-Book ratio instead of PE
# Historical Nifty 50 PB: Median ~3.3, P25 ~2.9, P10 ~2.5

@dataclass 
class PBStrategy:
    """Represents a PB-based investment strategy"""
    name: str
    tiers: List[PBTier] = field(default_factory=list)
    description: str = ""
    color: str = "#000000"
    
    def get_multiplier(self, pb_value: float) -> float:
        """Get the investment multiplier for a given PB value"""
        if not self.tiers:
            return 1.0
        
        sorted_tiers = sorted(self.tiers, key=lambda t: t.pb_threshold)
        
        for tier in sorted_tiers:
            if pb_value <= tier.pb_threshold:
                return tier.multiplier
        
        return 1.0
    
    def __repr__(self):
        tiers_str = ", ".join(str(t) for t in self.tiers)
        return f"{self.name}: [{tiers_str}]"


# PB-Based SIP Presets
PB_SIP_PRESETS = {
    "pb_balanced": PBStrategy(
        name="PB Balanced",
        tiers=[],  # No tiers = always 1x
        description="Regular SIP - Fixed amount regardless of PB",
        color="#6B7280"
    ),
    "pb_opportunistic": PBStrategy(
        name="PB Opportunistic",
        tiers=[
            PBTier(pb_threshold=3.0, multiplier=2),
            PBTier(pb_threshold=2.5, multiplier=3),
            PBTier(pb_threshold=2.0, multiplier=4),
        ],
        description="Moderate PB-based: 2x at PB≤3.0, 3x at PB≤2.5, 4x at PB≤2.0",
        color="#10B981"
    ),
    "pb_aggressive": PBStrategy(
        name="PB Aggressive",
        tiers=[
            PBTier(pb_threshold=3.2, multiplier=3),
            PBTier(pb_threshold=2.8, multiplier=6),
            PBTier(pb_threshold=2.4, multiplier=12),
        ],
        description="Strong PB-based: 3x at PB≤3.2, 6x at PB≤2.8, 12x at PB≤2.4",
        color="#F59E0B"
    ),
    "pb_hardcore": PBStrategy(
        name="PB Hardcore",
        tiers=[
            PBTier(pb_threshold=3.5, multiplier=3),
            PBTier(pb_threshold=3.0, multiplier=8),
            PBTier(pb_threshold=2.5, multiplier=16),
        ],
        description="Maximum aggression: 3x at PB≤3.5, 8x at PB≤3.0, 16x at PB≤2.5",
        color="#EF4444"
    ),
}


# AI-recommended PB-based strategies
AI_PB_STRATEGIES = {
    "pb_value_accumulator": PBStrategy(
        name="PB Value Accumulator",
        tiers=[
            PBTier(pb_threshold=3.3, multiplier=1.5),
            PBTier(pb_threshold=3.0, multiplier=2.5),
            PBTier(pb_threshold=2.7, multiplier=4),
            PBTier(pb_threshold=2.4, multiplier=6),
        ],
        description="Gradual PB increase: 1.5x→2.5x→4x→6x as PB drops",
        color="#06B6D4"
    ),
    "pb_deep_dive": PBStrategy(
        name="PB Deep Dive",
        tiers=[
            PBTier(pb_threshold=2.8, multiplier=2),
            PBTier(pb_threshold=2.4, multiplier=5),
            PBTier(pb_threshold=2.0, multiplier=10),
        ],
        description="Wait for deep PB value: 2x/5x/10x at PB≤2.8/2.4/2.0",
        color="#8B5CF6"
    ),
    "pb_steady_builder": PBStrategy(
        name="PB Steady Builder",
        tiers=[
            PBTier(pb_threshold=3.2, multiplier=1.5),
            PBTier(pb_threshold=2.9, multiplier=2.5),
            PBTier(pb_threshold=2.6, multiplier=3.5),
        ],
        description="Conservative PB scaling: 1.5x→2.5x→3.5x",
        color="#059669"
    ),
    "pb_contrarian": PBStrategy(
        name="PB Contrarian",
        tiers=[
            PBTier(pb_threshold=2.5, multiplier=4),
            PBTier(pb_threshold=2.0, multiplier=12),
        ],
        description="Only invest at extreme PB lows: 4x at PB≤2.5, 12x at PB≤2.0",
        color="#DC2626"
    ),
}


# ============== COMBINED PE+PB STRATEGIES ==============
# These strategies use both PE and PB for decision making

@dataclass
class CombinedTier:
    """Represents a combined PE+PB threshold"""
    pe_threshold: float
    pb_threshold: float
    multiplier: float
    logic: str = "AND"  # "AND" = both must be below, "OR" = either
    
    def __repr__(self):
        return f"PE≤{self.pe_threshold} {self.logic} PB≤{self.pb_threshold}: {self.multiplier}x"


@dataclass
class CombinedStrategy:
    """Strategy using both PE and PB for decisions"""
    name: str
    tiers: List[CombinedTier] = field(default_factory=list)
    description: str = ""
    color: str = "#000000"
    
    def get_multiplier(self, pe_value: float, pb_value: float) -> float:
        """Get multiplier based on both PE and PB values"""
        if not self.tiers:
            return 1.0
        
        # Check tiers from most restrictive (lowest thresholds) first
        sorted_tiers = sorted(self.tiers, key=lambda t: (t.pe_threshold + t.pb_threshold))
        
        for tier in sorted_tiers:
            if tier.logic == "AND":
                if pe_value <= tier.pe_threshold and pb_value <= tier.pb_threshold:
                    return tier.multiplier
            elif tier.logic == "OR":
                if pe_value <= tier.pe_threshold or pb_value <= tier.pb_threshold:
                    return tier.multiplier
        
        return 1.0


# AI Combined PE+PB Strategies
AI_COMBINED_STRATEGIES = {
    "dual_value": CombinedStrategy(
        name="Dual Value",
        tiers=[
            CombinedTier(pe_threshold=20, pb_threshold=3.0, multiplier=2, logic="AND"),
            CombinedTier(pe_threshold=18, pb_threshold=2.7, multiplier=4, logic="AND"),
            CombinedTier(pe_threshold=16, pb_threshold=2.4, multiplier=6, logic="AND"),
        ],
        description="Both PE AND PB must be cheap: 2x/4x/6x when both are low",
        color="#14B8A6"
    ),
    "stricter_value": CombinedStrategy(
        name="Stricter Value",
        tiers=[
            CombinedTier(pe_threshold=18, pb_threshold=2.8, multiplier=3, logic="AND"),
            CombinedTier(pe_threshold=16, pb_threshold=2.5, multiplier=8, logic="AND"),
            CombinedTier(pe_threshold=14, pb_threshold=2.2, multiplier=15, logic="AND"),
        ],
        description="Very strict: Only deploy when both PE AND PB hit low levels",
        color="#6366F1"
    ),
    "either_value": CombinedStrategy(
        name="Either Value",
        tiers=[
            CombinedTier(pe_threshold=20, pb_threshold=3.0, multiplier=2, logic="OR"),
            CombinedTier(pe_threshold=18, pb_threshold=2.5, multiplier=3, logic="OR"),
            CombinedTier(pe_threshold=16, pb_threshold=2.0, multiplier=5, logic="OR"),
        ],
        description="Flexible: Deploy when either PE OR PB becomes cheap",
        color="#F59E0B"
    ),
    "weighted_value": CombinedStrategy(
        name="Weighted Value",
        tiers=[
            CombinedTier(pe_threshold=21, pb_threshold=3.1, multiplier=1.5, logic="AND"),
            CombinedTier(pe_threshold=19, pb_threshold=2.9, multiplier=2.5, logic="AND"),
            CombinedTier(pe_threshold=17, pb_threshold=2.6, multiplier=4, logic="AND"),
            CombinedTier(pe_threshold=15, pb_threshold=2.3, multiplier=7, logic="AND"),
        ],
        description="Balanced approach: Gradual increase as both PE and PB drop",
        color="#8B5CF6"
    ),
}


def create_custom_strategy(name: str, tiers: List[Tuple[float, float]], 
                           color: str = "#8B5CF6") -> Strategy:
    """
    Create a custom strategy from a list of (pe_threshold, multiplier) tuples
    
    Args:
        name: Strategy name
        tiers: List of (pe_threshold, multiplier) tuples
        color: Hex color for charts
    
    Returns:
        Strategy object
    """
    pe_tiers = [PETier(pe_threshold=pe, multiplier=mult) for pe, mult in tiers]
    return Strategy(
        name=name,
        tiers=pe_tiers,
        description=f"Custom strategy: {', '.join(f'{mult}x at PE≤{pe}' for pe, mult in tiers)}",
        color=color
    )


@dataclass
class SIPResult:
    """Results of a SIP simulation"""
    strategy_name: str
    total_invested: float
    current_value: float
    units_held: float
    absolute_return: float
    absolute_return_pct: float
    xirr: float
    weeks_at_1x: int
    weeks_at_2x: int
    weeks_at_3x: int
    weeks_at_4x_plus: int
    avg_buy_price: float
    weekly_data: pd.DataFrame


def calculate_xirr(cashflows: List[Tuple[datetime, float]], 
                   guess: float = 0.1) -> float:
    """
    Calculate XIRR (Extended Internal Rate of Return) for irregular cashflows
    
    Args:
        cashflows: List of (date, amount) tuples. Negative = investment, Positive = redemption
        guess: Initial guess for the rate
    
    Returns:
        XIRR as a decimal (e.g., 0.15 for 15%)
    """
    if len(cashflows) < 2:
        return 0.0
    
    # Sort by date
    cashflows = sorted(cashflows, key=lambda x: x[0])
    
    dates = [cf[0] for cf in cashflows]
    amounts = [cf[1] for cf in cashflows]
    
    # Calculate day differences from first date
    first_date = dates[0]
    days = [(d - first_date).days for d in dates]
    
    def npv(rate):
        """Calculate NPV for a given rate"""
        if rate <= -1:
            return float('inf')
        return sum(amount / ((1 + rate) ** (day / 365)) 
                   for amount, day in zip(amounts, days))
    
    try:
        # Find the rate that makes NPV = 0
        result = optimize.brentq(npv, -0.9999, 10, maxiter=1000)
        return result
    except (ValueError, RuntimeError):
        # If optimization fails, try Newton's method
        try:
            result = optimize.newton(npv, guess, maxiter=1000)
            return result
        except:
            return 0.0


def simulate_sip(data: pd.DataFrame, strategy: Strategy, 
                 base_amount: float, 
                 price_col: str = 'close',
                 pe_col: str = 'pe') -> SIPResult:
    """
    Simulate SIP investment using a given strategy
    
    Args:
        data: DataFrame with date, price, and PE columns
        strategy: Strategy object defining investment multipliers
        base_amount: Base weekly SIP amount
        price_col: Name of the price column
        pe_col: Name of the PE column
    
    Returns:
        SIPResult with simulation results
    """
    data = data.copy().reset_index(drop=True)
    
    # Initialize tracking variables
    total_invested = 0.0
    total_units = 0.0
    cashflows = []
    
    # Track multiplier usage
    multiplier_counts = {1: 0, 2: 0, 3: 0, 4: 0}  # 4+ grouped
    
    weekly_records = []
    
    # Check if we have PB data for PB-based or Combined strategies
    has_pb = 'pb' in data.columns
    
    for idx, row in data.iterrows():
        date = row['date']
        price = row[price_col]
        pe = row[pe_col]
        pb = row.get('pb', None) if has_pb else None
        
        # Get multiplier based on strategy type
        if hasattr(strategy, 'tiers') and strategy.tiers:
            first_tier = strategy.tiers[0]
            # Check if it's a CombinedTier (has both pe_threshold and pb_threshold)
            if hasattr(first_tier, 'pe_threshold') and hasattr(first_tier, 'pb_threshold'):
                # CombinedStrategy - needs both PE and PB
                if pb is not None:
                    multiplier = strategy.get_multiplier(pe, pb)
                else:
                    multiplier = 1.0  # Fallback if no PB data
            elif hasattr(first_tier, 'pb_threshold'):
                # PBStrategy - needs PB
                if pb is not None:
                    multiplier = strategy.get_multiplier(pb)
                else:
                    multiplier = 1.0  # Fallback if no PB data
            else:
                # Regular PE Strategy
                multiplier = strategy.get_multiplier(pe)
        else:
            # No tiers defined, use default
            multiplier = strategy.get_multiplier(pe) if hasattr(strategy, 'get_multiplier') else 1.0
        
        investment = base_amount * multiplier
        
        # Calculate units bought
        units = investment / price
        total_units += units
        total_invested += investment
        
        # Track cashflow for XIRR (negative = outflow)
        cashflows.append((date, -investment))
        
        # Track multiplier usage
        mult_key = min(int(multiplier), 4)
        multiplier_counts[mult_key] = multiplier_counts.get(mult_key, 0) + 1
        
        # Record weekly data
        weekly_records.append({
            'date': date,
            'price': price,
            'pe': pe,
            'multiplier': multiplier,
            'investment': investment,
            'units_bought': units,
            'cumulative_units': total_units,
            'cumulative_invested': total_invested,
            'portfolio_value': total_units * price
        })
    
    # Calculate final values
    final_price = data.iloc[-1][price_col]
    current_value = total_units * final_price
    absolute_return = current_value - total_invested
    absolute_return_pct = (absolute_return / total_invested) * 100 if total_invested > 0 else 0
    
    # Add final value as positive cashflow for XIRR
    final_date = data.iloc[-1]['date']
    cashflows.append((final_date, current_value))
    
    # Calculate XIRR
    xirr = calculate_xirr(cashflows) * 100  # Convert to percentage
    
    # Average buy price
    avg_buy_price = total_invested / total_units if total_units > 0 else 0
    
    # Create weekly DataFrame
    weekly_df = pd.DataFrame(weekly_records)
    
    return SIPResult(
        strategy_name=strategy.name,
        total_invested=total_invested,
        current_value=current_value,
        units_held=total_units,
        absolute_return=absolute_return,
        absolute_return_pct=absolute_return_pct,
        xirr=xirr,
        weeks_at_1x=multiplier_counts.get(1, 0),
        weeks_at_2x=multiplier_counts.get(2, 0),
        weeks_at_3x=multiplier_counts.get(3, 0),
        weeks_at_4x_plus=multiplier_counts.get(4, 0),
        avg_buy_price=avg_buy_price,
        weekly_data=weekly_df
    )


def compare_strategies(data: pd.DataFrame, strategies: List[Strategy],
                       base_amount: float,
                       price_col: str = 'close',
                       pe_col: str = 'pe') -> Dict[str, SIPResult]:
    """
    Compare multiple strategies on the same data
    
    Args:
        data: DataFrame with date, price, and PE columns
        strategies: List of Strategy objects
        base_amount: Base weekly SIP amount
        price_col: Name of the price column
        pe_col: Name of the PE column
    
    Returns:
        Dictionary of {strategy_name: SIPResult}
    """
    results = {}
    for strategy in strategies:
        result = simulate_sip(data, strategy, base_amount, price_col, pe_col)
        results[strategy.name] = result
    return results


def get_current_recommendation(pe_value: float, base_amount: float,
                                strategies: List[Strategy]) -> Dict[str, Dict]:
    """
    Get investment recommendation for current PE value
    
    Args:
        pe_value: Current Nifty PE
        base_amount: Base SIP amount
        strategies: List of strategies to get recommendations for
    
    Returns:
        Dictionary with recommendations per strategy
    """
    recommendations = {}
    for strategy in strategies:
        multiplier = strategy.get_multiplier(pe_value)
        recommendations[strategy.name] = {
            'multiplier': multiplier,
            'investment': base_amount * multiplier,
            'pe_zone': _get_pe_zone(pe_value)
        }
    return recommendations


def _get_pe_zone(pe: float) -> str:
    """Get descriptive zone for PE value"""
    if pe <= 16:
        return "Deep Value (PE ≤ 16)"
    elif pe <= 18:
        return "Value (PE 16-18)"
    elif pe <= 20:
        return "Fair Value (PE 18-20)"
    elif pe <= 24:
        return "Slightly Expensive (PE 20-24)"
    else:
        return "Expensive (PE > 24)"


# ============== BULLET DEPLOYMENT STRATEGY ==============

@dataclass
class BulletDeploymentConfig:
    """Configuration for bullet deployment strategy"""
    name: str
    # PE thresholds for deployment (deploy when PE goes below these levels)
    cheap_threshold: float = 18.0  # Start deploying at this PE
    very_cheap_threshold: float = 16.0  # Deploy more aggressively
    extremely_cheap_threshold: float = 14.0  # Deploy maximum
    # Deployment percentages (% of accumulated cash to deploy)
    cheap_deploy_pct: float = 25.0  # Deploy 25% when cheap
    very_cheap_deploy_pct: float = 50.0  # Deploy 50% when very cheap
    extremely_cheap_deploy_pct: float = 100.0  # Deploy 100% when extremely cheap
    description: str = ""
    color: str = "#8B5CF6"


BULLET_PRESETS = {
    "conservative_bullet": BulletDeploymentConfig(
        name="Conservative Bullet",
        cheap_threshold=18.0,
        very_cheap_threshold=16.0,
        extremely_cheap_threshold=14.0,
        cheap_deploy_pct=20.0,
        very_cheap_deploy_pct=40.0,
        extremely_cheap_deploy_pct=75.0,
        description="Deploy 20%/40%/75% when PE hits 18/16/14",
        color="#22c55e"
    ),
    "moderate_bullet": BulletDeploymentConfig(
        name="Moderate Bullet",
        cheap_threshold=20.0,
        very_cheap_threshold=18.0,
        extremely_cheap_threshold=16.0,
        cheap_deploy_pct=25.0,
        very_cheap_deploy_pct=50.0,
        extremely_cheap_deploy_pct=100.0,
        description="Deploy 25%/50%/100% when PE hits 20/18/16",
        color="#f59e0b"
    ),
    "aggressive_bullet": BulletDeploymentConfig(
        name="Aggressive Bullet",
        cheap_threshold=22.0,
        very_cheap_threshold=20.0,
        extremely_cheap_threshold=18.0,
        cheap_deploy_pct=33.0,
        very_cheap_deploy_pct=66.0,
        extremely_cheap_deploy_pct=100.0,
        description="Deploy 33%/66%/100% when PE hits 22/20/18",
        color="#ef4444"
    ),
}


# AI-recommended Bullet strategies (PE-based)
AI_BULLET_PRESETS = {
    "value_hunter": BulletDeploymentConfig(
        name="Value Hunter",
        cheap_threshold=22.0,  # Start deploying earlier
        very_cheap_threshold=20.0,
        extremely_cheap_threshold=18.0,
        cheap_deploy_pct=30.0,
        very_cheap_deploy_pct=60.0,
        extremely_cheap_deploy_pct=100.0,
        description="Deploy earlier: 30%/60%/100% at PE ≤22/20/18",
        color="#14B8A6"  # Teal
    ),
    "deep_value": BulletDeploymentConfig(
        name="Deep Value",
        cheap_threshold=20.0,
        very_cheap_threshold=17.0,
        extremely_cheap_threshold=15.0,
        cheap_deploy_pct=40.0,
        very_cheap_deploy_pct=80.0,
        extremely_cheap_deploy_pct=100.0,
        description="Wait for deep value: 40%/80%/100% at PE ≤20/17/15",
        color="#6366F1"  # Indigo
    ),
}


# ============== PB-BASED BULLET STRATEGIES ==============

@dataclass
class PBBulletDeploymentConfig:
    """Configuration for PB-based bullet deployment strategy"""
    name: str
    cheap_threshold: float = 3.0  # Start deploying at this PB
    very_cheap_threshold: float = 2.5
    extremely_cheap_threshold: float = 2.0
    cheap_deploy_pct: float = 25.0
    very_cheap_deploy_pct: float = 50.0
    extremely_cheap_deploy_pct: float = 100.0
    description: str = ""
    color: str = "#8B5CF6"


PB_BULLET_PRESETS = {
    "pb_conservative_bullet": PBBulletDeploymentConfig(
        name="PB Conservative Bullet",
        cheap_threshold=3.0,
        very_cheap_threshold=2.5,
        extremely_cheap_threshold=2.0,
        cheap_deploy_pct=20.0,
        very_cheap_deploy_pct=40.0,
        extremely_cheap_deploy_pct=75.0,
        description="Deploy 20%/40%/75% when PB hits 3.0/2.5/2.0",
        color="#22c55e"
    ),
    "pb_moderate_bullet": PBBulletDeploymentConfig(
        name="PB Moderate Bullet",
        cheap_threshold=3.2,
        very_cheap_threshold=2.8,
        extremely_cheap_threshold=2.4,
        cheap_deploy_pct=25.0,
        very_cheap_deploy_pct=50.0,
        extremely_cheap_deploy_pct=100.0,
        description="Deploy 25%/50%/100% when PB hits 3.2/2.8/2.4",
        color="#f59e0b"
    ),
    "pb_aggressive_bullet": PBBulletDeploymentConfig(
        name="PB Aggressive Bullet",
        cheap_threshold=3.5,
        very_cheap_threshold=3.0,
        extremely_cheap_threshold=2.5,
        cheap_deploy_pct=33.0,
        very_cheap_deploy_pct=66.0,
        extremely_cheap_deploy_pct=100.0,
        description="Deploy 33%/66%/100% when PB hits 3.5/3.0/2.5",
        color="#ef4444"
    ),
    "pb_deep_value_bullet": PBBulletDeploymentConfig(
        name="PB Deep Value Bullet",
        cheap_threshold=2.8,
        very_cheap_threshold=2.3,
        extremely_cheap_threshold=1.8,
        cheap_deploy_pct=50.0,
        very_cheap_deploy_pct=80.0,
        extremely_cheap_deploy_pct=100.0,
        description="Wait for deep PB value: 50%/80%/100% at PB ≤2.8/2.3/1.8",
        color="#6366F1"
    ),
}


# ============== COMBINED PE+PB BULLET STRATEGIES ==============

@dataclass
class CombinedBulletConfig:
    """Configuration for combined PE+PB bullet deployment"""
    name: str
    # PE thresholds
    pe_cheap: float = 20.0
    pe_very_cheap: float = 18.0
    pe_extremely_cheap: float = 16.0
    # PB thresholds
    pb_cheap: float = 3.0
    pb_very_cheap: float = 2.5
    pb_extremely_cheap: float = 2.0
    # Deploy percentages
    cheap_deploy_pct: float = 25.0
    very_cheap_deploy_pct: float = 50.0
    extremely_cheap_deploy_pct: float = 100.0
    # Logic: "AND" = both must be below, "OR" = either triggers
    logic: str = "AND"
    description: str = ""
    color: str = "#8B5CF6"
    
    # Property aliases to match BulletDeploymentConfig interface
    @property
    def cheap_threshold(self) -> float:
        return self.pe_cheap
    
    @property
    def very_cheap_threshold(self) -> float:
        return self.pe_very_cheap
    
    @property
    def extremely_cheap_threshold(self) -> float:
        return self.pe_extremely_cheap


COMBINED_BULLET_PRESETS = {
    "dual_conservative": CombinedBulletConfig(
        name="Dual Conservative",
        pe_cheap=20.0, pe_very_cheap=18.0, pe_extremely_cheap=16.0,
        pb_cheap=3.0, pb_very_cheap=2.5, pb_extremely_cheap=2.0,
        cheap_deploy_pct=20.0, very_cheap_deploy_pct=45.0, extremely_cheap_deploy_pct=80.0,
        logic="AND",
        description="Deploy when BOTH PE AND PB are cheap: 20%/45%/80%",
        color="#22c55e"
    ),
    "dual_moderate": CombinedBulletConfig(
        name="Dual Moderate",
        pe_cheap=22.0, pe_very_cheap=20.0, pe_extremely_cheap=18.0,
        pb_cheap=3.2, pb_very_cheap=2.8, pb_extremely_cheap=2.4,
        cheap_deploy_pct=30.0, very_cheap_deploy_pct=60.0, extremely_cheap_deploy_pct=100.0,
        logic="AND",
        description="Deploy when BOTH PE AND PB hit levels: 30%/60%/100%",
        color="#f59e0b"
    ),
    "dual_aggressive": CombinedBulletConfig(
        name="Dual Aggressive",
        pe_cheap=24.0, pe_very_cheap=22.0, pe_extremely_cheap=20.0,
        pb_cheap=3.5, pb_very_cheap=3.2, pb_extremely_cheap=2.8,
        cheap_deploy_pct=40.0, very_cheap_deploy_pct=75.0, extremely_cheap_deploy_pct=100.0,
        logic="OR",
        description="Deploy when EITHER PE OR PB is cheap: 40%/75%/100%",
        color="#ef4444"
    ),
    "dual_value_hunter": CombinedBulletConfig(
        name="Dual Value Hunter",
        pe_cheap=18.0, pe_very_cheap=16.0, pe_extremely_cheap=14.0,
        pb_cheap=2.8, pb_very_cheap=2.4, pb_extremely_cheap=2.0,
        cheap_deploy_pct=35.0, very_cheap_deploy_pct=70.0, extremely_cheap_deploy_pct=100.0,
        logic="AND",
        description="Wait for extreme values in BOTH: 35%/70%/100%",
        color="#6366F1"
    ),
}


@dataclass
class BulletResult:
    """Results of a bullet deployment simulation"""
    strategy_name: str
    total_accumulated: float  # Total cash accumulated over time
    total_deployed: float  # Total actually invested
    cash_remaining: float  # Undeployed cash
    current_value: float  # Current portfolio value
    units_held: float
    absolute_return: float
    absolute_return_pct: float
    xirr: float
    num_deployments: int  # Number of times we deployed
    deployment_history: pd.DataFrame  # When and how much was deployed
    weekly_data: pd.DataFrame


def simulate_bullet_deployment(
    data: pd.DataFrame,
    config: BulletDeploymentConfig,
    weekly_accumulation: float,
    price_col: str = 'close',
    pe_col: str = 'pe'
) -> BulletResult:
    """
    Simulate bullet deployment strategy where cash is accumulated
    and only deployed when market becomes cheap.
    
    Args:
        data: DataFrame with date, price, and PE columns
        config: BulletDeploymentConfig with thresholds and deployment %
        weekly_accumulation: Amount to accumulate each week
        price_col: Name of the price column
        pe_col: Name of the PE column
    
    Returns:
        BulletResult with simulation results
    """
    data = data.sort_values('date').reset_index(drop=True)
    
    accumulated_cash = 0.0
    total_accumulated = 0.0
    total_deployed = 0.0
    total_units = 0.0
    
    weekly_records = []
    deployment_records = []
    cashflows = []
    
    prev_pe = None
    
    for idx, row in data.iterrows():
        date = row['date']
        price = row[price_col]
        pe = row[pe_col]
        
        if pd.isna(price) or pd.isna(pe) or price <= 0:
            continue
        
        # Accumulate cash each week
        accumulated_cash += weekly_accumulation
        total_accumulated += weekly_accumulation
        
        # Check if we should deploy
        deployment_amount = 0.0
        deployment_pct = 0.0
        deployed = False
        
        # Determine deployment based on PE level
        # Only deploy when PE crosses INTO the cheap zone (not every week it's cheap)
        if pe <= config.extremely_cheap_threshold:
            # Deploy maximum percentage
            deployment_pct = config.extremely_cheap_deploy_pct
            deployment_amount = accumulated_cash * (deployment_pct / 100)
            deployed = True
        elif pe <= config.very_cheap_threshold:
            # Deploy moderate percentage
            deployment_pct = config.very_cheap_deploy_pct
            deployment_amount = accumulated_cash * (deployment_pct / 100)
            deployed = True
        elif pe <= config.cheap_threshold:
            # Deploy small percentage
            deployment_pct = config.cheap_deploy_pct
            deployment_amount = accumulated_cash * (deployment_pct / 100)
            deployed = True
        
        units_bought = 0
        if deployed and deployment_amount > 0:
            units_bought = deployment_amount / price
            total_units += units_bought
            total_deployed += deployment_amount
            accumulated_cash -= deployment_amount
            
            # Track cashflow for XIRR
            cashflows.append((date, -deployment_amount))
            
            # Record deployment
            deployment_records.append({
                'date': date,
                'pe': pe,
                'price': price,
                'deployed_amount': deployment_amount,
                'deployed_pct': deployment_pct,
                'units_bought': units_bought,
                'cash_remaining': accumulated_cash
            })
        
        # Calculate current portfolio value
        current_value = total_units * price
        
        # Record weekly data
        weekly_records.append({
            'date': date,
            'price': price,
            'pe': pe,
            'accumulated': weekly_accumulation,
            'deployed': deployment_amount,
            'units_bought': units_bought,
            'cash_balance': accumulated_cash,
            'cumulative_deployed': total_deployed,
            'cumulative_units': total_units,
            'portfolio_value': current_value
        })
        
        prev_pe = pe
    
    # Final calculations
    if len(data) == 0 or total_units == 0:
        return BulletResult(
            strategy_name=config.name,
            total_accumulated=0,
            total_deployed=0,
            cash_remaining=0,
            current_value=0,
            units_held=0,
            absolute_return=0,
            absolute_return_pct=0,
            xirr=0,
            num_deployments=0,
            deployment_history=pd.DataFrame(),
            weekly_data=pd.DataFrame()
        )
    
    final_price = data.iloc[-1][price_col]
    current_value = total_units * final_price
    
    # Total value = portfolio value + remaining cash
    total_value = current_value + accumulated_cash
    
    # Returns calculated on deployed capital
    absolute_return = current_value - total_deployed
    absolute_return_pct = (absolute_return / total_deployed) * 100 if total_deployed > 0 else 0
    
    # Add final value as positive cashflow for XIRR
    if cashflows:
        final_date = data.iloc[-1]['date']
        cashflows.append((final_date, current_value))
        xirr = calculate_xirr(cashflows) * 100
    else:
        xirr = 0
    
    weekly_df = pd.DataFrame(weekly_records)
    deployment_df = pd.DataFrame(deployment_records)
    
    return BulletResult(
        strategy_name=config.name,
        total_accumulated=total_accumulated,
        total_deployed=total_deployed,
        cash_remaining=accumulated_cash,
        current_value=current_value,
        units_held=total_units,
        absolute_return=absolute_return,
        absolute_return_pct=absolute_return_pct,
        xirr=xirr,
        num_deployments=len(deployment_records),
        deployment_history=deployment_df,
        weekly_data=weekly_df
    )


if __name__ == "__main__":
    # Test the strategies
    print("Testing Strategy Module...")
    
    # Test preset strategies
    print("\nPreset Strategies:")
    for name, strategy in PRESET_STRATEGIES.items():
        print(f"\n{strategy.name}:")
        print(f"  Description: {strategy.description}")
        for pe in [25, 20, 18, 16, 14]:
            mult = strategy.get_multiplier(pe)
            print(f"  PE={pe}: {mult}x")
    
    # Test custom strategy
    print("\nCustom Strategy Test:")
    custom = create_custom_strategy(
        "My Strategy",
        [(22, 1.5), (19, 2.5), (17, 4)]
    )
    print(custom)
    for pe in [25, 22, 19, 17, 15]:
        mult = custom.get_multiplier(pe)
        print(f"  PE={pe}: {mult}x")
    
    # Test XIRR calculation
    print("\nXIRR Test:")
    from datetime import datetime
    cashflows = [
        (datetime(2020, 1, 1), -10000),
        (datetime(2020, 7, 1), -10000),
        (datetime(2021, 1, 1), -10000),
        (datetime(2021, 1, 1), 35000),  # Final value
    ]
    xirr = calculate_xirr(cashflows)
    print(f"  XIRR: {xirr * 100:.2f}%")
    
    print("\nAll tests completed!")

