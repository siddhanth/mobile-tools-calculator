Last updated: 2025-11-30 11:30

# Backtest Tab Specification

## Overview

The Backtest tab allows users to simulate various investment strategies (SIP and Bullet deployment) across different time periods and instruments. It includes both individual simulation and cross-strategy comparison features.

---

## Data Sources

### Functions Used

| Function | File | Purpose |
|----------|------|---------|
| `get_index_data(index, start, end)` | data_fetcher.py | Fetch index price history |
| `get_index_pe_data(index)` | data_fetcher.py | Fetch index PE history |
| `get_mf_nav_data(code, start, end)` | data_fetcher.py | Fetch mutual fund NAV history |
| `align_data(nifty_df, pe_df, mf_df)` | data_fetcher.py | Merge price and PE data on dates |
| `simulate_sip(data, strategy, amount, price_col, pe_col)` | strategy.py | Run SIP simulation |
| `simulate_bullet_deployment(data, config, amount, price_col, pe_col)` | strategy.py | Run bullet deployment simulation |

### Strategy Definitions (strategy.py)

| Strategy Type | Variable | Count | Description |
|---------------|----------|-------|-------------|
| PE-Based SIP | `PRESET_STRATEGIES` | 4 | Balanced, Opportunistic, Aggressive, Hardcore |
| AI PE SIP | `AI_STRATEGIES` | 4 | AI-recommended PE-based strategies |
| PB-Based SIP | `PB_SIP_PRESETS` | 4 | PB ratio based strategies |
| AI PB SIP | `AI_PB_STRATEGIES` | 4 | AI-recommended PB-based strategies |
| Combined PE+PB | `AI_COMBINED_STRATEGIES` | 4 | Uses both PE and PB thresholds |
| PE Bullet | `BULLET_PRESETS` | 4 | Deploy only when PE is cheap |
| AI PE Bullet | `AI_BULLET_PRESETS` | 4 | AI-recommended PE bullet strategies |
| PB Bullet | `PB_BULLET_PRESETS` | 4 | Deploy only when PB is cheap |
| Combined Bullet | `COMBINED_BULLET_PRESETS` | 4 | Uses both PE and PB for bullets |

**Total: 36 predefined strategies + Custom strategy builder**

---

## Sub-Tabs Structure

### Sub-Tab 1: SIP Simulation

**Purpose**: Run individual SIP simulations with selected strategies

### Sub-Tab 2: Strategy Comparison

**Purpose**: Compare all strategies side-by-side for a given instrument and period

---

## UI Components

### SIP Simulation Sub-Tab

#### Controls (Inline, not sidebar)

| Control | Type | Options | Default |
|---------|------|---------|---------|
| Asset Type | Radio | Index, Mutual Fund | Index |
| Select Index | Dropdown | Nifty 50, Midcap, Smallcap | Nifty 50 |
| Select Fund | Dropdown | TOP_EQUITY_FUNDS list | Sorted by AUM |
| SIP Amount | Number Input | 100 - 1,000,000 | 5,000 |
| SIP Frequency | Radio | Weekly, Daily, Monthly | Weekly |
| Period | Dropdown | 1, 3, 5, 10 years | 5 |
| Strategy Type | Radio | PE-Based, PB-Based, Combined, Custom | PE-Based |

#### Strategy Selection (Expander)

**Requirements**:
- [ ] Show strategy checkboxes based on selected Strategy Type
- [ ] PE-Based: Show PRESET_STRATEGIES + AI_STRATEGIES
- [ ] PB-Based: Show PB_SIP_PRESETS + AI_PB_STRATEGIES
- [ ] Combined: Show AI_COMBINED_STRATEGIES
- [ ] Custom: Show tier input fields (up to 10 tiers)

#### Custom Strategy Builder

**Requirements**:
- [ ] Allow up to 10 PE/PB tiers
- [ ] Each tier: threshold value (float) + multiplier (float)
- [ ] Support non-integer values (e.g., PE 19.5, multiplier 1.5)
- [ ] Validate: thresholds must be descending, multipliers ascending

#### Results Display

**Requirements**:
- [ ] Summary table with columns: Strategy, Invested, Current Value, Return %, XIRR %
- [ ] Portfolio value chart over time
- [ ] Sort tooltip values by highest
- [ ] Show weekly/daily/monthly data points based on frequency

