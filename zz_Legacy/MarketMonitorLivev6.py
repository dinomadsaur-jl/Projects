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

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {
    'Gold': 'GC=F',
    'Silver': 'SI=F',
    'DXY': 'DX-Y.NYB'   # Correct index ticker
}

SMA_PERIOD = 20
SMA_REVERSAL_THRESHOLD = 0.001

SELECTED_WINDOW = 365 * 5 + 100
RECENT_DAYS = 365 * 2

HTML_FILENAME = "market_analysis_5yr.html"

ROLLING_CORR_WINDOW = 504
ANNOTATION_CORR_WINDOW = 126

# ────────────────────────────────────────────────
# Data Fetching (Yahoo v8 Chart API)
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    """
    Fetch data using Yahoo v8 chart API (no crumb required).
    """
    try:
        print(f"Fetching {ticker} ({interval})")

        p1 = int(start_date.timestamp())
        p2 = int(end_date.timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        params = {
            "period1": p1,
            "period2": p2,
            "interval": interval,
            "includePrePost": "false"
        }

        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']

        dates = pd.to_datetime(timestamps, unit='s')
        series = pd.Series(closes, index=dates, name=ticker)

        series = series.dropna()
        print(f"→ Received {len(series)} points")
        return series

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
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
    print("\n--- Analyzing ~5 years of data ---")

    now = datetime.now()
    full_start = now - timedelta(days=SELECTED_WINDOW + 200)
    recent_start = now - timedelta(days=RECENT_DAYS)

    data_frames = []
    for name, symbol in TICKERS.items():
        print(f"\n{name} ({symbol})...")

        s_weekly = fetch_yahoo_data(symbol, full_start, now, '1wk')
        time.sleep(1)

        s_recent = fetch_yahoo_data(symbol, recent_start, now, '1d')
        time.sleep(1)

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
    cutoff = now - timedelta(days=SELECTED_WINDOW)
    df = df[df.index >= cutoff]

    if df.empty:
        print("No data after cutoff.")
        return None

    # Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    rolling_corr = df['Gold'].rolling(ROLLING_CORR_WINDOW, min_periods=100).corr(df['DXY'])

    # ─── Plot ───
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.6, 0.4],
        vertical_spacing=0.05,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Top panel
    fig.add_trace(go.Scatter(x=df.index, y=df['Gold'], name="Gold"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Silver'], name="Silver"), row=1, col=1, secondary_y=True)
    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'], name="G/S Ratio"), row=1, col=1, secondary_y=True)

    # Bottom panel
    fig.add_trace(go.Scatter(x=df.index, y=df['DXY'], name="DXY"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=rolling_corr, name="2yr Corr"), row=2, col=1, secondary_y=True)

    fig.add_hline(y=0, line_width=1, line_color="gray", row=2, col=1, secondary_y=True)

    fig.update_layout(
        template="plotly_white",
        title="Gold / Silver / DXY – ~5yr View",
        hovermode="x unified"
    )

    fig.write_html(HTML_FILENAME, include_plotlyjs='cdn')
    return HTML_FILENAME


# ────────────────────────────────────────────────
# Open HTML automatically
# ────────────────────────────────────────────────
def open_html(file_path):
    abs_path = os.path.abspath(file_path)
    print(f"\nOpening: {abs_path}")

    try:
        # Termux (Android)
        subprocess.run(["termux-open", abs_path], check=False)
    except:
        try:
            # Windows/Mac/Linux
            webbrowser.open(f"file://{abs_path}")
        except:
            print("Could not auto-open file.")


# ────────────────────────────────────────────────
# Run script
# ────────────────────────────────────────────────
if __name__ == "__main__":
    html_file = run_analysis()

    if html_file and os.path.exists(html_file):
        print("\nChart generated successfully.")
        open_html(html_file)
    else:
        print("\nFailed to generate chart.")