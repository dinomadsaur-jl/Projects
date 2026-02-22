import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import os
import subprocess
import webbrowser
from datetime import datetime, timedelta
from scipy.signal import argrelextrema

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {
    'Gold': 'GC=F',
    'Silver': 'SI=F',
    'DXY': 'DX-Y.NYB'
}

SMA_PERIOD = 20
SMA_REVERSAL_THRESHOLD = 0.015

SELECTED_WINDOW = 365 * 5 + 60
RECENT_DAYS = 365 * 2

HTML_FILENAME = "market_analysis_5yr.html"

ROLLING_CORR_WINDOW = 504   # ~2 years weekly
ANNOTATION_CORR_WINDOW = 126  # ~6 months weekly

# Scaling for Silver on shared G/S Ratio axis (right side)
SILVER_SCALE_FACTOR = 80   # Tune: 70–100 based on current prices (see title)

# Colors
COLOR_GOLD = '#D4AF37'
COLOR_SILVER = '#A9A9A9'
COLOR_RATIO = '#800080'
COLOR_DXY = '#003366'
COLOR_CORR = '#FF6347'
BG_COLOR = 'rgb(252, 252, 252)'
GRID_COLOR = 'rgb(220, 220, 220)'

# ────────────────────────────────────────────────
# Data Fetching
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    try:
        print(f"Fetching {ticker} ({interval})")
        p1 = int(start_date.timestamp())
        p2 = int(end_date.timestamp())
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        params = {
            "period1": p1,
            "period2": p2,
            "interval": interval,
            "includePrePost": "false",
            "includeAdjustedClose": "true",
            "events": "history"
        }
        
        r = requests.get(url, headers=headers, params=params, timeout=35)
        r.raise_for_status()
        data = r.json()
        
        result = data['chart']['result'][0]
        if not result.get('timestamp'):
            raise ValueError("No timestamp in response")
        
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        
        dates = pd.to_datetime(timestamps, unit='s')
        series = pd.Series(closes, index=dates, name=ticker)
        cleaned = series.dropna()
        print(f"→ {ticker} returned {len(cleaned)} points")
        return cleaned
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return pd.Series(dtype=float)

# ────────────────────────────────────────────────
# SMA Reversal Detection (adapted from your Matplotlib logic)
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
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma <= last_sma_val * (1 - threshold):
                trend = -1
                last_sma_val = curr_sma
                last_date = date

        elif trend == 1:
            if curr_sma > last_sma_val:
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma < last_sma_val * (1 - threshold):
                raw_price = df.loc[last_date, raw_col]
                reversals.append((last_date, raw_price, 'peak'))
                trend = -1
                last_sma_val = curr_sma
                last_date = date

        elif trend == -1:
            if curr_sma < last_sma_val:
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma > last_sma_val * (1 + threshold):
                raw_price = df.loc[last_date, raw_col]
                reversals.append((last_date, raw_price, 'trough'))
                trend = 1
                last_sma_val = curr_sma
                last_date = date

    return reversals

