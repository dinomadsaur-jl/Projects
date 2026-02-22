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

# ──── EASY TO CHANGE SMA PERIOD ────
PLOT_SMA_PERIOD = 50          # ← Change this number to 20, 50, 100, 200, etc.
# PLOT_SMA_PERIOD = 20
# PLOT_SMA_PERIOD = 200

SMA_KEY  = f'SMA_{PLOT_SMA_PERIOD}'
SMA_NAME = f'SMA {PLOT_SMA_PERIOD}'

# Cache settings
CACHE_DIR = "./cache"
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_HOURS = 24*7
MIN_BARS_REQUIRED = 200
EXPECTED_MIN_BARS_5Y = 1100
REVERSAL_PRICE_THRESHOLD = 10.0  # %

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
        
        age_hours = (datetime.now() - fetch_time).total_seconds() / 3600
        if age_hours > CACHE_HOURS:
            print(f"Cache expired for {ticker} ({age_hours:.1f}h)")
            return None
        
        if df is None or df.empty or len(df) < MIN_BARS_REQUIRED:
            print(f"Cache invalid for {ticker}")
            return None
        
        first_date = df.index.min()
        years = (datetime.now().date() - first_date.date()).days / 365.25
        if years < 4.7 or len(df) < EXPECTED_MIN_BARS_5Y:
            print(f"Cache for {ticker} < 5 years ({years:.1f}y)")
            return None
        
        last_date = df.index.max()
        if (datetime.now().date() - last_date.date()).days > 7:
            print(f"Cache stale for {ticker}")
            return None
        
        print(f"✓ Valid cache for {ticker}")
        return df
    
    except Exception as e:
        print(f"Cache load failed for {ticker}: {e}")
        return None


def save_cached_data(ticker, df):
    if df.empty: return
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
            start_ts = int((datetime.now() - timedelta(days=2000)).timestamp())

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

            print(f"Success: {ticker} - {len(df)} bars")
            save_cached_data(ticker, df)
            return df

        except Exception as e:
            print(f"Attempt {attempt} failed: {str(e)}")
            time.sleep(4 + attempt * 3)

    print(f"Failed to fetch {ticker}")
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
                df['Rel_Perf_3M'] = df['Rel_Line'].pct_change(63) * 100
                df['Alpha'] = df['Alpha'].fillna(0)
                return df
        except:
            pass
    df['Alpha'] = 0
    df['Rel_Perf_3M'] = 0
    return df


