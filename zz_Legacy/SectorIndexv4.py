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
CACHE_HOURS = 4
MIN_BARS_REQUIRED = 200   # more data now

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
    exit(1)

print(f"Loaded {len(SECTORS)} sectors")

# ====================== CACHED DATA FETCHING (now 5 years) ======================
def load_cached_data(ticker):
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, 'rb') as f:
            df, fetch_time = pickle.load(f)
        
        age_hours = (datetime.now() - fetch_time).total_seconds() / 3600
        if age_hours > CACHE_HOURS:
            return None, None
        
        if df is None or df.empty or len(df) < 200:
            return None, None
        
        last_date = df.index.max()
        if (datetime.now().date() - last_date.date()).days > 7:
            return None, None
        
        print(f"✓ Loaded cache for {ticker} ({len(df)} bars)")
        return df, fetch_time
    except:
        return None, None


def save_cached_data(ticker, df):
    if df.empty: return
    path = os.path.join(CACHE_DIR, f"{ticker}.pkl")
    with open(path, 'wb') as f:
        pickle.dump((df, datetime.now()), f)
    print(f"→ Saved cache for {ticker}")


def get_stock_data(ticker, force_refresh=False, max_retries=5):
    if not force_refresh:
        df, _ = load_cached_data(ticker)
        if df is not None:
            return df
    
    ua_list = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
    ]

    for attempt in range(max_retries):
        try:
            end_ts   = int(datetime.now().timestamp())
            start_ts = int((datetime.now() - timedelta(days=1825)).timestamp())  # ≈5 years

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
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            quote = result['indicators']['quote'][0]
            adj_close = result['indicators'].get('adjclose', [{}])[0].get('adjclose', quote.get('close', []))

            df = pd.DataFrame({
                'Open':   quote.get('open',   [None]*len(timestamps)),
                'High':   quote.get('high',   [None]*len(timestamps)),
                'Low':    quote.get('low',    [None]*len(timestamps)),
                'Close':  quote.get('close',  [None]*len(timestamps)),
                'Volume': quote.get('volume', [None]*len(timestamps)),
            }, index=pd.to_datetime(timestamps, unit='s'))

            if len(adj_close) == len(timestamps):
                df['Close'] = adj_close

            df = df.ffill().dropna(how='all')

            if len(df) < 200:
                raise ValueError(f"Too few bars: {len(df)}")

            print(f"✓ {ticker} SUCCESS - {len(df)} bars")
            save_cached_data(ticker, df)
            return df

        except Exception as e:
            print(f"✗ attempt {attempt+1} failed: {str(e)}")
            time.sleep(3 + attempt * 3)

    print(f"✗ {ticker} FAILED")
    return pd.DataFrame()


# ====================== INDICATORS (add SMA20) ======================
def calculate_indicators(df, spy_df=None):
    df = df.copy()
    df['SMA_20']  = df['Close'].rolling(20, min_periods=1).mean()
    df['SMA_50']  = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
    df['Return']  = df['Close'].pct_change() * 100
    
    # RSI (unchanged)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - 100 / (1 + rs)
    df['RSI'] = df['RSI'].fillna(50)

    # Relative vs SPY (unchanged)
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
    if df.empty: return "Neutral", "#8a94a6"
    current = df.iloc[-1]
    price = current['Close']
    sma50 = current['SMA_50']
    rel_perf = current.get('Rel_Perf_20D', 0)
    
    if price > sma50 and rel_perf > 0:   return "LEADING",   "#26a69a"
    if price > sma50 and rel_perf < 0:   return "WEAKENING", "#F7DC6F"
    if price < sma50 and rel_perf > 0:   return "IMPROVING", "#45B7D1"
    if price < sma50 and rel_perf < 0:   return "LAGGING",   "#ef5350"
    return "Neutral", "#8a94a6"


# ====================== SPARKLINE (small preview) ======================
def create_sparkline(df, color):
    if df.empty: return ""
    data = df['Close'].tail(60).tolist()  # longer preview
    if not data: return ""
    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val or 1
    points = ""
    width, height = 140, 40
    step = width / (len(data) - 1) if len(data) > 1 else 0
    for i, val in enumerate(data):
        x = i * step
        y = height - ((val - min_val) / range_val * height)
        points += f"{x},{y} "
    return f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none"><polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/></svg>'


