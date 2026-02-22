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

HTML_FILENAME = "market_analysis.html"

ROLLING_CORR_WINDOW = 60

# Colors
COLOR_GOLD = '#D4AF37'
COLOR_SILVER = '#A9A9A9'
COLOR_RATIO = '#800080'
COLOR_DXY = '#003366'
COLOR_CORR = '#FF6347'
BG_COLOR = 'rgb(252, 252, 252)'
GRID_COLOR = 'rgb(220, 220, 220)'

# Scaling factor so Silver line aligns visually with Ratio on shared right axis
SILVER_SCALE_FACTOR = 80  # ← adjust between 70–100 depending on current prices

# ────────────────────────────────────────────────
# Data Fetching
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, start_date, end_date, interval):
    try:
        print(f"Fetching {ticker} ({interval})")
        p1 = int(start_date.timestamp())
        p2 = int(end_date.timestamp())
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
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
# Peak/Trough Detection
# ────────────────────────────────────────────────
def get_peaks_troughs(series, window=10):
    n = window
    df_idx = series.iloc[argrelextrema(series.values, np.greater_equal, order=n)[0]]
    peaks = list(zip(df_idx.index, df_idx.values, ['peak'] * len(df_idx)))
    
    df_idx_min = series.iloc[argrelextrema(series.values, np.less_equal, order=n)[0]]
    troughs = list(zip(df_idx_min.index, df_idx_min.values, ['trough'] * len(df_idx_min)))
    
    return sorted(peaks + troughs, key=lambda x: x[0])

