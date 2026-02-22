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

ROLLING_CORR_WINDOW = 252          # ≈ 1 year trading days → smoother on 10yr chart
ANNOTATION_CORR_WINDOW = 126       # ≈ 6 months for the annotation box

# ────────────────────────────────────────────────
# 1. Data Fetching (Hybrid weekly old + daily recent)
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Referer": "https://finance.yahoo.com/"
    })
    
    p1 = int(start_date.timestamp())
    p2 = int(end_date.timestamp())
    
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
    
    params = {
        "period1": p1,
        "period2": p2,
        "interval": interval,
        "includePrePost": "false",
        "events": "history"
    }
    
    try:
        r = session.get(url, params=params, timeout=12)
        r.raise_for_status()
        data = r.json()
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        
        dates = [datetime.fromtimestamp(ts) for ts in timestamps]
        series = pd.Series(closes, index=dates, name=ticker)
        return series.dropna()
        
    except Exception as e:
        print(f"Error fetching {ticker} ({interval}): {e}")
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
        print(f"Fetching {name} ({symbol})...")
        
        s_old = fetch_yahoo_data(symbol, full_start, recent_start, '1wk')
        s_recent = fetch_yahoo_data(symbol, recent_start - timedelta(days=60), now, '1d')
        
        if s_old.empty and s_recent.empty:
            continue
        
        combined = pd.concat([s_old, s_recent])
        combined = combined.groupby(combined.index).last().sort_index()
        data_frames.append(combined.rename(name))
    
    if not data_frames:
        print("No data retrieved.")
        return
    
    df = pd.concat(data_frames, axis=1)
    cutoff = now - timedelta(days=days_count)
    df = df[df.index >= cutoff]
    
    if df.empty:
        print("No data after cutoff.")
        return

    # Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    
    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    # Rolling correlation line: 1-year window (smoother on 10yr chart)
    rolling_corr = df['Gold'].rolling(window=ROLLING_CORR_WINDOW).corr(df['DXY'])

    # Annotation: latest 6-month correlation value
    recent_df = df.tail(ANNOTATION_CORR_WINDOW * 2)  # safety margin
    if len(recent_df) >= ANNOTATION_CORR_WINDOW:
        corr_6m = recent_df['Gold'].corr(recent_df['DXY'])
    else:
        corr_6m = np.nan

    status = "Inversion" if corr_6m < -0.2 else "Positive" if corr_6m > 0.2 else "Decoupled"
    corr_text = f"Gold/DXY 6m Corr: {corr_6m:.2f} ({status})" if not np.isnan(corr_6m) else "Gold/DXY 6m Corr: N/A"
    
    # Bold if strong
    is_strong = abs(corr_6m) > 0.7 if not np.isnan(corr_6m) else False
    display_text = f"<b>{corr_text}</b>" if is_strong else corr_text

    # ─── Plot ───
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.70, 0.30],
        vertical_spacing=0.10,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # TOP: Gold (left), Silver (right), Ratio (right, dashed)
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold'],       name="Gold",       line=dict(color='#D4AF37', width=1.2), opacity=0.4), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold_SMA'],   name="Gold SMA",   line=dict(color='#D4AF37', width=2.4)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['Silver'],     name="Silver",     line=dict(color='#B0C4DE', width=1.2), opacity=0.4), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=df.index, y=df['Silver_SMA'], name="Silver SMA", line=dict(color='#B0C4DE', width=2.4)), row=1, col=1, secondary_y=True)

    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'],      name="G/S Ratio",  line=dict(color='#9370DB', width=1.8, dash='dot'), opacity=0.75), row=1, col=1, secondary_y=True)

    # Reversals
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
                marker=dict(symbol=rs, size=11, color=color, line=dict(width=1.5, color='black')),
                text=rt, textposition="top center", textfont=dict(size=10.5),
                name=f"{asset} Rev", showlegend=False
            ), row=1, col=1, secondary_y=sec_y)

    # Last Gold price tag
    last_g = df['Gold'].iloc[-1]
    fig.add_annotation(x=df.index[-1], y=last_g, text=f"{last_g:.0f}", xanchor="left", font=dict(color='#D4AF37', size=13), showarrow=False, xshift=10)

    # BOTTOM: DXY + 1-year rolling correlation line
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY'],       name="DXY",       line=dict(color='#4169E1', width=1.2), opacity=0.45), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY_SMA'],   name="DXY SMA",   line=dict(color='#4169E1', width=2.4)), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=rolling_corr, name="1yr Rolling Corr", line=dict(color='#FF4500', width=1.8, dash='dash')), row=2, col=1, secondary_y=True)

    fig.add_hline(y=0, line_width=1, line_color="gray", opacity=0.6, row=2, col=1, secondary_y=True)

    # DXY reversals
    dxy_revs = find_sma_reversals(df, 'DXY', 'DXY_SMA')
    if dxy_revs:
        rx, ry, rs, rt = [], [], [], []
        for d, p, typ in dxy_revs:
            rx.append(d); ry.append(p)
            rs.append('triangle-down' if typ=='peak' else 'triangle-up')
            rt.append(f"{p:.1f}")
        fig.add_trace(go.Scatter(
            x=rx, y=ry, mode='markers+text',
            marker=dict(symbol=rs, size=10, color='#4169E1', line=dict(width=1.2, color='white')),
            text=rt, textposition="top center", textfont=dict(size=10),
            name="DXY Rev", showlegend=False
        ), row=2, col=1)

    # Annotation - latest 6-month correlation, bold if strong
    box_color = 'darkgreen' if corr_6m > 0.7 else 'darkred' if corr_6m < -0.7 else 'gray'
    border_width = 2.5 if is_strong else 1.5
    fig.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.88,
        text=display_text, showarrow=False,
        bgcolor="white", bordercolor=box_color, borderwidth=border_width,
        font=dict(color=box_color, size=13)
    )

    # ─── Layout ───
    fig.update_layout(
        template="plotly_white",
        height=980,
        title=dict(text="Gold / Silver / DXY - 10yr Hybrid View", font=dict(size=20)),
        margin=dict(l=60, r=60, t=90, b=60),
        legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center", font=dict(size=12)),
        hovermode="x unified",
        hoverlabel=dict(font_size=13)
    )

    fig.update_xaxes(rangeslider_visible=False, tickfont=dict(size=11))
    fig.update_yaxes(title_text="Gold (USD)",           row=1, col=1, secondary_y=False,  tickfont=dict(size=11))
    fig.update_yaxes(title_text="Silver (USD) & Ratio", row=1, col=1, secondary_y=True,  tickfont=dict(size=11), showgrid=False)
    fig.update_yaxes(title_text="DXY",                  row=2, col=1, secondary_y=False, tickfont=dict(size=11))
    fig.update_yaxes(title_text="1-Year Rolling Corr", range=[-1.1,1.1], row=2, col=1, secondary_y=True, showgrid=False, tickfont=dict(size=11))

    fig.update_layout(autosize=True, font=dict(family="Arial", size=12))

    fig.write_html(
        HTML_FILENAME,
        include_plotlyjs='cdn',
        full_html=True,
        config={'responsive': True, 'displayModeBar': False, 'scrollZoom': True}
    )

    # Server
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args): pass

    def start_server():
        with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
            print(f"Server → http://localhost:{PORT}/{HTML_FILENAME}")
            httpd.serve_forever()

    if not any(t.name == 'ServerThread' for t in threading.enumerate()):
        threading.Thread(target=start_server, name='ServerThread', daemon=True).start()
        time.sleep(1.3)

    url = f"http://localhost:{PORT}/{HTML_FILENAME}"
    print(f"Chart: {url}")

    for cmd in ["termux-open-url", "termux-open", "xdg-open"]:
        try:
            subprocess.run(f"{cmd} {url}", shell=True, timeout=5)
            break
        except:
            pass
    else:
        print("Open the link manually.")

    print("Press Ctrl+C to stop.")
    try:
        while True: time.sleep(3)
    except KeyboardInterrupt:
        print("Stopped.")

if __name__ == "__main__":
    try:
        import plotly
    except ImportError:
        print("pip install plotly")
        exit(1)
    run_analysis_and_serve(SELECTED_WINDOW)