### Strategy Comparison Sub-Tab

#### Controls

| Control | Type | Options | Default |
|---------|------|---------|---------|
| Asset Type | Radio | Index, Mutual Fund | Index |
| Select Instrument | Dropdown | Based on asset type | First option |
| Amount | Number Input | 100 - 1,000,000 | 5,000 |
| Period | Dropdown | 1, 3, 5, 10 years | 5 |
| Run Comparison | Button | - | - |

#### Results Display

**Requirements**:
- [ ] Single table showing ALL strategies (PE, PB, Combined, Bullet, AI variants)
- [ ] Columns: Strategy, Type, Invested, Value, Return %, XIRR %, Avg Buy Price
- [ ] Sortable by any column
- [ ] Highlight best performing strategy
- [ ] Group by strategy type (collapsible sections)

---

## Data Flow

### SIP Simulation Flow

```
User selects options
    │
    ├─► If Index:
    │   ├─► get_index_data(index_key, start, end)
    │   └─► get_index_pe_data(index_key)
    │
    └─► If Mutual Fund:
        ├─► get_mf_nav_data(mf_code, start, end)
        └─► get_index_pe_data("nifty50")  # Use Nifty PE as market indicator
    │
    ▼
align_data(index_data, pe_data)
    │
    ▼
For each selected strategy:
    simulate_sip(aligned, strategy, amount, price_col, pe_col)
    │
    ▼
Display results table and chart
```

### Strategy Comparison Flow

```
User clicks "Compare All Strategies"
    │
    ▼
Fetch data (same as SIP flow)
    │
    ▼
For EACH strategy type:
    ├─► PRESET_STRATEGIES (4)
    ├─► AI_STRATEGIES (4)
    ├─► PB_SIP_PRESETS (4)
    ├─► AI_PB_STRATEGIES (4)
    ├─► AI_COMBINED_STRATEGIES (4)
    ├─► BULLET_PRESETS (4)
    ├─► AI_BULLET_PRESETS (4)
    ├─► PB_BULLET_PRESETS (4)
    └─► COMBINED_BULLET_PRESETS (4)
    │
    ▼
Aggregate results into single DataFrame
    │
    ▼
Display comparison table
```

---

## Critical Code Paths

### Price Column Handling

The `align_data()` function ALWAYS renames the price column to `nifty_close`:

```python
# data_fetcher.py line 1009
result.columns = ['date', 'nifty_close']
```

Therefore, ALL `simulate_sip()` calls should use `price_col='nifty_close'`.

### PE Column Handling

After `align_data()`, the PE column is named `pe` (from the PE data merge).

### Mutual Fund Data Path

1. `get_mf_nav_data()` returns columns: `['date', 'nav']`
2. App renames to `['date', 'close']` before passing to `align_data()`
3. `align_data()` renames to `['date', 'nifty_close']`
4. Simulation uses `price_col='nifty_close'`

---

## Acceptance Criteria

### SIP Simulation

- [ ] Can select between Index and Mutual Fund
- [ ] Index dropdown shows all 3 indices
- [ ] Mutual Fund dropdown shows all funds sorted by AUM
- [ ] SIP amount accepts values 100-1,000,000
- [ ] Period selector works for 1, 3, 5, 10 years
- [ ] Strategy Type selector switches between PE/PB/Combined/Custom
- [ ] PE-Based shows 8 strategies (4 preset + 4 AI)
- [ ] PB-Based shows 8 strategies (4 preset + 4 AI)
- [ ] Combined shows 4 strategies
- [ ] Custom builder allows up to 10 tiers with float values
- [ ] Results table displays correctly
- [ ] Portfolio chart renders with all selected strategies
- [ ] Chart tooltip sorted by highest value

### Strategy Comparison

- [ ] Asset type selection works
- [ ] Instrument selection populates correctly
- [ ] "Compare All Strategies" button runs simulation
- [ ] Results include ALL 36+ strategies
- [ ] Table is sortable
- [ ] Best strategy is highlighted
- [ ] No errors for Index selection
- [ ] No errors for Mutual Fund selection

### Frequency Support

- [ ] Weekly SIP calculates correctly
- [ ] Daily SIP calculates correctly
- [ ] Monthly SIP calculates correctly

---

## Error States

### E1: Data Fetch Failure

