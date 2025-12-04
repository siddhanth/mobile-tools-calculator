Last updated: 2025-12-03

# US Markets Tab Specification

## Overview

The US Markets tab provides a real-time overview of US market conditions including the S&P 500, NASDAQ, and Russell 2000. It mirrors the functionality of the India Dashboard but uses US-specific data sources and benchmarks.

---

## Data Sources

### Functions Used

| Function | File | Purpose | Caching |
|----------|------|---------|---------|
| `get_all_us_indices_pe_pb()` | us_data_fetcher.py | Fetch current PE, PB for US indices | Memory + Disk (1 hour) |
| `get_fear_greed_index()` | us_data_fetcher.py | Calculate Fear & Greed sentiment | Memory (30 min) |
| `get_us_pe_history_for_chart(years)` | us_data_fetcher.py | Historical PE estimates | Disk (24 hours) |
| `get_us_price_history_for_chart(years)` | us_data_fetcher.py | Historical index prices | Disk (24 hours) |
| `get_us_sector_performance()` | us_data_fetcher.py | Sector ETF performance | Memory (1 hour) |
| `get_vix_data()` | us_data_fetcher.py | VIX volatility index | Memory (30 min) |
| `scrape_shiller_pe()` | us_data_fetcher.py | Shiller CAPE ratio | Memory (1 hour) |

### External Data Sources

| Source | Purpose | Method | Fallback |
|--------|---------|--------|----------|
| Yahoo Finance (yfinance) | Index prices, ETF data | Python API | Cached data |
| SPY, QQQ, IWM ETFs | PE/PB proxies for indices | yfinance info | Historical benchmarks |
| VIX (^VIX) | Volatility/Fear indicator | yfinance | Static value (20) |
| multpl.com | Shiller PE (CAPE) | Web scraping | Static value (30) |

### US Index Symbols

```python
US_INDEX_SYMBOLS = {
    "sp500": "^GSPC",       # S&P 500
    "nasdaq": "^IXIC",      # NASDAQ Composite
    "russell2000": "^RUT",  # Russell 2000
    "dow": "^DJI",          # Dow Jones Industrial Average
    "nasdaq100": "^NDX",    # NASDAQ 100
    "vix": "^VIX",          # Volatility Index
}
```

### Sector ETFs Tracked

```python
US_SECTOR_ETFS = {
    "XLF": "Financials",
    "XLK": "Technology",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication Services",
}
```

---

## Data Flow

```
User loads US Markets tab
    │
    ├─► get_fear_greed_index() ─► Sentiment gauge
    │
    ├─► get_all_us_indices_pe_pb() ─► Valuation cards (S&P, NASDAQ, Russell)
    │
    ├─► get_vix_data() + scrape_shiller_pe() ─► Volatility section
    │
    ├─► get_us_price_history_for_chart(years) ─► Price trend chart
    │
    └─► get_us_sector_performance() ─► Sector ETF table & chart
```

---

## UI Components

### 1. Fear & Greed Sentiment Gauge

**Location**: Top of US Markets tab
**Purpose**: Visual indicator of overall US market sentiment

**Calculation Method**:
```
Fear & Greed Score = (VIX Score × 50%) + (Momentum Score × 30%) + (High Proximity Score × 20%)

Where:
- VIX Score = 100 - (VIX - 12) × 3  (VIX 12 = 100, VIX 45 = 0)
- Momentum Score = 50 + (50-day momentum %) × 3
- High Proximity Score = (Current Price / 52-week High) × 100
```