# ────────────────────────────────────────────────
# Main Analysis
# ────────────────────────────────────────────────
def run_analysis():
    print("\n--- Analyzing Market Data ---")
    now = datetime.now()
    full_start = now - timedelta(days=SELECTED_WINDOW + 200)
    recent_start = now - timedelta(days=RECENT_DAYS)

    data_frames = []
    for name, symbol in TICKERS.items():
        s_weekly = fetch_yahoo_data(symbol, full_start, now, '1wk')
        time.sleep(1.5)
        s_recent = fetch_yahoo_data(symbol, recent_start, now, '1d')
        time.sleep(1.5)

        if s_weekly.empty and s_recent.empty: 
            continue

        combined = pd.concat([s_weekly, s_recent])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
        data_frames.append(combined.rename(name))

    if not data_frames:
        print("No data fetched.")
        return None

    df = pd.concat(data_frames, axis=1, sort=False)
    df = df.interpolate(method='time')
    
    cutoff = now - timedelta(days=SELECTED_WINDOW)
    df = df[df.index >= cutoff]

    if df.empty:
        print("Empty after cutoff.")
        return None

    df['Ratio'] = df['Gold'] / df['Silver']
    df['Ratio_SMA'] = df['Ratio'].rolling(window=10).mean()
    df['Corr'] = df['Gold'].rolling(ROLLING_CORR_WINDOW).corr(df['DXY'])

    # Scale Silver to share right axis with Ratio
    df['Silver_Scaled'] = df['Silver'] * SILVER_SCALE_FACTOR

    # Last values for title
    last_gold   = df['Gold'].iloc[-1]   if 'Gold' in df else np.nan
    last_silver = df['Silver'].iloc[-1] if 'Silver' in df else np.nan
    last_ratio  = df['Ratio'].iloc[-1]  if 'Ratio' in df else np.nan
    last_corr   = df['Corr'].iloc[-1]   if 'Corr' in df else np.nan

    # ────────────────────────────────────────────────
    # VISUALIZATION
    # ────────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.65, 0.35],
        vertical_spacing=0.03,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}]]
    )

    # Gold – left axis
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Gold'],
        name="Gold ($)",
        line=dict(color=COLOR_GOLD, width=2.2)
    ), row=1, col=1, secondary_y=False)

    # Silver (scaled) – right axis, dashed for distinction
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Silver_Scaled'],
        name=f"Silver × {SILVER_SCALE_FACTOR}",
        line=dict(color=COLOR_SILVER, width=1.8, dash='dash')
    ), row=1, col=1, secondary_y=True)

    # G/S Ratio – right axis, solid
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Ratio'],
        name="G/S Ratio",
        line=dict(color=COLOR_RATIO, width=2.8)
    ), row=1, col=1, secondary_y=True)

    # Ratio reversals (on actual ratio values)
    reversals = get_peaks_troughs(df['Ratio_SMA'].dropna(), window=25)
    for date, val, type_ in reversals:
        if date < cutoff: continue
        ay = -25 if type_ == 'peak' else 25
        symbol = "triangle-down" if type_ == 'peak' else "triangle-up"

        fig.add_annotation(
            x=date, y=val,
            text=f"{val:.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=COLOR_RATIO,
            ax=0, ay=ay,
            bgcolor="white",
            bordercolor=COLOR_RATIO,
            opacity=0.95,
            font=dict(size=10, color="black"),
            row=1, col=1, secondary_y=True
        )
        
        fig.add_trace(go.Scatter(
            x=[date], y=[val],
            mode='markers',
            marker=dict(symbol=symbol, size=10, color=COLOR_RATIO),
            showlegend=False,
            hoverinfo='skip'
        ), row=1, col=1, secondary_y=True)

    # Bottom chart
    fig.add_trace(go.Scatter(
        x=df.index, y=df['DXY'],
        name="DXY",
        line=dict(color=COLOR_DXY, width=2.2)
    ), row=2, col=1, secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df.index, y=df['Corr'],
        name="Gold/DXY Corr",
        line=dict(color=COLOR_CORR, width=1.8, dash='dot'),
        opacity=0.85
    ), row=2, col=1, secondary_y=True)

    fig.add_shape(type="line",
        x0=df.index[0], y0=0, x1=df.index[-1], y1=0,
        line=dict(color="gray", width=1),
        row=2, col=1, secondary_y=True
    )

    # Correlation status
    corr_status = "Decoupled" if abs(last_corr) < 0.3 else ("Inverse" if last_corr < 0 else "Direct")
    fig.add_annotation(
        x=0.02, y=0.96, xref="paper", yref="paper",
        text=f"<b>Gold/DXY Corr: {last_corr:.2f} ({corr_status})</b>",
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        font=dict(size=11),
        row=2, col=1
    )

    # ────────────────────────────────────────────────
    # LAYOUT – detailed title with last prices
    # ────────────────────────────────────────────────
    fig.update_layout(
        title={
            'text': f"<b>Market Analysis (5yr) - Weekly SMA Direction Changes</b><br>"
                    f"<span style='font-size:0.9em; color:#444;'>"
                    f"Gold: ${last_gold:,.0f} | Silver: ${last_silver:,.2f} | "
                    f"G/S Ratio: {last_ratio:.2f}</span>",
            'x': 0.5,
            'y': 0.98,
            'font': {'size': 18}
        },
        template="plotly_white",
        plot_bgcolor=BG_COLOR,
        paper_bgcolor="white",
        height=920,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=60, r=60, t=110, b=60)
    )

    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)

    # Left: Gold
    fig.update_yaxes(
        title_text="<b>Gold Price ($)</b>",
        title_font=dict(color=COLOR_GOLD, size=13),
        tickfont=dict(color=COLOR_GOLD),
        row=1, col=1, secondary_y=False
    )

    # Right: Silver (scaled) + Ratio
    fig.update_yaxes(
        title_text=f"<b>Silver × {SILVER_SCALE_FACTOR} / G/S Ratio</b>",
        title_font=dict(color=COLOR_RATIO, size=13),
        tickfont=dict(color=COLOR_RATIO),
        row=1, col=1, secondary_y=True
    )

    # Bottom axes
    fig.update_yaxes(
        title_text="<b>DXY</b>",
        title_font=dict(color=COLOR_DXY, size=13),
        tickfont=dict(color=COLOR_DXY),
        row=2, col=1, secondary_y=False
    )

    fig.update_yaxes(
        title_text="<b>Correlation</b>",
        title_font=dict(color=COLOR_CORR, size=13),
        range=[-1.1, 1.1],
        row=2, col=1, secondary_y=True
    )

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