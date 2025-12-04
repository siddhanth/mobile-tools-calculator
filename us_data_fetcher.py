"""
US Market Data Fetcher Module
Fetches S&P 500, NASDAQ, Russell 2000 prices, PE ratios, and sentiment data
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
from datetime import datetime, timedelta
from pathlib import Path
import json
import time
from functools import wraps
from bs4 import BeautifulSoup

# Cache directory
CACHE_DIR = Path(__file__).parent / ".cache" / "us_markets"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache
_memory_cache = {}
_cache_timestamps = {}
CACHE_TTL_SECONDS = 3600  # 1 hour for memory cache
DISK_CACHE_TTL_SECONDS = 86400  # 24 hours for disk cache


def _get_disk_cache_path(key: str) -> Path:
    """Get the file path for a disk cache key."""
    safe_key = key.replace("/", "_").replace(":", "_").replace(" ", "_")
    return CACHE_DIR / f"{safe_key}.json"


def _get_disk_cached(key: str, ttl: int = DISK_CACHE_TTL_SECONDS):
    """Get value from disk cache if not expired."""
    cache_file = _get_disk_cache_path(key)
    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            if time.time() - data.get('timestamp', 0) < ttl:
                value = data.get('value')
                if isinstance(value, dict) and '_dataframe_' in value:
                    return pd.DataFrame(value['data'])
                return value
    except Exception:
        pass
    return None


def _set_disk_cached(key: str, value):
    """Store value in disk cache."""
    try:
        cache_file = _get_disk_cache_path(key)
        if isinstance(value, pd.DataFrame):
            serializable_value = {
                '_dataframe_': True,
                'data': value.to_dict(orient='records')
            }
        else:
            serializable_value = value
        cache_file.write_text(json.dumps({
            'timestamp': time.time(),
            'value': serializable_value
        }, default=str))
    except Exception:
        pass


def _get_cached(key: str, ttl: int = CACHE_TTL_SECONDS):
    """Get value from memory cache, then disk cache."""
    if key in _memory_cache and key in _cache_timestamps:
        if time.time() - _cache_timestamps[key] < ttl:
            return _memory_cache[key]
    
    disk_value = _get_disk_cached(key, DISK_CACHE_TTL_SECONDS)
    if disk_value is not None:
        _memory_cache[key] = disk_value
        _cache_timestamps[key] = time.time()
        return disk_value
    
    return None


def _set_cached(key: str, value):
    """Store value in both memory and disk cache."""
    _memory_cache[key] = value
    _cache_timestamps[key] = time.time()
    _set_disk_cached(key, value)


# US Index symbols
US_INDEX_SYMBOLS = {
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "russell2000": "^RUT",
    "dow": "^DJI",
    "nasdaq100": "^NDX",
    "vix": "^VIX",
}

# US Sector ETF symbols
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

# Historical PE benchmarks (based on long-term averages)
US_PE_BENCHMARKS = {
    "sp500": {
        "p10": 13.0,
        "p25": 15.5,
        "median": 18.5,
        "p75": 23.0,
        "p90": 28.0,
        "current_avg": 22.0,  # Approximate current long-term average
    },
    "nasdaq": {
        "p10": 18.0,
        "p25": 22.0,
        "median": 28.0,
        "p75": 35.0,
        "p90": 45.0,
        "current_avg": 30.0,
    },
    "russell2000": {
        "p10": 14.0,
        "p25": 18.0,
        "median": 22.0,
        "p75": 28.0,
        "p90": 35.0,
        "current_avg": 24.0,
    },
}

# CAPE/Shiller PE historical data URL
SHILLER_PE_URL = "https://www.multpl.com/shiller-pe/table/by-month"


def get_us_index_data(index_name: str, start_date: str, end_date: str, interval: str = "1wk") -> pd.DataFrame:
    """
    Fetch US index historical price data from yfinance
    
    Args:
        index_name: Index identifier (sp500, nasdaq, russell2000, dow, nasdaq100)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval (1d, 1wk, 1mo)
    
    Returns:
        DataFrame with Date and Close columns
    """
    symbol = US_INDEX_SYMBOLS.get(index_name, "^GSPC")
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if hist.empty:
            raise ValueError(f"No data returned for {index_name}")
        
        df = hist[['Close']].reset_index()
        df.columns = ['date', 'close']
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        
        return df
    
    except Exception as e:
        raise Exception(f"Error fetching {index_name} data: {e}")


def get_us_index_current(index_name: str = "sp500") -> dict:
    """
    Get current price and basic info for a US index.
    
    Returns:
        Dictionary with current price and change info
    """
    symbol = US_INDEX_SYMBOLS.get(index_name, "^GSPC")
    
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="5d")
        
        if hist.empty:
            return {"error": "No data available"}
        
        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price) * 100
        
        return {
            "price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "previous_close": round(prev_price, 2),
            "symbol": symbol,
            "name": info.get("shortName", index_name),
        }
    except Exception as e:
        return {"error": str(e)}


def get_sp500_pe_from_yfinance() -> dict:
    """
    Get S&P 500 PE ratio from yfinance SPY ETF as proxy.
    
    Returns:
        Dictionary with PE and related metrics
    """
    cache_key = "sp500_pe_yfinance"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached
    
    try:
        # Use SPY ETF as proxy for S&P 500
        spy = yf.Ticker("SPY")
        info = spy.info
        
        pe_ratio = info.get("trailingPE", None) or info.get("forwardPE", None)
        
        if pe_ratio is None:
            # Fallback: estimate from constituent data
            pe_ratio = 22.0  # Approximate average
        
        result = {
            "pe": round(pe_ratio, 2),
            "source": "yfinance (SPY)",
            "timestamp": datetime.now().isoformat(),
        }
        
        _set_cached(cache_key, result)
        return result
    except Exception as e:
        return {"pe": 22.0, "error": str(e), "source": "fallback"}


def scrape_shiller_pe() -> dict:
    """
    Scrape the Shiller PE (CAPE) ratio from multpl.com
    
    Returns:
        Dictionary with current CAPE and historical context
    """
    cache_key = "shiller_pe"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(SHILLER_PE_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the first data row in the table
        table = soup.find('table', {'id': 'datatable'})
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                first_row = rows[1]  # Skip header
                cells = first_row.find_all('td')
                if len(cells) >= 2:
                    pe_text = cells[1].get_text().strip()
                    pe_value = float(pe_text)
                    
                    result = {
                        "cape": round(pe_value, 2),
                        "source": "multpl.com",
                        "timestamp": datetime.now().isoformat(),
                        "historical_median": 16.0,
                        "historical_mean": 17.1,
                    }
                    
                    _set_cached(cache_key, result)
                    return result
        
        # Fallback if scraping fails
        return {"cape": 30.0, "source": "fallback", "error": "Could not parse page"}
    
    except Exception as e:
        return {"cape": 30.0, "source": "fallback", "error": str(e)}


def get_fear_greed_index() -> dict:
    """
    Get CNN Fear & Greed Index (estimated from VIX and market data).
    Since CNN doesn't provide an API, we calculate a proxy using VIX and market momentum.
    
    Fear & Greed Scale: 0 = Extreme Fear, 50 = Neutral, 100 = Extreme Greed
    
    Returns:
        Dictionary with fear/greed score and interpretation
    """
    cache_key = "fear_greed_index"
    cached = _get_cached(cache_key, ttl=1800)  # 30 min cache
    if cached is not None:
        return cached
    
    try:
        # Get VIX (fear indicator)
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="1mo")
        
        if vix_hist.empty:
            raise ValueError("No VIX data")
        
        current_vix = vix_hist['Close'].iloc[-1]
        avg_vix = vix_hist['Close'].mean()
        
        # Get S&P 500 for momentum
        sp500 = yf.Ticker("^GSPC")
        sp_hist = sp500.history(period="3mo")
        
        if sp_hist.empty:
            raise ValueError("No S&P 500 data")
        
        # Calculate 50-day momentum
        if len(sp_hist) >= 50:
            momentum = (sp_hist['Close'].iloc[-1] / sp_hist['Close'].iloc[-50] - 1) * 100
        else:
            momentum = 0
        
        # Calculate 52-week high proximity
        sp_1y = sp500.history(period="1y")
        if not sp_1y.empty:
            year_high = sp_1y['Close'].max()
            current = sp_hist['Close'].iloc[-1]
            high_proximity = (current / year_high) * 100
        else:
            high_proximity = 90
        
        # Calculate Fear & Greed Score (0-100)
        # VIX component: Lower VIX = more greed (inverted scale)
        vix_score = max(0, min(100, 100 - (current_vix - 12) * 3))  # VIX 12=100, VIX 45=0
        
        # Momentum component: Positive momentum = greed
        momentum_score = max(0, min(100, 50 + momentum * 3))
        
        # High proximity component: Close to high = greed
        high_score = high_proximity
        
        # Weighted average
        fear_greed_score = (vix_score * 0.5 + momentum_score * 0.3 + high_score * 0.2)
        fear_greed_score = max(0, min(100, fear_greed_score))
        
        # Determine sentiment label
        if fear_greed_score <= 20:
            sentiment = "Extreme Fear"
            color = "#dc2626"  # Red
        elif fear_greed_score <= 40:
            sentiment = "Fear"
            color = "#f97316"  # Orange
        elif fear_greed_score <= 60:
            sentiment = "Neutral"
            color = "#eab308"  # Yellow
        elif fear_greed_score <= 80:
            sentiment = "Greed"
            color = "#22c55e"  # Light Green
        else:
            sentiment = "Extreme Greed"
            color = "#16a34a"  # Dark Green
        
        result = {
            "score": round(fear_greed_score, 1),
            "sentiment": sentiment,
            "color": color,
            "vix": round(current_vix, 2),
            "vix_avg": round(avg_vix, 2),
            "momentum": round(momentum, 2),
            "high_proximity": round(high_proximity, 1),
            "timestamp": datetime.now().isoformat(),
            "source": "Calculated (VIX + Momentum)",
        }
        
        _set_cached(cache_key, result)
        return result
    
    except Exception as e:
        return {
            "score": 50,
            "sentiment": "Neutral",
            "color": "#eab308",
            "error": str(e),
            "source": "fallback",
        }


def get_all_us_indices_pe_pb() -> dict:
    """
    Get current PE, estimated PB, and valuation for all tracked US indices.
    
    Returns:
        Dictionary with index names as keys and valuation info as values
    """
    cache_key = "all_us_indices_pe_pb"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None:
        return cached
    
    indices_info = {
        "sp500": ("S&P 500", "SPY", "^GSPC"),
        "nasdaq": ("NASDAQ Composite", "QQQ", "^IXIC"),
        "russell2000": ("Russell 2000", "IWM", "^RUT"),
    }
    
    result = {}
    
    for idx_key, (name, etf_symbol, index_symbol) in indices_info.items():
        try:
            # Get PE from ETF
            etf = yf.Ticker(etf_symbol)
            etf_info = etf.info
            
            pe = etf_info.get("trailingPE") or etf_info.get("forwardPE")
            pb = etf_info.get("priceToBook")
            div_yield = etf_info.get("trailingAnnualDividendYield", 0) * 100 if etf_info.get("trailingAnnualDividendYield") else 0
            
            # Get benchmark data
            benchmarks = US_PE_BENCHMARKS.get(idx_key, US_PE_BENCHMARKS["sp500"])
            
            # Calculate valuation zone
            if pe:
                if pe <= benchmarks["p10"]:
                    zone = "Very Cheap"
                    zone_color = "#10b981"
                elif pe <= benchmarks["p25"]:
                    zone = "Cheap"
                    zone_color = "#22c55e"
                elif pe <= benchmarks["p75"]:
                    zone = "Fair"
                    zone_color = "#eab308"
                elif pe <= benchmarks["p90"]:
                    zone = "Expensive"
                    zone_color = "#f97316"
                else:
                    zone = "Very Expensive"
                    zone_color = "#ef4444"
            else:
                zone = "Unknown"
                zone_color = "#6b7280"
                pe = benchmarks.get("current_avg", 22)
            
            # Get current index price
            index_ticker = yf.Ticker(index_symbol)
            index_hist = index_ticker.history(period="5d")
            current_price = index_hist['Close'].iloc[-1] if not index_hist.empty else None
            change_pct = None
            if not index_hist.empty and len(index_hist) > 1:
                change_pct = ((index_hist['Close'].iloc[-1] - index_hist['Close'].iloc[-2]) / 
                              index_hist['Close'].iloc[-2]) * 100
            
            result[idx_key] = {
                "name": name,
                "pe": round(pe, 2) if pe else None,
                "pb": round(pb, 2) if pb else None,
                "div_yield": round(div_yield, 2),
                "zone": zone,
                "zone_color": zone_color,
                "thresholds": benchmarks,
                "median": benchmarks["median"],
                "price": round(current_price, 2) if current_price else None,
                "change_pct": round(change_pct, 2) if change_pct else None,
            }
        
        except Exception as e:
            result[idx_key] = {
                "name": name,
                "error": str(e),
                "pe": US_PE_BENCHMARKS.get(idx_key, {}).get("current_avg", 22),
                "zone": "Unknown",
                "zone_color": "#6b7280",
            }
    
    _set_cached(cache_key, result)
    return result


def get_us_pe_history_for_chart(years: int = 10) -> pd.DataFrame:
    """
    Get historical PE estimates for US indices.
    Since direct PE history isn't available, we use price history 
    and estimate PE trends based on earnings growth assumptions.
    
    Args:
        years: Number of years of history
    
    Returns:
        DataFrame with date and PE columns for each index
    """
    cache_key = f"us_pe_history_{years}"
    cached = _get_cached(cache_key, ttl=86400)  # 24 hour cache
    if cached is not None and isinstance(cached, pd.DataFrame):
        return cached
    
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    indices = {
        "sp500": ("^GSPC", "S&P 500"),
        "nasdaq": ("^IXIC", "NASDAQ"),
        "russell2000": ("^RUT", "Russell 2000"),
    }
    
    result_df = None
    
    for idx_key, (symbol, name) in indices.items():
        try:
            df = get_us_index_data(idx_key, start_date, end_date, interval="1wk")
            
            if df is not None and not df.empty:
                # Normalize prices to create a PE-like trend
                # This is an approximation - we scale prices to typical PE ranges
                benchmarks = US_PE_BENCHMARKS.get(idx_key, US_PE_BENCHMARKS["sp500"])
                
                # Use price relative to a baseline to estimate PE movement
                baseline = df['close'].iloc[0]
                current = df['close'].iloc[-1]
                current_pe_estimate = benchmarks["current_avg"]
                
                # Scale factor: assume PE moves proportionally to price/earnings growth ratio
                # This is a simplification - real PE would need earnings data
                scale_factor = current_pe_estimate / (current / baseline)
                df['pe'] = (df['close'] / baseline) * scale_factor * benchmarks["median"] / benchmarks["current_avg"]
                
                # Smooth the PE series
                df['pe'] = df['pe'].rolling(window=4, min_periods=1).mean()
                
                df = df.rename(columns={'pe': name})
                
                if result_df is None:
                    result_df = df[['date', name]]
                else:
                    result_df = pd.merge(result_df, df[['date', name]], on='date', how='outer')
        
        except Exception as e:
            print(f"Error loading PE data for {idx_key}: {e}")
    
    if result_df is not None:
        result_df = result_df.sort_values('date').ffill()
        _set_cached(cache_key, result_df)
    
    return result_df


def get_us_price_history_for_chart(years: int = 10) -> pd.DataFrame:
    """
    Get historical price data for US indices.
    
    Args:
        years: Number of years of history
    
    Returns:
        DataFrame with date and price columns for each index
    """
    cache_key = f"us_price_history_{years}"
    cached = _get_cached(cache_key, ttl=86400)
    if cached is not None and isinstance(cached, pd.DataFrame):
        return cached
    
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    indices = {
        "sp500": ("^GSPC", "S&P 500"),
        "nasdaq": ("^IXIC", "NASDAQ"),
        "russell2000": ("^RUT", "Russell 2000"),
    }
    
    result_df = None
    
    for idx_key, (symbol, name) in indices.items():
        try:
            df = get_us_index_data(idx_key, start_date, end_date, interval="1wk")
            
            if df is not None and not df.empty:
                df = df.rename(columns={'close': f'{name} Value'})
                
                if result_df is None:
                    result_df = df[['date', f'{name} Value']]
                else:
                    result_df = pd.merge(result_df, df[['date', f'{name} Value']], on='date', how='outer')
        
        except Exception as e:
            print(f"Error loading price data for {idx_key}: {e}")
    
    if result_df is not None:
        result_df = result_df.sort_values('date').ffill()
        _set_cached(cache_key, result_df)
    
    return result_df


def get_us_sector_performance() -> pd.DataFrame:
    """
    Get current performance metrics for US sector ETFs.
    
    Returns:
        DataFrame with sector performance data
    """
    cache_key = "us_sector_performance"
    cached = _get_cached(cache_key, ttl=3600)
    if cached is not None and isinstance(cached, pd.DataFrame):
        return cached
    
    results = []
    
    for symbol, name in US_SECTOR_ETFS.items():
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")
            
            if hist.empty:
                continue
            
            current_price = hist['Close'].iloc[-1]
            
            # Calculate returns
            returns_1d = ((current_price / hist['Close'].iloc[-2]) - 1) * 100 if len(hist) > 1 else 0
            returns_1w = ((current_price / hist['Close'].iloc[-5]) - 1) * 100 if len(hist) > 5 else 0
            returns_1m = ((current_price / hist['Close'].iloc[-22]) - 1) * 100 if len(hist) > 22 else 0
            returns_ytd = ((current_price / hist['Close'].iloc[0]) - 1) * 100
            
            pe = info.get("trailingPE") or info.get("forwardPE")
            
            results.append({
                "symbol": symbol,
                "sector": name,
                "price": round(current_price, 2),
                "pe": round(pe, 2) if pe else None,
                "1d_return": round(returns_1d, 2),
                "1w_return": round(returns_1w, 2),
                "1m_return": round(returns_1m, 2),
                "ytd_return": round(returns_ytd, 2),
            })
        
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
    
    df = pd.DataFrame(results)
    _set_cached(cache_key, df)
    return df


def get_vix_data() -> dict:
    """
    Get current VIX (volatility index) data.
    
    Returns:
        Dictionary with VIX value and interpretation
    """
    cache_key = "vix_data"
    cached = _get_cached(cache_key, ttl=1800)
    if cached is not None:
        return cached
    
    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1mo")
        
        if hist.empty:
            raise ValueError("No VIX data")
        
        current = hist['Close'].iloc[-1]
        avg = hist['Close'].mean()
        high = hist['Close'].max()
        low = hist['Close'].min()
        
        # Interpret VIX level
        if current < 12:
            interpretation = "Extremely Low (Complacency)"
            color = "#16a34a"
        elif current < 17:
            interpretation = "Low (Calm)"
            color = "#22c55e"
        elif current < 22:
            interpretation = "Normal"
            color = "#eab308"
        elif current < 30:
            interpretation = "Elevated (Concern)"
            color = "#f97316"
        else:
            interpretation = "High (Fear)"
            color = "#ef4444"
        
        result = {
            "current": round(current, 2),
            "avg_1m": round(avg, 2),
            "high_1m": round(high, 2),
            "low_1m": round(low, 2),
            "interpretation": interpretation,
            "color": color,
            "timestamp": datetime.now().isoformat(),
        }
        
        _set_cached(cache_key, result)
        return result
    
    except Exception as e:
        return {
            "current": 20.0,
            "interpretation": "Normal",
            "color": "#eab308",
            "error": str(e),
        }


if __name__ == "__main__":
    # Test the data fetchers
    print("Testing US Market data fetchers...")
    
    print("\n1. S&P 500 PE data:")
    pe_data = get_sp500_pe_from_yfinance()
    print(f"   PE: {pe_data}")
    
    print("\n2. Fear & Greed Index:")
    fg = get_fear_greed_index()
    print(f"   Score: {fg.get('score')}, Sentiment: {fg.get('sentiment')}")
    
    print("\n3. All US Indices PE/PB:")
    indices = get_all_us_indices_pe_pb()
    for idx, data in indices.items():
        print(f"   {idx}: PE={data.get('pe')}, Zone={data.get('zone')}")
    
    print("\n4. VIX Data:")
    vix = get_vix_data()
    print(f"   VIX: {vix.get('current')}, {vix.get('interpretation')}")
    
    print("\n5. Sector Performance:")
    sectors = get_us_sector_performance()
    print(sectors.head())
    
    print("\nAll tests completed!")



