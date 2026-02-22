import requests
import pandas as pd
import numpy as np
import matplotlib
# Force headless backend for Termux to prevent crashes
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import subprocess
import time
from datetime import datetime, timedelta

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {'Gold': 'GC=F', 'Silver': 'SI=F', 'DXY': 'DX-Y.NYB'}
SMA_PERIOD = 20
# Threshold to confirm SMA reversal (1%)
SMA_REVERSAL_THRESHOLD = 0.01 

WINDOWS = {"6mo": 180, "1yr": 365, "5yr": 1825}

# Check Android Storage
if os.path.exists("/sdcard/Download"):
    SAVE_DIR = "/sdcard/Download"
else:
    SAVE_DIR = os.getcwd()

# ────────────────────────────────────────────────
# 1. Manual Data Fetching (No yfinance)
# ────────────────────────────────────────────────
def fetch_yahoo_data(ticker, days_back):
    """
    Manually requests data from Yahoo Finance API v8.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back + 100) # Buffer for SMA
    
    # Convert to Unix timestamps
    p1 = int(start_date.timestamp())
    p2 = int(end_date.timestamp())
    
    # Yahoo Chart API Endpoint
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    
    # Mimic a real browser to avoid 403 Forbidden errors
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    params = {
        "period1": p1,
        "period2": p2,
        "interval": "1d",
        "includePrePost": "false"
    }
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # Parse JSON structure
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quotes = result['indicators']['quote'][0]['close']
        
        # Create Pandas Series
        dates = [datetime.fromtimestamp(ts) for ts in timestamps]
        series = pd.Series(quotes, index=dates, name=ticker)
        
        # Clean data (remove None/NaN)
        return series.dropna()
        
    except Exception as e:
        print(f"!! Error fetching {ticker}: {e}")
        return pd.Series(dtype=float)

# ────────────────────────────────────────────────
# 2. Logic: SMA Trigger -> Raw Price Annotation
# ────────────────────────────────────────────────
def find_sma_reversals(df, raw_col, sma_col, threshold=SMA_REVERSAL_THRESHOLD):
    """
    Analyzes the SMA column to find peaks/troughs.
    When one is found, looks up the RAW PRICE for that date.
    """
    # Work only with valid SMA data
    valid_data = df[[raw_col, sma_col]].dropna()
    
    if valid_data.empty: 
        return []

    reversals = []
    
    # State tracking
    last_sma_val = valid_data[sma_col].iloc[0]
    last_date = valid_data.index[0]
    trend = 0 # 0: Unknown, 1: Up, -1: Down
    
    for date, row in valid_data.iterrows():
        curr_sma = row[sma_col]
        
        # Establish initial trend
        if trend == 0:
            if curr_sma >= last_sma_val * (1 + threshold):
                trend = 1
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma <= last_sma_val * (1 - threshold):
                trend = -1
                last_sma_val = curr_sma
                last_date = date
        
        # Uptrend Logic
        elif trend == 1:
            if curr_sma > last_sma_val:
                # SMA still going up, update peak tracker
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma < last_sma_val * (1 - threshold):
                # SMA has dropped enough to confirm previous date was the peak
                # CAPTURE THE RAW PRICE AT THAT PEAK DATE
                raw_price = df.loc[last_date, raw_col]
                reversals.append((last_date, raw_price, 'peak'))
                
                trend = -1
                last_sma_val = curr_sma
                last_date = date
                
        # Downtrend Logic
        elif trend == -1:
            if curr_sma < last_sma_val:
                # SMA still going down, update trough tracker
                last_sma_val = curr_sma
                last_date = date
            elif curr_sma > last_sma_val * (1 + threshold):
                # SMA has risen enough to confirm previous date was the trough
                # CAPTURE THE RAW PRICE AT THAT TROUGH DATE
                raw_price = df.loc[last_date, raw_col]
                reversals.append((last_date, raw_price, 'trough'))
                
                trend = 1
                last_sma_val = curr_sma
                last_date = date
                
    return reversals

# ────────────────────────────────────────────────
# 3. Main Processing & Plotting
# ────────────────────────────────────────────────
def run_analysis(period_name, days_count):
    print(f"\n--- Analyzing {period_name} ---")
    
    # A. Gather Data
    data_frames = []
    for name, symbol in TICKERS.items():
        print(f"Requesting {name} ({symbol})...")
        s = fetch_yahoo_data(symbol, days_count)
        if s.empty:
            print(f"Skipping due to missing data for {name}")
            return None
        s.name = name
        data_frames.append(s)
    
    # Align dates (only days where all markets have data)
    df = pd.concat(data_frames, axis=1).dropna()
    
    # Filter to requested period (trim buffer)
    cutoff_date = datetime.now() - timedelta(days=days_count)
    df = df[df.index >= cutoff_date]
    
    if df.empty:
        print("No overlapping data found.")
        return None

    # B. Calculate Indicators
    df['Ratio'] = df['Gold'] / df['Silver']
    
    # Calculate SMAs
    for col in ['Gold', 'Silver', 'DXY', 'Ratio']:
        df[f'{col}_SMA'] = df[col].rolling(window=SMA_PERIOD).mean()

    # C. Plotting
    print("Generating Chart...")
    plt.style.use('bmh')
    fig, (ax1, ax_d) = plt.subplots(2, 1, figsize=(15, 14), gridspec_kw={'height_ratios': [2.5, 1]})
    plt.subplots_adjust(left=0.1, right=0.85, hspace=0.3)

    # Secondary Y-Axes
    ax_s = ax1.twinx()
    ax_s.spines['right'].set_position(('outward', 60))
    ax_r = ax1.twinx()

    configs = [
        (ax1, 'Gold', '#D4AF37'), 
        (ax_s, 'Silver', '#708090'),
        (ax_r, 'Ratio', 'purple'),
        (ax_d, 'DXY', 'blue')
    ]

    for ax, name, color in configs:
        # 1. Plot Raw Price (Faint)
        ax.plot(df.index, df[name], color=color, alpha=0.3, linewidth=1)
        
        # 2. Plot SMA (Solid)
        ax.plot(df.index, df[f'{name}_SMA'], color=color, linestyle='-', linewidth=2, label=f"{name} SMA")
        
        # 3. Annotations based on SMA Reversals
        reversals = find_sma_reversals(df, name, f'{name}_SMA')
        
        for r_date, r_raw_price, r_type in reversals:
            if r_type == 'peak':
                marker = 'v'
                offset = (0, 15)
                va = 'bottom'
            else:
                marker = '^'
                offset = (0, -20)
                va = 'top'
                
            # Dot on the Raw Price
            ax.scatter(r_date, r_raw_price, color=color, marker=marker, s=80, edgecolors='black', zorder=10)
            
            # Text Label of the Raw Price
            ax.annotate(f"{r_raw_price:.2f}", 
                        xy=(r_date, r_raw_price), 
                        xytext=offset, 
                        textcoords='offset points', 
                        ha='center', va=va,
                        fontsize=9, fontweight='bold', color='black',
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85, ec=color))

        # Current Price Tag
        last_val = df[name].iloc[-1]
        ax.annotate(f"{last_val:.2f}", xy=(df.index[-1], last_val), xytext=(5, 0), 
                    textcoords='offset points', color=color, fontweight='bold')

        ax.set_ylabel(name, color=color, fontweight='bold')
        ax.tick_params(axis='y', colors=color)

    # D. Correlation Box
    corr = df['Gold'].corr(df['DXY'])
    c_color = 'green' if corr > 0.2 else 'red' if corr < -0.2 else 'black'
    status = "Inversion" if corr < -0.2 else "Positive" if corr > 0.2 else "Decoupled"
    
    ax_d.text(0.02, 0.9, f"Gold/DXY Corr: {corr:.2f} ({status})", transform=ax_d.transAxes,
              bbox=dict(facecolor='white', edgecolor=c_color, alpha=0.9), 
              color=c_color, fontweight='bold')

    # Rolling Correlation
    rolling = df['Gold'].rolling(30).corr(df['DXY'])
    ax_rc = ax_d.twinx()
    ax_rc.plot(df.index, rolling, color='red', alpha=0.25, linestyle='--')
    ax_rc.axhline(0, color='black', alpha=0.3)
    ax_rc.set_ylim(-1.1, 1.1)
    ax_rc.set_ylabel("30D Rolling Corr", color='red')

    # Formatting
    ax1.set_title(f"Market Analysis ({period_name}) - SMA Direction Changes", fontsize=16)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

    # Save
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"Market_Requests_{period_name}_{timestamp}.jpg"
    path = os.path.join(SAVE_DIR, filename)
    plt.savefig(path, format='jpg', dpi=100, bbox_inches='tight')
    plt.close()
    return path

if __name__ == "__main__":
    if not os.access(SAVE_DIR, os.W_OK):
        print(f"!! Error: Cannot write to {SAVE_DIR}. Run 'termux-setup-storage'")
    else:
        for p_name, p_days in WINDOWS.items():
            saved_file = run_analysis(p_name, p_days)
            if saved_file:
                print(f"Saved: {saved_file}")
                # Try opening on Android
                try:
                    subprocess.run(["termux-open", saved_file])
                except:
                    pass
                time.sleep(1)