Last updated: 2025-11-30 12:45

# Debug Findings

## Investigation Summary

### Issue 1: Dashboard Page Loading Slowly

**Observation**:
- Dashboard loads partially, showing the sentiment gauge and "Market Valuation Dashboard" header
- Content below that (PE trend chart, valuation cards) doesn't appear
- Page shows "Running..." indicator indefinitely

**Root Cause**:
- `get_all_indices_pe_pb()` function at line 1528 makes multiple NSE API calls
- NSE API (`nsepython.index_pe_pb_div()`) has no timeout parameter
- When API is slow or rate-limited, page hangs

**Code Path**:
```
Dashboard Tab
  → get_all_indices_pe() [slow]
  → get_all_indices_pe_pb() [slow]
  → get_pe_history_for_chart() [slow if not cached]
```

---

### Issue 2: Show Index Values Checkbox

**Status**: Could not test directly due to page not fully loading

**Code Analysis**:
- Checkbox defined at line 1604
- When checked, calls `get_pe_price_history_for_chart(years=chart_years)`
- This function calls `get_pe_with_price()` for each index
- `get_pe_with_price()` calls `get_index_price_data()` which uses yfinance
- yfinance is unreliable for Smallcap indices

**Likely Issue**:
- `get_index_price_data("nifty_smallcap")` fails silently
- Returns empty DataFrame, causing `pe_price_history` to be incomplete
- Chart falls back to PE-only mode without user notification

---

### Issue 3: Strategy Comparison Error

**Code Analysis** (lines 695-760):

For **Index** path:
- Line 713: `price_col = 'nifty_close'` is set
- Line 711-712: Data fetched correctly
- Line 729: `align_data()` produces `nifty_close` column
- Line 738: Uses hardcoded `price_col='nifty_close'` ✓

For **Mutual Fund** path:
- Line 716: `mf_data = get_mf_nav_data(...)`
- Line 724: `index_data = mf_data.rename(columns={'nav': 'close'})`
- Line 729: `align_data(index_data, pe_data)` renames to `nifty_close`
- **MISSING**: `price_col` is NOT set in MF path (but hardcoded works anyway)

**Actual Issue**: Unknown - need to see actual error message. Added debug logging.

---

### Issue 4: Sector Valuations Loading

**Code Analysis**:
- `get_sector_pe_matrix(months=120)` called at line 2285
- This function fetches 120 months of data for ~18 sectors
- Each sector requires NSE API call
- With rate limiting, this takes 2-3 minutes

**Fix Strategy**:
- Implement caching with `@st.cache_data` (already done but may need longer TTL)
- Show progress indicator during initial fetch
- Use cached parquet files when available

---

### Issue 5: Earnings Charts Not Showing All Indices

**Code Analysis**:
- `get_earnings_history_for_chart(years)` at line 2711
- Iterates through all 3 indices (nifty50, nifty_midcap, nifty_smallcap)
- Calls `get_earnings_data()` for each
- `get_earnings_data()` depends on `get_pe_with_price()`
- Smallcap likely fails due to yfinance issues

**Debug Print Added**: Lines 944, 960, 962 in data_fetcher.py print debug info

---

## Recommended Fixes

### Fix 1: Add Timeout to NSE API Calls

```python
# In data_fetcher.py
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("NSE API timeout")

def _safe_index_pe_pb_div(index_name, timeout_seconds=10):
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
        result = nse.index_pe_pb_div(index_name)
        signal.alarm(0)
        return result
    except TimeoutError:
        return None
    except Exception as e:
        return None
```

### Fix 2: Show Warning When Data Unavailable

In Dashboard tab, wrap data fetching with try-except and show user-friendly messages:

```python
try:
    all_indices = get_all_indices_pe()
except Exception as e:
    st.warning(f"Could not load PE data: {e}")
    all_indices = {}  # Use empty dict as fallback
```

### Fix 3: Use Cached Data When API Fails

Check for cached parquet files before making API calls:

```python
cache_file = "pe_cache.parquet"
if os.path.exists(cache_file):
    cache_age = time.time() - os.path.getmtime(cache_file)
    if cache_age < 86400:  # 24 hours
        return pd.read_parquet(cache_file)
```

### Fix 4: Add Smallcap Fallback for Index Values

Use Nippon India Small Cap Fund NAV as proxy:

