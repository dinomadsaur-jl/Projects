import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
import random
import time
import os
import pickle
import json

warnings.filterwarnings('ignore')

# Cache settings
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_HOURS = 4           # general refresh interval
MIN_BARS_REQUIRED = 200
EXPECTED_MIN_BARS_5Y = 1100  # rough minimum for \~5 years of trading days

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

print("Loaded sectors:")
for k, v in SECTORS.items():
    print(f"  {k:12} → {v['name']:12} ({v['ticker']})")

# ====================== CACHED DATA FETCHING ======================
def load_cached_data(ticker):
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    if not os.path.exists(path):
        return None
    
    try:
        with open(path, 'rb') as f:
            df, fetch_time = pickle.load(f)
        
        # Age check
        age_hours = (datetime.now() - fetch_time).total_seconds() / 3600
        if age_hours > CACHE_HOURS:
            print(f"Cache for {ticker} expired ({age_hours:.1f}h old)")
            return None
        
        # Basic validation
        if df is None or df.empty or len(df) < MIN_BARS_REQUIRED:
            print(f"Cache invalid for {ticker}: too few bars ({len(df) if df is not None else 0})")
            return None
        
        # Check if we have \~5 years of data
        first_date = df.index.min()
        years_covered = (datetime.now().date() - first_date.date()).days / 365.25
        if years_covered < 4.7 or len(df) < EXPECTED_MIN_BARS_5Y:
            print(f"Cache for {ticker} does not cover 5 years (only {years_covered:.1f} years, {len(df)} bars)")
            return None
        
        last_date = df.index.max()
        days_old = (datetime.now().date() - last_date.date()).days
        if days_old > 7:
            print(f"Cache for {ticker} stale: last bar {days_old} days old")
            return None
        
        print(f"✓ Valid 5-year cache loaded for {ticker} ({len(df)} bars, {years_covered:.1f} years)")
        return df
    
    except Exception as e:
        print(f"Cache load failed for {ticker}: {e}")
        return None


def save_cached_data(ticker, df):
    if df.empty:
        return
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    with open(path, 'wb') as f:
        pickle.dump((df, datetime.now()), f)
    print(f"→ Saved cache for {ticker}")


def get_stock_data(ticker, force_refresh=False):
    if not force_refresh:
        df = load_cached_data(ticker)
        if df is not None:
            return df

    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
    ]

    for attempt in range(1, 6):
        try:
            end_ts = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=2000)).timestamp())  # try \~5.5 years to be safe

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

            print(f"Fetching {ticker} (attempt {attempt}/5)...")
            r = requests.get(url, params=params, headers=headers, timeout=25)
            r.raise_for_status()

            data = r.json()
            result = data['chart']['result'][0]
            ts = result['timestamp']
            quote = result['indicators']['quote'][0]
            adj = result['indicators'].get('adjclose', [{}])[0].get('adjclose', quote.get('close', []))

            df = pd.DataFrame({
                'Open': quote.get('open'),
                'High': quote.get('high'),
                'Low': quote.get('low'),
                'Close': adj if len(adj) == len(ts) else quote.get('close'),
                'Volume': quote.get('volume'),
            }, index=pd.to_datetime(ts, unit='s')).ffill().dropna(how='all')

            if len(df) < 800:  # rough threshold for <4 years
                print(f"Warning: {ticker} returned only {len(df)} bars")
            
            print(f"Success: {ticker} - {len(df)} bars from {df.index.min():%Y-%m-%d}")
            save_cached_data(ticker, df)
            return df

        except Exception as e:
            print(f"Failed attempt {attempt}: {str(e)}")
            time.sleep(4 + attempt * 3)

    print(f"Failed to fetch {ticker} after 5 attempts")
    return pd.DataFrame()