**Sentiment Zones**:
| Score | Zone | Color |
|-------|------|-------|
| 0-20 | Extreme Fear | Red (#dc2626) |
| 20-40 | Fear | Orange (#f97316) |
| 40-60 | Neutral | Yellow (#eab308) |
| 60-80 | Greed | Light Green (#22c55e) |
| 80-100 | Extreme Greed | Dark Green (#16a34a) |

**Requirements**:
- [ ] Arc-shaped gauge with 5 segments
- [ ] Labels on arc: EXTREME FEAR, FEAR, NEUTRAL, GREED, EXTREME GREED
- [ ] Needle pointing to current score
- [ ] Info panel showing VIX, Momentum, 52-week high proximity

### 2. Current Valuation Cards

**Location**: Below sentiment gauge
**Purpose**: Show current PE, PB for each US index

**Indices Displayed**:
- S&P 500 (via SPY ETF)
- NASDAQ (via QQQ ETF)
- Russell 2000 (via IWM ETF)

**Card Contents**:
- Current price with daily change
- PE Ratio (from ETF)
- PB Ratio (from ETF)
- Dividend Yield
- Valuation zone (based on historical PE benchmarks)

**PE Benchmarks (S&P 500)**:
| Percentile | PE Value |
|------------|----------|
| P10 (Very Cheap) | 13.0 |
| P25 (Cheap) | 15.5 |
| Median (Fair) | 18.5 |
| P75 (Expensive) | 23.0 |
| P90 (Very Expensive) | 28.0 |

### 3. Volatility Section

**Location**: Below valuation cards
**Layout**: Two columns

**Column 1: VIX Display**
- Current VIX value
- 1-month average, high, low
- Interpretation (Complacency → Fear)

**VIX Interpretation**:
| VIX Level | Interpretation |
|-----------|----------------|
| < 12 | Extremely Low (Complacency) |
| 12-17 | Low (Calm) |
| 17-22 | Normal |
| 22-30 | Elevated (Concern) |
| > 30 | High (Fear) |

**Column 2: Shiller PE (CAPE)**
- Current CAPE value
- Historical median (16.0) and mean (17.1)
- Valuation zone

### 4. Historical Trend Charts

**Location**: Main chart area
**Controls**:
- Time period: 1, 3, 5, 10 years
- Show Index Prices checkbox
- Index visibility toggles (S&P 500, NASDAQ, Russell 2000)

**Charts**:
1. **Index Price Chart**: Historical prices for selected indices
2. **Estimated PE Chart**: PE trend estimates based on price movements

**Note**: PE history is estimated from price movements since direct historical PE data requires paid sources.

### 5. Sector Performance Table

**Location**: Bottom of tab
**Content**: US sector ETF performance

**Table Columns**:
| Column | Description |
|--------|-------------|
| Symbol | ETF ticker (XLF, XLK, etc.) |
| Sector | Sector name |
| Price | Current price |
| PE | Trailing PE ratio |
| 1D % | 1-day return |
| 1W % | 1-week return |
| 1M % | 1-month return |
| YTD % | Year-to-date return |

**Visual**: Bar chart of YTD returns by sector

---

## User Interactions

### Checkboxes

| Checkbox | Key | Default | Action |
|----------|-----|---------|--------|
| Show Index Prices | `us_show_prices` | True | Shows price chart |
| S&P 500 | `us_show_sp500` | True | Toggle S&P 500 visibility |
| NASDAQ | `us_show_nasdaq` | True | Toggle NASDAQ visibility |
| Russell 2000 | `us_show_russell` | True | Toggle Russell visibility |

### Dropdowns

| Dropdown | Key | Options | Default |
|----------|-----|---------|---------|
| Time Period | `us_chart_years` | 1, 3, 5, 10 | 5 |

---

## Error States

### E1: Yahoo Finance API Failure

**Trigger**: yfinance returns empty data
**Behavior**:
- Show cached data with warning
- Fall back to historical benchmarks

### E2: VIX Data Unavailable

**Trigger**: VIX fetch fails
**Behavior**:
- Use static value (20) for Fear & Greed calculation
- Show warning about estimated sentiment

### E3: Shiller PE Scraping Fails

**Trigger**: multpl.com unavailable or page structure changed
**Behavior**:
- Use fallback value (30)
- Show "Data unavailable" note

### E4: Sector ETF Partial Failure

**Trigger**: Some ETF data unavailable
**Behavior**:
- Show available sectors
- Skip missing ones silently

---

## Caching Strategy

### Memory Cache (Fast, Session-bound)

| Data | TTL | Key Pattern |
|------|-----|-------------|
| Fear & Greed | 30 min | `fear_greed_index` |
| VIX Data | 30 min | `vix_data` |
| US Indices PE/PB | 1 hour | `all_us_indices_pe_pb` |
| Sector Performance | 1 hour | `us_sector_performance` |
| Shiller PE | 1 hour | `shiller_pe` |

### Disk Cache (Persistent)

| Data | TTL | Location |
|------|-----|----------|
| Price History | 24 hours | `.cache/us_markets/us_price_history_{years}.json` |
| PE History | 24 hours | `.cache/us_markets/us_pe_history_{years}.json` |
| All cached data | 24 hours | `.cache/us_markets/*.json` |

---

## Acceptance Criteria

### Core Functionality

- [ ] Tab loads within 5 seconds on cached data
- [ ] Fear & Greed gauge displays with correct sentiment
- [ ] All 3 index valuation cards display correctly
- [ ] VIX and Shiller PE section loads
- [ ] Price trend chart renders with correct data
- [ ] Sector performance table displays all 11 sectors

### Gauge Functionality

- [ ] Gauge shows 5 colored segments
- [ ] Labels appear on arc
- [ ] Needle points to current score
- [ ] Info panel shows component values

### Chart Functionality

- [ ] Time period selector changes data range
- [ ] Index toggles hide/show respective lines
- [ ] Hover shows date and values

### Error Handling

- [ ] API failures show cached data with warning
- [ ] Missing data shows partial information
- [ ] No unhandled exceptions

---

## Comparison with India Dashboard

| Feature | India Dashboard | US Markets |
|---------|-----------------|------------|
| Sentiment Gauge | ExitMantra-style (PE-based) | Fear & Greed (VIX + Momentum) |
| Indices | Nifty 50, Midcap, Smallcap | S&P 500, NASDAQ, Russell |
| PE Source | nsepython API | ETF proxies (SPY, QQQ, IWM) |
| Additional Metrics | - | VIX, Shiller PE (CAPE) |
| Sector View | NSE Sectoral Indices | Sector ETFs (XLF, XLK, etc.) |

---

## Known Limitations

1. **PE Data is Estimated**: US index PE from ETF proxies, not official index data
2. **Historical PE Approximated**: Based on price movements, not actual earnings data
3. **Shiller PE via Scraping**: May break if multpl.com changes page structure
4. **No Mutual Fund Data**: US MF/ETF NAV comparison not yet implemented

---

## Future Enhancements

- Add historical Shiller PE chart
- Add put/call ratio indicator
- Add Treasury yield curve
- Add market breadth indicators (advance/decline)
- Add US mutual fund/ETF comparison similar to India Analysis tab
- Integrate with FRED API for more economic indicators

---

## Dependencies

### Internal

- `us_data_fetcher.py`: All US market data functions

### External

- `yfinance`: Index and ETF data
- `requests`: HTTP calls for web scraping
- `beautifulsoup4`: Shiller PE scraping
- `plotly`: Charts
- `streamlit`: UI framework

---

## Test Scenarios

### T1: Fresh Load

1. Navigate to US Markets tab
2. **Expected**: Sentiment gauge, valuation cards, charts all load

### T2: Toggle Index Visibility

1. Load US Markets tab
2. Uncheck "S&P 500"
3. **Expected**: S&P 500 line disappears from charts

### T3: Change Time Period

1. Load with 5Y default
2. Select "10 Years"
3. **Expected**: Charts show 10 years of data

### T4: API Failure Recovery

1. Simulate network failure
2. Load US Markets tab
3. **Expected**: Cached data shown with warning

### T5: Sector Performance Sorting

1. Load US Markets tab
2. View sector table
3. **Expected**: Table sorted by YTD return (descending)