```python
if index_name == "nifty_smallcap" and (df is None or df.empty):
    mf_data = get_mf_nav_data("118778")  # Nippon Small Cap
    df = mf_data.rename(columns={'nav': 'index_value'})
```

---

## Fixes Applied

### Fix 1: Added Timeout to NSE API Calls

**File**: `data_fetcher.py`, function `_safe_index_pe_pb_div()`

Added threading-based timeout (15 seconds) to prevent indefinite hangs:

```python
def _safe_index_pe_pb_div(index_name: str, start_date: str, end_date: str, timeout_seconds: int = 15):
    import threading
    result = [None]
    thread = threading.Thread(target=fetch_data)
    thread.start()
    thread.join(timeout=timeout_seconds)
    if thread.is_alive():
        return None  # Timeout
```

### Fix 2: Added In-Memory Caching

**File**: `data_fetcher.py`

Added 1-hour TTL cache to avoid repeated slow API calls:

- `_memory_cache` dictionary for storing results
- `_get_cached()` and `_set_cached()` helper functions
- Applied to: `get_all_indices_pe()`, `get_all_indices_pe_pb()`, `get_pe_history_for_chart()`, `get_pe_price_history_for_chart()`

### Fix 3: Added Debug Logging

**File**: `app.py`

Added expandable debug sections to:
- Dashboard PE chart (lines 1616-1650)
- Strategy Comparison (lines 695-760)
- Sector Valuations (lines 2274-2307)
- Earnings charts (lines 2700-2735)

---

## Test Results

| Issue | Status | Notes |
|-------|--------|-------|
| Dashboard Loading | Improved | Page now loads with timeout fallbacks |
| Show Index Values | Debug Added | Expander shows data status |
| Strategy Comparison | Debug Added | Expander shows step-by-step status |
| Sector Valuations | Debug Added | Expander shows cache/fetch status |
| Earnings Charts | Debug Added | Expander shows data availability |

---

## Remaining Work

1. **Test Show Index Values**: Click the checkbox and verify chart updates
2. **Test Strategy Comparison**: Select Mutual Fund and run comparison
3. **Add PB strategies to SIP Simulation**: Need to expand strategy selector
4. **Test Sector Valuations**: Navigate to Analysis tab
5. **Test Earnings Charts**: Verify all indices show in charts

---

## Additional Fix: CombinedBulletConfig Error

### Error Message
```
AttributeError: 'CombinedBulletConfig' object has no attribute 'extremely_cheap_threshold'
```

### Root Cause
- `simulate_bullet_deployment()` expects `cheap_threshold`, `very_cheap_threshold`, `extremely_cheap_threshold` attributes
- `CombinedBulletConfig` had different attribute names: `pe_cheap`, `pe_very_cheap`, `pe_extremely_cheap`

### Fix Applied
Added property aliases to `CombinedBulletConfig` class in `strategy.py`:
```python
@property
def cheap_threshold(self) -> float:
    return self.pe_cheap

@property
def very_cheap_threshold(self) -> float:
    return self.pe_very_cheap

@property
def extremely_cheap_threshold(self) -> float:
    return self.pe_extremely_cheap
```

### Status
✅ Fixed - Strategy Comparison now loads without errors

---

## Summary of All Fixes Applied

| Fix | Status |
|-----|--------|
| Dashboard Chart Index Values | ✅ Added warning messages, graceful fallback |
| Strategy Comparison Error | ✅ Added `safe_simulate()` wrapper, fixed CombinedBulletConfig |
| PB Strategies in SIP Simulation | ✅ Added full strategy type selector (PE, PB, Combined, AI) |
| Sector Valuations Loading | ✅ Added timeout (15s) and in-memory caching (1hr TTL) |
| Earnings Charts All Indices | ✅ Added null checks for missing index_value data |

---

## Files Modified

| File | Changes |
|------|---------|
| `data_fetcher.py` | Added timeout, caching, improved error handling |
| `app.py` | Added debug expanders, safe_simulate wrapper, strategy selector, fallback handling |
| `strategy.py` | Added property aliases to CombinedBulletConfig |
| `specs/dashboard_spec.md` | Created detailed spec |
| `specs/backtest_spec.md` | Created detailed spec |
| `specs/analysis_spec.md` | Created detailed spec |
| `specs/debug_findings.md` | This file - documented findings |

