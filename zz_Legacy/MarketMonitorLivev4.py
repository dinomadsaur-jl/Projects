import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import os
import random
from datetime import datetime, timedelta
from requests.exceptions import HTTPError
from io import StringIO

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

SELECTED_WINDOW = 365 * 5 + 100    # ~5 years + buffer
RECENT_DAYS = 365 * 2              # last 2 years daily patch

HTML_FILENAME = "market_analysis_5yr.html"

ROLLING_CORR_WINDOW = 504          # ≈ 2 years trading days
ANNOTATION_CORR_WINDOW = 126       # ≈ 6 months for annotation

CACHE_DIR = "yahoo_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
]

# ────────────────────────────────────────────────
# Data Fetching with cache & anti-rate-limit
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval, use_cache=True):
    cache_filename = f"{ticker}_{interval}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    cache_path = os.path.join(CACHE_DIR, cache_filename)

    if use_cache and os.path.exists(cache_path):
        print(f"Cache hit: {cache_filename}")
        try:
            df = pd.read_csv(cache_path, index_col="Date", parse_dates=True)
            if 'Close' in df.columns:
                return df['Close'].rename(ticker).dropna()
            else:
                print("Cache missing 'Close' column")
        except Exception as e:
            print(f"Cache read failed: {e} → refetching")

    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/csv,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://finance.yahoo.com/",
        "Connection": "keep-alive",
    })

    p1 = int(start_date.timestamp())
    p2 = int(end_date.timestamp() + 86400)

    url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
    # You can try query2 if query1 keeps failing:
    # url = f"https://query2.finance.yahoo.com/v7/finance/download/{ticker}"

    params = {
        "period1": p1,
        "period2": p2,
        "interval": interval,
        "events": "history",
        "includeAdjustedClose": "true"
    }

    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Fetching {ticker} ({interval}) attempt {attempt+1}")
            r = session.get(url, params=params, timeout=60)

            if r.status_code == 429:
                wait = 180 + attempt * 120 + random.uniform(0, 30)  # 3–10+ min
                print(f"429 → sleeping ~{wait//60:.0f} minutes")
                time.sleep(wait)
                continue

            if r.status_code in (403, 401, 400):
                print(f"Blocked ({r.status_code}) – likely premium restriction or IP issue")
                break

            r.raise_for_status()

            df = pd.read_csv(StringIO(r.text), index_col="Date", parse_dates=True)
            if 'Close' not in df.columns:
                print("Response missing 'Close' column")
                break

            series = df['Close'].rename(ticker).dropna()
            print(f"→ Received {len(series)} points")

            df.to_csv(cache_path)
            print(f"Saved cache: {cache_filename}")
            return series

        except HTTPError as e:
            print(f"HTTP {getattr(e.response, 'status_code', 'unknown')}: {e}")
            if attempt < max_retries - 1:
                time.sleep(120 + attempt * 60)
        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt < max_retries - 1:
                time.sleep(120 + attempt * 60)

    print(f"Failed to fetch {ticker} ({interval}) after {max_retries} attempts")
    return pd.Series(dtype=float)


