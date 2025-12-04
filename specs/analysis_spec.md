Last updated: 2025-11-30 11:30

# Analysis Tab Specification

## Overview

The Analysis tab provides deep-dive analysis tools including sector valuations, fund comparison reports, and earnings trends. It helps users understand broader market context beyond the main indices.

---

## Sub-Tabs Structure

1. **PE/PB Trends** - Historical valuation trends
2. **Sector Valuations** - Sectoral index PE multiples vs Nifty
3. **Index Details** - Detailed view of individual indices with earnings
4. **Fund Comparison** - Performance comparison across mutual funds

---

## Sub-Tab 1: PE/PB Trends

### Purpose

Display historical PE and PB ratio trends for main indices.

### Data Sources

| Function | Purpose |
|----------|---------|
| `get_pe_history_for_chart(years)` | Historical PE data |
| `get_pe_price_history_for_chart(years)` | PE + Price combined |

### UI Components

- [ ] Time period selector (3, 5, 10 years)
- [ ] Index toggles (Nifty 50, Midcap, Smallcap)
- [ ] PE trend chart
- [ ] PB trend chart (if available)

### Acceptance Criteria

- [ ] Charts render with correct historical data
- [ ] Index toggles filter chart traces
- [ ] Time period changes data range

---

## Sub-Tab 2: Sector Valuations

### Purpose

Compare sectoral index PE ratios to Nifty 50 to identify relatively cheap/expensive sectors.

### Data Sources

| Function | File | Purpose |
|----------|------|---------|
| `get_sector_pe_matrix(months)` | data_fetcher.py | Historical PE multiple matrix |
| `get_all_sectors_pe()` | data_fetcher.py | Current PE for all sectors |
| `calculate_sector_zones(sector_data)` | data_fetcher.py | Percentile-based valuation zones |

### Sectoral Indices Tracked

```python
SECTORAL_INDICES = {
    "NIFTY 50": "Nifty 50",
    "NIFTY BANK": "Nifty Bank",
    "NIFTY IT": "Nifty IT",
    "NIFTY PHARMA": "Nifty Pharma",
    "NIFTY AUTO": "Nifty Auto",
    "NIFTY FMCG": "Nifty FMCG",
    "NIFTY METAL": "Nifty Metal",
    "NIFTY REALTY": "Nifty Realty",
    "NIFTY ENERGY": "Nifty Energy",
    "NIFTY INFRA": "Nifty Infra",
    "NIFTY PSE": "Nifty PSE",
    "NIFTY MEDIA": "Nifty Media",
    "NIFTY PRIVATE BANK": "Nifty Pvt Bank",
    "NIFTY PSU BANK": "Nifty PSU Bank",
    "NIFTY COMMODITIES": "Nifty Commodities",
    "NIFTY CONSUMPTION": "Nifty Consumption",
    "NIFTY FIN SERVICE": "Nifty Fin Service",
    "NIFTY HEALTHCARE": "Nifty Healthcare"
}
```

### Sub-Sub-Tabs

#### A. Historical Matrix

**Purpose**: Show PE multiple (Sector PE / Nifty PE) over time

**UI Components**:
- [ ] Matrix table: Months as rows, Sectors as columns
- [ ] Color coding: Green (cheap) → Yellow (fair) → Red (expensive)
- [ ] Fixed 10-year view (120 months)
- [ ] Average row displayed SEPARATELY above historical data

**Matrix Structure**:
```
| Month     | Bank | IT   | Pharma | Auto | ... |
|-----------|------|------|--------|------|-----|
| Average   | 1.05 | 1.42 | 1.21   | 0.95 | ... |  ← Separate table
|-----------|------|------|--------|------|-----|
| Nov 2025  | 1.02 | 1.38 | 1.18   | 0.92 | ... |
| Oct 2025  | 1.04 | 1.40 | 1.20   | 0.94 | ... |
| ...       | ...  | ...  | ...    | ...  | ... |
```