def determine_trend_state(df):
    if df.empty:
        return "Neutral", "#8a94a6"
    cur = df.iloc[-1]
    price = cur['Close']
    sma = cur[SMA_KEY]
    rel = cur.get('Rel_Perf_3M', 0)

    if price > sma and rel > 0:   return "LEADING",   "#26a69a"
    if price > sma and rel < 0:   return "WEAKENING", "#F7DC6F"
    if price < sma and rel > 0:   return "IMPROVING", "#45B7D1"
    if price < sma and rel < 0:   return "LAGGING",   "#ef5350"
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
    print("Generating dashboard...\n")

    spy_df = get_stock_data('SPY', force_refresh)
    if spy_df.empty:
        print("WARNING: No SPY data")

    sectors_data = []

    for key, config in SECTORS.items():
        print(f"Processing {config['name']} ({config['ticker']})")
        df = get_stock_data(config['ticker'], force_refresh)
        time.sleep(random.uniform(1.0, 2.5))

        if df.empty or len(df) < 100:
            print(f"  → Skipped")
            continue

        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        last = df.iloc[-1]

        # Detect SMA direction reversals (using the chosen SMA period)
        df['SMA_Slope'] = df[SMA_KEY].diff().fillna(0)
        df['SMA_Direction'] = np.sign(df['SMA_Slope'])
        df['Direction_Change'] = df['SMA_Direction'] != df['SMA_Direction'].shift(1).fillna(0)

        reversals = []
        for idx in df[df['Direction_Change']].index:
            if idx == df.index[0]: continue

            lookback = df.loc[:idx].tail(30)
            if lookback.empty: continue

            current_dir = df.at[idx, 'SMA_Direction']

            if current_dir > 0:  # Bullish reversal
                prev_low = lookback['Close'].min()
                move_pct = (df.at[idx, 'Close'] - prev_low) / prev_low * 100
                if move_pct >= REVERSAL_PRICE_THRESHOLD:
                    reversals.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'price': round(df.at[idx, 'Close'], 2),
                        'signal': 'Bull',
                        'move': round(move_pct, 2)
                    })

            elif current_dir < 0:  # Bearish reversal
                prev_high = lookback['Close'].max()
                move_pct = (df.at[idx, 'Close'] - prev_high) / prev_high * 100
                if move_pct <= -REVERSAL_PRICE_THRESHOLD:
                    reversals.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'price': round(df.at[idx, 'Close'], 2),
                        'signal': 'Bear',
                        'move': round(move_pct, 2)
                    })

        plot_data = {
            'dates': df.index.strftime('%Y-%m-%d').tolist(),
            'close': df['Close'].replace([np.inf, -np.inf, np.nan], None).round(2).tolist(),
            'sma':   df[SMA_KEY].replace([np.inf, -np.inf, np.nan], None).round(2).tolist(),
            'alpha': df['Alpha'].replace([np.inf, -np.inf, np.nan], None).round(2).tolist(),
            'volume': (df['Volume'] / 1e6).replace([np.inf, -np.inf, np.nan], 0).round(1).tolist(),
            'reversals': reversals,
            'ticker': config['ticker'],
            'name': config['name']
        }

        sectors_data.append({
            'config': config,
            'price': last['Close'],
            'return': last['Return'],
            'alpha': last['Alpha'],
            'rel_perf': last['Rel_Perf_3M'],
            'trend_text': trend_text,
            'trend_color': trend_color,
            'sparkline': create_sparkline(df, config['color']),
            'plot_data': plot_data
        })

    sectors_data.sort(key=lambda x: x.get('alpha', 0))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = fr"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Sector Rotation Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        html, body {{ margin:0; padding:0; height:100%; font-family:Arial,sans-serif; background:#f8f9fa; overflow:hidden; }}
        h1 {{ text-align:center; color:#222; margin:8px 0; font-size:1.3rem; }}
        .update {{ text-align:center; color:#555; margin:4px 0; font-size:0.8rem; padding:0 8px; }}
        .grid {{ display:grid; grid-template-columns:repeat(2, 1fr); gap:8px; height:calc(100% - 80px); overflow-y:auto; padding:8px; box-sizing:border-box; }}
        .card {{ background:white; border-radius:8px; padding:10px; box-shadow:0 2px 8px rgba(0,0,0,0.1); cursor:pointer; font-size:0.82rem; }}
        .card:hover {{ transform:translateY(-2px); }}
        .name {{ font-size:1.05rem; font-weight:bold; margin-bottom:5px; }}
        .metric {{ margin:3px 0; }}
        .trend {{ display:inline-block; padding:4px 10px; border-radius:14px; color:white; font-weight:bold; font-size:0.78rem; min-width:85px; text-align:center; }}
        .spark {{ width:100%; height:40px; margin-top:6px; }}
        #modal {{ display:none; position:fixed; z-index:1000; inset:0; background:rgba(0,0,0,0.7); overflow-y:auto; }}
        #modal-content {{ background:white; margin:2% auto; padding:14px; width:96%; max-width:1000px; border-radius:8px; position:relative; }}
        #close {{ position:absolute; right:14px; top:6px; font-size:28px; cursor:pointer; color:#888; }}
        #close:hover {{ color:#000; }}
        #plot {{ width:100%; height:80vh; min-height:480px; }}
    </style>
</head>
<body>
    <h1>Sector Rotation Dashboard</h1>
    <div class="update">Updated: {timestamp} • Sorted: Worst Alpha → Best • 3M Rel Perf • Click for 5Y + {SMA_NAME} (colored) + Alpha subplot</div>

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
                html += '<div class="metric">1D: <strong>' + Number(s.return || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="metric">Alpha: <strong>' + Number(s.alpha || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="metric">3M Rel: <strong>' + Number(s.rel_perf || 0).toFixed(2) + '%</strong></div>';
                html += '<div class="trend" style="background:' + s.trend_color + '">' + (s.trend_text || '—') + '</div>';
                html += '<div class="spark">' + (s.sparkline || '') + '</div>';

                card.innerHTML = html;
                card.onclick = function() {{ showPlot(s); }};
                grid.appendChild(card);
            }});
        }}

        function showPlot(s) {{
            console.log("Chart for:", s.config.name, s.config.ticker);
            console.log("Dates length:", s.plot_data.dates ? s.plot_data.dates.length : 0);
            console.log("Alpha length:", s.plot_data.alpha ? s.plot_data.alpha.length : 0);
            console.log("{SMA_NAME} length:", s.plot_data.sma ? s.plot_data.sma.length : 0);
            console.log("Reversals:", s.plot_data.reversals ? s.plot_data.reversals.length : 0);

            document.getElementById('modal-title').textContent = 
                s.config.name + " (" + s.config.ticker + ") - 5 Years + {SMA_NAME} (colored) + Alpha Subplot";

            document.getElementById('modal').style.display = 'block';

            const d = s.plot_data || {{}};
            const traces = [];

            // Close price (top subplot)
            if (d.dates && d.dates.length > 0 && d.close && d.close.length === d.dates.length) {{
                traces.push({{
                    x: d.dates,
                    y: d.close,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Close',
                    line: {{ color: '#1f77b4', width: 2 }},
                    xaxis: 'x',
                    yaxis: 'y'
                }});
            }}

            // Chosen SMA (colored by direction - green rising, red falling)
            if (d.dates && d.sma && d.sma.length === d.dates.length) {{
                const smaColors = [];
                for (let i = 1; i < d.sma.length; i++) {{
                    smaColors.push(d.sma[i] > d.sma[i-1] ? '#2ca02c' : '#d62728');
                }}
                smaColors.unshift(smaColors[0] || '#2ca02c');

                traces.push({{
                    x: d.dates,
                    y: d.sma,
                    type: 'scatter',
                    mode: 'lines',
                    name: '{SMA_NAME}',
                    line: {{ width: 2.2 }},
                    marker: {{ color: smaColors }},
                    xaxis: 'x',
                    yaxis: 'y'
                }});
            }}

            // Volume (top subplot)
            if (d.dates && d.volume && d.volume.length === d.dates.length) {{
                traces.push({{
                    x: d.dates,
                    y: d.volume,
                    type: 'bar',
                    name: 'Volume (M)',
                    yaxis: 'y2',
                    marker: {{ color: 'rgba(120,120,120,0.35)' }},
                    xaxis: 'x',
                    yaxis: 'y2'
                }});
            }}

            // Alpha (bottom subplot)
            if (d.dates && d.alpha && d.alpha.length === d.dates.length) {{
                traces.push({{
                    x: d.dates,
                    y: d.alpha,
                    type: 'scatter',
                    mode: 'lines',
                    name: 'Alpha vs SPY',
                    line: {{ color: '#9467bd', width: 1.5, dash: 'dot' }},
                    xaxis: 'x2',
                    yaxis: 'y3'
                }});
            }}

            // Reversal markers (top subplot)
            if (d.reversals && d.reversals.length > 0) {{
                const revDates = d.reversals.map(r => r.date);
                const revPrices = d.reversals.map(r => r.price);
                const revSignals = d.reversals.map(r => r.signal);
                const revMoves = d.reversals.map(r => r.move);

                traces.push({{
                    x: revDates,
                    y: revPrices,
                    mode: 'markers+text',
                    name: '{SMA_NAME} Reversals',
                    text: revPrices.map(p => '$' + p.toFixed(2)),
                    textposition: 'top center',
                    textfont: {{ size: 10, color: '#000' }},
                    marker: {{
                        size: 10,
                        color: revSignals.map(sig => sig === 'Bull' ? '#00cc44' : '#ff4444'),
                        symbol: revSignals.map(sig => sig === 'Bull' ? 'triangle-up' : 'triangle-down')
                    }},
                    hovertemplate: '%{{x}}<br>Price: $%{{y}}<br>Move: %{{text}}%<br>Signal: %{{customdata}}<extra></extra>',
                    customdata: revMoves,
                    xaxis: 'x',
                    yaxis: 'y'
                }});
            }}

            if (traces.length === 0) {{
                console.error("No valid traces for plot");
                return;
            }}

            Plotly.newPlot('plot', traces, {{
                grid: {{rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom'}},
                xaxis: {{ title: 'Date', type: 'date', domain: [0, 1], anchor: 'y' }},
                yaxis: {{ title: 'Price', domain: [0.55, 1] }},
                xaxis2: {{ title: 'Date', type: 'date', domain: [0, 1], anchor: 'y3', showgrid: false }},
                yaxis2: {{ title: 'Volume (M)', overlaying: 'y', side: 'right', domain: [0.55, 1] }},
                yaxis3: {{ title: 'Alpha (%)', domain: [0, 0.45] }},
                hovermode: 'x unified',
                legend: {{ orientation: 'h', y: -0.2 }},
                margin: {{ t:40, b:60, l:50, r:80 }},
                height: '100%'
            }}, {{ responsive: true }});
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
    print(f"   → Using {SMA_NAME} (green = rising, red = falling)")
    print("   → Alpha in bottom subplot")
    print("   → Cards sorted worst-to-best Alpha")


if __name__ == "__main__":
    generate_dashboard(force_refresh=False)