Last updated: 2025-11-30 11:30

# Dashboard Tab Specification

## Overview

The Dashboard tab provides a real-time market overview with sentiment indicators, current valuations for major indices, and historical PE trend charts. It serves as the primary landing page for users to assess current market conditions.

---

## Data Sources

### Functions Used

| Function | File | Purpose | Caching |
|----------|------|---------|---------|
| `get_all_indices_pe_pb()` | data_fetcher.py | Fetch current PE, PB, Div Yield for all indices | @st.cache_data (1 hour) |
| `get_pe_history_for_chart(years)` | data_fetcher.py | Historical PE data for charting | @st.cache_data (1 day) |
| `get_pe_price_history_for_chart(years)` | data_fetcher.py | Combined PE + Index Value data | @st.cache_data (1 day) |

### External APIs

| API | Purpose | Fallback |
|-----|---------|----------|
| nsepython `index_pe_pb_div()` | Current PE/PB/DivYield | Return cached data with warning |
| yfinance | Historical index prices | Use MF NAV proxy for Smallcap |

### Data Flow

```
User loads Dashboard
    │
    ├─► get_all_indices_pe_pb() ─► Current valuation cards
    │
    ├─► get_pe_history_for_chart(years) ─► PE trend chart (default)
    │
    └─► [if Show Index Values checked]
        get_pe_price_history_for_chart(years) ─► Stacked PE + Price chart
```

---

## UI Components

### 1. Sentiment Gauge

**Location**: Top of Dashboard
**Purpose**: Visual indicator of overall market sentiment

**Requirements**:
- [ ] Display arc-shaped gauge with 4 segments: PANIC, PESSIMISM, OPTIMISM, EUPHORIA
- [ ] Color coding: Red (Panic) → Orange (Pessimism) → Light Green (Optimism) → Dark Green (Euphoria)
- [ ] Labels positioned ON the arc segments (not floating)
- [ ] Needle pointing to current sentiment position
- [ ] Attribution: "Inspired by ExitMantra Market Sentiment Gauge"

**Error State**: Show "Data Unavailable" if sentiment calculation fails

### 2. Current Valuation Cards

**Location**: Below sentiment gauge
**Purpose**: Show current PE, PB, Dividend Yield for each index

**Requirements**:
- [ ] Display 3 cards: Nifty 50, Nifty Midcap 50, Nifty Smallcap 250
- [ ] Each card shows: PE Ratio, PB Ratio, Dividend Yield
- [ ] Valuation label: "Cheap", "Fair", "Expensive" based on percentile zones
- [ ] Color coding matches valuation (green=cheap, yellow=fair, red=expensive)

**Error State**: Show "Loading..." then "Data unavailable" after timeout

### 3. Combined Valuation Summary

**Location**: After valuation cards
**Purpose**: Overall market assessment

**Requirements**:
- [ ] Aggregate valuation across indices
- [ ] Show recommendation text (e.g., "Market appears fairly valued")

### 4. PE Trend Chart

**Location**: Main chart area
**Purpose**: Historical PE ratios for all indices

**Requirements**:
- [ ] Time period selector: 1Y, 3Y, 5Y, 10Y (default: 10Y)
- [ ] Log Scale checkbox: Toggles Y-axis to logarithmic
- [ ] Show Index Values checkbox: Adds stacked index value chart
- [ ] Index visibility toggles: Nifty 50, Midcap, Smallcap (each can be hidden)
- [ ] Median lines: Dotted lines showing historical median for each index
- [ ] Ideal PE lines: Dotted lines at Nifty=20, Midcap=18, Smallcap=15
- [ ] Legend explaining line styles

**Chart Behavior**:
- Default: Single PE chart with all indices
- With "Show Index Values": Stacked subplots (top=Index Values, bottom=PE)
- Hover shows date and values for all visible indices

**Error State**: Show warning if data fetch fails, display cached data if available

---

## User Interactions

### Checkboxes

| Checkbox | Key | Default | Action |
|----------|-----|---------|--------|
| Log Scale | `use_log_scale` | False | Changes Y-axis to log scale |
| Show Index Values | `show_index_values` | False | Adds index value subplot |
| Nifty 50 | `show_nifty50` | True | Toggle Nifty 50 visibility |
| Nifty Midcap 50 | `show_midcap` | True | Toggle Midcap visibility |
| Nifty Smallcap 250 | `show_smallcap` | True | Toggle Smallcap visibility |