# ────────────────────────────────────────────────
# SMA Reversal Detection
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
# Main function
# ────────────────────────────────────────────────
def run_analysis():
    print(f"\n--- Analyzing ~5 years of data ---")

    now = datetime.now()
    full_start = now - timedelta(days=SELECTED_WINDOW + 200)
    recent_start = now - timedelta(days=RECENT_DAYS)

    data_frames = []
    for name, symbol in TICKERS.items():
        print(f"\n{name} ({symbol})...")

        s_weekly = fetch_yahoo_data(symbol, full_start, now, '1wk')
        time.sleep(180 + random.uniform(0, 60))  # forced long wait

        s_recent = fetch_yahoo_data(symbol, recent_start - timedelta(days=30), now + timedelta(days=5), '1d')
        time.sleep(180 + random.uniform(0, 60))

        if s_weekly.empty and s_recent.empty:
            print(f"Skipping {name} - no data")
            continue

        combined = pd.concat([s_weekly, s_recent])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
        data_frames.append(combined.rename(name))

    if not data_frames:
        print("No data retrieved from any ticker.")
        return None

    df = pd.concat(data_frames, axis=1)
    cutoff = now - timedelta(days=SELECTED_WINDOW)
    df = df[df.index >= cutoff]

    if df.empty:
        print("No data after cutoff date.")
        return None

    # Indicators
    df['Ratio'] = df['Gold'] / df['Silver']

    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    rolling_corr = df['Gold'].rolling(window=ROLLING_CORR_WINDOW, min_periods=100).corr(df['DXY'])

    recent_df = df.tail(ANNOTATION_CORR_WINDOW * 2)
    corr_6m = np.nan
    if len(recent_df) >= ANNOTATION_CORR_WINDOW:
        corr_6m = recent_df['Gold'].corr(recent_df['DXY'])

    status = ("Strong Inversion" if corr_6m < -0.5 else "Inversion" if corr_6m < -0.2 else
              "Strong Positive" if corr_6m > 0.5 else "Positive" if corr_6m > 0.2 else "Decoupled")
    corr_text = f"Gold vs DXY 6m Corr: {corr_6m:.2f} ({status})" if not np.isnan(corr_6m) else "N/A"
    
    is_strong = abs(corr_6m) > 0.5 if not np.isnan(corr_6m) else False
    display_text = f"<b>{corr_text}</b>" if is_strong else corr_text

    # ─── Plot ───
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.04,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Top panel traces
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold'],       name="Gold",       line=dict(color='#D4AF37', width=1.2), opacity=0.4), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold_SMA'],   name="Gold SMA",   line=dict(color='#D4AF37', width=2.4)), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['Silver'],     name="Silver",     line=dict(color='#B0C4DE', width=1.2), opacity=0.4), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=df.index, y=df['Silver_SMA'], name="Silver SMA", line=dict(color='#B0C4DE', width=2.4)), row=1, col=1, secondary_y=True)

    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'],      name="G/S Ratio",  line=dict(color='#9370DB', width=1.8, dash='dot'), opacity=0.75), row=1, col=1, secondary_y=True)

    # Reversals - top panel
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
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY'],       name="DXY",       line=dict(color='#4169E1', width=1.2), opacity=0.45), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY_SMA'],   name="DXY SMA",   line=dict(color='#4169E1', width=2.4)), row=2, col=1)

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

    # Last known prices
    last_idx = df.index[-1]
    today_str = datetime.now().strftime("%b %d")

    def last_valid(series):
        valid = series.dropna()
        if valid.empty:
            return np.nan, None
        return valid.iloc[-1], valid.index[-1]

    for asset, color, sec_y, row in [
        ('Gold',   '#D4AF37', False, 1),
        ('Silver', '#B0C4DE', True,  1),
        ('DXY',    '#4169E1', False, 2)
    ]:
        price, date = last_valid(df[asset])
        if not np.isnan(price):
            text = f"{asset} {price:,.0f}" if asset == 'Gold' else f"{asset} {price:,.2f}"
            if date and date.strftime("%b %d") != today_str:
                text += f" ({date.strftime('%b %d')})"
            fig.add_annotation(
                x=last_idx, y=price,
                text=text,
                xanchor="left", ax=40, ay=0,
                font=dict(color=color, size=13),
                bgcolor="rgba(255,255,255,0.85)",
                bordercolor=color, borderwidth=1,
                showarrow=False,
                row=row, col=1, secondary_y=sec_y
            )

    # 6-month correlation annotation
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

    # ─── Layout ───
    fig.update_layout(
        template="plotly_white",
        autosize=True,
        title=dict(text="Gold / Silver / DXY – ~5yr View (2yr Corr)", font=dict(size=15)),
        margin=dict(l=30, r=10, t=45, b=30),
        legend=dict(orientation="h", y=1.06, x=0.5, xanchor="center", font=dict(size=8.5)),
        hovermode="x unified",
        hoverlabel=dict(font_size=10),
        font=dict(family="Arial", size=9.5)
    )

    fig.update_xaxes(rangeslider_visible=False, tickfont=dict(size=9))
    fig.update_yaxes(title_text="Gold (USD)",           row=1, col=1, secondary_y=False,  tickfont=dict(size=9))
    fig.update_yaxes(title_text="Silver & Ratio",       row=1, col=1, secondary_y=True,   tickfont=dict(size=9), showgrid=False)
    fig.update_yaxes(title_text="DXY",                  row=2, col=1, secondary_y=False,  tickfont=dict(size=9))
    fig.update_yaxes(title_text="2yr Rolling Corr", range=[-1.1,1.1], row=2, col=1, secondary_y=True, tickfont=dict(size=9), showgrid=False)

    # ─── Export to HTML ───
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

    # ─── Mobile optimization ───
    with open(HTML_FILENAME, 'r', encoding='utf-8') as f:
        html_content = f.read()

    mobile_head = """
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<style>
    html, body { margin:0; padding:0; height:100%; width:100%; overflow:hidden; font-size: 14px; }
    .js-plotly-plot { width:100vw !important; height:100vh !important; }
    .plotly .modebar { display:none !important; }
    @media (orientation: portrait) {
        .js-plotly-plot .plotly { min-height: 100vh !important; }
        .subplot:nth-child(2) { height: 45vh !important; min-height: 45vh !important; }
        .yaxis-title, .yaxis2-title { font-size: 11px !important; }
    }
    @media (orientation: landscape) {
        .subplot:nth-child(2) { height: 35vh !important; }
    }
</style>
"""

    head_close_pos = html_content.lower().rfind('</head>')
    if head_close_pos != -1:
        new_html = html_content[:head_close_pos] + mobile_head + html_content[head_close_pos:]
        with open(HTML_FILENAME, 'w', encoding='utf-8') as f:
            f.write(new_html)

    return HTML_FILENAME


if __name__ == "__main__":
    html_file = run_analysis()

    if html_file and os.path.exists(html_file):
        abs_path = os.path.abspath(html_file)
        
        print("\n" + "="*70)
        print("Chart successfully generated!")
        print(f"File location:  {abs_path}")
        print("="*70)
        
        print("\nHow to open the interactive chart:")
        print(" • Double-click the file in your file explorer")
        print(" • Drag the file into any browser (Chrome, Firefox, Safari, Edge)")
        print(" • In browser → File → Open File… → select the file")
        print(" • Or paste this into your browser address bar:")
        print(f"   file://{abs_path.replace(os.sep, '/')}")
        
        print("\nQuick one-liner commands (copy-paste):")
        print("macOS / Linux:    open " + abs_path)
        print("Windows (cmd):    start " + abs_path)
        print("Termux (Android): termux-open " + abs_path)
        
        print("\nThe file is self-contained (uses CDN for Plotly.js) and works offline after generation.")
    else:
        print("\nFailed to generate the chart. Check the console output above for errors.")