# ────────────────────────────────────────────────
# Main Analysis
# ────────────────────────────────────────────────
def run_analysis():
    print("\n--- Analyzing ~5 years of data ---")
    now = datetime.now()
    full_start = now - timedelta(days=SELECTED_WINDOW + 200)
    recent_start = now - timedelta(days=RECENT_DAYS)

    data_frames = []
    for name, symbol in TICKERS.items():
        print(f"\n{name} ({symbol})...")
        s_weekly = fetch_yahoo_data(symbol, full_start, now, '1wk')
        time.sleep(1.2)
        s_recent = fetch_yahoo_data(symbol, recent_start, now, '1d')
        time.sleep(1.2)

        if s_weekly.empty and s_recent.empty:
            print(f"Skipping {name} - no data")
            continue

        combined = pd.concat([s_weekly, s_recent])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
        data_frames.append(combined.rename(name))

    if not data_frames:
        print("No data retrieved.")
        return None

    df = pd.concat(data_frames, axis=1)
    df = df.interpolate(method='time')
    
    cutoff = now - timedelta(days=SELECTED_WINDOW)
    df = df[df.index >= cutoff]

    if df.empty:
        print("No data after cutoff.")
        return None

    # Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    df['Silver_Scaled'] = df['Silver'] * SILVER_SCALE_FACTOR  # ← for shared right axis

    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    df['Corr'] = df['Gold'].rolling(ROLLING_CORR_WINDOW).corr(df['DXY'])

    # Last values for title
    last_gold   = df['Gold'].iloc[-1]   if 'Gold' in df else np.nan
    last_silver = df['Silver'].iloc[-1] if 'Silver' in df else np.nan
    last_ratio  = df['Ratio'].iloc[-1]  if 'Ratio' in df else np.nan
    last_corr   = df['Corr'].iloc[-1]   if 'Corr' in df else np.nan

    # ────────────────────────────────────────────────
    # Plotting
    # ────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.05,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Top panel: Gold (left), Silver scaled + Ratio (right)
    fig.add_trace(
        go.Scatter(x=df.index, y=df['Gold'], name="Gold", line=dict(color=COLOR_GOLD, width=2.2)),
        row=1, col=1, secondary_y=False
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['Silver_Scaled'], name=f"Silver × {SILVER_SCALE_FACTOR}", 
                   line=dict(color=COLOR_SILVER, width=1.8, dash='dash')),
        row=1, col=1, secondary_y=True
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['Ratio'], name="G/S Ratio", line=dict(color=COLOR_RATIO, width=2.8)),
        row=1, col=1, secondary_y=True
    )

    # Reversal annotations on Ratio (raw values)
    reversals = find_sma_reversals(df, 'Ratio', 'Ratio_SMA')
    for r_date, r_raw_price, r_type in reversals:
        ay = -30 if r_type == 'peak' else 30
        symbol = "triangle-down" if r_type == 'peak' else "triangle-up"

        fig.add_annotation(
            x=r_date, y=r_raw_price,
            text=f"{r_raw_price:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=COLOR_RATIO,
            ax=0, ay=ay,
            bgcolor="white",
            bordercolor=COLOR_RATIO,
            font=dict(size=10),
            row=1, col=1, secondary_y=True
        )

        fig.add_trace(
            go.Scatter(
                x=[r_date], y=[r_raw_price],
                mode='markers',
                marker=dict(symbol=symbol, size=10, color=COLOR_RATIO),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1, secondary_y=True
        )

    # Bottom panel: DXY + rolling corr
    fig.add_trace(
        go.Scatter(x=df.index, y=df['DXY'], name="DXY", line=dict(color=COLOR_DXY, width=2.2)),
        row=2, col=1, secondary_y=False
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=df['Corr'], name="2yr Corr", 
                   line=dict(color=COLOR_CORR, width=1.8, dash='dot'), opacity=0.9),
        row=2, col=1, secondary_y=True
    )

    fig.add_hline(y=0, line_width=1, line_color="gray", row=2, col=1, secondary_y=True)

    # ────────────────────────────────────────────────
    # Layout with detailed title
    # ────────────────────────────────────────────────
    corr_status = "Decoupled" if abs(last_corr) < 0.3 else ("Inverse" if last_corr < 0 else "Direct")

    fig.update_layout(
        title={
            'text': f"<b>Market Analysis (5yr) - Weekly SMA Direction Changes</b><br>"
                    f"<span style='font-size:0.85em;'>"
                    f"Gold: ${last_gold:,.0f} | Silver: ${last_silver:,.2f} | "
                    f"G/S Ratio: {last_ratio:.2f} | Corr: {last_corr:.2f} ({corr_status})</span>",
            'x': 0.5,
            'y': 0.98,
            'font': {'size': 18}
        },
        template="plotly_white",
        height=900,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=60, r=60, t=110, b=60)
    )

    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)

    # Axes titles
    fig.update_yaxes(title_text="<b>Gold Price ($)</b>", title_font=dict(color=COLOR_GOLD), row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text=f"<b>Silver × {SILVER_SCALE_FACTOR} / G/S Ratio</b>", title_font=dict(color=COLOR_RATIO), row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="<b>DXY</b>", title_font=dict(color=COLOR_DXY), row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="<b>Correlation</b>", title_font=dict(color=COLOR_CORR), range=[-1.1, 1.1], row=2, col=1, secondary_y=True)

    print("Generating HTML...")
    fig.write_html(HTML_FILENAME, include_plotlyjs='cdn')
    return HTML_FILENAME

# ────────────────────────────────────────────────
# Execution
# ────────────────────────────────────────────────
def open_html(file_path):
    abs_path = os.path.abspath(file_path)
    print(f"\nOpening: {abs_path}")
    try:
        subprocess.run(["termux-open", abs_path], check=False)
    except:
        try:
            webbrowser.open(f"file://{abs_path}")
        except:
            print("Could not auto-open file.")

if __name__ == "__main__":
    html_file = run_analysis()
    if html_file and os.path.exists(html_file):
        print("\nChart generated successfully.")
        open_html(html_file)
    else:
        print("\nFailed to generate chart.")