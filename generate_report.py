"""
Generate comparison report for top equity mutual funds across all strategies
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
from data_fetcher import get_nifty_pe_data, resample_to_weekly, align_data, get_nifty_data
from strategy import PRESET_STRATEGIES, simulate_sip
import time

# Top 50 Equity Growth Direct Mutual Funds (AMFI codes)
TOP_EQUITY_FUNDS = {
    # Large Cap
    "122639": "Parag Parikh Flexi Cap Fund",
    "120505": "Axis Bluechip Fund",
    "118989": "Mirae Asset Large Cap Fund",
    "120587": "HDFC Index Fund Nifty 50",
    "120716": "UTI Nifty 50 Index Fund",
    "119598": "SBI Small Cap Fund",
    "119597": "SBI Bluechip Fund",
    "125497": "Canara Robeco Bluechip Equity",
    "118834": "ICICI Pru Bluechip Fund",
    
    # Flexi Cap / Multi Cap
    "125354": "Quant Active Fund",
    "120503": "Axis Long Term Equity (ELSS)",
    "118778": "HDFC Flexi Cap Fund",
    "120847": "Kotak Flexi Cap Fund",
    "119062": "ICICI Pru Value Discovery",
    "125307": "Nippon India Multi Cap Fund",
    
    # Mid Cap
    "119600": "SBI Magnum Midcap Fund",
    "118825": "HDFC Mid-Cap Opportunities",
    "119024": "Kotak Emerging Equity Fund",
    "125492": "Axis Midcap Fund",
    "118989": "Mirae Asset Midcap Fund",
    
    # Small Cap
    "125494": "Axis Small Cap Fund",
    "125356": "Quant Small Cap Fund",
    "118826": "HDFC Small Cap Fund",
    "125308": "Nippon India Small Cap Fund",
    "119022": "Kotak Small Cap Fund",
    
    # Focused / Thematic
    "120861": "ICICI Pru Technology Fund",
    "118778": "HDFC Top 100 Fund",
    "119023": "Kotak Equity Opportunities",
    "119596": "SBI Focused Equity Fund",
    "118835": "ICICI Pru Large & Mid Cap",
    
    # Index Funds
    "135781": "Nippon India Nifty BeES ETF",
    "120465": "ICICI Pru Nifty 50 Index",
    "147622": "Motilal Oswal Nifty 50 Index",
    "145552": "Navi Nifty 50 Index Fund",
    
    # Additional Popular Funds
    "118632": "Franklin India Flexi Cap",
    "119064": "ICICI Pru Multicap Fund",
    "119065": "ICICI Pru Midcap Fund",
    "125353": "Quant Flexi Cap Fund",
    "125355": "Quant Mid Cap Fund",
    "118550": "DSP Flexi Cap Fund",
    "118551": "DSP Midcap Fund",
    "118552": "DSP Small Cap Fund",
    "119599": "SBI Large & Midcap Fund",
    "125496": "Canara Robeco Emerging Equities",
    "147623": "Motilal Oswal Midcap Fund",
    "119063": "ICICI Pru Focused Equity",
}


def fetch_mf_nav(scheme_code: str, start_date: str, end_date: str):
    """Fetch MF NAV data from mfapi.in"""
    try:
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data:
            return None, None
        
        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y')
        df['nav'] = df['nav'].astype(float)
        df = df.sort_values('date').reset_index(drop=True)
        
        # Filter by date
        df = df[(df['date'] >= pd.to_datetime(start_date)) & 
                (df['date'] <= pd.to_datetime(end_date))]
        
        scheme_name = data.get('meta', {}).get('scheme_name', f'Scheme {scheme_code}')
        return df, scheme_name
    except Exception as e:
        print(f"  Error fetching {scheme_code}: {e}")
        return None, None


def run_fund_simulation(mf_data, pe_data, scheme_name, base_amount=5000):
    """Run simulation for a single fund across all strategies"""
    try:
        # Resample to weekly
        mf_weekly = resample_to_weekly(mf_data, 'date', 'nav')
        mf_weekly.columns = ['date', 'close']
        
        # Align with PE data
        aligned = align_data(mf_weekly, pe_data)
        
        if len(aligned) < 52:  # At least 1 year of data
            return None
        
        results = {}
        for name, strategy in PRESET_STRATEGIES.items():
            result = simulate_sip(aligned, strategy, base_amount, 
                                 price_col='nifty_close', pe_col='pe')
            results[name] = {
                'invested': result.total_invested,
                'value': result.current_value,
                'return_pct': result.absolute_return_pct,
                'xirr': result.xirr,
                'weeks': len(aligned)
            }
        
        return results
    except Exception as e:
        print(f"  Simulation error for {scheme_name}: {e}")
        return None


def generate_html_report(results_df, nifty_results):
    """Generate beautiful HTML report"""
    
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIP Strategy Comparison - Top 50 Equity Funds</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: #e2e8f0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1600px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            text-align: center;
            color: #94a3b8;
            margin-bottom: 30px;
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }
        .card h3 { color: #60a5fa; margin-bottom: 10px; }
        .card .value { font-size: 2rem; font-weight: bold; color: #4ade80; }
        .card .label { color: #94a3b8; font-size: 0.9rem; }
        
        .nifty-baseline {
            background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            border: 2px solid #6366f1;
        }
        .nifty-baseline h3 { color: #818cf8; margin-bottom: 15px; }
        .nifty-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }
        .nifty-item { text-align: center; }
        .nifty-item .strategy { color: #94a3b8; font-size: 0.85rem; }
        .nifty-item .return { font-size: 1.5rem; font-weight: bold; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            margin-top: 20px;
        }
        th {
            background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
            color: white;
            padding: 15px 10px;
            text-align: left;
            font-weight: 600;
            cursor: pointer;
            position: sticky;
            top: 0;
        }
        th:hover { background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); }
        td {
            padding: 12px 10px;
            border-bottom: 1px solid #334155;
        }
        tr:hover { background: #334155; }
        .fund-name { 
            max-width: 250px; 
            overflow: hidden; 
            text-overflow: ellipsis; 
            white-space: nowrap;
        }
        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .best { background: rgba(34, 197, 94, 0.2); font-weight: bold; }
        .number { text-align: right; font-family: 'Monaco', monospace; }
        
        .legend {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }
        .balanced { background: #6b7280; }
        .opportunistic { background: #22c55e; }
        .aggressive { background: #f59e0b; }
        .hardcore { background: #ef4444; }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #64748b;
            font-size: 0.85rem;
        }
        
        @media (max-width: 768px) {
            table { font-size: 0.8rem; }
            th, td { padding: 8px 5px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📈 SIP Strategy Comparison</h1>
        <p class="subtitle">Top Equity Mutual Funds | 5-Year Backtest | ₹5,000/week SIP</p>
        
        <div class="nifty-baseline">
            <h3>📊 Nifty 50 Baseline (Reference)</h3>
            <div class="nifty-grid">
"""
    
    # Add Nifty baseline
    for strategy, data in nifty_results.items():
        color = '#4ade80' if data['return_pct'] > 0 else '#f87171'
        html += f"""
                <div class="nifty-item">
                    <div class="strategy">{strategy}</div>
                    <div class="return" style="color: {color};">{data['return_pct']:+.1f}%</div>
                    <div class="strategy">XIRR: {data['xirr']:.1f}%</div>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <div class="legend">
            <div class="legend-item"><div class="legend-color balanced"></div>Balanced (1x always)</div>
            <div class="legend-item"><div class="legend-color opportunistic"></div>Opportunistic (2x-4x)</div>
            <div class="legend-item"><div class="legend-color aggressive"></div>Aggressive (3x-12x)</div>
            <div class="legend-item"><div class="legend-color hardcore"></div>Hardcore (3x-16x)</div>
        </div>
        
        <table id="fundsTable">
            <thead>
                <tr>
                    <th onclick="sortTable(0)">Fund Name</th>
                    <th onclick="sortTable(1)" class="number">Balanced Return</th>
                    <th onclick="sortTable(2)" class="number">Opportunistic Return</th>
                    <th onclick="sortTable(3)" class="number">Aggressive Return</th>
                    <th onclick="sortTable(4)" class="number">Hardcore Return</th>
                    <th onclick="sortTable(5)" class="number">Best Strategy</th>
                    <th onclick="sortTable(6)" class="number">Extra Return vs Balanced</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add fund rows
    for _, row in results_df.iterrows():
        best_strategy = row['best_strategy']
        extra_return = row['hardcore_return'] - row['balanced_return']
        extra_class = 'positive' if extra_return > 0 else 'negative'
        
        html += f"""
                <tr>
                    <td class="fund-name" title="{row['fund_name']}">{row['fund_name'][:45]}{'...' if len(row['fund_name']) > 45 else ''}</td>
                    <td class="number">{row['balanced_return']:+.1f}%</td>
                    <td class="number">{row['opportunistic_return']:+.1f}%</td>
                    <td class="number">{row['aggressive_return']:+.1f}%</td>
                    <td class="number">{row['hardcore_return']:+.1f}%</td>
                    <td class="number"><span class="{best_strategy.lower()}" style="padding: 3px 8px; border-radius: 4px; color: white;">{best_strategy}</span></td>
                    <td class="number {extra_class}">{extra_return:+.1f}%</td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>
        
        <div class="footer">
            <p>Generated on """ + datetime.now().strftime("%d %b %Y %H:%M") + """</p>
            <p>Data Source: mfapi.in | PE Data: Historical Nifty PE</p>
            <p>⚠️ Past performance does not guarantee future results. This is for educational purposes only.</p>
        </div>
    </div>
    
    <script>
        function sortTable(n) {
            var table = document.getElementById("fundsTable");
            var rows = Array.from(table.rows).slice(1);
            var asc = table.getAttribute('data-sort-asc') === 'true';
            
            rows.sort(function(a, b) {
                var x = a.cells[n].innerText.replace(/[₹,%+]/g, '');
                var y = b.cells[n].innerText.replace(/[₹,%+]/g, '');
                
                if (!isNaN(parseFloat(x)) && !isNaN(parseFloat(y))) {
                    return asc ? parseFloat(x) - parseFloat(y) : parseFloat(y) - parseFloat(x);
                }
                return asc ? x.localeCompare(y) : y.localeCompare(x);
            });
            
            rows.forEach(row => table.tBodies[0].appendChild(row));
            table.setAttribute('data-sort-asc', !asc);
        }
    </script>
