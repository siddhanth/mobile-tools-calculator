"""
Data Fetcher Module
Fetches Nifty 50/Midcap/Smallcap prices, Mutual Fund NAVs, and PE ratios
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


def retry_with_backoff(max_retries=3, base_delay=1, max_delay=30):
    """
    Decorator for retrying API calls with exponential backoff.
    Useful for handling NSE API rate limits and temporary failures.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        print(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator

# Cache directory
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# In-memory cache for API results (to avoid repeated slow calls within same session)
_memory_cache = {}
_cache_timestamps = {}
CACHE_TTL_SECONDS = 3600  # 1 hour for memory cache
DISK_CACHE_TTL_SECONDS = 86400  # 24 hours for disk cache

def _get_disk_cache_path(key: str) -> Path:
    """Get the file path for a disk cache key."""
    safe_key = key.replace("/", "_").replace(":", "_")
    return CACHE_DIR / f"{safe_key}.json"

def _get_disk_cached(key: str, ttl: int = DISK_CACHE_TTL_SECONDS):
    """Get value from disk cache if not expired."""
    cache_file = _get_disk_cache_path(key)
    try:
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            if time.time() - data.get('timestamp', 0) < ttl:
                value = data.get('value')
                # Handle DataFrame serialization
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
        # Handle DataFrame serialization
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
        pass  # Silently fail disk cache writes

def _get_cached(key: str, ttl: int = CACHE_TTL_SECONDS):
    """Get value from memory cache if not expired, then try disk cache."""
    # Try memory cache first (fastest)
    if key in _memory_cache and key in _cache_timestamps:
        if time.time() - _cache_timestamps[key] < ttl:
            return _memory_cache[key]
    
    # Try disk cache (slower but persists between restarts)
    disk_value = _get_disk_cached(key, DISK_CACHE_TTL_SECONDS)
    if disk_value is not None:
        # Promote to memory cache
        _memory_cache[key] = disk_value
        _cache_timestamps[key] = time.time()
        return disk_value
    
    return None

def _set_cached(key: str, value):
    """Store value in both memory and disk cache."""
    _memory_cache[key] = value
    _cache_timestamps[key] = time.time()
    # Also save to disk for faster startup next time
    _set_disk_cached(key, value)

# PE Data file paths
PE_DATA_FILE = Path(__file__).parent / "nifty_pe_data.csv"
MIDCAP_PE_DATA_FILE = Path(__file__).parent / "nifty_midcap_pe_data.csv"
SMALLCAP_PE_DATA_FILE = Path(__file__).parent / "nifty_smallcap_pe_data.csv"

# Index symbols
INDEX_SYMBOLS = {
    "nifty50": "^NSEI",
    "nifty_midcap": "^NSEMDCP50",  # Nifty Midcap 50
    "nifty_smallcap": "NIFTYSMLCAP100.NS",  # Nifty Smallcap 100
}

# PE thresholds will be calculated dynamically from historical data
# These are fallback static values if calculation fails
PE_ZONES_FALLBACK = {
    "nifty50": {"too_cheap": 15, "cheap": 19, "fair": 23, "expensive": 27, "too_expensive": 31},
    "nifty_midcap": {"too_cheap": 10, "cheap": 18, "fair": 27, "expensive": 35, "too_expensive": 43},
    "nifty_smallcap": {"too_cheap": 20, "cheap": 30, "fair": 45, "expensive": 65, "too_expensive": 90},
}

# Cache for computed PE zones
_PE_ZONES_CACHE = {}

# Top Equity Mutual Funds (AMFI codes) with AUM in Crores (as of Nov 2024)
# AUM data is approximate and should be updated periodically
FUND_AUM = {
    "122639": 79000,   # Parag Parikh Flexi Cap
    "120465": 35000,   # Axis Large Cap
    "118834": 40000,   # Mirae Asset Large & Midcap
    "120716": 18000,   # UTI Nifty 50 Index
    "119598": 33000,   # SBI Large Cap
    "118269": 14000,   # Canara Robeco Large Cap
    "120586": 60000,   # ICICI Pru Large Cap
    "120843": 7000,    # Quant Flexi Cap
    "120823": 11000,   # Quant Multi Cap
    "120503": 35000,   # Axis ELSS Tax Saver
    "118955": 66000,   # HDFC Flexi Cap
    "120166": 52000,   # Kotak Flexi Cap
    "120323": 48000,   # ICICI Pru Value Fund
    "118650": 38000,   # Nippon India Multi Cap
    "118275": 12000,   # Canara Robeco Flexi Cap
    "118989": 75000,   # HDFC Mid Cap
    "120505": 32000,   # Axis Midcap
    "120841": 9000,    # Quant Mid Cap
    "150817": 8000,    # Canara Robeco Mid Cap
    "125354": 22000,   # Axis Small Cap
    "120828": 9000,    # Quant Small Cap
    "130503": 33000,   # HDFC Small Cap
    "118778": 62000,   # Nippon India Small Cap
    "120164": 17000,   # Kotak Small Cap
    "125497": 33000,   # SBI Small Cap
    "146130": 12000,   # Canara Robeco Small Cap
    "119721": 28000,   # SBI Large & Midcap
    "118278": 15000,   # Canara Robeco Large & Mid Cap
    "147794": 5000,    # Motilal Oswal Nifty 50 Index
    "149039": 2000,    # Navi Nifty 50 Index
    "118535": 15000,   # Franklin India Flexi Cap
    "119076": 12000,   # DSP Flexi Cap
    "119071": 19000,   # DSP Midcap
    "119212": 16000,   # DSP Small Cap
    "147704": 6000,    # Motilal Oswal Large & Midcap
}

# Top Equity Mutual Funds (AMFI codes) - Verified Nov 2024
TOP_EQUITY_FUNDS = {
    # Large Cap / Flexi Cap
    "122639": "Parag Parikh Flexi Cap Fund",
    "120465": "Axis Large Cap Fund",
    "118834": "Mirae Asset Large & Midcap Fund",
    "120716": "UTI Nifty 50 Index Fund",
    "119598": "SBI Large Cap Fund",
    "118269": "Canara Robeco Large Cap Fund",
    "120586": "ICICI Pru Large Cap Fund",
    
    # Flexi Cap / Multi Cap
    "120843": "Quant Flexi Cap Fund",
    "120823": "Quant Multi Cap Fund",
    "120503": "Axis ELSS Tax Saver Fund",
    "118955": "HDFC Flexi Cap Fund",
    "120166": "Kotak Flexi Cap Fund",
    "120323": "ICICI Pru Value Fund",
    "118650": "Nippon India Multi Cap Fund",
    "118275": "Canara Robeco Flexi Cap Fund",
    
    # Mid Cap
    "118989": "HDFC Mid Cap Fund",
    "120505": "Axis Midcap Fund",
    "120841": "Quant Mid Cap Fund",
    "150817": "Canara Robeco Mid Cap Fund",
    
    # Small Cap
    "125354": "Axis Small Cap Fund",
    "120828": "Quant Small Cap Fund",
    "130503": "HDFC Small Cap Fund",
    "118778": "Nippon India Small Cap Fund",
    "120164": "Kotak Small Cap Fund",
    "125497": "SBI Small Cap Fund",
    "146130": "Canara Robeco Small Cap Fund",
    
    # Focused / Thematic
    "119721": "SBI Large & Midcap Fund",
    "118278": "Canara Robeco Large & Mid Cap Fund",
    
    # Index Funds
    "147794": "Motilal Oswal Nifty 50 Index Fund",
    "149039": "Navi Nifty 50 Index Fund",
    
    # Additional Popular Funds
    "118535": "Franklin India Flexi Cap Fund",
    "119076": "DSP Flexi Cap Fund",
    "119071": "DSP Midcap Fund",
    "119212": "DSP Small Cap Fund",
    "147704": "Motilal Oswal Large & Midcap Fund",
}


def get_index_data(index_name: str, start_date: str, end_date: str, interval: str = "1wk") -> pd.DataFrame:
    """
    Fetch index historical price data from yfinance
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval (1d, 1wk, 1mo)
    
    Returns:
        DataFrame with Date and Close columns
    """
    symbol = INDEX_SYMBOLS.get(index_name, "^NSEI")
    
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(start=start_date, end=end_date, interval=interval)
        
        if hist.empty or len(hist) < 10:
            # Fallback for small cap - use Nippon India Small Cap Fund as proxy
            if index_name == "nifty_smallcap":
                print(f"Using Nippon India Small Cap Fund (118778) as proxy for Smallcap index")
                mf_data = get_mf_nav_data("118778", start_date, end_date)
                if mf_data is not None and not mf_data.empty:
                    # Resample to weekly if needed
                    if interval == "1wk":
                        mf_data = mf_data.set_index('date')
                        mf_data = mf_data.resample('W-FRI').last().dropna().reset_index()
                    elif interval == "1mo":
                        mf_data = mf_data.set_index('date')
                        mf_data = mf_data.resample('ME').last().dropna().reset_index()
                    mf_data.columns = ['date', 'close']
                    return mf_data
            raise ValueError(f"No data returned for {index_name}")
        
        df = hist[['Close']].reset_index()
        df.columns = ['date', 'close']
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        
        return df
    
    except Exception as e:
        # Fallback for small cap - use Nippon India Small Cap Fund as proxy
        if index_name == "nifty_smallcap":
            try:
                print(f"Fallback: Using Nippon India Small Cap Fund (118778) as proxy")
                mf_data = get_mf_nav_data("118778", start_date, end_date)
                if mf_data is not None and not mf_data.empty:
                    if interval == "1wk":
                        mf_data = mf_data.set_index('date')
                        mf_data = mf_data.resample('W-FRI').last().dropna().reset_index()
                    elif interval == "1mo":
                        mf_data = mf_data.set_index('date')
                        mf_data = mf_data.resample('ME').last().dropna().reset_index()
                    mf_data.columns = ['date', 'close']
                    return mf_data
            except:
                pass
        raise Exception(f"Error fetching {index_name} data: {e}")


def get_nifty_data(start_date: str, end_date: str, interval: str = "1wk") -> pd.DataFrame:
    """
    Fetch Nifty 50 historical price data from yfinance
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        interval: Data interval (1d, 1wk, 1mo)
    
    Returns:
        DataFrame with Date and Close columns
    """
    try:
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(start=start_date, end=end_date, interval=interval)
        
        if hist.empty:
            raise ValueError("No data returned from yfinance")
        
        df = hist[['Close']].reset_index()
        df.columns = ['date', 'close']
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
        
        return df
    
    except Exception as e:
        raise Exception(f"Error fetching Nifty data: {e}")


# MF NAV Cache directory
MF_NAV_CACHE_DIR = Path(__file__).parent / ".cache" / "mf_nav"
MF_NAV_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_mf_nav_cache_path(scheme_code: str) -> Path:
    """Get the cache file path for MF NAV data."""
    return MF_NAV_CACHE_DIR / f"{scheme_code}_nav.csv"

def _load_cached_mf_nav(scheme_code: str) -> tuple:
    """Load cached MF NAV data from disk. Returns (df, scheme_name)."""
    cache_path = _get_mf_nav_cache_path(scheme_code)
    meta_path = MF_NAV_CACHE_DIR / f"{scheme_code}_meta.json"
    
    if cache_path.exists():
        try:
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            scheme_name = None
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                    scheme_name = meta.get('scheme_name')
            return df, scheme_name
        except Exception as e:
            print(f"Error loading cached NAV for {scheme_code}: {e}")
    return None, None

def _save_mf_nav_cache(scheme_code: str, df: pd.DataFrame, scheme_name: str = None):
    """Save MF NAV data to disk cache."""
    try:
        cache_path = _get_mf_nav_cache_path(scheme_code)
        df_to_save = df.copy()
        df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d')
        df_to_save.to_csv(cache_path, index=False)
        
        # Save metadata
        if scheme_name:
            meta_path = MF_NAV_CACHE_DIR / f"{scheme_code}_meta.json"
            with open(meta_path, 'w') as f:
                json.dump({'scheme_name': scheme_name}, f)
        
        print(f"💾 Saved NAV cache for {scheme_code}: {len(df)} rows")
    except Exception as e:
        print(f"Error saving NAV cache for {scheme_code}: {e}")

def get_mf_nav_data(scheme_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetch Mutual Fund NAV data from mfapi.in with incremental caching.
    
    Args:
        scheme_code: AMFI scheme code (e.g., "122639" for Parag Parikh Flexi Cap)
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        DataFrame with date and nav columns
    """
    # Try to load cached data first
    cached_df, cached_scheme_name = _load_cached_mf_nav(scheme_code)
    
    if cached_df is not None and not cached_df.empty:
        last_cached_date = cached_df['date'].max()
        today = pd.Timestamp.now().normalize()
        
        # If cache is recent (within 1 day), use it directly
        if (today - last_cached_date).days <= 1:
            print(f"📦 Using cached NAV for {scheme_code}: {len(cached_df)} rows (up to date)")
            df = cached_df.copy()
            df.attrs['scheme_name'] = cached_scheme_name or f'Scheme {scheme_code}'
            
            # Filter by date range if provided
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]
            return df
        
        # Fetch only new data (API doesn't support date range, so we fetch all and merge)
        print(f"📊 Updating NAV cache for {scheme_code} from {last_cached_date.date()}")
    
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' not in data:
            # Fall back to cache if available
            if cached_df is not None:
                df = cached_df.copy()
                df.attrs['scheme_name'] = cached_scheme_name or f'Scheme {scheme_code}'
                if start_date:
                    df = df[df['date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['date'] <= pd.to_datetime(end_date)]
                return df
            raise ValueError(f"Invalid response from mfapi.in: {data}")
        
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = df['nav'].astype(float)
        df = df.sort_values('date').reset_index(drop=True)
        
        # Get scheme name
        scheme_name = data.get('meta', {}).get('scheme_name', f'Scheme {scheme_code}')
        
        # Save to cache (full data, not filtered)
        _save_mf_nav_cache(scheme_code, df, scheme_name)
        
        # Filter by date range if provided
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]
        
        df.attrs['scheme_name'] = scheme_name
        
        return df
    
    except Exception as e:
        # Fall back to cache if API fails
        if cached_df is not None and not cached_df.empty:
            print(f"⚠️ API failed, using cached data for {scheme_code}")
            df = cached_df.copy()
            df.attrs['scheme_name'] = cached_scheme_name or f'Scheme {scheme_code}'
            if start_date:
                df = df[df['date'] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df['date'] <= pd.to_datetime(end_date)]
            return df
        raise Exception(f"Error fetching MF NAV data: {e}")


def search_mf_schemes(query: str = None) -> dict:
    """
    Get list of all mutual fund schemes from mfapi.in
    
    Args:
        query: Optional search query to filter schemes
    
    Returns:
        Dictionary of {scheme_code: scheme_name}
    """
    cache_file = CACHE_DIR / "mf_schemes.json"
    
    # Check cache (valid for 24 hours)
    if cache_file.exists():
        cache_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - cache_time < timedelta(hours=24):
            with open(cache_file, 'r') as f:
                schemes = json.load(f)
                if query:
                    schemes = {k: v for k, v in schemes.items() 
                              if query.lower() in v.lower()}
                return schemes
    
    try:
        url = "https://api.mfapi.in/mf"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        schemes = {str(item['schemeCode']): item['schemeName'] for item in data}
        
        # Cache the result
        with open(cache_file, 'w') as f:
            json.dump(schemes, f)
        
        if query:
            schemes = {k: v for k, v in schemes.items() 
                      if query.lower() in v.lower()}
        
        return schemes
    
    except Exception as e:
        raise Exception(f"Error fetching MF schemes: {e}")


def get_nifty_pe_data(start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Load Nifty PE ratio data from bundled CSV file
    
    Args:
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        DataFrame with date and pe columns
    """
    if not PE_DATA_FILE.exists():
        raise FileNotFoundError(
            f"PE data file not found at {PE_DATA_FILE}. "
            "Please ensure nifty_pe_data.csv exists in the app directory."
        )
    
    try:
        df = pd.read_csv(PE_DATA_FILE)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Filter by date range if provided
        if start_date:
            df = df[df['date'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['date'] <= pd.to_datetime(end_date)]
        
        return df
    
    except Exception as e:
        raise Exception(f"Error loading PE data: {e}")


def get_index_pe_data(index_name: str = "nifty50", start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Load PE ratio data for specified index from bundled CSV file
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
    
    Returns:
        DataFrame with date and pe columns
    """
    pe_files = {
        "nifty50": PE_DATA_FILE,
        "nifty_midcap": MIDCAP_PE_DATA_FILE,
        "nifty_smallcap": SMALLCAP_PE_DATA_FILE,
    }
    
    pe_file = pe_files.get(index_name, PE_DATA_FILE)
    
    if not pe_file.exists():
        # Fall back to Nifty 50 PE data with adjustments for other indices
        if PE_DATA_FILE.exists():
            df = pd.read_csv(PE_DATA_FILE)
            df['date'] = pd.to_datetime(df['date'])
            # Adjust PE for different indices (rough approximation)
            if index_name == "nifty_midcap":
                df['pe'] = df['pe'] * 1.3  # Midcap typically trades at higher PE
            elif index_name == "nifty_smallcap":
                df['pe'] = df['pe'] * 1.1  # Smallcap varies more
        else:
            raise FileNotFoundError(f"PE data file not found for {index_name}")
    else:
        df = pd.read_csv(pe_file)
        df['date'] = pd.to_datetime(df['date'])
    
    df = df.sort_values('date').reset_index(drop=True)
    
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    return df


def calculate_pe_zones(index_name: str) -> dict:
    """
    Calculate valuation zones based on statistical analysis of historical PE data.
    
    Uses robust statistics (percentiles) for highly volatile data:
    - Too Cheap: Below 10th percentile
    - Cheap: 10th to 25th percentile
    - Fair: 25th to 75th percentile (interquartile range)
    - Expensive: 75th to 90th percentile
    - Too Expensive: Above 90th percentile
    
    Also calculates median and std for reference.
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
    
    Returns:
        Dictionary with valuation thresholds
    """
    global _PE_ZONES_CACHE
    
    # Return cached result if available
    if index_name in _PE_ZONES_CACHE:
        return _PE_ZONES_CACHE[index_name]
    
    try:
        df = get_index_pe_data(index_name)
        pe_values = df['pe']
        
        median = pe_values.median()
        std = pe_values.std()
        
        # Use percentiles for robust thresholds (better for volatile data)
        p10 = pe_values.quantile(0.10)
        p25 = pe_values.quantile(0.25)
        p75 = pe_values.quantile(0.75)
        p90 = pe_values.quantile(0.90)
        
        zones = {
            'too_cheap': round(p10, 2),
            'cheap': round(p25, 2),
            'fair': round(median, 2),
            'expensive': round(p75, 2),
            'too_expensive': round(p90, 2),
            'median': round(median, 2),
            'std': round(std, 2),
            'min': round(pe_values.min(), 2),
            'max': round(pe_values.max(), 2),
            'p10': round(p10, 2),
            'p25': round(p25, 2),
            'p75': round(p75, 2),
            'p90': round(p90, 2),
        }
        
        # Cache the result
        _PE_ZONES_CACHE[index_name] = zones
        return zones
    
    except Exception:
        # Return fallback if calculation fails
        return PE_ZONES_FALLBACK.get(index_name, PE_ZONES_FALLBACK["nifty50"])


def get_valuation_zone(pe: float, zones: dict) -> tuple:
    """
    Determine the valuation zone for a given PE value.
    
    Zones based on percentiles:
    - Too Cheap: Below 10th percentile (rare buying opportunity)
    - Cheap: 10th to 25th percentile (undervalued)
    - Fair: 25th to 75th percentile (normal valuation)
    - Expensive: 75th to 90th percentile (overvalued)
    - Too Expensive: Above 90th percentile (extreme overvaluation)
    
    Args:
        pe: Current PE ratio
        zones: Dictionary with valuation thresholds
    
    Returns:
        Tuple of (zone_name, zone_color)
    """
    # Use percentile-based thresholds (p10, p25, p75, p90) if available
    # Fall back to standard thresholds if not
    too_cheap = zones.get('p10', zones.get('too_cheap', 0))
    cheap = zones.get('p25', zones.get('cheap', 0))
    expensive = zones.get('p75', zones.get('expensive', 100))
    too_expensive = zones.get('p90', zones.get('too_expensive', 200))
    
    if pe <= too_cheap:
        return "Too Cheap", "#10b981"  # Emerald green
    elif pe <= cheap:
        return "Cheap", "#22c55e"  # Green
    elif pe <= expensive:
        return "Fair", "#eab308"  # Yellow
    elif pe <= too_expensive:
        return "Expensive", "#f97316"  # Orange
    else:
        return "Too Expensive", "#ef4444"  # Red


def get_current_nifty_pe() -> dict:
    """
    Get the most recent Nifty PE value from the data file
    
    Returns:
        Dictionary with 'pe', 'date', and 'days_old' keys
    """
    df = get_nifty_pe_data()
    latest = df.iloc[-1]
    
    days_old = (datetime.now() - latest['date']).days
    
    return {
        'pe': latest['pe'],
        'date': latest['date'],
        'days_old': days_old
    }


def get_current_index_pe(index_name: str = "nifty50") -> dict:
    """
    Get the most recent PE value for specified index with statistical valuation zones.
    
    Valuation zones are calculated based on median and standard deviation:
    - Too Cheap: Below median - 2*std
    - Cheap: Between median - 2*std and median - 1*std
    - Fair: Around median (± 1*std)
    - Expensive: Between median + 1*std and median + 2*std
    - Too Expensive: Above median + 2*std
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
    
    Returns:
        Dictionary with PE info and valuation zone details
    """
    df = get_index_pe_data(index_name)
    latest = df.iloc[-1]
    
    days_old = (datetime.now() - latest['date']).days
    pe = latest['pe']
    
    # Calculate statistical zones
    zones = calculate_pe_zones(index_name)
    zone_name, zone_color = get_valuation_zone(pe, zones)
    
    return {
        'pe': round(pe, 2),
        'date': latest['date'],
        'days_old': days_old,
        'zone': zone_name,
        'zone_color': zone_color,
        'thresholds': zones,
        'median': zones.get('median'),
        'std': zones.get('std'),
    }


def get_all_indices_pe() -> dict:
    """
    Get current PE values for all tracked indices.
    Uses in-memory cache to avoid repeated slow API calls.
    
    Returns:
        Dictionary with index names as keys and PE info as values
    """
    cache_key = "all_indices_pe"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    result = {}
    for index_name in ["nifty50", "nifty_midcap", "nifty_smallcap"]:
        try:
            result[index_name] = get_current_index_pe(index_name)
        except Exception as e:
            print(f"Error fetching PE for {index_name}: {e}")
            result[index_name] = {'error': str(e)}
    
    _set_cached(cache_key, result)
    return result


def get_all_indices_pe_pb() -> dict:
    """
    Get current PE and PB values for all tracked indices with combined valuation.
    Uses in-memory cache to avoid repeated slow API calls.
    
    Combined Valuation Score = (PE Percentile * 0.6) + (PB Percentile * 0.4)
    
    Returns:
        Dictionary with index names as keys and PE/PB/Combined info as values
    """
    cache_key = "all_indices_pe_pb"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    try:
        from nsepython import index_pe_pb_div
    except ImportError:
        return {"error": "nsepython not installed"}
    
    nse_index_names = {
        "nifty50": "NIFTY 50",
        "nifty_midcap": "NIFTY MIDCAP 50",
        "nifty_smallcap": "NIFTY SMLCAP 250",
    }
    
    # Historical benchmarks for PB (approximate - based on historical ranges)
    pb_benchmarks = {
        "nifty50": {"p10": 2.5, "p25": 2.9, "median": 3.3, "p75": 3.8, "p90": 4.5},
        "nifty_midcap": {"p10": 2.0, "p25": 2.5, "median": 3.2, "p75": 4.0, "p90": 5.0},
        "nifty_smallcap": {"p10": 1.5, "p25": 2.0, "median": 2.8, "p75": 3.8, "p90": 5.0},
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    start_str = start_date.strftime('%d-%b-%Y')
    end_str = end_date.strftime('%d-%b-%Y')
    
    result = {}
    for index_key, nse_name in nse_index_names.items():
        try:
            data = _safe_index_pe_pb_div(nse_name, start_str, end_str)
            
            if isinstance(data, pd.DataFrame) and not data.empty:
                pe = float(data['pe'].iloc[0])
                pb = float(data['pb'].iloc[0])
                div_yield = float(data.get('divYield', data.get('dy', 0)).iloc[0] if 'divYield' in data.columns or 'dy' in data.columns else 0)
                
                # Get PE zones from historical data
                pe_zones = calculate_pe_zones(index_key)
                pe_zone_name, pe_zone_color = get_valuation_zone(pe, pe_zones)
                
                # Calculate PE percentile (0-100, lower is cheaper)
                if pe <= pe_zones['p10']:
                    pe_percentile = 10
                elif pe <= pe_zones['p25']:
                    pe_percentile = 25
                elif pe <= pe_zones['median']:
                    pe_percentile = 50
                elif pe <= pe_zones['p75']:
                    pe_percentile = 75
                elif pe <= pe_zones['p90']:
                    pe_percentile = 90
                else:
                    pe_percentile = 100
                
                # Calculate PB percentile
                pb_zones = pb_benchmarks[index_key]
                if pb <= pb_zones['p10']:
                    pb_percentile = 10
                elif pb <= pb_zones['p25']:
                    pb_percentile = 25
                elif pb <= pb_zones['median']:
                    pb_percentile = 50
                elif pb <= pb_zones['p75']:
                    pb_percentile = 75
                elif pb <= pb_zones['p90']:
                    pb_percentile = 90
                else:
                    pb_percentile = 100
                
                # Combined score (weighted average)
                combined_percentile = (pe_percentile * 0.6) + (pb_percentile * 0.4)
                
                # Map combined percentile to zone
                if combined_percentile <= 20:
                    combined_zone = "Very Cheap"
                    combined_color = "#22c55e"
                elif combined_percentile <= 40:
                    combined_zone = "Cheap"
                    combined_color = "#86efac"
                elif combined_percentile <= 60:
                    combined_zone = "Fair"
                    combined_color = "#fbbf24"
                elif combined_percentile <= 80:
                    combined_zone = "Expensive"
                    combined_color = "#f97316"
                else:
                    combined_zone = "Very Expensive"
                    combined_color = "#dc2626"
                
                result[index_key] = {
                    'pe': round(pe, 2),
                    'pb': round(pb, 2),
                    'div_yield': round(div_yield, 2),
                    'pe_zone': pe_zone_name,
                    'pe_zone_color': pe_zone_color,
                    'pe_percentile': pe_percentile,
                    'pb_percentile': pb_percentile,
                    'combined_percentile': round(combined_percentile, 1),
                    'combined_zone': combined_zone,
                    'combined_color': combined_color,
                    'pe_thresholds': pe_zones,
                    'pb_thresholds': pb_zones,
                }
            else:
                result[index_key] = {'error': 'No data returned'}
        except Exception as e:
            print(f"Error fetching PE/PB for {index_key}: {e}")
            result[index_key] = {'error': str(e)}
    
    _set_cached(cache_key, result)
    return result


def get_pe_history_for_chart(years: int = 10) -> pd.DataFrame:
    """
    Get PE history for all indices, suitable for charting.
    Uses in-memory cache to avoid repeated slow calls.
    
    Args:
        years: Number of years of history to return
    
    Returns:
        DataFrame with date and PE columns for each index
    """
    cache_key = f"pe_history_{years}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    
    result_df = None
    
    index_names = {
        "nifty50": "Nifty 50",
        "nifty_midcap": "Nifty Midcap 50",
        "nifty_smallcap": "Nifty Smallcap 250",
    }
    
    for index_key, display_name in index_names.items():
        try:
            df = get_index_pe_data(index_key, start_date=start_date)
            df = df.rename(columns={'pe': display_name})
            
            if result_df is None:
                result_df = df[['date', display_name]]
            else:
                result_df = pd.merge(result_df, df[['date', display_name]], on='date', how='outer')
        except Exception as e:
            print(f"Error loading PE data for {index_key}: {e}")
    
    if result_df is not None:
        result_df = result_df.sort_values('date').ffill()
    
    _set_cached(cache_key, result_df)
    return result_df


def get_index_price_data(index_name: str = "nifty50", start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Fetch historical index price data using yfinance.
    Uses fallback symbols for reliability.
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
    
    Returns:
        DataFrame with date and index_value columns
    """
    # Symbol fallback chains for each index
    symbol_chains = {
        "nifty50": ["^NSEI"],
        "nifty_midcap": ["^NSEMDCP50", "NIFTYMIDCAP50.NS"],
        "nifty_smallcap": ["^CNXSC", "NIFTYSMLCAP100.NS"],
    }
    
    symbols = symbol_chains.get(index_name, ["^NSEI"])
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=365 * 10)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date)
            
            if hist is not None and not hist.empty and len(hist) > 10:
                df = hist[['Close']].reset_index()
                df.columns = ['date', 'index_value']
                df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
                return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            print(f"Failed to fetch {symbol}: {e}")
            continue
    
    # If all symbols failed for smallcap, use MF proxy
    if index_name == "nifty_smallcap":
        try:
            mf_df = get_mf_nav_data("118778", start_date, end_date)  # Nippon India Small Cap
            if mf_df is not None and not mf_df.empty:
                mf_df = mf_df.rename(columns={'nav': 'index_value'})
                return mf_df[['date', 'index_value']]
        except:
            pass
    
    return pd.DataFrame(columns=['date', 'index_value'])


def get_pe_with_price(index_name: str = "nifty50", start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Combine PE data with index prices.
    Uses left join on PE data dates with forward-fill for missing prices.
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
        start_date: Start date (YYYY-MM-DD format)
        end_date: End date (YYYY-MM-DD format)
    
    Returns:
        DataFrame with date, pe, and index_value columns
    """
    # Get PE data
    pe_df = get_index_pe_data(index_name, start_date, end_date)
    if pe_df is None or pe_df.empty:
        return pd.DataFrame()
    
    # Get price data
    price_df = get_index_price_data(index_name, start_date, end_date)
    if price_df is None or price_df.empty:
        # Return PE data without prices
        pe_df['index_value'] = None
        return pe_df
    
    # Merge on date (left join to keep all PE dates)
    pe_df['date'] = pd.to_datetime(pe_df['date'])
    price_df['date'] = pd.to_datetime(price_df['date'])
    
    merged = pd.merge(pe_df, price_df, on='date', how='left')
    
    # Forward-fill missing prices (weekends, holidays)
    merged['index_value'] = merged['index_value'].ffill()
    
    return merged


def get_pe_price_history_for_chart(years: int = 10) -> pd.DataFrame:
    """
    Get PE and price history for all indices, suitable for charting.
    Uses in-memory cache to avoid repeated slow calls.
    
    Args:
        years: Number of years of history to return
    
    Returns:
        DataFrame with date, PE and price columns for each index
    """
    cache_key = f"pe_price_history_{years}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    
    result_df = None
    
    index_names = {
        "nifty50": "Nifty 50",
        "nifty_midcap": "Nifty Midcap 50",
        "nifty_smallcap": "Nifty Smallcap 250",
    }
    
    for index_key, display_name in index_names.items():
        try:
            df = get_pe_with_price(index_key, start_date=start_date)
            if df is not None and not df.empty:
                df = df.rename(columns={
                    'pe': f'{display_name} PE',
                    'index_value': f'{display_name} Value'
                })
                
                if result_df is None:
                    result_df = df[['date', f'{display_name} PE', f'{display_name} Value']]
                else:
                    result_df = pd.merge(
                        result_df, 
                        df[['date', f'{display_name} PE', f'{display_name} Value']], 
                        on='date', 
                        how='outer'
                    )
            else:
                print(f"Warning: No PE/price data for {display_name}")
        except Exception as e:
            print(f"Error loading PE/price data for {index_key}: {e}")
    
    if result_df is not None:
        result_df = result_df.sort_values('date').ffill()
    
    _set_cached(cache_key, result_df)
    return result_df


# Earnings cache file paths
EARNINGS_CACHE_DIR = Path(__file__).parent / ".cache" / "earnings"
EARNINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_earnings_cache_path(index_name: str) -> Path:
    """Get the cache file path for earnings data."""
    return EARNINGS_CACHE_DIR / f"{index_name}_earnings.csv"

def _load_cached_earnings(index_name: str) -> pd.DataFrame:
    """Load cached earnings data from disk."""
    cache_path = _get_earnings_cache_path(index_name)
    if cache_path.exists():
        try:
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            print(f"Error loading cached earnings for {index_name}: {e}")
    return None

def _save_earnings_cache(index_name: str, df: pd.DataFrame):
    """Save earnings data to disk cache."""
    try:
        cache_path = _get_earnings_cache_path(index_name)
        df_to_save = df.copy()
        df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d')
        df_to_save.to_csv(cache_path, index=False)
        print(f"💾 Saved earnings cache for {index_name}: {len(df)} rows")
    except Exception as e:
        print(f"Error saving earnings cache for {index_name}: {e}")

def get_earnings_data(index_name: str = "nifty50", years: int = 10) -> pd.DataFrame:
    """
    Derive earnings from PE and Index Value.
    
    Earnings = Index Value / PE
    
    Also calculates YoY growth rate.
    Uses incremental caching - only calculates for new dates.
    
    Args:
        index_name: Index identifier (nifty50, nifty_midcap, nifty_smallcap)
        years: Number of years of history
    
    Returns:
        DataFrame with date, earnings, and earnings_yoy columns
    """
    start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y-%m-%d')
    requested_start = pd.to_datetime(start_date)
    
    # Try to load cached earnings first
    cached_df = _load_cached_earnings(index_name)
    
    if cached_df is not None and not cached_df.empty:
        # Check if cache covers the requested date range
        first_cached_date = cached_df['date'].min()
        last_cached_date = cached_df['date'].max()
        
        # If requested start is earlier than cache, re-fetch full range
        if requested_start < first_cached_date:
            print(f"📊 Requested data ({start_date}) is older than cache ({first_cached_date.strftime('%Y-%m-%d')}). Re-fetching full range...")
            # Fall through to fresh calculation below
        else:
            # Cache covers the range, check if we need to update forward
            new_start_date = (last_cached_date + timedelta(days=1)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            if new_start_date >= today:
                # Cache is up to date
                print(f"📦 Using cached earnings for {index_name}: {len(cached_df)} rows (up to date)")
                # Filter by requested years
                cached_df = cached_df[cached_df['date'] >= requested_start]
                return cached_df
            
            # Fetch only new data
            print(f"📊 Fetching new earnings data for {index_name} from {new_start_date}")
            new_df = get_pe_with_price(index_name, start_date=new_start_date)
            
            if new_df is not None and not new_df.empty:
                # Calculate earnings for new data
                new_df = new_df.copy()
                new_df = new_df.dropna(subset=['index_value', 'pe'])
                
                if not new_df.empty:
                    new_df['earnings'] = new_df['index_value'] / new_df['pe']
                    new_df['earnings_yoy'] = None  # Will recalculate after merge
                    new_df = new_df[['date', 'pe', 'index_value', 'earnings', 'earnings_yoy']]
                    
                    # Merge with cached data
                    full_df = pd.concat([cached_df, new_df], ignore_index=True)
                    full_df = full_df.drop_duplicates(subset=['date'], keep='last')
                    full_df = full_df.sort_values('date').reset_index(drop=True)
                    
                    # Recalculate YoY for entire dataset
                    if len(full_df) > 250:
                        full_df['earnings_yoy'] = full_df['earnings'].pct_change(periods=250) * 100
                    
                    # Save updated cache
                    _save_earnings_cache(index_name, full_df)
                    
                    # Filter by requested years
                    full_df = full_df[full_df['date'] >= requested_start]
                    print(f"✅ Updated earnings for {index_name}: {len(full_df)} rows")
                    return full_df
            
            # No new data, return cached
            cached_df = cached_df[cached_df['date'] >= requested_start]
            return cached_df
    
    # No cache exists - calculate from scratch
    print(f"📊 Calculating earnings from scratch for {index_name}")
    df = get_pe_with_price(index_name, start_date=start_date)
    
    if df is None or df.empty:
        print(f"No PE+Price data for {index_name}")
        return pd.DataFrame(columns=['date', 'earnings', 'earnings_yoy'])
    
    # Check if we have index_value data
    if 'index_value' not in df.columns or df['index_value'].isna().all():
        print(f"No index value data for {index_name}, trying PE-only approach")
        # Just return empty - can't calculate earnings without price
        return pd.DataFrame(columns=['date', 'earnings', 'earnings_yoy'])
    
    # Calculate derived earnings
    df = df.copy()
    
    # Handle potential NaN values
    df = df.dropna(subset=['index_value', 'pe'])
    if df.empty:
        return pd.DataFrame(columns=['date', 'earnings', 'earnings_yoy'])
    
    df['earnings'] = df['index_value'] / df['pe']
    
    # Calculate YoY growth (approximately 252 trading days in a year)
    # Use 250 as a round number
    if len(df) > 250:
        df['earnings_yoy'] = df['earnings'].pct_change(periods=250) * 100
    else:
        df['earnings_yoy'] = None  # Not enough data for YoY
    
    # Clean up
    df = df[['date', 'pe', 'index_value', 'earnings', 'earnings_yoy']].dropna(subset=['earnings'])
    
    # Save to cache
    _save_earnings_cache(index_name, df)
    
    print(f"✅ Earnings data for {index_name}: {len(df)} rows")
    return df


def get_earnings_history_for_chart(years: int = 10) -> pd.DataFrame:
    """
    Get derived earnings history for all indices, suitable for charting.
    Uses cached earnings data for fast loading.
    
    Args:
        years: Number of years of history to return
    
    Returns:
        DataFrame with date and earnings columns for each index
    """
    # Check memory cache first
    cache_key = f"earnings_history_{years}"
    cached = _get_cached(cache_key, ttl=3600)  # 1 hour cache
    if cached is not None:
        print(f"📦 Using cached earnings history: {len(cached) if hasattr(cached, '__len__') else 'N/A'} rows")
        return cached
    
    result_df = None
    
    index_names = {
        "nifty50": "Nifty 50",
        "nifty_midcap": "Nifty Midcap 50",
        "nifty_smallcap": "Nifty Smallcap 250",
    }
    
    for index_key, display_name in index_names.items():
        try:
            df = get_earnings_data(index_key, years=years)
            if df is not None and not df.empty:
                print(f"✅ Loaded earnings data for {display_name}: {len(df)} rows")
                df = df.rename(columns={
                    'earnings': f'{display_name} Earnings',
                    'earnings_yoy': f'{display_name} YoY%'
                })
                
                if result_df is None:
                    result_df = df[['date', f'{display_name} Earnings', f'{display_name} YoY%']]
                else:
                    result_df = pd.merge(
                        result_df, 
                        df[['date', f'{display_name} Earnings', f'{display_name} YoY%']], 
                        on='date', 
                        how='outer'
                    )
            else:
                print(f"⚠️ No earnings data for {display_name}")
        except Exception as e:
            print(f"❌ Error loading earnings data for {index_key}: {e}")
    
    if result_df is not None:
        result_df = result_df.sort_values('date').ffill()
        # Cache the result
        _set_cached(cache_key, result_df)
    
    return result_df


def resample_to_weekly(df: pd.DataFrame, date_col: str = 'date', 
                       value_col: str = 'nav') -> pd.DataFrame:
    """
    Resample daily data to weekly (Friday close)
    
    Args:
        df: DataFrame with date and value columns
        date_col: Name of date column
        value_col: Name of value column
    
    Returns:
        Weekly resampled DataFrame
    """
    df = df.copy()
    df = df.set_index(date_col)
    
    # Resample to weekly (Friday)
    weekly = df[[value_col]].resample('W-FRI').last()
    weekly = weekly.dropna().reset_index()
    weekly.columns = ['date', value_col]
    
    return weekly


def align_data(nifty_df: pd.DataFrame, pe_df: pd.DataFrame, 
               mf_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Align all data sources to common weekly dates
    
    Args:
        nifty_df: Nifty price data (weekly)
        pe_df: PE ratio data
        mf_df: Optional MF NAV data
    
    Returns:
        Merged DataFrame with all data aligned
    """
    # Start with Nifty data as base
    result = nifty_df.copy()
    result.columns = ['date', 'nifty_close']
    
    # Merge PE data (forward fill for missing dates)
    pe_df = pe_df.copy()
    pe_df = pe_df.set_index('date').resample('D').ffill().reset_index()
    
    result = pd.merge_asof(
        result.sort_values('date'),
        pe_df.sort_values('date'),
        on='date',
        direction='backward'
    )
    
    # Merge MF data if provided
    if mf_df is not None:
        mf_weekly = resample_to_weekly(mf_df, 'date', 'nav')
        result = pd.merge(
            result,
            mf_weekly,
            on='date',
            how='left'
        )
        result['nav'] = result['nav'].ffill()
    
    return result.dropna()


# Sectoral indices for PE comparison
SECTORAL_INDICES = {
    "NIFTY BANK": "Nifty Bank",
    "NIFTY IT": "Nifty IT",
    "NIFTY PHARMA": "Nifty Pharma",
    "NIFTY AUTO": "Nifty Auto",
    "NIFTY FMCG": "Nifty FMCG",
    "NIFTY METAL": "Nifty Metal",
    "NIFTY REALTY": "Nifty Realty",
    "NIFTY ENERGY": "Nifty Energy",
    "NIFTY INFRA": "Nifty Infra",
    "NIFTY MEDIA": "Nifty Media",
    "NIFTY COMMODITIES": "Nifty Commodities",
    "NIFTY NEXT 50": "Nifty Next 50",
    "NIFTY 100": "Nifty 100",
    "NIFTY 500": "Nifty 500",
    "NIFTY MIDCAP 50": "Nifty Midcap 50",
    "NIFTY SMLCAP 250": "Nifty Smallcap 250",
}


SECTOR_CURRENT_CACHE_FILE = Path(__file__).parent / "sector_current_pe_cache.csv"
SECTOR_CURRENT_CACHE_META = Path(__file__).parent / "sector_current_pe_cache_meta.txt"


def get_all_sectors_pe(force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetch current PE for all sectoral and broad market indices.
    Returns DataFrame with PE data and comparison to HISTORICAL averages.
    
    Valuation is based on each sector's own historical PE multiple trend,
    not just comparison to Nifty 50 baseline.
    
    Caching: Data is cached and refreshed daily.
    """
    from datetime import datetime
    
    # Check cache first
    if not force_refresh and SECTOR_CURRENT_CACHE_FILE.exists() and SECTOR_CURRENT_CACHE_META.exists():
        try:
            with open(SECTOR_CURRENT_CACHE_META, 'r') as f:
                cache_date = f.read().strip()
            
            today = datetime.now().strftime('%Y-%m-%d')
            if cache_date == today:
                # Cache is fresh, load it
                cached_df = pd.read_csv(SECTOR_CURRENT_CACHE_FILE)
                return cached_df
        except:
            pass  # Cache read failed, fetch fresh
    
    # Fetch fresh data
    df = _fetch_all_sectors_pe_from_nse()
    
    # Save to cache
    if df is not None and not df.empty:
        try:
            df.to_csv(SECTOR_CURRENT_CACHE_FILE, index=False)
            with open(SECTOR_CURRENT_CACHE_META, 'w') as f:
                f.write(datetime.now().strftime('%Y-%m-%d'))
        except:
            pass  # Cache write failed, continue anyway
    
    return df


@retry_with_backoff(max_retries=3, base_delay=1, max_delay=10)
def _safe_index_pe_pb_div(index_name: str, start_date: str, end_date: str, timeout_seconds: int = 8):
    """
    Wrapper around nsepython's index_pe_pb_div with retry logic and timeout.
    Handles rate limits and temporary failures gracefully.
    
    Args:
        index_name: NSE index name (e.g., "NIFTY 50")
        start_date: Start date in DD-MMM-YYYY format
        end_date: End date in DD-MMM-YYYY format
        timeout_seconds: Maximum time to wait for API response
    
    Returns:
        DataFrame with PE/PB data or None if failed
    """
    import threading
    
    result = [None]
    error = [None]
    
    def fetch_data():
        try:
            from nsepython import index_pe_pb_div
            result[0] = index_pe_pb_div(index_name, start_date, end_date)
        except Exception as e:
            error[0] = e
            print(f"NSE API error for {index_name}: {e}")
    
    thread = threading.Thread(target=fetch_data)
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        print(f"NSE API timeout for {index_name} after {timeout_seconds}s")
        return None
    
    if error[0]:
        return None
    
    return result[0]


def _fetch_all_sectors_pe_from_nse() -> pd.DataFrame:
    """
    Internal function to fetch current sector PE from NSE.
    Compares current PE multiple to each sector's historical average.
    """
    try:
        from nsepython import index_pe_pb_div
    except ImportError:
        return pd.DataFrame()
    
    from datetime import datetime, timedelta
    import time
    
    # First, load historical matrix to get averages
    historical_averages = {}
    if SECTOR_MATRIX_CACHE_FILE.exists():
        try:
            matrix_df = pd.read_csv(SECTOR_MATRIX_CACHE_FILE)
            # Calculate historical stats for each sector (excluding 'Month' column)
            for col in matrix_df.columns:
                if col != 'Month':
                    vals = pd.to_numeric(matrix_df[col], errors='coerce').dropna()
                    if len(vals) > 0:
                        # Filter out extreme outliers (> 10x or < 0.1x) which are likely data errors
                        vals_filtered = vals[(vals >= 0.1) & (vals <= 10)]
                        if len(vals_filtered) > 0:
                            historical_averages[col] = {
                                'avg': vals_filtered.mean(),
                                'median': vals_filtered.median(),
                                'std': vals_filtered.std(),
                                'p10': vals_filtered.quantile(0.10),
                                'p25': vals_filtered.quantile(0.25),
                                'p75': vals_filtered.quantile(0.75),
                                'p90': vals_filtered.quantile(0.90),
                                'min': vals_filtered.min(),
                                'max': vals_filtered.max()
                            }
        except:
            pass
    
    results = []
    
    # Get date range for recent data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    start_str = start_date.strftime("%d-%b-%Y")
    end_str = end_date.strftime("%d-%b-%Y")
    
    # Get Nifty 50 PE first as baseline
    try:
        nifty50_data = _safe_index_pe_pb_div("NIFTY 50", start_str, end_str)
        if isinstance(nifty50_data, pd.DataFrame) and not nifty50_data.empty:
            nifty50_pe = float(nifty50_data['pe'].iloc[0])
        else:
            nifty50_pe = 22.0  # Fallback
    except:
        nifty50_pe = 22.0
    
    results.append({
        'index_code': 'NIFTY 50',
        'index_name': 'Nifty 50',
        'pe': nifty50_pe,
        'pe_multiple': 1.0,
        'hist_avg': 1.0,
        'vs_history': 0.0,
        'category': 'Broad Market',
        'valuation': 'Fair (Baseline)'
    })
    
    # Fetch PE for all sectors
    for code, name in SECTORAL_INDICES.items():
        try:
            data = _safe_index_pe_pb_div(code, start_str, end_str)
            if isinstance(data, pd.DataFrame) and not data.empty:
                pe = float(data['pe'].iloc[0])
                pe_multiple = round(pe / nifty50_pe, 2)
                
                # Get column name for historical lookup
                col_name = name.replace('Nifty ', '').replace(' ', '')
                
                # Get historical stats for this sector
                hist_data = historical_averages.get(col_name, {})
                hist_median = hist_data.get('median', pe_multiple)
                hist_p10 = hist_data.get('p10', hist_median * 0.8)
                hist_p25 = hist_data.get('p25', hist_median * 0.9)
                hist_p75 = hist_data.get('p75', hist_median * 1.1)
                hist_p90 = hist_data.get('p90', hist_median * 1.2)
                
                # Calculate deviation from historical median (in %)
                if hist_median > 0:
                    vs_history = round((pe_multiple - hist_median) / hist_median * 100, 1)
                else:
                    vs_history = 0
                
                # Determine valuation based on historical percentiles
                if pe_multiple <= hist_p10:
                    valuation = 'Very Cheap (vs History)'
                elif pe_multiple <= hist_p25:
                    valuation = 'Cheap (vs History)'
                elif pe_multiple >= hist_p90:
                    valuation = 'Very Expensive (vs History)'
                elif pe_multiple >= hist_p75:
                    valuation = 'Expensive (vs History)'
                else:
                    valuation = 'Fair (vs History)'
                
                # Categorize
                if 'BANK' in code or 'METAL' in code or 'ENERGY' in code or 'COMMODITIES' in code or 'INFRA' in code:
                    category = 'Sectoral'
                elif 'MIDCAP' in code or 'SMLCAP' in code or 'NEXT' in code or '100' in code or '500' in code:
                    category = 'Broad Market'
                else:
                    category = 'Sectoral'
                
                results.append({
                    'index_code': code,
                    'index_name': name,
                    'pe': pe,
                    'pe_multiple': pe_multiple,
                    'hist_avg': round(hist_median, 2),  # Using median as it's more robust
                    'vs_history': vs_history,
                    'category': category,
                    'valuation': valuation
                })
            time.sleep(0.1)  # Small delay
        except Exception as e:
            pass  # Skip failed indices
    
    df = pd.DataFrame(results)
    
    return df.sort_values('vs_history')


SECTOR_MATRIX_CACHE_FILE = Path(__file__).parent / "sector_pe_matrix_cache.csv"
SECTOR_MATRIX_CACHE_META = Path(__file__).parent / "sector_pe_matrix_cache_meta.txt"


def get_sector_pe_matrix(months: int = 120, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetch historical PE multiples for all sectors in matrix format.
    Rows = Months, Columns = Sectors
    Similar to nifty-pe-ratio.com matrix view.
    
    INCREMENTAL CACHING:
    - Historical months are stored and never re-fetched
    - Only current month is updated daily
    - force_refresh=True fetches last 3 months only (to catch corrections)
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    
    # Check in-memory cache first (faster than file)
    cache_key = f"sector_matrix_{months}"
    if not force_refresh:
        cached = _get_cached(cache_key, ttl=3600)  # 1 hour memory cache
        if cached is not None:
            print(f"📦 Using memory-cached sector matrix: {len(cached)} rows")
            return cached
    
    # Load existing file cache
    cached_df = None
    last_month_in_cache = None
    
    if SECTOR_MATRIX_CACHE_FILE.exists():
        try:
            cached_df = pd.read_csv(SECTOR_MATRIX_CACHE_FILE)
            if not cached_df.empty and 'Month' in cached_df.columns:
                # Parse the first month to see how recent the cache is
                # Format is 'Nov-24', 'Oct-24', etc.
                first_month_str = cached_df['Month'].iloc[0]  # Most recent month (sorted desc)
                last_month_in_cache = pd.to_datetime(first_month_str, format='%b-%y')
                print(f"📦 Loaded cached sector matrix: {len(cached_df)} rows, latest: {first_month_str}")
        except Exception as e:
            print(f"Cache load error: {e}")
    
    current_month = pd.Timestamp.now().to_period('M').to_timestamp()
    
    # Determine if we need to fetch new data
    if cached_df is not None and not cached_df.empty:
        # Check if cache is current month
        if last_month_in_cache is not None:
            if last_month_in_cache.month == current_month.month and last_month_in_cache.year == current_month.year:
                if not force_refresh:
                    # Cache is up to date
                    _set_cached(cache_key, cached_df)
                    print(f"✅ Sector matrix cache is current")
                    return cached_df
        
        # Need to update - fetch only recent months (current + previous for corrections)
        months_to_fetch = 3 if force_refresh else 2
        print(f"📊 Updating sector matrix with last {months_to_fetch} months...")
        new_df = _fetch_sector_pe_matrix_from_nse(months_to_fetch)
        
        if new_df is not None and not new_df.empty:
            # Merge: replace overlapping months, add new ones
            new_months = set(new_df['Month'].tolist())
            
            # Keep old months that aren't in new data
            if cached_df is not None:
                old_rows = cached_df[~cached_df['Month'].isin(new_months)]
                merged_df = pd.concat([new_df, old_rows], ignore_index=True)
            else:
                merged_df = new_df
            
            # Sort by month (most recent first) - convert for sorting
            merged_df['_sort_date'] = pd.to_datetime(merged_df['Month'], format='%b-%y')
            merged_df = merged_df.sort_values('_sort_date', ascending=False).drop('_sort_date', axis=1)
            
            # Limit to requested months
            merged_df = merged_df.head(months)
            
            # Save updated cache
            try:
                merged_df.to_csv(SECTOR_MATRIX_CACHE_FILE, index=False)
                _set_cached(cache_key, merged_df)
                print(f"💾 Updated sector matrix cache: {len(merged_df)} rows")
            except Exception as e:
                print(f"Cache save error: {e}")
            
            return merged_df
        
        # New fetch failed, return cached data
        _set_cached(cache_key, cached_df)
        return cached_df
    
    # No cache exists - fetch full history
    print(f"📊 Fetching full sector PE matrix for {months} months (first time)...")
    df = _fetch_sector_pe_matrix_from_nse(months)
    
    # Save to cache
    if df is not None and not df.empty:
        try:
            df.to_csv(SECTOR_MATRIX_CACHE_FILE, index=False)
            with open(SECTOR_MATRIX_CACHE_META, 'w') as f:
                f.write(datetime.now().strftime('%Y-%m-%d'))
            _set_cached(cache_key, df)
            print(f"💾 Sector PE matrix cached: {len(df)} rows")
        except Exception as e:
            print(f"Cache write failed: {e}")
    
    return df


def _fetch_sector_pe_matrix_from_nse(months: int = 12) -> pd.DataFrame:
    """
    Internal function to fetch sector PE matrix from NSE.
    """
    try:
        from nsepython import index_pe_pb_div
    except ImportError:
        return pd.DataFrame()
    
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import time
    
    # Define sectors to fetch
    all_indices = [("NIFTY 50", "Nifty50")]
    for code, name in SECTORAL_INDICES.items():
        col_name = name.replace('Nifty ', '').replace(' ', '')
        all_indices.append((code, col_name))
    
    # Generate date range for all months
    end_date = datetime.now()
    start_date = end_date - relativedelta(months=months)
    start_str = start_date.strftime("%d-%b-%Y")
    end_str = end_date.strftime("%d-%b-%Y")
    
    # Fetch all data for each sector
    sector_data = {}
    
    for code, col_name in all_indices:
        try:
            data = _safe_index_pe_pb_div(code, start_str, end_str)
            if isinstance(data, pd.DataFrame) and not data.empty:
                data['date'] = pd.to_datetime(data['DATE'], format='%d %b %Y')
                data['pe'] = pd.to_numeric(data['pe'], errors='coerce')
                data['month'] = data['date'].dt.to_period('M')
                sector_data[col_name] = data
            time.sleep(0.2)  # Small delay to avoid rate limiting
        except Exception as e:
            pass
    
    if 'Nifty50' not in sector_data:
        return pd.DataFrame()
    
    # Calculate monthly PE multiples
    nifty_monthly = sector_data['Nifty50'].groupby('month')['pe'].mean()
    
    # Generate month labels for display
    months_list = sorted(nifty_monthly.index, reverse=True)
    
    rows = []
    for month in months_list:
        month_label = month.strftime('%b-%y')
        row = {'Month': month_label, 'Nifty50': 1.0}
        
        nifty_pe = nifty_monthly.get(month)
        if nifty_pe is None or pd.isna(nifty_pe):
            continue
        
        for code, col_name in all_indices:
            if col_name == 'Nifty50':
                continue
            if col_name in sector_data:
                sector_monthly = sector_data[col_name].groupby('month')['pe'].mean()
                sector_pe = sector_monthly.get(month)
                if sector_pe is not None and not pd.isna(sector_pe) and nifty_pe > 0:
                    row[col_name] = round(sector_pe / nifty_pe, 1)
                else:
                    row[col_name] = None
            else:
                row[col_name] = None
        
        rows.append(row)
    
    return pd.DataFrame(rows)


# Index Historical Data Cache directory
INDEX_HIST_CACHE_DIR = Path(__file__).parent / ".cache" / "index_history"
INDEX_HIST_CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _get_index_hist_cache_path(index_code: str) -> Path:
    """Get the cache file path for index historical data."""
    safe_code = index_code.replace(" ", "_").replace("/", "_")
    return INDEX_HIST_CACHE_DIR / f"{safe_code}_history.csv"

def _load_cached_index_history(index_code: str) -> pd.DataFrame:
    """Load cached index historical data from disk."""
    cache_path = _get_index_hist_cache_path(index_code)
    if cache_path.exists():
        try:
            df = pd.read_csv(cache_path)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            print(f"Error loading cached history for {index_code}: {e}")
    return None

def _save_index_hist_cache(index_code: str, df: pd.DataFrame):
    """Save index historical data to disk cache."""
    try:
        cache_path = _get_index_hist_cache_path(index_code)
        df_to_save = df.copy()
        df_to_save['date'] = df_to_save['date'].dt.strftime('%Y-%m-%d')
        df_to_save.to_csv(cache_path, index=False)
        print(f"💾 Saved history cache for {index_code}: {len(df)} rows")
    except Exception as e:
        print(f"Error saving history cache for {index_code}: {e}")

def get_index_historical_data(index_codes: list, months: int = 60) -> dict:
    """
    Fetch historical PE, PB, Div Yield data for selected indices.
    Uses incremental caching - only fetches new data.
    Returns a dict with index_code as key and DataFrame as value.
    """
    try:
        from nsepython import index_pe_pb_div
    except ImportError:
        return {}
    
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    import time
    
    # All available indices
    all_indices = {
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
        "NIFTY MEDIA": "Nifty Media",
        "NIFTY COMMODITIES": "Nifty Commodities",
        "NIFTY NEXT 50": "Nifty Next 50",
        "NIFTY 100": "Nifty 100",
        "NIFTY 500": "Nifty 500",
        "NIFTY MIDCAP 50": "Nifty Midcap 50",
        "NIFTY SMLCAP 250": "Nifty Smallcap 250",
    }
    
    # Date range for requested period
    end_date = datetime.now()
    requested_start = end_date - relativedelta(months=months)
    
    results = {}
    
    for code in index_codes:
        if code not in all_indices:
            continue
        
        name = all_indices[code]
        
        # Try to load cached data first
        cached_df = _load_cached_index_history(code)
        
        if cached_df is not None and not cached_df.empty:
            last_cached_date = cached_df['date'].max()
            today = pd.Timestamp.now().normalize()
            
            # If cache is recent (within 1 day), use it
            if (today - last_cached_date).days <= 1:
                print(f"📦 Using cached history for {code}: {len(cached_df)} rows")
                # Filter to requested period
                filtered_df = cached_df[cached_df['date'] >= pd.to_datetime(requested_start)]
                filtered_df['index_name'] = name
                results[code] = filtered_df
                continue
            
            # Fetch only new data
            new_start = (last_cached_date + timedelta(days=1)).strftime("%d-%b-%Y")
            end_str = end_date.strftime("%d-%b-%Y")
            
            print(f"📊 Updating history for {code} from {new_start}")
            
            try:
                new_data = _safe_index_pe_pb_div(code, new_start, end_str)
                
                if isinstance(new_data, pd.DataFrame) and not new_data.empty:
                    new_df = new_data.copy()
                    new_df['date'] = pd.to_datetime(new_df['DATE'], format='%d %b %Y')
                    new_df['pe'] = pd.to_numeric(new_df['pe'], errors='coerce')
                    new_df['pb'] = pd.to_numeric(new_df['pb'], errors='coerce')
                    new_df['div_yield'] = pd.to_numeric(new_df['divYield'], errors='coerce')
                    new_df = new_df[['date', 'pe', 'pb', 'div_yield']]
                    
                    # Merge with cached data
                    full_df = pd.concat([cached_df[['date', 'pe', 'pb', 'div_yield']], new_df], ignore_index=True)
                    full_df = full_df.drop_duplicates(subset=['date'], keep='last')
                    full_df = full_df.sort_values('date').reset_index(drop=True)
                    
                    # Save updated cache
                    _save_index_hist_cache(code, full_df)
                    
                    # Filter to requested period
                    filtered_df = full_df[full_df['date'] >= pd.to_datetime(requested_start)]
                    filtered_df['index_name'] = name
                    results[code] = filtered_df
                else:
                    # No new data, use cached
                    filtered_df = cached_df[cached_df['date'] >= pd.to_datetime(requested_start)]
                    filtered_df['index_name'] = name
                    results[code] = filtered_df
                
                time.sleep(0.2)
                continue
            except Exception as e:
                print(f"Error updating {code}: {e}")
                # Fall back to cached data
                filtered_df = cached_df[cached_df['date'] >= pd.to_datetime(requested_start)]
                filtered_df['index_name'] = name
                results[code] = filtered_df
                continue
        
        # No cache - fetch full history
        start_str = requested_start.strftime("%d-%b-%Y")
        end_str = end_date.strftime("%d-%b-%Y")
        
        try:
            data = _safe_index_pe_pb_div(code, start_str, end_str)
            
            if isinstance(data, pd.DataFrame) and not data.empty:
                df = data.copy()
                df['date'] = pd.to_datetime(df['DATE'], format='%d %b %Y')
                df['pe'] = pd.to_numeric(df['pe'], errors='coerce')
                df['pb'] = pd.to_numeric(df['pb'], errors='coerce')
                df['div_yield'] = pd.to_numeric(df['divYield'], errors='coerce')
                df = df[['date', 'pe', 'pb', 'div_yield']].sort_values('date')
                
                # Save to cache
                _save_index_hist_cache(code, df)
                
                df['index_name'] = name
                results[code] = df
            
            time.sleep(0.2)
        except Exception as e:
            print(f"Error fetching {code}: {e}")
    
    return results


def get_index_details(index_codes: list) -> pd.DataFrame:
    """
    Fetch detailed data for selected indices including PE, PB, Div Yield, and Index Value.
    """
    try:
        from nsepython import index_pe_pb_div, nse_index
    except ImportError:
        return pd.DataFrame()
    
    from datetime import datetime, timedelta
    import time
    
    results = []
    
    # Date range for recent data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    start_str = start_date.strftime("%d-%b-%Y")
    end_str = end_date.strftime("%d-%b-%Y")
    
    # All available indices
    all_indices = {
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
        "NIFTY MEDIA": "Nifty Media",
        "NIFTY COMMODITIES": "Nifty Commodities",
        "NIFTY NEXT 50": "Nifty Next 50",
        "NIFTY 100": "Nifty 100",
        "NIFTY 500": "Nifty 500",
        "NIFTY MIDCAP 50": "Nifty Midcap 50",
        "NIFTY SMLCAP 250": "Nifty Smallcap 250",
    }
    
    for code in index_codes:
        if code not in all_indices:
            continue
        
        name = all_indices[code]
        
        try:
            # Fetch PE, PB, Div Yield
            pe_data = _safe_index_pe_pb_div(code, start_str, end_str)
            
            if isinstance(pe_data, pd.DataFrame) and not pe_data.empty:
                latest = pe_data.iloc[0]
                pe = float(latest['pe']) if 'pe' in latest else None
                pb = float(latest['pb']) if 'pb' in latest else None
                div_yield = float(latest['divYield']) if 'divYield' in latest else None
                date = latest['DATE'] if 'DATE' in latest else None
                
                # Try to get index value
                index_value = None
                try:
                    idx_data = nse_index(code)
                    if idx_data and 'last' in idx_data:
                        index_value = float(idx_data['last'])
                    elif idx_data and 'lastPrice' in idx_data:
                        index_value = float(idx_data['lastPrice'])
                except:
                    pass
                
                results.append({
                    'index_code': code,
                    'index_name': name,
                    'index_value': index_value,
                    'pe': pe,
                    'pb': pb,
                    'div_yield': div_yield,
                    'date': date
                })
            
            time.sleep(0.2)
        except Exception as e:
            pass
    
    return pd.DataFrame(results)


def get_available_indices() -> dict:
    """Return all available indices for selection."""
    return {
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
        "NIFTY MEDIA": "Nifty Media",
        "NIFTY COMMODITIES": "Nifty Commodities",
        "NIFTY NEXT 50": "Nifty Next 50",
        "NIFTY 100": "Nifty 100",
        "NIFTY 500": "Nifty 500",
        "NIFTY MIDCAP 50": "Nifty Midcap 50",
        "NIFTY SMLCAP 250": "Nifty Smallcap 250",
    }


# Popular MF scheme codes for quick access
POPULAR_SCHEMES = {
    "122639": "Parag Parikh Flexi Cap Fund - Direct Growth",
    "120505": "Axis Bluechip Fund - Direct Growth",
    "120503": "Axis Long Term Equity Fund - Direct Growth",
    "118989": "Mirae Asset Large Cap Fund - Direct Growth",
    "119598": "SBI Small Cap Fund - Direct Growth",
    "120587": "HDFC Index Fund - Nifty 50 Plan - Direct Growth",
    "120716": "UTI Nifty 50 Index Fund - Direct Growth",
    "135781": "Nippon India Nifty 50 BeES ETF",
}


# ExitMantra sentiment cache
_EXITMANTRA_CACHE = {"data": None, "timestamp": None}
_EXITMANTRA_CACHE_TTL = 3600  # 1 hour cache


def get_exitmantra_sentiment() -> dict:
    """
    Scrape market sentiment from ExitMantra homepage.
    Returns sentiment zone and estimated percentage.
    
    Zones: Panic (0-25%), Pessimism (25-45%), Optimism (45-75%), Euphoria (75-100%)
    """
    global _EXITMANTRA_CACHE
    
    # Check cache
    if _EXITMANTRA_CACHE["data"] and _EXITMANTRA_CACHE["timestamp"]:
        age = (datetime.now() - _EXITMANTRA_CACHE["timestamp"]).total_seconds()
        if age < _EXITMANTRA_CACHE_TTL:
            return _EXITMANTRA_CACHE["data"]
    
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "BeautifulSoup not installed", "sentiment": "Unknown", "percentage": 50}
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get("https://exitmantra.com/", headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for sentiment text - ExitMantra shows it prominently
        # The sentiment appears below the gauge as text like "Optimism", "Pessimism" etc.
        sentiment_text = None
        
        # Try to find the sentiment indicator text
        for tag in soup.find_all(['h2', 'h3', 'p', 'span', 'div']):
            text = tag.get_text().strip().lower()
            if text in ['panic', 'pessimism', 'optimism', 'euphoria']:
                sentiment_text = text.capitalize()
                break
        
        if not sentiment_text:
            # Default if not found
            sentiment_text = "Unknown"
        
        # Map sentiment to percentage range
        sentiment_percentages = {
            "Panic": {"min": 0, "max": 25, "mid": 12, "color": "#dc2626"},
            "Pessimism": {"min": 25, "max": 45, "mid": 35, "color": "#f97316"},
            "Optimism": {"min": 45, "max": 75, "mid": 60, "color": "#0ea5e9"},
            "Euphoria": {"min": 75, "max": 100, "mid": 87, "color": "#22c55e"},
            "Unknown": {"min": 40, "max": 60, "mid": 50, "color": "#6b7280"},
        }
        
        info = sentiment_percentages.get(sentiment_text, sentiment_percentages["Unknown"])
        
        result = {
            "sentiment": sentiment_text,
            "percentage": info["mid"],
            "percentage_range": f"{info['min']}-{info['max']}%",
            "color": info["color"],
            "source": "ExitMantra",
            "last_updated": datetime.now().isoformat(),
        }
        
        # Cache the result
        _EXITMANTRA_CACHE["data"] = result
        _EXITMANTRA_CACHE["timestamp"] = datetime.now()
        
        return result
        
    except Exception as e:
        return {
            "error": str(e),
            "sentiment": "Unknown",
            "percentage": 50,
            "color": "#6b7280",
            "source": "ExitMantra",
        }


if __name__ == "__main__":
    # Test the data fetchers
    print("Testing data fetchers...")
    
    # Test Nifty data
    print("\n1. Nifty 50 data:")
    nifty = get_nifty_data("2024-01-01", "2024-12-31")
    print(f"   Fetched {len(nifty)} weeks")
    print(nifty.tail())
    
    # Test MF data
    print("\n2. Parag Parikh NAV data:")
    mf = get_mf_nav_data("122639", "2024-01-01", "2024-12-31")
    print(f"   Fetched {len(mf)} days")
    print(f"   Scheme: {mf.attrs.get('scheme_name')}")
    print(mf.tail())
    
    # Test PE data
    print("\n3. Nifty PE data:")
    try:
        pe = get_nifty_pe_data("2024-01-01", "2024-12-31")
        print(f"   Fetched {len(pe)} days")
        print(pe.tail())
    except FileNotFoundError as e:
        print(f"   {e}")
    
    print("\nAll tests completed!")

