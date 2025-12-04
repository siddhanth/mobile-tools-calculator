"""
ETL Scheduler Module
Batch fetches and caches all data for the SIP simulator.
Run daily at market close (3:45 PM IST) or on app startup if stale.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import time

# Cache configuration
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# Cache files
INDICES_PE_PB_CACHE = CACHE_DIR / "indices_daily_pe_pb.parquet"
SECTORS_MATRIX_CACHE = CACHE_DIR / "sectors_monthly_matrix.parquet"
LAST_UPDATE_FILE = CACHE_DIR / "last_update.json"

# Stale threshold in hours
STALE_THRESHOLD_HOURS = 4


def get_last_update_times() -> dict:
    """Get timestamps of last data updates."""
    if LAST_UPDATE_FILE.exists():
        with open(LAST_UPDATE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_last_update_time(dataset: str):
    """Save the current timestamp for a dataset."""
    times = get_last_update_times()
    times[dataset] = datetime.now().isoformat()
    with open(LAST_UPDATE_FILE, 'w') as f:
        json.dump(times, f, indent=2)


def is_stale(dataset: str, hours: int = STALE_THRESHOLD_HOURS) -> bool:
    """Check if a dataset is stale (older than threshold)."""
    times = get_last_update_times()
    if dataset not in times:
        return True
    
    last_update = datetime.fromisoformat(times[dataset])
    age = (datetime.now() - last_update).total_seconds() / 3600
    return age > hours


def fetch_indices_pe_pb_data(years: int = 10) -> pd.DataFrame:
    """
    Fetch PE/PB data for all main indices.
    
    Args:
        years: Number of years of history to fetch
        
    Returns:
        DataFrame with date and PE/PB columns for each index
    """
    try:
        from nsepython import index_pe_pb_div
    except ImportError:
        print("nsepython not installed. Skipping indices PE/PB fetch.")
        return pd.DataFrame()
    
    nse_indices = {
        "NIFTY 50": "nifty50",
        "NIFTY MIDCAP 50": "nifty_midcap",
        "NIFTY SMLCAP 250": "nifty_smallcap",
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    
    all_data = []
    
    for nse_name, key in nse_indices.items():
        print(f"Fetching {nse_name} data...")
        
        # Fetch year by year to avoid API limits
        current_start = start_date
        while current_start < end_date:
            current_end = min(current_start + timedelta(days=365), end_date)
            
            start_str = current_start.strftime('%d-%b-%Y')
            end_str = current_end.strftime('%d-%b-%Y')
            
            try:
                data = index_pe_pb_div(nse_name, start_str, end_str)
                
                if isinstance(data, pd.DataFrame) and not data.empty:
                    df = data.copy()
                    df['index'] = key
                    df['date'] = pd.to_datetime(df['DATE'], format='%d %b %Y')
                    all_data.append(df[['date', 'index', 'pe', 'pb']])
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"Error fetching {nse_name} ({start_str} to {end_str}): {e}")
            
            current_start = current_end
    
    if all_data:
        result = pd.concat(all_data, ignore_index=True)
        result = result.drop_duplicates(subset=['date', 'index']).sort_values(['index', 'date'])
        return result
    
    return pd.DataFrame()


def fetch_sectors_matrix(months: int = 120) -> pd.DataFrame:
    """
    Fetch sector PE multiples matrix.
    
    Args:
        months: Number of months of history
        
    Returns:
        DataFrame with monthly sector PE multiples
    """
    try:
        from data_fetcher import get_sector_pe_matrix
        return get_sector_pe_matrix(months=months, force_refresh=True)
    except Exception as e:
        print(f"Error fetching sector matrix: {e}")
        return pd.DataFrame()


def run_etl(force: bool = False):
    """
    Run the full ETL process.
    
    Args:
        force: If True, refresh all data regardless of staleness
    """
    print(f"Starting ETL at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Indices PE/PB data
    if force or is_stale("indices_pe_pb"):
        print("\n=== Fetching Indices PE/PB Data ===")
        indices_data = fetch_indices_pe_pb_data(years=10)
        
        if not indices_data.empty:
            indices_data.to_parquet(INDICES_PE_PB_CACHE)
            save_last_update_time("indices_pe_pb")
            print(f"Saved {len(indices_data)} rows to {INDICES_PE_PB_CACHE}")
        else:
            print("No indices data fetched")
    else:
        print("Indices PE/PB data is fresh, skipping...")
    
    # 2. Sector matrix
    if force or is_stale("sectors_matrix", hours=24):
        print("\n=== Fetching Sector Matrix ===")
        sectors_data = fetch_sectors_matrix(months=120)
        
        if not sectors_data.empty:
            sectors_data.to_parquet(SECTORS_MATRIX_CACHE)
            save_last_update_time("sectors_matrix")
            print(f"Saved sector matrix with {len(sectors_data)} months")
        else:
            print("No sector data fetched")
    else:
        print("Sector matrix is fresh, skipping...")
    
    print(f"\nETL completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def load_cached_indices_pe_pb() -> pd.DataFrame:
    """Load cached indices PE/PB data."""
    if INDICES_PE_PB_CACHE.exists():
        return pd.read_parquet(INDICES_PE_PB_CACHE)
    return pd.DataFrame()


def load_cached_sectors_matrix() -> pd.DataFrame:
    """Load cached sector matrix."""
    if SECTORS_MATRIX_CACHE.exists():
        return pd.read_parquet(SECTORS_MATRIX_CACHE)
    return pd.DataFrame()


def should_refresh_on_startup() -> bool:
    """Check if data should be refreshed on app startup."""
    return is_stale("indices_pe_pb") or is_stale("sectors_matrix", hours=24)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ETL Scheduler for SIP Simulator")
    parser.add_argument("--force", action="store_true", help="Force refresh all data")
    parser.add_argument("--check", action="store_true", help="Check staleness only")
    
    args = parser.parse_args()
    
    if args.check:
        times = get_last_update_times()
        print("Last Update Times:")
        for dataset, ts in times.items():
            stale = is_stale(dataset)
            status = "STALE" if stale else "Fresh"
            print(f"  {dataset}: {ts} ({status})")
    else:
        run_etl(force=args.force)

