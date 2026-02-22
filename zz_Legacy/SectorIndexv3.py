import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import random
import time
import os
import pickle

warnings.filterwarnings('ignore')

# Cache settings
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_HOURS = 4           # refresh data older than this
MIN_BARS_REQUIRED = 100
MAX_AGE_DAYS_LAST_BAR = 5

# ====================== CONFIGURATION ======================
SECTORS = {
    'tech':          {'ticker': 'SOXX', 'name': 'Tech',         'color': '#FF6B6B'},
    'finance':       {'ticker': 'XLF',  'name': 'Finance',      'color': '#45B7D1'},
    'health':        {'ticker': 'XLV',  'name': 'Health',       'color': '#DDA0DD'},
    'energy':        {'ticker': 'XLE',  'name': 'Energy',       'color': '#F7DC6F'},
    'reits':         {'ticker': 'VNQ',  'name': 'REITs',        'color': '#FFEAA7'},
    'industrials':   {'ticker': 'XLI',  'name': 'Industrials',  'color': '#85C1E9'},
    'materials':     {'ticker': 'XLB',  'name': 'Materials',    'color': '#BB8FCE'},
    'utilities':     {'ticker': 'XLU',  'name': 'Utilities',    'color': '#73C6B6'},
    'consumer_disc': {'ticker': 'XLY',  'name': 'Consumption',  'color': '#82E0AA'},
    'consumer_stap': {'ticker': 'XLP',  'name': 'Staples',      'color': '#F8C471'},
    'transport':     {'ticker': 'IYT',  'name': 'Transport',    'color': '#EB984E'},
    'insurance':     {'ticker': 'KIE',  'name': 'Insurance',    'color': '#96CEB4'}
}

# Safety check
if not isinstance(SECTORS, dict):
    print("CRITICAL ERROR: SECTORS is not a dictionary!")
    print("Type found:", type(SECTORS))
    exit(1)

print(f"Loaded {len(SECTORS)} sectors successfully")

# ====================== CACHED DATA FETCHING ======================
def load_cached_data(ticker):
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    if not os.path.exists(path):
        return None, None
    
    try:
        with open(path, 'rb') as f:
            df, fetch_time = pickle.load(f)
        
        age_hours = (datetime.now() - fetch_time).total_seconds() / 3600
        if age_hours > CACHE_HOURS:
            print(f"Cache for {ticker} expired ({age_hours:.1f}h old)")
            return None, None
        
        # Basic validation
        if df is None or df.empty or len(df) < MIN_BARS_REQUIRED:
            print(f"Cache invalid for {ticker}: too few bars ({len(df) if df is not None else 0})")
            return None, None
        
        last_date = df.index.max()
        days_old = (datetime.now().date() - last_date.date()).days
        if days_old > MAX_AGE_DAYS_LAST_BAR:
            print(f"Cache stale for {ticker}: last bar {days_old} days old")
            return None, None
        
        if df['Close'].isna().all():
            print(f"Cache invalid for {ticker}: all Close values NaN")
            return None, None
        
        print(f"✓ Loaded cache for {ticker} ({len(df)} bars, fetched {fetch_time:%Y-%m-%d %H:%M})")
        return df, fetch_time
    except Exception as e:
        print(f"Cache load failed for {ticker}: {e}")
        return None, None


def save_cached_data(ticker, df):
    if df.empty:
        return
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    fetch_time = datetime.now()
    with open(path, 'wb') as f:
        pickle.dump((df, fetch_time), f)
    print(f"→ Saved cache for {ticker}")