# ====================== INDICATORS ======================
def calculate_indicators(df, spy_df=None):
    df = df.copy()
    df['SMA_20']  = df['Close'].rolling(20, min_periods=1).mean()
    df['SMA_50']  = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
    df['Return']  = df['Close'].pct_change() * 100

    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - 100 / (1 + rs)
    df['RSI'] = df['RSI'].fillna(50)

    if spy_df is not None and not spy_df.empty:
        try:
            aligned = spy_df['Close'].reindex(df.index).ffill()
            if aligned.notna().any():
                df['Rel_Line'] = df['Close'] / aligned
                df['Alpha'] = df['Return'] - aligned.pct_change() * 100
                df['Rel_Perf_20D'] = df['Rel_Line'].pct_change(20) * 100
                return df
        except:
            pass
    df['Alpha'] = df['Rel_Perf_20D'] = 0
    return df


def determine_trend_state(df):
    if df.empty:
        return "Neutral", "#8a94a6"
    cur = df.iloc[-1]
    price = cur['Close']
    sma50 = cur['SMA_50']
    rel = cur.get('Rel_Perf_20D', 0)

    if price > sma50 and rel > 0:   return "LEADING",   "#26a69a"
    if price > sma50 and rel < 0:   return "WEAKENING", "#F7DC6F"
    if price < sma50 and rel > 0:   return "IMPROVING", "#45B7D1"
    if price < sma50 and rel < 0:   return "LAGGING",   "#ef5350"
    return "Neutral", "#8a94a6"


def create_sparkline(df, color):
    if df.empty: return ""
    data = df['Close'].tail(60).tolist()
    if not data: return ""
    mn, mx = min(data), max(data)
    rg = mx - mn or 1
    points = ""
    w, h = 140, 40
    step = w / (len(data) - 1) if len(data) > 1 else 0
    for i, v in enumerate(data):
        x = i * step
        y = h - ((v - mn) / rg * h)
        points += f"{x},{y} "
    return f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/></svg>'