**Color Scheme** (Pastel):
- Multiple < 0.8: Light Green (#90EE90) - Very Cheap
- Multiple 0.8-0.95: Pale Green (#98FB98) - Cheap
- Multiple 0.95-1.05: Light Yellow (#FFFACD) - Fair
- Multiple 1.05-1.2: Peach (#FFDAB9) - Expensive
- Multiple > 1.2: Light Coral (#F08080) - Very Expensive

#### B. Current Valuations

**Purpose**: Show which sectors are currently cheap vs their OWN historical average

**UI Components**:
- [ ] Table: Sector, Current PE, Avg PE, Current Multiple, Avg Multiple, Status
- [ ] Status based on comparison to sector's own history (not just Nifty baseline)
- [ ] Color coding matches status

**Valuation Logic**:
```
For each sector:
    current_multiple = sector_pe / nifty_pe
    historical_avg_multiple = mean(last 120 months of multiples)
    
    if current_multiple < historical_avg_multiple * 0.85:
        status = "Cheap"
    elif current_multiple > historical_avg_multiple * 1.15:
        status = "Expensive"
    else:
        status = "Fair"
```

#### C. Index Details

**Purpose**: Detailed metrics for selected indices including earnings

**UI Components**:
- [ ] Multi-select for indices
- [ ] Time period selector (3, 5, 10 years)
- [ ] "Fetch Data" button (or auto-fetch when selections change)
- [ ] Charts: PE Trend, PB Trend, Index Value Trend
- [ ] Earnings Trend chart (derived from PE and Index Value)
- [ ] Earnings YoY Growth chart

**Data Caching**:
- Store fetched data in `st.session_state`
- Only fetch new data when period extends beyond cached range
- Auto-update charts when period changes (no button needed if data cached)

**Earnings Calculation**:
```
Earnings = Index Value / PE
YoY Growth = (Earnings[t] - Earnings[t-252]) / Earnings[t-252] * 100
```

### Acceptance Criteria

- [ ] Historical Matrix loads within 10 seconds (cached)
- [ ] Matrix shows 120 months of data
- [ ] Average table appears separately above historical data
- [ ] Color coding uses pastel colors
- [ ] Current Valuations compares to sector's own history
- [ ] Index Details shows all 5 charts (PE, PB, Value, Earnings, YoY Growth)
- [ ] Earnings charts show data for ALL selected indices
- [ ] Data caching works - period changes reflect immediately if data cached

### Error States

**E1: NSE API Timeout**
- Show: "Loading sector data..." then "Using cached data" after timeout
- Display cached matrix with warning about staleness

**E2: Individual Sector Fails**
- Show available sectors, indicate missing ones
- Don't fail entire matrix for one sector

**E3: Earnings Data Missing**
- If PE or Price missing, show: "Earnings data unavailable for [index]"
- Chart shows available indices only

---

## Sub-Tab 3: Fund Comparison

### Purpose

Compare mutual fund performance across different SIP strategies.

### Data Sources

| File | Content |
|------|---------|
| `fund_comparison_data.csv` | Weekly SIP comparison data |
| `daily_fund_comparison_data.csv` | Daily SIP comparison data |
| `monthly_fund_comparison_data.csv` | Monthly SIP comparison data |

### UI Components

#### Report Selection

- [ ] Tabs or radio: Weekly SIP, Daily SIP, Monthly SIP
- [ ] Data table with columns: Fund, AUM, Invested, Value, Return %, XIRR %
- [ ] Best strategy column showing which strategy worked best for each fund
- [ ] Filter/sort capabilities

#### Table Columns

| Column | Description |
|--------|-------------|
| Fund Name | Mutual fund name |
| AUM (Cr) | Assets Under Management |
| Base SIP Value | Returns with 1x SIP |
| Balanced Value | Returns with Balanced strategy |
| Opportunistic Value | Returns with Opportunistic strategy |
| Aggressive Value | Returns with Aggressive strategy |
| Hardcore Value | Returns with Hardcore strategy |
| Best Strategy | Strategy with highest returns |
| Best Return % | Return % of best strategy |

### Report Generation

Reports are pre-generated by:
- `generate_report.py` - Weekly SIP report
- `generate_daily_report.py` - Daily SIP report
- `generate_monthly_report.py` - Monthly SIP report

### Acceptance Criteria

- [ ] Weekly SIP report displays with all 33 funds
- [ ] Daily SIP report displays correctly
- [ ] Monthly SIP report displays correctly
- [ ] AUM column shows current AUM values
- [ ] Table is sortable by any column
- [ ] Best strategy correctly identified for each fund
- [ ] Can switch between Weekly/Daily/Monthly reports

### Error States

**E1: Report File Missing**
- Show: "Report not generated yet. Run generate_report.py"
- Provide button to trigger generation (if possible)

**E2: Stale Report Data**
- Show last generated timestamp
- Warn if > 7 days old

---

## Data Caching Strategy

### Sector PE Matrix

- **Cache Location**: `sector_pe_matrix_cache.csv`
- **Meta File**: `sector_pe_matrix_cache_meta.txt`
- **Stale Threshold**: 24 hours
- **Function**: `@st.cache_data(ttl=86400)` decorator

### Current Sector PE

- **Cache Location**: `sector_current_pe_cache.csv`
- **Meta File**: `sector_current_pe_cache_meta.txt`
- **Stale Threshold**: 1 hour

### Index Details Data

- **Cache Location**: `st.session_state['index_details_cache']`
- **Structure**: `{index_name: {start_date: DataFrame}}`
- **Behavior**: Persist within session, check before fetching

---

## Acceptance Criteria (Overall)

### Sector Valuations

- [ ] Tab loads without "Loading sector PE data..." hanging indefinitely
- [ ] Historical Matrix shows full 120 months
- [ ] Average table separate from historical matrix
- [ ] Pastel color scheme applied
- [ ] Current Valuations uses sector's own historical baseline
- [ ] Index Details shows all charts including earnings
- [ ] Earnings charts show ALL indices, not just first one

### Fund Comparison

- [ ] All three reports (Weekly, Daily, Monthly) accessible
- [ ] AUM data displayed for all funds
- [ ] Tables sortable
- [ ] Best strategy highlighted

### Performance

- [ ] Initial load < 10 seconds with cached data
- [ ] Tab switches < 2 seconds
- [ ] Matrix rendering < 3 seconds

---

## Edge Cases

### EC1: Empty Sector Data

**Scenario**: NSE returns empty for a sector
**Expected**: Skip that sector, show others, note which missing

### EC2: Very High PE Multiple

**Scenario**: Sector PE / Nifty PE > 5 (anomaly)
**Expected**: Cap display at 5.0, flag as "Anomalous"

### EC3: Negative PE (Losses)

**Scenario**: Index has negative PE (aggregate losses)
**Expected**: Show "N/A" instead of negative multiple

### EC4: No Cached Data Available

**Scenario**: First run, no cache files exist
**Expected**: Fetch fresh, show progress indicator

### EC5: Earnings Data Gaps

**Scenario**: PE available but Price missing for some dates
**Expected**: Show earnings only where both available, note gaps

---

## Test Scenarios

### T1: Sector Valuations - Historical Matrix

1. Navigate to Analysis → Sector Valuations → Historical Matrix
2. **Expected**: Matrix loads with 120 rows, all sectors as columns
3. **Expected**: Average table appears above matrix
4. **Expected**: Colors are pastel shades

### T2: Sector Valuations - Current Valuations

1. Navigate to Analysis → Sector Valuations → Current Valuations
2. **Expected**: Table shows all sectors with current vs historical comparison
3. **Expected**: Status reflects comparison to OWN history, not just Nifty

### T3: Index Details - All Charts

1. Navigate to Analysis → Sector Valuations → Index Details
2. Select: Nifty 50, Nifty Bank, Nifty IT
3. Select: 10 years
4. Click Fetch Data (or wait for auto-fetch)
5. **Expected**: PE chart shows 3 lines
6. **Expected**: Earnings chart shows 3 lines
7. **Expected**: YoY Growth chart shows 3 lines

### T4: Index Details - Cache Behavior

1. Fetch data for 5 years
2. Change to 3 years
3. **Expected**: Charts update immediately (data already cached)
4. Change to 10 years
5. **Expected**: Fetch only missing years, then update

### T5: Fund Comparison - Weekly Report

1. Navigate to Analysis → Fund Comparison
2. Select Weekly SIP
3. **Expected**: Table with 33 funds, AUM column visible
4. Sort by "Best Return %"
5. **Expected**: Table sorts correctly

### T6: Fund Comparison - Daily vs Weekly

1. View Weekly report, note top performer
2. Switch to Daily report
3. **Expected**: Data changes, potentially different rankings

### T7: API Timeout Recovery

1. Simulate slow network
2. Load Sector Valuations
3. **Expected**: Shows "Loading..." then falls back to cached data with warning

---

## Dependencies

### Internal

- `data_fetcher.py`: All sector and index data functions
- `etl_scheduler.py`: Background data refresh

### External

- `nsepython`: Sector PE data
- `yfinance`: Index prices
- `plotly`: Charts
- `streamlit`: UI

### Generated Files

- `sector_pe_matrix_cache.csv`
- `sector_current_pe_cache.csv`
- `fund_comparison_data.csv`
- `daily_fund_comparison_data.csv`
- `monthly_fund_comparison_data.csv`

---

## Notes

### Known Issues

1. NSE API can be slow/timeout - caching critical
2. Some sectors may have sparse PE data
3. Earnings calculation requires both PE and Price - may have gaps

### Future Enhancements

- Add PB ratio analysis to sector valuations
- Add sector rotation recommendations
- Add fund category comparison (Large Cap vs Mid Cap vs Flexi)
- Add historical fund comparison (not just current)

