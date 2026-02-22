import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import http.server
import socketserver
import threading
import subprocess
import time
import os
from datetime import datetime, timedelta
from requests.exceptions import HTTPError

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {
    'Gold': 'GC=F',
    'Silver': 'SI=F',
    'DXY': 'DX=F'
}

SMA_PERIOD = 20
SMA_REVERSAL_THRESHOLD = 0.001     # 0.1%

SELECTED_WINDOW = 365 * 10         # 10 years total
RECENT_DAYS = 365                  # last year → daily data
HTML_FILENAME = "market_analysis.html"
PORT = 8000

ROLLING_CORR_WINDOW = 504          # ≈ 2 years trading days
ANNOTATION_CORR_WINDOW = 126       # ≈ 6 months for annotation

# ────────────────────────────────────────────────
# 1. Data Fetching via direct Yahoo requests + retry on 429
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S928B Build/UP1A.231005.007) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.6778.200 Mobile Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
    })
    
    p1 = int(start_date.timestamp())
    p2 = int(end_date.timestamp() + 86400)  # +1 day buffer
    
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    
    params = {
        "period1": p1,
        "period2": p2,
        "interval": interval,
        "includePrePost": "false",
        "events": "history",
        "includeAdjustedClose": "true"
    }
    
    max_retries = 4
    for attempt in range(max_retries):
        try:
            print(f"Requesting {ticker} ({interval}) ... attempt {attempt+1}")
            r = session.get(url, params=params, timeout=18)
            
            if r.status_code == 429:
                wait_time = (2 ** attempt) * 12   # 12s → 24s → 48s → 96s
                print(f"429 Too Many Requests → waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
                
            r.raise_for_status()
            
            data = r.json()
            
            if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                print(f"No chart data for {ticker} ({interval})")
                return pd.Series(dtype=float)
                
            result = data['chart']['result'][0]
            if 'timestamp' not in result or not result['timestamp']:
                print(f"Empty timestamps for {ticker} ({interval})")
                return pd.Series(dtype=float)
                
            timestamps = result['timestamp']
            closes = result['indicators']['quote'][0]['close']
            
            dates = [datetime.fromtimestamp(ts) for ts in timestamps]
            series = pd.Series(closes, index=dates, name=ticker)
            print(f"→ Received {len(series)} points for {ticker} ({interval})")
            return series.dropna()
            
        except HTTPError as e:
            print(f"HTTP Error {e.response.status_code if 'response' in locals() else 'unknown'} for {ticker} ({interval})")
            if 'response' in locals() and e.response.status_code == 429:
                wait_time = (2 ** attempt) * 12
                print(f"→ Retrying after {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                print(f"Other error: {e}")
                break
        except Exception as e:
            print(f"Unexpected error fetching {ticker} ({interval}): {e}")
            break
    
    print(f"Failed to fetch {ticker} ({interval}) after {max_retries} attempts")
    return pd.Series(dtype=float)


# ────────────────────────────────────────────────
# 2. SMA Reversal Detection
# ────────────────────────────────────────────────
def find_sma_reversals(df, raw_col, sma_col, threshold=SMA_REVERSAL_THRESHOLD):
    valid_data = df[[raw_col, sma_col]].dropna()
    if valid_data.empty:
        return []

    reversals = []
    last_sma_val = valid_data[sma_col].iloc[0]
    last_date = valid_data.index[0]
    trend = 0
    
    for date, row in valid_data.iterrows():
        curr_sma = row[sma_col]
        
        if trend == 0:
            if curr_sma >= last_sma_val * (1 + threshold):
                trend = 1
                last_sma_val, last_date = curr_sma, date
            elif curr_sma <= last_sma_val * (1 - threshold):
                trend = -1
                last_sma_val, last_date = curr_sma, date
        
        elif trend == 1:
            if curr_sma > last_sma_val:
                last_sma_val, last_date = curr_sma, date
            elif curr_sma < last_sma_val * (1 - threshold):
                reversals.append((last_date, df.loc[last_date, raw_col], 'peak'))
                trend = -1
                last_sma_val, last_date = curr_sma, date
                
        elif trend == -1:
            if curr_sma < last_sma_val:
                last_sma_val, last_date = curr_sma, date
            elif curr_sma > last_sma_val * (1 + threshold):
                reversals.append((last_date, df.loc[last_date, raw_col], 'trough'))
                trend = 1
                last_sma_val, last_date = curr_sma, date
                
    return reversals


# ────────────────────────────────────────────────
# 3. Main function
# ────────────────────────────────────────────────
def run_analysis_and_serve(days_count):
    print(f"\n--- Analyzing ~{days_count//365} years ---")
    
    now = datetime.now()
    full_start = now - timedelta(days=days_count + 400)
    recent_start = now - timedelta(days=RECENT_DAYS)
    
    data_frames = []
    for name, symbol in TICKERS.items():
        print(f"\nFetching {name} ({symbol})...")
        
        s_old = fetch_yahoo_data(symbol, full_start, recent_start, '1wk')
        time.sleep(10)  # delay between weekly and daily requests
        
        s_recent = fetch_yahoo_data(symbol, recent_start - timedelta(days=10), now + timedelta(days=2), '1d')
        time.sleep(12)  # delay before next symbol
        
        if s_old.empty and s_recent.empty:
            print(f"Skipping {name} - no data")
            continue
        
        combined = pd.concat([s_old, s_recent])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
        data_frames.append(combined.rename(name))
    
    if not data_frames:
        print("No data retrieved from any ticker.")
        return
    
    df = pd.concat(data_frames, axis=1)
    cutoff = now - timedelta(days=days_count)
    df = df[df.index >= cutoff]
    
    if df.empty:
        print("No data after cutoff date.")
        return

    # Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    
    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    # Rolling correlation
    rolling_corr = df['Gold'].rolling(window=ROLLING_CORR_WINDOW, min_periods=100).corr(df['DXY'])

    # 6-month correlation
    recent_df = df.tail(ANNOTATION_CORR_WINDOW * 2)
    corr_6m = np.nan
    if len(recent_df) >= ANNOTATION_CORR_WINDOW:
        corr_6m = recent_df['Gold'].corr(recent_df['DXY'])

    status = ("Strong Inversion" if corr_6m < -0.5 else "Inversion" if corr_6m < -0.2 else
              "Strong Positive" if corr_6m > 0.5 else "Positive" if corr_6m > 0.2 else "Decoupled")
    corr_text = f"Gold vs DXY 6m Corr: {corr_6m:.2f} ({status})" if not np.isnan(corr_6m) else "N/A"
    
    is_strong = abs(corr_6m) > 0.5 if not np.isnan(corr_6m) else False
    display_text = f"<b>{corr_text}</b>" if is_strong else corr_text

    # ─── Plot setup (unchanged from previous portrait-friendly version) ───
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.58, 0.42],
        vertical_spacing=0.06,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Top panel
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold'], name="Gold", line=dict(color='#D4AF37', width=1.2), opacity=0.4), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold_SMA'], name="Gold SMA", line=dict(color='#D4AF37', width=2.4)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['Silver'], name="Silver", line=dict(color='#B0C4DE', width=1.2), opacity=0.4), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=df.index, y=df['Silver_SMA'], name="Silver SMA", line=dict(color='#B0C4DE', width=2.4)), row=1, col=1, secondary_y=True)

    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'], name="G/S Ratio", line=dict(color='#9370DB', width=1.8, dash='dot'), opacity=0.75), row=1, col=1, secondary_y=True)

    # Reversals (top)
    for asset, color, sec_y in [('Gold', '#D4AF37', False), ('Silver', '#B0C4DE', True)]:
        revs = find_sma_reversals(df, asset, f'{asset}_SMA')
        if revs:
            rx, ry, rs, rt = [], [], [], []
            for d, p, typ in revs:
                rx.append(d); ry.append(p)
                rs.append('triangle-down' if typ=='peak' else 'triangle-up')
                rt.append(f"{p:.0f}")
            fig.add_trace(go.Scatter(
                x=rx, y=ry, mode='markers+text',
                marker=dict(symbol=rs, size=10, color=color, line=dict(width=1.2, color='black')),
                text=rt, textposition="top center", textfont=dict(size=9),
                name=f"{asset} Rev", showlegend=False
            ), row=1, col=1, secondary_y=sec_y)

    # Bottom panel
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY'], name="DXY", line=dict(color='#4169E1', width=1.2), opacity=0.45), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY_SMA'], name="DXY SMA", line=dict(color='#4169E1', width=2.4)), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=rolling_corr, name="2yr Rolling Corr", line=dict(color='#FF4500', width=1.8, dash='dash')), row=2, col=1, secondary_y=True)

    fig.add_hline(y=0, line_width=1, line_color="gray", opacity=0.6, row=2, col=1, secondary_y=True)

    dxy_revs = find_sma_reversals(df, 'DXY', 'DXY_SMA')
    if dxy_revs:
        rx, ry, rs, rt = [], [], [], []
        for d, p, typ in dxy_revs:
            rx.append(d); ry.append(p)
            rs.append('triangle-down' if typ=='peak' else 'triangle-up')
            rt.append(f"{p:.1f}")
        fig.add_trace(go.Scatter(
            x=rx, y=ry, mode='markers+text',
            marker=dict(symbol=rs, size=9, color='#4169E1', line=dict(width=1, color='white')),
            text=rt, textposition="top center", textfont=dict(size=9),
            name="DXY Rev", showlegend=False
        ), row=2, col=1)

    # Last price annotations
    last_idx = df.index[-1]
    last_g = df['Gold'].iloc[-1] if 'Gold' in df.columns else np.nan
    fig.add_annotation(x=last_idx, y=last_g, text=f"Gold {last_g:,.0f}",
                       xanchor="left", ax=35, font=dict(color='#D4AF37', size=12), showarrow=False, row=1, col=1)

    last_s = df['Silver'].iloc[-1] if 'Silver' in df.columns else np.nan
    fig.add_annotation(x=last_idx, y=last_s, text=f"Silver {last_s:,.2f}",
                       xanchor="left", ax=35, font=dict(color='#B0C4DE', size=12), showarrow=False, row=1, col=1, secondary_y=True)

    last_d = df['DXY'].iloc[-1] if 'DXY' in df.columns else np.nan
    fig.add_annotation(x=last_idx, y=last_d, text=f"DXY {last_d:,.2f}",
                       xanchor="left", ax=35, font=dict(color='#4169E1', size=12), showarrow=False, row=2, col=1)

    # Correlation annotation
    box_color = 'darkgreen' if corr_6m > 0.5 else 'darkred' if corr_6m < -0.5 else 'gray'
    border_width = 2.5 if is_strong else 1.5
    fig.add_annotation(
        xref="x domain", yref="y domain",
        x=0.03, y=0.94,
        text=display_text,
        showarrow=False,
        bgcolor="rgba(255,255,255,0.92)",
        bordercolor=box_color,
        borderwidth=border_width,
        font=dict(color=box_color, size=12),
        row=2, col=1
    )

    # Layout
    fig.update_layout(
        template="plotly_white",
        autosize=True,
        title=dict(text="Gold / Silver / DXY – 10yr (2yr Corr)", font=dict(size=16)),
        margin=dict(l=35, r=15, t=50, b=35),
        legend=dict(orientation="h", y=1.04, x=0.5, xanchor="center", font=dict(size=9)),
        hovermode="x unified",
        hoverlabel=dict(font_size=11),
        font=dict(family="Arial", size=10)
    )

    fig.update_xaxes(rangeslider_visible=False, tickfont=dict(size=9))
    fig.update_yaxes(title_text="Gold (USD)", row=1, col=1, secondary_y=False, tickfont=dict(size=9))
    fig.update_yaxes(title_text="Silver & Ratio", row=1, col=1, secondary_y=True, tickfont=dict(size=9), showgrid=False)
    fig.update_yaxes(title_text="DXY", row=2, col=1, secondary_y=False, tickfont=dict(size=9))
    fig.update_yaxes(title_text="2yr Rolling Corr", range=[-1.1,1.1], row=2, col=1, secondary_y=True, tickfont=dict(size=9), showgrid=False)

    # Export
    fig.write_html(
        HTML_FILENAME,
        include_plotlyjs='cdn',
        full_html=True,
        config={
            'responsive': True,
            'displayModeBar': False,
            'scrollZoom': True,
            'doubleClick': 'reset'
        }
    )

    # Mobile optimization
    with open(HTML_FILENAME, 'r', encoding='utf-8') as f:
        html_content = f.read()

    mobile_head = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<style>
    html, body { margin:0; padding:0; height:100%; width:100%; overflow:hidden; }
    .js-plotly-plot { width:100vw !important; height:100vh !important; }
    .plotly .modebar { display:none !important; }
    @media (orientation: portrait) {
        .js-plotly-plot .plotly { min-height: 100vh !important; }
        .subplot { min-height: 38vh !important; }
    }
</style>
"""

    head_close_pos = html_content.lower().rfind('</head>')
    if head_close_pos != -1:
        new_html = html_content[:head_close_pos] + mobile_head + html_content[head_close_pos:]
        with open(HTML_FILENAME, 'w', encoding='utf-8') as f:
            f.write(new_html)

    # Server
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args): pass

    def start_server():
        with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
            print(f"Server running → http://localhost:{PORT}/{HTML_FILENAME}")
            httpd.serve_forever()

    if not any(t.name == 'ServerThread' for t in threading.enumerate()):
        threading.Thread(target=start_server, name='ServerThread', daemon=True).start()
        time.sleep(1.2)

    url = f"http://localhost:{PORT}/{HTML_FILENAME}"
    print(f"Chart ready: {url}")

    for cmd in ["termux-open-url", "termux-open", "xdg-open", "open"]:
        try:
            subprocess.run(f"{cmd} {url}", shell=True, timeout=5)
            break
        except:
            pass
    else:
        print("Please open the link manually.")

    print("Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(3)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    run_analysis_and_serve(SELECTED_WINDOW)