# ====================== MAIN DASHBOARD ======================
def generate_dashboard(force_refresh=False):
    print("🚀 Generating dashboard with 5-year clickable plots...\n")
    
    spy_df = get_stock_data('SPY', force_refresh)
    if spy_df.empty:
        print("WARNING: No SPY → relative metrics = 0")
    
    analyzed_sectors = []
    
    for key, config in SECTORS.items():
        df = get_stock_data(config['ticker'], force_refresh)
        time.sleep(random.uniform(1.0, 2.5))
        
        if df.empty or len(df) < 100:
            print(f"Skipping {config['name']} — insufficient data")
            continue
        
        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        last = df.iloc[-1]
        
        # Prepare Plotly data for modal (JSON serializable)
        plot_data = {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'close': df['Close'].round(2).tolist(),
            'sma20': df['SMA_20'].round(2).tolist(),
            'sma50': df['SMA_50'].round(2).tolist(),
            'sma200': df['SMA_200'].round(2).tolist(),
            'volume': (df['Volume'] / 1e6).round(1).tolist(),  # millions
            'ticker': config['ticker'],
            'name': config['name']
        }
        
        analyzed_sectors.append({
            'id': key,
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

    analyzed_sectors.sort(key=lambda x: x.get('rel_perf', -9999), reverse=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ====================== HTML with Plotly modal ======================
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sector Rotation Dashboard - 5Y Plots</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 1rem; background: #f8f9fa; }}
        h1 {{ text-align: center; color: #222; }}
        .update {{ text-align: center; color: #666; margin: 1rem 0; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 1.2rem; }}
        .card {{ background: white; border-radius: 10px; padding: 1.2rem; box-shadow: 0 3px 12px rgba(0,0,0,0.1); cursor: pointer; transition: transform 0.15s; }}
        .card:hover {{ transform: translateY(-4px); }}
        .name {{ font-size: 1.4rem; font-weight: bold; margin-bottom: 0.5rem; }}
        .metric {{ margin: 0.35rem 0; font-size: 0.95rem; }}
        .trend {{ display: inline-block; padding: 0.35rem 0.9rem; border-radius: 1rem; color: white; font-weight: bold; font-size: 0.9rem; }}
        .spark {{ width: 100%; height: 60px; margin-top: 0.8rem; }}
        #modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); }}
        #modal-content {{ background: white; margin: 4% auto; padding: 1.5rem; width: 90%; max-width: 1100px; border-radius: 10px; position: relative; }}
        #close {{ position: absolute; right: 15px; top: 5px; font-size: 2rem; cursor: pointer; color: #aaa; }}
        #close:hover {{ color: #000; }}
        #plot {{ width: 100%; height: 65vh; }}
    </style>
</head>
<body>
    <h1>Sector Rotation Dashboard</h1>
    <div class="update">Last updated: {timestamp} • Click card for 5-year chart + SMA20</div>
    
    <div class="grid" id="grid"></div>

    <!-- Modal -->
    <div id="modal">
        <div id="modal-content">
            <span id="close">&times;</span>
            <h2 id="modal-title"></h2>
            <div id="plot"></div>
        </div>
    </div>

    <script>
        const sectors = {json.dumps(analyzed_sectors, default=str)};

        function renderCards() {{
            const grid = document.getElementById('grid');
            grid.innerHTML = '';
            sectors.forEach(s => {{
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="name" style="color:\( {{s.config.color}}"> \){{s.config.name}} (${{s.config.ticker}})</div>
                    <div class="metric">Price: <strong>${{Number(s.price).toFixed(2)}}</strong></div>
                    <div class="metric">1D: <strong>${{Number(s.return).toFixed(2)}}%</strong></div>
                    <div class="metric">Alpha: <strong>${{Number(s.alpha).toFixed(2)}}%</strong></div>
                    <div class="metric">20D Rel: <strong>${{Number(s.rel_perf).toFixed(2)}}%</strong></div>
                    <div class="trend" style="background:\( {{s.trend_color}}"> \){{s.trend_text}}</div>
                    <div class="spark">${{s.sparkline}}</div>
                `;
                card.onclick = () => showChart(s);
                grid.appendChild(card);
            }});
        }}

        function showChart(sector) {{
            document.getElementById('modal-title').textContent = `\( {{sector.config.name}} ( \){{sector.config.ticker}}) - 5 Years`;
            document.getElementById('modal').style.display = 'block';

            const d = sector.plot_data;
            const tracePrice = {{
                x: d.dates,
                y: d.close,
                type: 'scatter',
                mode: 'lines',
                name: 'Close',
                line: {{color: '#1f77b4', width: 2}}
            }};
            const traceSMA20 = {{
                x: d.dates,
                y: d.sma20,
                type: 'scatter',
                mode: 'lines',
                name: 'SMA 20',
                line: {{color: '#ff7f0e', width: 1.5, dash: 'dash'}}
            }};
            const traceVol = {{
                x: d.dates,
                y: d.volume,
                type: 'bar',
                name: 'Volume (M)',
                yaxis: 'y2',
                marker: {{color: 'rgba(100,100,100,0.4)'}}
            }};

            Plotly.newPlot('plot', [tracePrice, traceSMA20, traceVol], {{
                title: '',
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Price'}},
                yaxis2: {{
                    title: 'Volume (M)',
                    overlaying: 'y',
                    side: 'right'
                }},
                hovermode: 'x unified',
                legend: {{orientation: 'h', y: -0.2}},
                margin: {{t: 30, b: 60, l: 50, r: 50}},
                height: 550
            }}, {{responsive: true}});
        }}

        document.getElementById('close').onclick = () => {{
            document.getElementById('modal').style.display = 'none';
            Plotly.purge('plot');
        }};

        window.onclick = (e) => {{
            if (e.target == document.getElementById('modal')) {{
                document.getElementById('modal').style.display = 'none';
                Plotly.purge('plot');
            }}
        }}

        renderCards();
    </script>
</body>
</html>
"""

    with open('sector_flow.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard created: sector_flow.html")
    print("   → Click any card → interactive 5Y chart with Close + SMA20 + Volume")


if __name__ == "__main__":
    generate_dashboard(force_refresh=False)  # change to True for full refresh