"""
Fetch real daily PE data from NSE using nsepython library.
This replaces the interpolated monthly data with actual daily PE values.
"""

import pandas as pd
from nsepython import index_pe_pb_div
from datetime import datetime, timedelta
import os
import time

# Index mappings
INDEX_CONFIG = {
    "nifty50": {
        "nse_symbol": "NIFTY 50",
        "csv_file": "nifty_pe_data.csv",
        "start_year": 2010,
    },
    "nifty_midcap": {
        "nse_symbol": "NIFTY MIDCAP 50",
        "csv_file": "nifty_midcap_pe_data.csv",
        "start_year": 2010,
    },
    "nifty_smallcap": {
        "nse_symbol": "NIFTY SMLCAP 250",  # Note: NSE uses "SMLCAP" not "SMALLCAP"
        "csv_file": "nifty_smallcap_pe_data.csv",
        "start_year": 2018,  # Smallcap 250 data starts around 2018
    },
}


def fetch_pe_data_for_year(symbol: str, year: int) -> pd.DataFrame:
    """Fetch PE data for a specific year."""
    start_date = f"01-Jan-{year}"
    end_date = f"31-Dec-{year}"
    
    try:
        df = index_pe_pb_div(symbol, start_date, end_date)
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    except Exception as e:
        print(f"  Error fetching {year}: {e}")
    
    return pd.DataFrame()


def fetch_all_pe_data(index_key: str) -> pd.DataFrame:
    """Fetch all available PE data for an index."""
    config = INDEX_CONFIG[index_key]
    symbol = config["nse_symbol"]
    start_year = config["start_year"]
    current_year = datetime.now().year
    
    print(f"\nFetching data for {symbol}...")
    
    all_data = []
    
    for year in range(start_year, current_year + 1):
        print(f"  Fetching {year}...", end=" ")
        df = fetch_pe_data_for_year(symbol, year)
        if not df.empty:
            all_data.append(df)
            print(f"{len(df)} records")
        else:
            print("No data")
        time.sleep(0.5)  # Be nice to the API
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        
        # Clean up the data
        combined['date'] = pd.to_datetime(combined['DATE'], format='%d %b %Y')
        combined['pe'] = pd.to_numeric(combined['pe'], errors='coerce')
        
        # Select and sort
        result = combined[['date', 'pe']].dropna()
        result = result.sort_values('date').drop_duplicates(subset=['date'])
        result['date'] = result['date'].dt.strftime('%Y-%m-%d')
        
        return result
    
    return pd.DataFrame()


def calculate_statistics(df: pd.DataFrame) -> dict:
    """Calculate statistics for the PE data."""
    pe = df['pe']
    return {
        'count': len(df),
        'min': pe.min(),
        'max': pe.max(),
        'median': pe.median(),
        'std': pe.std(),
        'p10': pe.quantile(0.10),
        'p25': pe.quantile(0.25),
        'p75': pe.quantile(0.75),
        'p90': pe.quantile(0.90),
    }


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("FETCHING REAL DAILY PE DATA FROM NSE")
    print("Using nsepython library")
    print("=" * 60)
    
    for index_key, config in INDEX_CONFIG.items():
        df = fetch_all_pe_data(index_key)
        
        if not df.empty:
            csv_path = os.path.join(output_dir, config["csv_file"])
            df.to_csv(csv_path, index=False)
            
            stats = calculate_statistics(df)
            
            print(f"\n✅ {config['nse_symbol']}:")
            print(f"   Records: {stats['count']}")
            print(f"   Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
            print(f"   PE range: {stats['min']:.2f} - {stats['max']:.2f}")
            print(f"   Median: {stats['median']:.2f}, Std: {stats['std']:.2f}")
            print(f"   Percentiles: P10={stats['p10']:.1f}, P25={stats['p25']:.1f}, P75={stats['p75']:.1f}, P90={stats['p90']:.1f}")
            print(f"   Saved to: {csv_path}")
        else:
            print(f"\n❌ {config['nse_symbol']}: No data fetched")
    
    print("\n" + "=" * 60)
    print("DONE! PE data files updated with real NSE daily data.")
    print("=" * 60)


if __name__ == "__main__":
    main()