def get_stock_data(ticker, force_refresh=False, max_retries=5, base_delay=5):
    """Try cache first → fetch only if needed or forced"""
    if not force_refresh:
        cached_df, _ = load_cached_data(ticker)
        if cached_df is not None:
            return cached_df
    
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1',
    ]

    for attempt in range(max_retries):
        try:
            end_ts   = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=1095)).timestamp())

            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
            
            params = {
                'period1': start_ts,
                'period2': end_ts,
                'interval': '1d',
                'includePrePost': 'false',
                'events': 'history',
                'includeAdjustedClose': 'true'
            }

            headers = {'User-Agent': random.choice(ua_list)}

            print(f"Fetching {ticker} (attempt {attempt+1}/{max_retries})...")
            response = requests.get(url, params=params, headers=headers, timeout=20)
            response.raise_for_status()

            data = response.json()
            
            if not data.get('chart', {}).get('result'):
                raise ValueError("No chart result")

            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]
            adj_close = result['indicators'].get('adjclose', [{}])[0].get('adjclose', [])

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

            if len(df) < 50:
                raise ValueError(f"Too few bars: {len(df)}")

            print(f"✓ {ticker:6s} SUCCESS - {len(df):4d} bars   {df.index.min():%Y-%m-%d} → {df.index.max():%Y-%m-%d}")
            
            save_cached_data(ticker, df)
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]

        except Exception as e:
            print(f"✗ {ticker} attempt {attempt+1} failed → {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = base_delay + random.uniform(0, 3) + attempt * 2
                print(f"   → Retrying in {sleep_time:.1f} s ...")
                time.sleep(sleep_time)
    
    print(f"✗ {ticker} FAILED after {max_retries} attempts")
    return pd.DataFrame()


# ====================== ANALYTICS LOGIC ======================
def calculate_indicators(df, spy_df=None):
    df = df.copy()
    
    df['SMA_50']  = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
    df['Return']  = df['Close'].pct_change() * 100
    
    # RSI
    delta = df['Close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - 100 / (1 + rs)
    df['RSI'] = df['RSI'].fillna(50)

    # Relative strength vs SPY
    if spy_df is not None and not spy_df.empty and 'Close' in spy_df.columns:
        try:
            aligned_spy = spy_df['Close'].reindex(df.index).ffill()
            if aligned_spy.notna().any():
                df['Rel_Line']     = df['Close'] / aligned_spy
                spy_ret            = aligned_spy.pct_change() * 100
                df['Alpha']        = df['Return'] - spy_ret
                df['Rel_Perf_20D'] = df['Rel_Line'].pct_change(20) * 100
            else:
                raise ValueError("Aligned SPY data all NaN")
        except Exception as e:
            print(f"Relative strength failed ({e}) → using zeros")
            df['Alpha'] = df['Rel_Perf_20D'] = 0
    else:
        df['Alpha'] = df['Rel_Perf_20D'] = 0

    return df


def determine_trend_state(df):
    if df.empty:
        return "Neutral", "#8a94a6"
    
    current   = df.iloc[-1]
    price     = current['Close']
    sma50     = current['SMA_50']
    rel_perf  = current.get('Rel_Perf_20D', 0)
    
    if   price > sma50 and rel_perf > 0: return "LEADING",   "#26a69a"
    elif price > sma50 and rel_perf < 0: return "WEAKENING", "#F7DC6F"
    elif price < sma50 and rel_perf > 0: return "IMPROVING", "#45B7D1"
    elif price < sma50 and rel_perf < 0: return "LAGGING",   "#ef5350"
    return "Neutral", "#8a94a6"


# ====================== SPARKLINE ======================
def create_sparkline(df, color):
    if df.empty:
        return ""
    data = df['Close'].tail(30).tolist()
    if not data:
        return ""
    
    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val if max_val != min_val else 1
    
    points = ""
    width = 100
    height = 30
    step = width / (len(data) - 1) if len(data) > 1 else 0
    
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


# ====================== MAIN DASHBOARD ======================
def generate_dashboard(force_refresh=False):
    print("🚀 Starting sector rotation dashboard (with cache)...\n")
    
    spy_df = get_stock_data('SPY', force_refresh=force_refresh)
    if spy_df.empty:
        print("WARNING: No SPY data (even after fetch) → relative metrics = 0\n")
    
    analyzed_sectors = []
    
    for key, config in SECTORS.items():
        df = get_stock_data(config['ticker'], force_refresh=force_refresh)
        time.sleep(random.uniform(1.2, 2.8))  # polite delay only when actually fetching
        
        if df.empty or len(df) < 20:
            print(f"Skipping {config['name']} ({config['ticker']}) — insufficient data")
            continue
            
        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        
        last = df.iloc[-1]
        
        analyzed_sectors.append({
            'id': key,
            'config': config,
            'price': last['Close'],
            'return': last['Return'],
            'alpha': last['Alpha'],
            'rel_perf': last['Rel_Perf_20D'],
            'trend_text': trend_text,
            'trend_color': trend_color,
            'sparkline': create_sparkline(df, config['color'])
        })

    analyzed_sectors.sort(key=lambda x: x.get('rel_perf', -9999), reverse=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ====================== SIMPLE BUT NICE HTML ======================
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sector Rotation Dashboard</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 1rem; background: #f5f5f5; }}
        h1 {{ text-align: center; color: #222; }}
        .last-update {{ text-align: center; color: #666; margin-bottom: 1.5rem; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.2rem; }}
        .card {{ background: white; border-radius: 10px; padding: 1.2rem; box-shadow: 0 3px 10px rgba(0,0,0,0.08); }}
        .name {{ font-size: 1.4rem; font-weight: bold; margin-bottom: 0.6rem; }}
        .metric {{ margin: 0.4rem 0; }}
        .trend {{ display: inline-block; padding: 0.4rem 1rem; border-radius: 1rem; color: white; font-weight: bold; }}
        svg {{ width: 100%; height: 70px; margin-top: 0.8rem; }}
    </style>
</head>
<body>
    <h1>Sector Rotation Dashboard</h1>
    <div class="last-update">Last updated: {timestamp}</div>
    
    <div class="grid">
"""

    for sector in analyzed_sectors:
        c = sector['config']
        html += f"""
        <div class="card">
            <div class="name" style="color: {c['color']}">{c['name']} ({c['ticker']})</div>
            <div class="metric">Price: <strong>{sector['price']:.2f}</strong></div>
            <div class="metric">1D Return: <strong>{sector['return']:.2f}%</strong></div>
            <div class="metric">Alpha: <strong>{sector['alpha']:.2f}%</strong></div>
            <div class="metric">20D Rel Perf: <strong>{sector['rel_perf']:.2f}%</strong></div>
            <div class="trend" style="background: {sector['trend_color']}">{sector['trend_text']}</div>
            {sector['sparkline']}
        </div>
"""

    html += """
    </div>
</body>
</html>
"""

    with open('sector_flow.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard generated → sector_flow.html")
    print(f"   → {len(analyzed_sectors)} sectors included")


if __name__ == "__main__":
    # Normal run: use cache when valid
    generate_dashboard(force_refresh=False)
    
    # Uncomment to force full refresh (ignores cache):
    # generate_dashboard(force_refresh=True)