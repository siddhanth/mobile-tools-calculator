Last updated: 2025-11-30 22:35

# Suggested Plan Tab Specification

## Overview

The Suggested Plan tab provides a comprehensive portfolio allocation planner that helps users analyze their current portfolio, set target returns, and compare different deployment strategies over a 30-year horizon.

## Data Sources

- **User Config**: `user_config.json` - Persisted user settings for allocations and expected returns
- **Nifty PE**: Cached from Dashboard tab via `st.session_state['cached_nifty_pe']`
- **No External API Calls**: All calculations are done locally using user inputs

## UI Components

### 1. Your Current Portfolio Section

**Asset Allocation Inputs (%)**
- Equity (0-100%, default: 37.3%)
- Gold (0-100%, default: 14.668%)
- Sovereign Debt (0-100%, default: 35.672%)
- Cash/Liquid Funds (0-100%, default: 12.36%)
- Total validation: Must equal 100%

**Expected Returns Inputs (%)**
- Equity Expected Return (8-25%, default: 13%)
- Gold Expected Return (5-15%, default: 9%)
- Debt Expected Return (5-10%, default: 7.5%)
- Cash/Liquid Return (3-8%, default: 5.5%)

**Target**
- Target Blended IRR (8-20%, default: 12%)

### 2. Current Portfolio Analysis

**Metrics Displayed**
- Current Blended IRR (calculated from inputs)
- Target IRR (user input)
- Gap to Target (Target - Current)
- Nifty PE (Current) - from cache

**Charts**
- Current Allocation (Pie chart)
- Return Contribution by Asset (Bar chart)

### 3. Recommendations Section

Displays when Gap to Target > 0:
- Option A: Increase Equity Allocation (immediate)
- Option B: Equity + Value Timing (wait for opportunity)

### 4. Multi-Scenario Comparison (30-Year Projection)

**Scenarios Modeled**

| Scenario | Equity Allocation | Timing |
|----------|-------------------|--------|
| Existing | Current % constant | No change |
| Option A | 50% from Year 1 | Immediate increase |
| Option B-12 | Current → +20% | Deploy at month 12 |
| Option B-24 | Current → +20% | Deploy at month 24 |
| Option B-36 | Current → +20% | Deploy at month 36 |
| Option B-48 | Current → +20% | Deploy at month 48 |
| Option B-60 | Current → +20% | Deploy at month 60 |
| Option B-72 | Current → +20% | Deploy at month 72 |

**Simulated Market Returns (30-Year Cycle)**
- Years 1-10: Standard market cycle
- Years 11-20: Repeat with slight variations
- Years 21-30: Repeat with slight variations
- Dip years receive +8% boost for Option B scenarios when deploying

**Charts**
1. YoY Returns Trend (Line chart with 8 scenarios)
2. Cumulative Portfolio Value (Line chart, indexed to 100)

**Summary Table**
- Scenario name
- 30Y CAGR
- Final Value (from 100 base)
- Total Growth %

### 5. Implementation Strategy Section

Displays phased approach based on current PE level:
- Phase 1: Immediate actions
- Phase 2: PE < 20 triggers
- Phase 3: PE < 18 triggers
- Phase 4: PE < 16 triggers

## User Interactions

| Action | Response |
|--------|----------|
| Change allocation input | Recalculates blended IRR, saves to config |
| Change expected return | Recalculates blended IRR, saves to config |
| Change target IRR | Updates gap calculation, saves to config |
| Expand Scenario Configuration | Shows detailed scenario table |

## Persistence

All user inputs are saved to `user_config.json` on change:
- File location: `sip_simulator/user_config.json`
- Format: JSON with allocation %, return %, and target IRR
- Load: On tab open, reads saved values
- Save: On any input change via `on_change` callback

## Error States

| Condition | Display |
|-----------|---------|
| Total allocation ≠ 100% | Warning message with current total |
| Total allocation = 100% | Success checkmark |
| No cached PE data | Uses default 22.0 |

## Acceptance Criteria

- [ ] All allocation inputs persist across page refresh
- [ ] All expected return inputs persist across page refresh
- [ ] Target IRR persists across page refresh
- [ ] Blended IRR calculates correctly from inputs
- [ ] Gap to Target shows correct difference
- [ ] Pie chart shows current allocation proportions
- [ ] Bar chart shows return contribution breakdown
- [ ] All 8 scenarios appear in YoY chart
- [ ] All 8 scenarios appear in cumulative value chart
- [ ] Summary table shows correct CAGR for 30 years
- [ ] Best performer is highlighted in green
- [ ] Implementation strategy references correct PE thresholds

## Test Scenarios

### Test 1: Config Persistence
1. Change Equity allocation to 40%
2. Refresh page
3. Verify Equity shows 40%

### Test 2: Blended IRR Calculation
1. Set: Equity 50%, Gold 20%, Debt 20%, Cash 10%
2. Set: Returns 15%, 10%, 8%, 6%
3. Expected: (50*15 + 20*10 + 20*8 + 10*6)/100 = 11.7%

### Test 3: Multi-Scenario Charts
1. Navigate to Suggested Plan tab
2. Scroll to Multi-Scenario Comparison
3. Verify 8 lines appear on YoY chart
4. Verify 8 lines appear on cumulative chart
5. Verify Option B-12 shows highest CAGR (earliest deployment)

### Test 4: 30-Year Projection
1. Check summary table shows "30Y CAGR"
2. Check cumulative chart x-axis goes to Year 30
3. Verify final values reflect 30-year compounding

## Edge Cases

- User enters 0% for all allocations (show warning)
- User enters > 100% total (show warning, don't calculate)
- Config file is corrupted (fall back to defaults)
- Config file doesn't exist (create with defaults)

## Performance Requirements

- Tab should load in < 1 second (no API calls)
- Config save should be imperceptible (< 50ms)
- Chart rendering should complete in < 500ms

## Dependencies

- `user_config.json` for persistence
- `st.session_state['cached_nifty_pe']` for PE display
- Plotly for charts
- Pandas for data manipulation

## Notes

- 30-year projection uses simulated market returns, not actual historical data
- Option B scenarios assume market dip provides +8% boost in deployment year
- All calculations are deterministic (same inputs = same outputs)

