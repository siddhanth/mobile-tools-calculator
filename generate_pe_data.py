"""
Generate PE data files for Nifty 50, Midcap 50, and Smallcap 250
Based on monthly values observed from nifty-pe-ratio.com screenshots.
Daily values are interpolated from monthly averages.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

# Monthly PE data from nifty-pe-ratio.com screenshots
# Format: {year: [Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec]}

# Nifty 50 PE monthly data (observed from website)
NIFTY50_MONTHLY = {
    2014: [18.5, 18.6, 19.2, 20.1, 20.8, 21.5, 22.3, 22.0, 21.8, 21.5, 22.1, 22.5],
    2015: [22.8, 23.1, 23.5, 22.8, 23.2, 22.5, 22.8, 21.2, 20.8, 21.5, 22.0, 22.2],
    2016: [20.5, 19.8, 20.5, 21.2, 21.0, 22.0, 22.5, 23.0, 22.8, 22.5, 21.0, 21.5],
    2017: [22.0, 22.5, 23.5, 24.0, 24.5, 25.0, 25.5, 24.8, 25.2, 26.0, 26.5, 27.0],
    2018: [27.5, 26.0, 24.5, 25.0, 26.5, 27.0, 28.0, 28.5, 27.0, 25.5, 26.5, 26.0],
    2019: [26.5, 26.0, 28.5, 29.0, 29.5, 28.5, 27.5, 26.5, 27.5, 27.0, 28.0, 28.5],
    2020: [28.0, 26.0, 18.5, 21.0, 22.5, 24.0, 26.0, 30.0, 32.5, 33.0, 34.5, 37.0],  # COVID crash
    2021: [39.0, 40.0, 38.5, 32.0, 30.0, 29.5, 28.0, 27.5, 27.0, 26.5, 25.0, 24.5],
    2022: [23.5, 22.5, 22.0, 21.5, 20.0, 20.5, 21.5, 22.0, 21.5, 21.0, 22.0, 22.5],
    2023: [21.5, 20.5, 20.0, 21.0, 21.5, 22.0, 22.5, 22.0, 21.5, 20.5, 21.0, 22.0],
    2024: [22.5, 23.0, 22.5, 22.0, 23.0, 23.5, 24.0, 23.5, 23.0, 22.5, 22.0, 22.5],
    2025: [22.0, 21.5, 22.0, 22.5, 23.0, 23.5, 24.0, 23.5, 23.0, 22.5, 22.0, 22.0],
}

# Nifty Midcap 50 PE monthly data (from screenshot - has data from 2004)
MIDCAP50_MONTHLY = {
    2004: [15.0, 16.0, 17.0, 14.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 19.0, 18.0],
    2005: [16.0, 17.0, 15.0, 13.0, 14.0, 16.0, 18.0, 19.0, 21.0, 20.0, 22.0, 23.0],
    2006: [25.0, 24.0, 22.0, 20.0, 17.0, 16.0, 18.0, 19.0, 21.0, 23.0, 25.0, 26.0],
    2007: [25.0, 22.0, 19.0, 21.0, 24.0, 26.0, 29.0, 28.0, 32.0, 38.0, 42.0, 39.0],  # Bull run
    2008: [35.0, 32.0, 25.0, 28.0, 30.0, 24.0, 22.0, 24.0, 18.0, 12.0, 10.0, 11.0],  # Crash
    2009: [11.0, 10.0, 12.0, 16.0, 22.0, 25.0, 26.0, 27.0, 28.0, 26.0, 27.0, 29.0],  # Recovery
    2010: [28.0, 26.0, 27.0, 28.0, 25.0, 26.0, 28.0, 29.0, 32.0, 33.0, 31.0, 29.0],
    2011: [27.0, 24.0, 25.0, 26.0, 25.0, 26.0, 27.0, 24.0, 21.0, 22.0, 20.0, 18.0],
    2012: [19.0, 21.0, 20.0, 19.0, 18.0, 19.0, 20.0, 20.0, 22.0, 23.0, 24.0, 25.0],
    2013: [25.0, 23.0, 21.0, 20.0, 21.0, 18.0, 17.0, 15.0, 16.0, 18.0, 19.0, 20.0],
    2014: [21.0, 22.0, 24.0, 26.0, 28.0, 30.0, 33.0, 34.0, 35.0, 33.0, 35.0, 34.0],
    2015: [36.0, 38.0, 40.0, 38.0, 37.0, 35.0, 36.0, 32.0, 30.0, 31.0, 30.0, 29.0],
    2016: [26.0, 24.0, 25.0, 27.0, 28.0, 30.0, 33.0, 35.0, 34.0, 32.0, 28.0, 29.0],
    2017: [31.0, 33.0, 36.0, 38.0, 40.0, 42.0, 45.0, 44.0, 43.0, 45.0, 47.0, 48.0],  # Peak
    2018: [46.0, 42.0, 38.0, 40.0, 42.0, 40.0, 42.0, 44.0, 38.0, 32.0, 34.0, 32.0],
    2019: [34.0, 32.0, 30.0, 28.0, 26.0, 28.0, 25.0, 22.0, 24.0, 26.0, 28.0, 30.0],
    2020: [28.0, 26.0, 16.0, 18.0, 22.0, 26.0, 30.0, 35.0, 38.0, 40.0, 45.0, 50.0],  # COVID recovery
    2021: [55.0, 52.0, 48.0, 42.0, 38.0, 36.0, 34.0, 32.0, 30.0, 28.0, 26.0, 25.0],
    2022: [24.0, 22.0, 21.0, 20.0, 18.0, 19.0, 21.0, 23.0, 22.0, 21.0, 23.0, 24.0],
    2023: [23.0, 22.0, 21.0, 22.0, 24.0, 26.0, 28.0, 27.0, 26.0, 25.0, 27.0, 29.0],
    2024: [30.0, 32.0, 31.0, 30.0, 32.0, 34.0, 36.0, 35.0, 34.0, 33.0, 32.0, 34.0],
    2025: [33.0, 31.0, 30.0, 32.0, 34.0, 35.0, 36.0, 35.0, 34.0, 33.0, 34.0, 34.0],
}

# Nifty Small Cap 250 PE monthly data (from screenshot - data starts 2016)
SMALLCAP250_MONTHLY = {
    2016: [86.0, 92.0, 95.0, 100.0, 105.0, 110.0, 115.0, 120.0, 100.0, 90.0, 80.0, 75.0],
    2017: [76.0, 80.0, 99.0, 103.0, 109.0, 90.0, 110.0, 111.0, 101.0, 76.0, 86.0, 89.0],
    2018: [94.0, 96.0, 90.0, 108.0, 77.0, 64.0, 107.0, 120.0, 64.0, 62.0, 63.0, 41.0],
    2019: [43.0, 42.0, 46.0, 34.0, 31.0, 41.0, 33.0, 31.0, 31.0, 50.0, 63.0, 55.0],
    2020: [52.0, 93.0, 66.0, 60.0, 62.0, 96.0, 25.0, 29.0, 32.0, 57.0, 51.0, 40.0],  # COVID volatility
    2021: [43.0, 41.0, 43.0, 44.0, 45.0, 38.0, 37.0, 29.0, 31.0, 30.0, 29.0, 30.0],
    2022: [32.0, 28.0, 27.0, 25.0, 21.0, 20.0, 20.0, 19.0, 20.0, 19.0, 19.0, 19.0],
    2023: [19.0, 18.0, 18.0, 18.0, 19.0, 21.0, 22.0, 23.0, 25.0, 25.0, 25.0, 26.0],
    2024: [28.0, 29.0, 27.0, 28.0, 28.0, 30.0, 32.0, 31.0, 32.0, 33.0, 32.0, 35.0],
    2025: [33.0, 28.0, 27.0, 30.0, 32.0, 33.0, 34.0, 32.0, 32.0, 31.0, 29.0, 29.0],
}


def interpolate_daily_from_monthly(monthly_data: dict, start_year: int = None) -> pd.DataFrame:
    """
    Convert monthly PE data to daily PE data using linear interpolation.
    Each month's value is placed at mid-month, then interpolated to daily.
    """
    # Create monthly anchor points
    records = []
    for year, monthly_values in monthly_data.items():
        if start_year and year < start_year:
            continue
        for month_idx, pe_value in enumerate(monthly_values, 1):
            # Place value at 15th of each month (mid-month)
            date = datetime(year, month_idx, 15)
            records.append({'date': date, 'pe': pe_value})
    
    df = pd.DataFrame(records)
    df = df.sort_values('date').set_index('date')
    
    # Create daily date range
    start_date = df.index.min() - timedelta(days=14)  # Start from beginning of first month
    end_date = datetime.now()
    daily_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Reindex and interpolate
    df_daily = df.reindex(daily_range)
    df_daily['pe'] = df_daily['pe'].interpolate(method='linear')
    
    # Fill any remaining NaN at edges
    df_daily['pe'] = df_daily['pe'].ffill().bfill()
    
    # Add small random noise for realistic daily variation (±2%)
    np.random.seed(42)
    noise = np.random.uniform(-0.02, 0.02, len(df_daily))
    df_daily['pe'] = df_daily['pe'] * (1 + noise)
    df_daily['pe'] = df_daily['pe'].round(2)
    
    # Reset index and rename
    df_daily = df_daily.reset_index()
    df_daily.columns = ['date', 'pe']
    df_daily['date'] = df_daily['date'].dt.strftime('%Y-%m-%d')
    
    return df_daily


def calculate_statistics(df: pd.DataFrame) -> dict:
    """Calculate statistics for PE data."""
    pe_values = df['pe']
    return {
        'median': pe_values.median(),
        'mean': pe_values.mean(),
        'std': pe_values.std(),
        'min': pe_values.min(),
        'max': pe_values.max(),
        'too_cheap': pe_values.median() - 2 * pe_values.std(),
        'cheap': pe_values.median() - pe_values.std(),
        'fair': pe_values.median(),
        'expensive': pe_values.median() + pe_values.std(),
        'too_expensive': pe_values.median() + 2 * pe_values.std(),
    }


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("Generating PE data files based on nifty-pe-ratio.com monthly data...")
    print("=" * 60)
    
    # Generate Nifty 50 PE data
    print("\n1. Nifty 50 PE Data:")
    nifty50_df = interpolate_daily_from_monthly(NIFTY50_MONTHLY, start_year=2014)
    nifty50_path = os.path.join(output_dir, 'nifty_pe_data.csv')
    nifty50_df.to_csv(nifty50_path, index=False)
    stats = calculate_statistics(nifty50_df)
    print(f"   Records: {len(nifty50_df)}")
    print(f"   Date range: {nifty50_df['date'].iloc[0]} to {nifty50_df['date'].iloc[-1]}")
    print(f"   Median PE: {stats['median']:.2f}")
    print(f"   Std Dev: {stats['std']:.2f}")
    print(f"   Valuation zones:")
    print(f"      Too Cheap: < {stats['too_cheap']:.2f}")
    print(f"      Cheap: {stats['too_cheap']:.2f} - {stats['cheap']:.2f}")
    print(f"      Fair: {stats['cheap']:.2f} - {stats['expensive']:.2f}")
    print(f"      Expensive: {stats['expensive']:.2f} - {stats['too_expensive']:.2f}")
    print(f"      Too Expensive: > {stats['too_expensive']:.2f}")
    print(f"   Saved to: {nifty50_path}")
    
    # Generate Midcap 50 PE data
    print("\n2. Nifty Midcap 50 PE Data:")
    midcap_df = interpolate_daily_from_monthly(MIDCAP50_MONTHLY, start_year=2004)
    midcap_path = os.path.join(output_dir, 'nifty_midcap_pe_data.csv')
    midcap_df.to_csv(midcap_path, index=False)
    stats = calculate_statistics(midcap_df)
    print(f"   Records: {len(midcap_df)}")
    print(f"   Date range: {midcap_df['date'].iloc[0]} to {midcap_df['date'].iloc[-1]}")
    print(f"   Median PE: {stats['median']:.2f}")
    print(f"   Std Dev: {stats['std']:.2f}")
    print(f"   Valuation zones:")
    print(f"      Too Cheap: < {stats['too_cheap']:.2f}")
    print(f"      Cheap: {stats['too_cheap']:.2f} - {stats['cheap']:.2f}")
    print(f"      Fair: {stats['cheap']:.2f} - {stats['expensive']:.2f}")
    print(f"      Expensive: {stats['expensive']:.2f} - {stats['too_expensive']:.2f}")
    print(f"      Too Expensive: > {stats['too_expensive']:.2f}")
    print(f"   Saved to: {midcap_path}")
    
    # Generate Smallcap 250 PE data
    print("\n3. Nifty Small Cap 250 PE Data:")
    smallcap_df = interpolate_daily_from_monthly(SMALLCAP250_MONTHLY, start_year=2016)
    smallcap_path = os.path.join(output_dir, 'nifty_smallcap_pe_data.csv')
    smallcap_df.to_csv(smallcap_path, index=False)
    stats = calculate_statistics(smallcap_df)
    print(f"   Records: {len(smallcap_df)}")
    print(f"   Date range: {smallcap_df['date'].iloc[0]} to {smallcap_df['date'].iloc[-1]}")
    print(f"   Median PE: {stats['median']:.2f}")
    print(f"   Std Dev: {stats['std']:.2f}")
    print(f"   Valuation zones:")
    print(f"      Too Cheap: < {stats['too_cheap']:.2f}")
    print(f"      Cheap: {stats['too_cheap']:.2f} - {stats['cheap']:.2f}")
    print(f"      Fair: {stats['cheap']:.2f} - {stats['expensive']:.2f}")
    print(f"      Expensive: {stats['expensive']:.2f} - {stats['too_expensive']:.2f}")
    print(f"      Too Expensive: > {stats['too_expensive']:.2f}")
    print(f"   Saved to: {smallcap_path}")
    
    print("\n" + "=" * 60)
    print("PE data generation complete!")
    print("\nNote: Daily values are interpolated from monthly data observed")
    print("on nifty-pe-ratio.com, with small random noise added for realism.")


if __name__ == "__main__":
    main()