# ====================== DASHBOARD ======================
def generate_dashboard(force_refresh=False):
    print("Starting dashboard generation...\n")

    spy_df = get_stock_data('SPY', force_refresh)
    if spy_df.empty:
        print("WARNING: No SPY data → relative metrics zeroed")

    sectors_data = []

    for key, config in SECTORS.items():
        print(f"Processing {config['name']} ({config['ticker']})")
        df = get_stock_data(config['ticker'], force_refresh)
        time.sleep(random.uniform(1.0, 2.5))

        if df.empty or len(df) < 100:
            print(f"  → Skipped (insufficient data)")
            continue

        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        last = df.iloc[-1]

        plot_data = {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'close': df['Close'].round(2).tolist(),
            'sma20': df['SMA_20'].round(2).tolist(),
            'sma50': df['SMA_50'].round(2).tolist(),
            'sma200': df['SMA_200'].round(2).tolist(),
            'volume': (df['Volume'] / 1e6).round(1).tolist(),
            'ticker': config['ticker'],
            'name': config['name']
        }

        sectors_data.append({
            'config': config,
            'price': last['Close'],
            'return': last['Return'],
            'alpha': last['Alpha'],
            'rel_perf': last['Rel_Perf_20D'],
            'trend_text': trend_text,
            'trend_color': trend_color,
            'sparkline': create_sparkline(df, config['color']),
            'plot_data': plot_data
        })

    sectors_data.sort(key=lambda x: x.get('rel_perf', -9999), reverse=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sector Rotation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 16px; background: #f8f9fa; }}
        h1 {{ text-align: center; color: #222; }}
        .update {{ text-align: center; color: #555; margin: 1rem 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }}
        .card {{ background: white; border-radius: 10px; padding: 16px; box-shadow: 0 3px 12px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.15s; }}
        .card:hover {{ transform: translateY(-4px); }}
        .name {{ font-size: 1.5rem; font-weight: bold; margin-bottom: 8px; }}
        .metric {{ margin: 6px 0; font-size: 1rem; }}
        .trend {{ display: inline-block; padding: 6px 14px; border-radius: 20px; color: white; font-weight: bold; font-size: 1.1rem; min-width: 110px; text-align: center; }}
        .spark {{ width: 100%; height: 60px; margin-top: 10px; }}
        #modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.65); }}
        #modal-content {{ background: white; margin: 5% auto; padding: 20px; width: 92%; max-width: 1150px; border-radius: 10px; position: relative; }}
        #close {{ position: absolute; right: 20px; top: 5px; font-size: 36px; cursor: pointer; color: #888; }}
        #close:hover {{ color: #000; }}
        #plot {{ width: 100%; height: 65vh; min-height: 500px; }}
    </style>
</head>
<body>
    <h1>Sector Rotation Dashboard</h1>
    <div class="update">Updated: {timestamp} • Click any card for 5-year chart (Price + SMA20 + Volume)</div>

    <div class="grid" id="grid"></div>

    <div id="modal">
        <div id="modal-content">
            <span id="close">&times;</span>
            <h2 id="modal-title"></h2>
            <div id="plot"></div>
        </div>
    </div>

    <script>
        const sectors = {json.dumps(sectors_data, default=str)};

        function render() {{
            const grid = document.getElementById('grid');
            grid.innerHTML = '';
            sectors.forEach(function(s) {{
                const card = document.createElement('div');
                card.className = 'card';

                let html = '<div class="name" style="color:' + s.config.color + '">' 
                         + s.config.name + ' (' + s.config.ticker + ')</div>';

                html += '<div class="metric">Price: <strong>$' + Number(s.price).toFixed(2) + '</strong></div>';
                html += '<div class="metric">1D Return: <strong>' + Number(s.return || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="metric">Alpha: <strong>' + Number(s.alpha || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="metric">20D Rel Perf: <strong>' + Number(s.rel_perf || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="trend" style="background:' + s.trend_color + '">' + s.trend_text + '</div>';
                html += '<div class="spark">' + (s.sparkline || '') + '</div>';

                card.innerHTML = html;
                card.onclick = function() {{ showPlot(s); }};
                grid.appendChild(card);
            }});
        }}

        function showPlot(s) {{
            document.getElementById('modal-title').textContent = 
                s.config.name + " (" + s.config.ticker + ") - 5 Years";
            document.getElementById('modal').style.display = 'block';

            const d = s.plot_data;
            const traces = [
                {{ x: d.dates, y: d.close, type: 'scatter', mode: 'lines', name: 'Close', line: {{color: '#1f77b4', width: 2}} }},
                {{ x: d.dates, y: d.sma20, type: 'scatter', mode: 'lines', name: 'SMA 20', line: {{color: '#ff7f0e', width: 1.5, dash: 'dash'}} }},
                {{ x: d.dates, y: d.volume, type: 'bar', name: 'Volume (M)', yaxis: 'y2', marker: {{color: 'rgba(120,120,120,0.35)'}} }}
            ];

            Plotly.newPlot('plot', traces, {{
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Price'}},
                yaxis2: {{title: 'Volume (M)', overlaying: 'y', side: 'right'}},
                hovermode: 'x unified',
                legend: {{orientation: 'h', y: -0.2}},
                margin: {{t:20, b:60, l:50, r:60}},
                height: 580
            }}, {{responsive: true}});
        }}

        document.getElementById('close').onclick = function() {{
            document.getElementById('modal').style.display = 'none';
            Plotly.purge('plot');
        }};

        window.onclick = function(e) {{
            if (e.target.id === 'modal') {{
                document.getElementById('modal').style.display = 'none';
                Plotly.purge('plot');
            }}
        }};

        render();
    </script>
</body>
</html>
"""

    with open('sector_flow.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("\nDashboard saved to sector_flow.html")
    print("Open in browser → sector names, tickers and trend labels should now display correctly")


if __name__ == "__main__":
    generate_dashboard(force_refresh=False)