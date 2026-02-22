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
SMA_REVERSAL_THRESHOLD = 0.015  # Adjusted for sensitivity

SELECTED_WINDOW = 365 * 5 + 60
RECENT_DAYS = 365 * 2

HTML_FILENAME = "market_analysis_revamped.html"

ROLLING_CORR_WINDOW = 60 # Approx 3 months rolling for sensitivity
CORR_LOOKBACK_YEARS = 2

# Colors
COLOR_GOLD = '#D4AF37'
COLOR_SILVER = '#A9A9A9' # Dark Gray for visibility
COLOR_RATIO = '#800080'  # Purple
COLOR_DXY = '#003366'    # Navy
COLOR_CORR = '#FF6347'   # Tomato/Red
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
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"period1": p1, "period2": p2, "interval": interval, "includePrePost": "false"}
        
        r = requests.get(url, headers=headers, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        
        dates = pd.to_datetime(timestamps, unit='s')
        series = pd.Series(closes, index=dates, name=ticker)
        return series.dropna()
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return pd.Series(dtype=float)

# ────────────────────────────────────────────────
# Peak/Trough Detection
# ────────────────────────────────────────────────
def get_peaks_troughs(series, window=10):
    """
    Finds local max/min for placing annotations.
    """
    n = window
    # Find local peaks
    df_idx = series.iloc[argrelextrema(series.values, np.greater_equal, order=n)[0]]
    peaks = list(zip(df_idx.index, df_idx.values, ['peak'] * len(df_idx)))
    
    # Find local troughs
    df_idx_min = series.iloc[argrelextrema(series.values, np.less_equal, order=n)[0]]
    troughs = list(zip(df_idx_min.index, df_idx_min.values, ['trough'] * len(df_idx_min)))
    
    # Merge and sort
    all_points = sorted(peaks + troughs, key=lambda x: x[0])
    return all_points

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
        # Fetch Weekly for history
        s_weekly = fetch_yahoo_data(symbol, full_start, now, '1wk')
        time.sleep(0.5)
        # Fetch Daily for recent precision
        s_recent = fetch_yahoo_data(symbol, recent_start, now, '1d')
        time.sleep(0.5)

        if s_weekly.empty and s_recent.empty: 
            continue

        # Merge: Prefer recent daily data, fill back with weekly
        combined = pd.concat([s_weekly, s_recent])
        combined = combined[~combined.index.duplicated(keep='last')].sort_index()
        data_frames.append(combined.rename(name))

    if not data_frames:
        return None

    df = pd.concat(data_frames, axis=1)
    
    # Interpolate to fill gaps between weekly points so SMAs are smooth
    df = df.interpolate(method='time')
    
    # Cutoff to 5 years
    cutoff = now - timedelta(days=SELECTED_WINDOW)
    df = df[df.index >= cutoff]

    # Calculate Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    
    # Calculate SMAs for visual trends
    df['Ratio_SMA'] = df['Ratio'].rolling(window=10).mean()
    
    # Calculate Correlation (Gold vs DXY)
    df['Corr'] = df['Gold'].rolling(ROLLING_CORR_WINDOW).corr(df['DXY'])

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

    # --- TOP CHART: Gold (L), Silver (L-Hidden Scale), Ratio (R) ---
    
    # 1. Gold (Left Axis)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Gold'], 
        name="Gold ($)", 
        line=dict(color=COLOR_GOLD, width=2)
    ), row=1, col=1, secondary_y=False)

    # 2. Silver (Left Axis - Scaled purely for visual comparison if needed, or separate)
    # To mimic the image, Silver is usually plotted against the left axis but is much lower. 
    # Or we can put it on the right axis. Let's put it on the Left but let the user toggle it.
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Silver'], 
        name="Silver ($)", 
        line=dict(color=COLOR_SILVER, width=1),
        visible='legendonly' # Hidden by default to keep clean, click to view
    ), row=1, col=1, secondary_y=False)

    # 3. Ratio (Right Axis - The Purple Line)
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Ratio'], 
        name="G/S Ratio", 
        line=dict(color=COLOR_RATIO, width=2.5)
    ), row=1, col=1, secondary_y=True)

    # --- TOP ANNOTATIONS (Ratio Reversals) ---
    # We find significant peaks on the SMA or the Ratio itself. 
    # The image uses the SMA Direction Changes. Let's use the Ratio SMA for smoother points.
    reversals = get_peaks_troughs(df['Ratio_SMA'].dropna(), window=25)
    
    for date, val, type_ in reversals:
        # Only annotate if within the visible range and significant
        if date < cutoff: continue
        
        # Determine styling based on Peak vs Trough
        if type_ == 'peak':
            y_shift = 10
            arrow_color = COLOR_RATIO
            symbol = "triangle-down"
            ay = -20
            val_text = f"{val:.2f}"
            bg = "white"
        else:
            y_shift = -10
            arrow_color = COLOR_RATIO
            symbol = "triangle-up"
            ay = 20
            val_text = f"{val:.2f}"
            bg = "white"

        fig.add_annotation(
            x=date, y=val,
            text=val_text,
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor=arrow_color,
            ax=0, ay=ay,
            bgcolor=bg,
            bordercolor=arrow_color,
            borderwidth=1,
            opacity=0.9,
            font=dict(size=9, color="black"),
            row=1, col=1, secondary_y=True
        )
        
        # Add the small triangle marker on the line
        fig.add_trace(go.Scatter(
            x=[date], y=[val],
            mode='markers',
            marker=dict(symbol=symbol, size=8, color=arrow_color),
            showlegend=False,
            hoverinfo='skip'
        ), row=1, col=1, secondary_y=True)


    # --- BOTTOM CHART: DXY (L), Correlation (R) ---

    # 4. DXY
    fig.add_trace(go.Scatter(
        x=df.index, y=df['DXY'], 
        name="DXY", 
        line=dict(color=COLOR_DXY, width=2)
    ), row=2, col=1, secondary_y=False)

    # 5. Correlation
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Corr'], 
        name="Gold/DXY Corr", 
        line=dict(color=COLOR_CORR, width=1.5, dash='dot'),
        opacity=0.8
    ), row=2, col=1, secondary_y=True)

    # Zero Line for Correlation
    fig.add_shape(type="line",
        x0=df.index[0], y0=0, x1=df.index[-1], y1=0,
        line=dict(color="gray", width=1),
        row=2, col=1, secondary_y=True
    )

    # Annotate Correlation Ends/Significant points
    current_corr = df['Corr'].iloc[-1]
    corr_status = "Decoupled" if abs(current_corr) < 0.3 else ("Inverse" if current_corr < 0 else "Direct")
    
    # Text Box for Correlation Status
    fig.add_annotation(
        x=0.01, y=0.95, xref="paper", yref="paper",  # Relative to subplot
        text=f"<b>Gold/DXY Corr: {current_corr:.2f} ({corr_status})</b>",
        showarrow=False,
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        row=2, col=1
    )
    
    # Annotate peaks on Correlation
    corr_reversals = get_peaks_troughs(df['Corr'].dropna(), window=60) # Less frequent
    for date, val, type_ in corr_reversals:
        if date < now - timedelta(days=365*3): continue # Only last 3 years
        
        fig.add_annotation(
            x=date, y=val,
            text=f"{val:.2f}",
            showarrow=True,
            arrowhead=0,
            ax=0, ay= -15 if type_ == 'peak' else 15,
            font=dict(color=COLOR_CORR, size=8),
            row=2, col=1, secondary_y=True
        )
        
        # Add Marker
        fig.add_trace(go.Scatter(
            x=[date], y=[val],
            mode='markers',
            marker=dict(symbol="triangle-down" if type_=='peak' else "triangle-up", size=6, color=COLOR_CORR),
            showlegend=False
        ), row=2, col=1, secondary_y=True)

    # ────────────────────────────────────────────────
    # LAYOUT STYLING
    # ────────────────────────────────────────────────
    fig.update_layout(
        title=dict(text="<b>Market Analysis (5yr) - Weekly SMA Direction Changes</b>", x=0.5),
        template="plotly_white",
        plot_bgcolor=BG_COLOR,
        paper_bgcolor="white",
        height=900,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Axis Styling
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, rangeslider_visible=False)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False)

    # Specific Y-Axis Labels
    fig.update_yaxes(title_text="<b>Gold Price ($)</b>", title_font=dict(color=COLOR_GOLD), row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="<b>G/S Ratio</b>", title_font=dict(color=COLOR_RATIO), row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="<b>DXY</b>", title_font=dict(color=COLOR_DXY), row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="<b>Correlation</b>", title_font=dict(color=COLOR_CORR), range=[-1.1, 1.1], row=2, col=1, secondary_y=True)

    fig.write_html(HTML_FILENAME, include_plotlyjs='cdn')
    return HTML_FILENAME

# ────────────────────────────────────────────────
# Execution
# ────────────────────────────────────────────────
def open_html(file_path):
    abs_path = os.path.abspath(file_path)
    print(f"\nOpening: {abs_path}")
    try:
        subprocess.run(["termux-open", abs_path], check=False) # For Termux
    except:
        try:
            webbrowser.open(f"file://{abs_path}") # For Desktop
        except:
            print("Could not auto-open file.")

if __name__ == "__main__":
    html_file = run_analysis()
    if html_file and os.path.exists(html_file):
        print("\nChart generated successfully.")
        open_html(html_file)
    else:
        print("\nFailed to generate chart.")