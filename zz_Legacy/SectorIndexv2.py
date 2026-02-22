import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import random
import time

warnings.filterwarnings('ignore')

# ====================== CONFIGURATION ======================
SECTORS = {
    'tech': {'ticker': 'SOXX', 'name': 'Tech', 'color': '#FF6B6B'},
    'finance': {'ticker': 'XLF', 'name': 'Finance', 'color': '#45B7D1'},
    'health': {'ticker': 'XLV', 'name': 'Health', 'color': '#DDA0DD'},
    'energy': {'ticker': 'XLE', 'name': 'Energy', 'color': '#F7DC6F'},
    'reits': {'ticker': 'VNQ', 'name': 'REITs', 'color': '#FFEAA7'},
    'industrials': {'ticker': 'XLI', 'name': 'Industrials', 'color': '#85C1E9'},
    'materials': {'ticker': 'XLB', 'name': 'Materials', 'color': '#BB8FCE'},
    'utilities': {'ticker': 'XLU', 'name': 'Utilities', 'color': '#73C6B6'},
    'consumer_disc': {'ticker': 'XLY', 'name': 'Consumption', 'color': '#82E0AA'},
    'consumer_stap': {'ticker': 'XLP', 'name': 'Staples', 'color': '#F8C471'},
    'transport': {'ticker': 'IYT', 'name': 'Transport', 'color': '#EB984E'},
    'insurance': {'ticker': 'KIE', 'name': 'Insurance', 'color': '#96CEB4'}
}

