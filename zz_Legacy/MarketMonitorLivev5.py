import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import os
from datetime import datetime, timedelta
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
SMA_REVERSAL_THRESHOLD = 0.001

SELECTED_WINDOW = 365 * 5 + 100
RECENT_DAYS = 365 * 2

HTML_FILENAME = "market_analysis_5yr.html"

ROLLING_CORR_WINDOW = 504
ANNOTATION_CORR_WINDOW = 126


# ────────────────────────────────────────────────
# Yahoo cookie + crumb
# ────────────────────────────────────────────────
def get_crumb_and_cookie(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9"
    })

    r = session.get(url, timeout=30)
    r.raise_for_status()

    crumb = None
    for line in r.text.splitlines():
        if '"CrumbStore":{"crumb":"' in line:
            crumb = line.split('"CrumbStore":{"crumb":"')[1].split('"')[0]
            crumb = crumb.encode('ascii').decode('unicode_escape')
            break

    if not crumb:
        raise RuntimeError("Could not extract crumb token")

    return session, crumb


# ────────────────────────────────────────────────
# Data Fetching
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    try:
        print(f"Fetching {ticker} ({interval})")

        session, crumb = get_crumb_and_cookie(ticker)

        p1 = int(start_date.timestamp())
        p2 = int(end_date.timestamp() + 86400)

        url = f"https://query1.finance.yahoo.com/v7/finance/download/{ticker}"
        params = {
            "period1": p1,
            "period2": p2,
            "interval": interval,
            "events": "history",
            "crumb": crumb
        }

        r = session.get(url, params=params, timeout=60)
        r.raise_for_status()

        df = pd.read_csv(StringIO(r.text), index_col="Date", parse_dates=True)

        if "Close" not in df.columns:
            print("Missing Close column")
            return pd.Series(dtype=float)

        series = df["Close"].rename(ticker).dropna()
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
        time.sleep(2)

        s_recent = fetch_yahoo_data(symbol, recent_start, now, '1d')
        time.sleep(2)

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

    df['Ratio'] = df['Gold'] / df['Silver']

    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(SMA_PERIOD).mean()

    rolling_corr = df['Gold'].rolling(ROLLING_CORR_WINDOW, min_periods=100).corr(df['DXY'])

    # ─── Plot ───
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True)

    fig.add_trace(go.Scatter(x=df.index, y=df['Gold'], name="Gold"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Silver'], name="Silver"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Ratio'], name="G/S Ratio"), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['DXY'], name="DXY"), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=rolling_corr, name="2yr Corr"), row=2, col=1)

    fig.update_layout(
        template="plotly_white",
        title="Gold / Silver / DXY – ~5yr View",
        hovermode="x unified"
    )

    fig.write_html(HTML_FILENAME, include_plotlyjs='cdn')
    return HTML_FILENAME


if __name__ == "__main__":
    html_file = run_analysis()

    if html_file and os.path.exists(html_file):
        print("\nChart generated:")
        print(os.path.abspath(html_file))
    else:
        print("\nFailed to generate chart.")