</body>
</html>
"""
    return html


def main():
    print("=" * 60)
    print("SIP Strategy Comparison Report Generator")
    print("=" * 60)
    
    # Date range (5 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    print(f"\nDate range: {start_str} to {end_str}")
    
    # Load PE data
    print("\nLoading PE data...")
    pe_data = get_nifty_pe_data(start_str, end_str)
    print(f"  PE data: {len(pe_data)} days")
    
    # Run Nifty baseline
    print("\nRunning Nifty 50 baseline...")
    nifty_data = get_nifty_data(start_str, end_str)
    nifty_aligned = align_data(nifty_data, pe_data)
    
    nifty_results = {}
    for name, strategy in PRESET_STRATEGIES.items():
        result = simulate_sip(nifty_aligned, strategy, 5000, 
                             price_col='nifty_close', pe_col='pe')
        nifty_results[name.title()] = {
            'invested': result.total_invested,
            'value': result.current_value,
            'return_pct': result.absolute_return_pct,
            'xirr': result.xirr
        }
    print(f"  Nifty Balanced: {nifty_results['Balanced']['return_pct']:+.1f}%")
    print(f"  Nifty Hardcore: {nifty_results['Hardcore']['return_pct']:+.1f}%")
    
    # Process each fund
    print(f"\nProcessing {len(TOP_EQUITY_FUNDS)} mutual funds...")
    results = []
    
    for i, (code, name) in enumerate(TOP_EQUITY_FUNDS.items()):
        print(f"  [{i+1}/{len(TOP_EQUITY_FUNDS)}] {name[:40]}...", end=" ")
        
        mf_data, scheme_name = fetch_mf_nav(code, start_str, end_str)
        if mf_data is None or len(mf_data) < 100:
            print("SKIPPED (insufficient data)")
            continue
        
        sim_results = run_fund_simulation(mf_data, pe_data, scheme_name)
        if sim_results is None:
            print("SKIPPED (simulation failed)")
            continue
        
        # Find best strategy
        best = max(sim_results.items(), key=lambda x: x[1]['return_pct'])
        
        results.append({
            'fund_code': code,
            'fund_name': scheme_name,
            'balanced_return': sim_results['balanced']['return_pct'],
            'balanced_xirr': sim_results['balanced']['xirr'],
            'opportunistic_return': sim_results['opportunistic']['return_pct'],
            'aggressive_return': sim_results['aggressive']['return_pct'],
            'hardcore_return': sim_results['hardcore']['return_pct'],
            'best_strategy': best[0].title(),
            'weeks': sim_results['balanced']['weeks']
        })
        print(f"OK ({sim_results['balanced']['return_pct']:+.1f}%)")
        
        time.sleep(0.3)  # Rate limit
    
    # Create DataFrame
    df = pd.DataFrame(results)
    df = df.sort_values('hardcore_return', ascending=False)
    
    print(f"\n✓ Processed {len(df)} funds successfully")
    
    # Generate HTML report
    print("\nGenerating HTML report...")
    html = generate_html_report(df, nifty_results)
    
    report_path = "/Users/siddharthjain/Documents/Sid/sip_simulator/fund_comparison_report.html"
    with open(report_path, 'w') as f:
        f.write(html)
    
    print(f"\n✓ Report saved to: {report_path}")
    print(f"\nOpen in browser: file://{report_path}")
    
    # Also save CSV
    csv_path = "/Users/siddharthjain/Documents/Sid/sip_simulator/fund_comparison_data.csv"
    df.to_csv(csv_path, index=False)
    print(f"✓ CSV data saved to: {csv_path}")


if __name__ == "__main__":
    main()