# ====================== DATA FETCHING with RETRIES ======================
def get_stock_data(ticker, max_retries=3, base_delay=4):
    """Fetch with retries and backoff - using query2 endpoint"""
    for attempt in range(max_retries):
        try:
            end_ts   = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=1095)).timestamp())  # ~3 years

            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
            
            params = {
                'period1': start_ts,
                'period2': end_ts,
                'interval': '1d',
                'includePrePost': 'false',
                'events': 'history',
                'includeAdjustedClose': 'true'
            }

            ua_list = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
            ]
            headers = {'User-Agent': random.choice(ua_list)}

            print(f"Fetching {ticker} (attempt {attempt+1}/{max_retries})...")
            response = requests.get(url, params=params, headers=headers, timeout=12)
            response.raise_for_status()

            data = response.json()
            
            if not data.get('chart', {}).get('result'):
                raise ValueError("No chart result in response")

            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]
            adj_close = result['indicators'].get('adjclose', [{}])[0].get('adjclose', [])

            if not timestamps or len(timestamps) == 0:
                raise ValueError("No timestamps returned")

            df = pd.DataFrame({
                'Open':   quote.get('open',   [None]*len(timestamps)),
                'High':   quote.get('high',   [None]*len(timestamps)),
                'Low':    quote.get('low',    [None]*len(timestamps)),
                'Close':  quote.get('close',  [None]*len(timestamps)),
                'Volume': quote.get('volume', [None]*len(timestamps)),
            }, index=pd.to_datetime(timestamps, unit='s'))

            if adj_close and len(adj_close) == len(timestamps):
                df['Close'] = adj_close

            df = df.ffill().dropna(how='all')

            print(f"✓ {ticker:6s} SUCCESS - {len(df):4d} bars   {df.index.min():%Y-%m-%d} → {df.index.max():%Y-%m-%d}")
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]

        except Exception as e:
            print(f"✗ {ticker:6s} attempt {attempt+1} failed → {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = base_delay + attempt * 2
                print(f"   → Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
    
    print(f"✗ {ticker:6s} FAILED after {max_retries} attempts")
    return pd.DataFrame()

# ====================== ANALYTICS LOGIC ======================
def calculate_indicators(df, spy_df=None):
    """Safe version that doesn't crash when spy_df is missing/empty"""
    df = df.copy()
    
    df['SMA_50']  = df['Close'].rolling(50,  min_periods=1).mean()
    df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
    df['Return']  = df['Close'].pct_change() * 100
    
    # RSI
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - 100 / (1 + rs)
    df['RSI'] = df['RSI'].fillna(50)

    # Relative strength vs SPY - safe handling
    if spy_df is not None and not spy_df.empty and 'Close' in spy_df.columns:
        try:
            aligned_spy = spy_df['Close'].reindex(df.index).ffill()
            if aligned_spy.notna().any():
                df['Rel_Line']     = df['Close'] / aligned_spy
                spy_ret            = aligned_spy.pct_change() * 100
                df['Alpha']        = df['Return'] - spy_ret
                df['Rel_Perf_20D'] = df['Rel_Line'].pct_change(20) * 100
                print("Relative strength calculated successfully")
            else:
                raise ValueError("Aligned SPY data is all NaN")
        except Exception as e:
            print(f"Warning: Relative strength calculation failed ({e}) → using zeros")
            df['Alpha']        = 0
            df['Rel_Perf_20D'] = 0
    else:
        print("No valid SPY data → relative metrics set to 0")
        df['Alpha']        = 0
        df['Rel_Perf_20D'] = 0

    return df

def determine_trend_state(df):
    if df.empty: return "Neutral", "#8a94a6"
    
    current   = df.iloc[-1]
    price     = current['Close']
    sma50     = current['SMA_50']
    rel_perf  = current.get('Rel_Perf_20D', 0)
    
    if   price > sma50 and rel_perf > 0:  return "LEADING",   "#26a69a"
    elif price > sma50 and rel_perf < 0:  return "WEAKENING", "#F7DC6F"
    elif price < sma50 and rel_perf > 0:  return "IMPROVING", "#45B7D1"
    elif price < sma50 and rel_perf < 0:  return "LAGGING",   "#ef5350"
    return "Neutral", "#8a94a6"

# ====================== CHART & HTML GENERATION ======================
def create_sparkline(df, color):
    if df.empty: return ""
    data = df['Close'].tail(30).tolist()
    if not data: return ""
    
    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val if max_val != min_val else 1
    
    points = ""
    width  = 100
    height = 30
    step   = width / (len(data) - 1) if len(data) > 1 else 0
    
    for i, val in enumerate(data):
        x = i * step
        y = height - ((val - min_val) / range_val * height)
        points += f"{x},{y} "
        
    return f"""
    <svg viewBox="0 0 {width} {height}" class="sparkline" preserveAspectRatio="none">
        <polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" vector-effect="non-scaling-stroke"/>
        <circle cx="{width}" cy="{height - ((data[-1] - min_val) / range_val * height)}" r="2.5" fill="{color}"/>
    </svg>
    """

def generate_dashboard():
    print("🚀 Fetching sector data (query2 + retries)...\n")
    
    spy_df = get_stock_data('SPY')
    if spy_df.empty:
        print("WARNING: SPY data missing → relative metrics (Alpha, Rel_Perf_20D) set to 0 for all sectors\n")
    
    analyzed_sectors = []
    
    for key, config in SECTORS.items():
        df = get_stock_data(config['ticker'])
        time.sleep(2)  # polite delay
        
        if df.empty or len(df) < 20:
            print(f"Skipping {config['name']} ({config['ticker']}) — insufficient data")
            continue
            
        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        
        last = df.iloc[-1]
        
        analyzed_sectors.append({
            'id': key,
            'config': config,
            'df': df,
            'price': last['Close'],
            'return': last['Return'],
            'alpha': last['Alpha'],
            'rel_perf': last['Rel_Perf_20D'],
            'trend_text': trend_text,
            'trend_color': trend_color
        })

    analyzed_sectors.sort(key=lambda x: x['rel_perf'] if pd.notna(x['rel_perf']) else -9999, reverse=True)

    timestamp = datetime.now().strftime("%H:%M")
    
    # HTML generation (same as before - shortened here for brevity)
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Sector Rotation Dashboard</title>
    <style>
        /* ... your full CSS here (copy from previous version) ... */
    </style>
</head>
<body>
<!-- ... full HTML structure, header, grid, modal, Plotly script ... -->
<!-- Paste your previous HTML template here -->
</body>
</html>
"""

    # (Insert your full HTML string generation code here - the loop for cards, dataStore, openChart function, etc.)
    # For space reasons I'm not repeating the entire 200+ line HTML block again.
    # Just replace the html = """ ... """ part with your previous working version.

    with open('sector_flow.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated: sector_flow.html")
    print(f"   → {len(analyzed_sectors)} sectors included")

if __name__ == "__main__":
    generate_dashboard()