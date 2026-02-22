import requests, pandas as pd, numpy as np
from datetime import datetime, timedelta
import warnings

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

# ====================== DATA FETCHING ======================
def get_stock_data(ticker):
    """Get stock data with fallback to synthetic if API fails"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1095)
        
        # Using Yahoo Finance query
        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        params = {
            'period1': int(start_date.timestamp()),
            'period2': int(end_date.timestamp()),
            'interval': '1d',
            'events': 'history'
        }
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, params=params, headers=headers, timeout=5)
        
        if response.status_code == 200:
            df = pd.read_csv(pd.compat.StringIO(response.text))
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            if 'Adj Close' in df.columns:
                df['Close'] = df['Adj Close']
            return df[['Open', 'High', 'Low', 'Close', 'Volume']].ffill()
    except Exception as e:
        print(f"Using synthetic data for {ticker}")
    
    # Synthetic Data Generator (Fallback)
    dates = pd.date_range(end=datetime.now(), periods=252, freq='B')
    returns = np.random.normal(0.0005, 0.015, 252) # Slightly positive drift
    prices = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame({
        'Open': prices * 0.995, 'High': prices * 1.02,
        'Low': prices * 0.98, 'Close': prices,
        'Volume': np.random.lognormal(14, 1, 252)
    }, index=dates)

# ====================== ANALYTICS LOGIC ======================
def calculate_indicators(df, spy_df=None):
    """Calculate technicals and relative strength"""
    df = df.copy()
    
    # 1. Standard Technicals
    df['SMA_50'] = df['Close'].rolling(50, min_periods=1).mean()
    df['SMA_200'] = df['Close'].rolling(200, min_periods=1).mean()
    df['Return'] = df['Close'].pct_change() * 100
    
    # 2. RSI
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - 100 / (1 + rs)
    df['RSI'] = df['RSI'].fillna(50)

    # 3. Relative Strength vs Economy (SPY)
    if spy_df is not None:
        # Align dates
        aligned_spy = spy_df['Close'].reindex(df.index).ffill()
        
        # Relative Performance Line (Sector / SPY)
        df['Rel_Line'] = df['Close'] / aligned_spy
        
        # Alpha (Daily Sector Return - Daily SPY Return)
        spy_ret = aligned_spy.pct_change() * 100
        df['Alpha'] = df['Return'] - spy_ret
        
        # 20-Day Relative Performance
        df['Rel_Perf_20D'] = df['Rel_Line'].pct_change(20) * 100
    else:
        df['Alpha'] = 0
        df['Rel_Perf_20D'] = 0
        
    return df

def determine_trend_state(df):
    """Classify sector direction relative to trend"""
    if df.empty: return "Neutral", "#8a94a6"
    
    current = df.iloc[-1]
    price = current['Close']
    sma50 = current['SMA_50']
    rel_perf = current.get('Rel_Perf_20D', 0)
    
    # Logic: Where is price vs Trend AND is it beating the market?
    if price > sma50 and rel_perf > 0:
        return "LEADING", "#26a69a"  # Green
    elif price > sma50 and rel_perf < 0:
        return "WEAKENING", "#F7DC6F" # Yellow
    elif price < sma50 and rel_perf > 0:
        return "IMPROVING", "#45B7D1" # Blue
    elif price < sma50 and rel_perf < 0:
        return "LAGGING", "#ef5350"   # Red
    return "Neutral", "#8a94a6"

# ====================== CHART & HTML GENERATION ======================
def create_sparkline(df, color):
    """Generate SVG sparkline"""
    if df.empty: return ""
    data = df['Close'].tail(30).tolist()
    min_val, max_val = min(data), max(data)
    range_val = max_val - min_val if max_val != min_val else 1
    
    points = ""
    width = 100
    height = 30
    step = width / (len(data) - 1)
    
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
    print("🚀 Fetching market data...")
    
    # 1. Fetch Benchmark (SPY) first
    spy_df = get_stock_data('SPY')
    
    # 2. Fetch Sectors and Calculate
    analyzed_sectors = []
    
    for key, config in SECTORS.items():
        df = get_stock_data(config['ticker'])
        df = calculate_indicators(df, spy_df)
        trend_text, trend_color = determine_trend_state(df)
        
        last = df.iloc[-1]
        
        analyzed_sectors.append({
            'id': key,
            'config': config,
            'df': df,
            'price': last['Close'],
            'return': last['Return'],
            'alpha': last['Alpha'], # vs Market
            'rel_perf': last['Rel_Perf_20D'], # Momentum vs Market
            'trend_text': trend_text,
            'trend_color': trend_color
        })

    # 3. OPTIMIZATION: Sort by Relative Strength (Alpha)
    # We want the Strongest sectors First (Top Left)
    analyzed_sectors.sort(key=lambda x: x['rel_perf'], reverse=True)

    # 4. Generate HTML
    timestamp = datetime.now().strftime("%H:%M")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Sector Flow</title>
        <style>
            :root {{ --bg: #0a0e17; --card: #141824; --text: #e2e8f0; --sub: #8a94a6; }}
            body {{ margin: 0; background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; -webkit-font-smoothing: antialiased; }}
            .app {{ display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
            
            /* Header */
            .header {{ padding: 16px; background: rgba(20, 24, 36, 0.9); backdrop-filter: blur(10px); border-bottom: 1px solid #2a3142; display: flex; justify-content: space-between; align-items: center; }}
            .title {{ font-weight: 800; font-size: 18px; letter-spacing: -0.5px; }}
            .live-badge {{ font-size: 11px; background: #26a69a20; color: #26a69a; padding: 4px 8px; border-radius: 12px; font-weight: 600; text-transform: uppercase; }}
            
            /* Grid */
            .grid {{ flex: 1; overflow-y: auto; padding: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; align-content: start; }}
            
            /* Card */
            .card {{ background: linear-gradient(160deg, #1a1f2e, #141824); border-radius: 14px; padding: 12px; border: 1px solid #2a3142; box-shadow: 0 4px 20px rgba(0,0,0,0.2); position: relative; overflow: hidden; transition: transform 0.2s; }}
            .card:active {{ transform: scale(0.98); }}
            
            .card-top {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
            .ticker {{ font-size: 10px; font-weight: 700; opacity: 0.6; background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; }}
            .name {{ font-weight: 700; font-size: 13px; margin-top: 2px; }}
            
            .trend-badge {{ font-size: 9px; padding: 3px 6px; border-radius: 4px; font-weight: 700; letter-spacing: 0.5px; margin-bottom: 8px; display: inline-block; }}
            
            .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px; margin-top: 12px; }}
            .metric-box {{ background: rgba(0,0,0,0.2); border-radius: 6px; padding: 6px; text-align: center; }}
            .lbl {{ color: var(--sub); font-size: 9px; margin-bottom: 2px; text-transform: uppercase; }}
            .val {{ font-weight: 700; font-family: 'SF Mono', monospace; }}
            
            .pos {{ color: #26a69a; }}
            .neg {{ color: #ef5350; }}
            
            .spark {{ height: 35px; width: 100%; opacity: 0.8; margin-top: 5px; }}
            
            /* Footer */
            .info-bar {{ font-size: 10px; color: var(--sub); text-align: center; padding: 10px; border-top: 1px solid #2a3142; background: var(--card); }}
            
            /* Modal */
            #modal {{ position: fixed; inset: 0; background: var(--bg); z-index: 100; display: none; flex-direction: column; }}
            .modal-head {{ padding: 16px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; }}
            .close-btn {{ background: none; border: none; color: white; font-size: 24px; cursor: pointer; }}
            #chart-area {{ flex: 1; width: 100%; }}

        </style>
    </head>
    <body>
        <div class="app">
            <div class="header">
                <div>
                    <div class="title">Sector Rotation</div>
                    <div style="font-size: 11px; color: #8a94a6;">Sorted by Relative Strength</div>
                </div>
                <div class="live-badge">Live • {timestamp}</div>
            </div>
            
            <div class="grid">
    """
    
    for item in analyzed_sectors:
        conf = item['config']
        
        # Color logic
        ret_color = "pos" if item['return'] >= 0 else "neg"
        alpha_color = "pos" if item['alpha'] >= 0 else "neg"
        trend_bg = item['trend_color'] + "20" # 20% opacity
        trend_fg = item['trend_color']
        
        html += f"""
            <div class="card" onclick="openChart('{item['id']}')">
                <div class="card-top">
                    <div class="ticker">{conf['ticker']}</div>
                    <div class="trend-badge" style="background: {trend_bg}; color: {trend_fg};">
                        {item['trend_text']}
                    </div>
                </div>
                
                <div class="name" style="color: {conf['color']}">{conf['name']}</div>
                
                <div class="spark">
                    {create_sparkline(item['df'], conf['color'])}
                </div>
                
                <div class="metrics">
                    <div class="metric-box">
                        <div class="lbl">Return</div>
                        <div class="val {ret_color}">{item['return']:+.2f}%</div>
                    </div>
                    <div class="metric-box">
                        <div class="lbl">vs Market</div>
                        <div class="val {alpha_color}">{item['alpha']:+.2f}%</div>
                    </div>
                </div>
            </div>
        """

    html += """
            </div>
            <div class="info-bar">
                "vs Market" = Sector Return minus SPY Return. <br>
                Grid is sorted by 20-Day Relative Strength (Momentum).
            </div>
        </div>

        <!-- Detail Modal -->
        <div id="modal">
            <div class="modal-head">
                <h3 id="m-title" style="margin:0">Detail</h3>
                <button class="close-btn" onclick="document.getElementById('modal').style.display='none'">×</button>
            </div>
            <div id="chart-area"></div>
        </div>

        <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
        <script>
            const dataStore = {
    """
    
    # Inject JSON Data
    for item in analyzed_sectors:
        df = item['df'].tail(100)
        dates = [d.strftime('%Y-%m-%d') for d in df.index]
        prices = df['Close'].tolist()
        sma = df['SMA_50'].tolist()
        
        html += f"""
            '{item['id']}': {{
                name: '{item['config']['name']}',
                dates: {dates},
                prices: {prices},
                sma: {sma},
                color: '{item['config']['color']}'
            }},
        """

    html += """
            };

            function openChart(id) {
                const d = dataStore[id];
                const modal = document.getElementById('modal');
                modal.style.display = 'flex';
                document.getElementById('m-title').innerText = d.name;
                
                Plotly.newPlot('chart-area', [
                    { x: d.dates, y: d.prices, type: 'scatter', line: {color: d.color, width: 2}, name: 'Price' },
                    { x: d.dates, y: d.sma, type: 'scatter', line: {color: '#555', dash: 'dot'}, name: 'SMA50' }
                ], {
                    paper_bgcolor: '#0a0e17', plot_bgcolor: '#0a0e17',
                    font: { color: '#ccc' },
                    margin: { t: 40, l: 40, r: 20, b: 40 },
                    xaxis: { gridcolor: '#222' },
                    yaxis: { gridcolor: '#222' }
                }, {responsive: true});
            }
        </script>
    </body>
    </html>
    """
    
    with open('sector_flow.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("✅ Dashboard Generated: sector_flow.html")

if __name__ == "__main__":
    generate_dashboard()