### Dropdowns

| Dropdown | Key | Options | Default |
|----------|-----|---------|---------|
| Time Period | `chart_years` | 1, 3, 5, 10 | 10 |

### Expected Response Times

- Initial load: < 5 seconds (cached data)
- Chart re-render on toggle: < 1 second
- Fresh data fetch: < 10 seconds

---

## Error States

### Scenario 1: NSE API Unavailable

**Trigger**: `index_pe_pb_div()` times out or returns error
**Behavior**:
- Show warning: "Using cached data - last updated: [timestamp]"
- Display cached valuation cards
- Chart uses historical CSV data

### Scenario 2: yfinance Fails for Smallcap

**Trigger**: `get_index_price_data("nifty_smallcap")` returns empty
**Behavior**:
- Use Nippon India Small Cap Fund NAV as proxy
- Show info: "Using MF proxy for Smallcap index values"

### Scenario 3: Show Index Values Returns Empty

**Trigger**: `get_pe_price_history_for_chart()` returns None/empty
**Behavior**:
- Fall back to PE-only chart
- Show warning: "Could not load index value data"

---

## Acceptance Criteria

### Core Functionality

- [ ] Dashboard loads within 5 seconds on cached data
- [ ] All 3 index valuation cards display correctly
- [ ] PE trend chart renders with correct data
- [ ] Time period selector changes chart data
- [ ] Index toggles hide/show respective lines

### Checkbox Functionality

- [ ] "Log Scale" checkbox changes Y-axis to logarithmic
- [ ] "Show Index Values" checkbox adds stacked subplot
- [ ] When "Show Index Values" is checked and data unavailable, warning is shown
- [ ] Index visibility checkboxes correctly filter chart traces

### Sentiment Gauge

- [ ] Gauge displays with 4 colored segments
- [ ] Labels (PANIC, PESSIMISM, OPTIMISM, EUPHORIA) appear on arc
- [ ] Needle points to current sentiment
- [ ] Attribution text visible below gauge

### Error Handling

- [ ] API timeout shows cached data with warning
- [ ] Missing index data shows partial chart with explanation
- [ ] No unhandled exceptions crash the page

---

## Edge Cases

### E1: All Index Data Missing

**Scenario**: NSE API down, no cached data
**Expected**: Show error message, offer retry button

### E2: Partial Data Available

**Scenario**: Nifty 50 available, Midcap/Smallcap unavailable
**Expected**: Show available data, hide unavailable indices with note

### E3: Very Old Cached Data

**Scenario**: Cached data > 7 days old
**Expected**: Show warning about stale data, still display it

### E4: User Checks All Options Simultaneously

**Scenario**: Log scale + Show Index Values + All indices visible
**Expected**: Chart renders correctly with all options applied

---

## Test Scenarios

### T1: Fresh Load

1. Clear browser cache
2. Navigate to Dashboard
3. **Expected**: Valuation cards load, PE chart displays, no errors

### T2: Toggle Log Scale

1. Load Dashboard
2. Check "Log Scale" checkbox
3. **Expected**: Y-axis changes to log scale, chart re-renders

### T3: Toggle Show Index Values

1. Load Dashboard
2. Check "Show Index Values" checkbox
3. **Expected**: Chart becomes stacked subplot with index values on top

### T4: Hide Single Index

1. Load Dashboard
2. Uncheck "Nifty 50" visibility
3. **Expected**: Nifty 50 line disappears from chart, others remain

### T5: Change Time Period

1. Load Dashboard with 10Y default
2. Select "3 Years" from dropdown
3. **Expected**: Chart shows only last 3 years of data

### T6: API Failure Recovery

1. Simulate NSE API failure (disconnect network)
2. Load Dashboard
3. **Expected**: Cached data shown with warning message

---

## Dependencies

### Internal

- `data_fetcher.py`: All data fetching functions
- `strategy.py`: `get_current_recommendation()` for sentiment

### External

- `nsepython`: PE/PB/DivYield data
- `yfinance`: Historical index prices
- `plotly`: Chart rendering
- `streamlit`: UI framework

---

## Notes

### Known Issues

1. **Smallcap yfinance unreliable**: Using MF proxy as fallback
2. **NSE API rate limiting**: May timeout under heavy use
3. **Gauge label positioning**: Required manual coordinate tuning

### Future Enhancements

- Add PB ratio trend chart
- Add dividend yield trend
- Add correlation matrix between indices
- Add market breadth indicators