**Trigger**: `get_index_data()` or `get_mf_nav_data()` returns None
**Behavior**: Show error message with specific reason, don't crash

### E2: PE Data Unavailable

**Trigger**: `get_index_pe_data()` returns empty
**Behavior**: Show error "PE data unavailable for selected period"

### E3: Alignment Produces Empty DataFrame

**Trigger**: No overlapping dates between price and PE data
**Behavior**: Show error "Could not align data - no overlapping dates"

### E4: Invalid Custom Strategy

**Trigger**: User enters invalid tier values
**Behavior**: Show validation error, don't run simulation

---

## Edge Cases

### EC1: Very Short Period

**Scenario**: User selects 1 year period but data only available for 6 months
**Expected**: Show warning, simulate with available data

### EC2: Fund with Limited History

**Scenario**: Mutual fund launched 2 years ago, user selects 10 year period
**Expected**: Show warning about limited data, simulate available period

### EC3: All Strategies Selected

**Scenario**: User selects all 8+ strategies for simulation
**Expected**: Chart renders all lines, may need horizontal scroll for legend

### EC4: Zero Multiplier Tier

**Scenario**: User enters 0 as multiplier
**Expected**: Validation error - multiplier must be > 0

### EC5: Duplicate Threshold Values

**Scenario**: User enters same PE threshold twice
**Expected**: Validation error - thresholds must be unique

---

## Test Scenarios

### T1: Basic SIP Simulation (Index)

1. Select "Index" → "Nifty 50"
2. Set amount to 10,000
3. Set period to 5 years
4. Select "PE-Based" strategies
5. Check "Balanced" and "Aggressive"
6. Run simulation
7. **Expected**: Table shows 2 rows, chart shows 2 lines

### T2: Basic SIP Simulation (Mutual Fund)

1. Select "Mutual Fund"
2. Select "Parag Parikh Flexi Cap"
3. Set amount to 5,000
4. Set period to 5 years
5. Select "PE-Based" → "Balanced"
6. Run simulation
7. **Expected**: Results display, no errors

### T3: PB-Based Strategy

1. Select "Index" → "Nifty 50"
2. Select "PB-Based" strategy type
3. Select "PB Conservative" strategy
4. Run simulation
5. **Expected**: Simulation uses PB thresholds, results display

### T4: Custom Strategy Builder

1. Select "Custom" strategy type
2. Add 3 tiers:
   - Tier 1: PE < 22, Multiplier 1.5
   - Tier 2: PE < 18, Multiplier 2.5
   - Tier 3: PE < 15, Multiplier 4.0
3. Run simulation
4. **Expected**: Custom strategy applied, results show custom strategy name

### T5: Strategy Comparison - All Strategies

1. Go to "Strategy Comparison" sub-tab
2. Select "Index" → "Nifty 50"
3. Set period to 10 years
4. Click "Compare All Strategies"
5. **Expected**: Table shows 36+ rows (all strategy types), best highlighted

### T6: Strategy Comparison - Mutual Fund

1. Go to "Strategy Comparison" sub-tab
2. Select "Mutual Fund" → Any fund
3. Click "Compare All Strategies"
4. **Expected**: No errors, results display

### T7: Daily SIP Frequency

1. Select Daily frequency
2. Run simulation
3. **Expected**: More data points than weekly, results consistent

### T8: Monthly SIP Frequency

1. Select Monthly frequency
2. Run simulation
3. **Expected**: Fewer data points than weekly, results consistent

---

## Dependencies

### Internal

- `data_fetcher.py`: Data fetching and alignment
- `strategy.py`: Strategy definitions and simulation logic

### External

- `yfinance`: Index price data
- `mfapi.in`: Mutual fund NAV data
- `nsepython`: PE/PB data
- `plotly`: Charts
- `streamlit`: UI

---

## Notes

### Performance Considerations

- Running 36+ strategies can take 10-20 seconds
- Consider adding progress bar for strategy comparison
- Cache aligned data to avoid re-fetching on strategy change

### Known Issues

1. Smallcap index data unreliable - uses MF proxy
2. `price_col` hardcoded to `'nifty_close'` - correct but confusing
3. PB data not always available for older periods

### Future Enhancements

- Add Bullet deployment to SIP Simulation sub-tab
- Add export to CSV/Excel functionality
- Add Monte Carlo simulation for future projections
- Add rolling returns analysis

