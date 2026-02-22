import requests
import numpy as np
import matplotlib
# Force headless backend for Termux to prevent crashes
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime, timedelta
import subprocess
import time

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {'Gold': 'GC=F', 'Silver': 'SI=F', 'DXY': 'DX-Y.NYB'}
# check if running on Android/Termux or PC
if os.path.exists("/sdcard/Download"):
    SAVE_DIR = "/sdcard/Download"
else:
    SAVE_DIR = os.getcwd() # Fallback for PC

THRESHOLD = 1/100 # threshold percentage
SMA = 20
WINDOWS = {"6mo": 180, "1yr": 365, "5yr": 1825}

def get_data(ticker, days):
    """Fetches data from Yahoo Finance with error handling."""
    end = datetime.now()
    start = end - timedelta(days=days + 150) # Buffer for SMA
    
    # Using specific user-agent to avoid Yahoo 403 Forbidden errors
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    interval = "1d" if days < 1000 else "1wk"
    params = {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": interval}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        
        if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
            print(f"!! No data found for {ticker}")
            return {}

        res = data['chart']['result'][0]
        timestamps = res.get('timestamp', [])
        quotes = res['indicators']['quote'][0].get('close', [])
        
        if not timestamps or not quotes:
            return {}

        # Dictionary comprehension to map Date -> Price
        return {datetime.fromtimestamp(ts).strftime('%Y-%m-%d'): c 
                for ts, c in zip(timestamps, quotes) if c is not None}
                
    except Exception as e:
        print(f"!! Error fetching {ticker}: {e}")
        return {}

def calculate_sma(data, window=SMA):
    """Calculates Simple Moving Average."""
    if not data: return []
    ret = np.cumsum(data, dtype=float)
    ret[window:] = ret[window:] - ret[:-window]
    return list(ret[window - 1:] / window)

def find_significant_reversals(data_list, threshold=THRESHOLD):
    """Identifies peaks and troughs for annotation."""
    reversals = []
    if not data_list: return reversals
    
    last_extreme_val = data_list[0]
    trend = 0 # 0: undefined, 1: up, -1: down
    
    for i in range(1, len(data_list)):
        price = data_list[i]
        pct_change = (price - last_extreme_val) / last_extreme_val
        
        if trend <= 0 and pct_change >= threshold:
            reversals.append((i, 'trough'))
            last_extreme_val = price
            trend = 1
        elif trend >= 0 and pct_change <= -threshold:
            reversals.append((i, 'peak'))
            last_extreme_val = price
            trend = -1
        elif (trend == 1 and price > last_extreme_val) or (trend == -1 and price < last_extreme_val):
            last_extreme_val = price
            
    return reversals

def plot_market(period_name, days_count):
    print(f"Generating {period_name} analysis...")
    
    # Fetch Data
    hist = {}
    for name, symbol in TICKERS.items():
        data = get_data(symbol, days_count)
        if not data:
            print(f"Skipping {period_name} due to missing data for {name}")
            return None
        hist[name] = data

    # Find Intersection of Dates (only trade days where all 3 markets were open)
    common_dates = sorted(set(hist['Gold'].keys()) & set(hist['Silver'].keys()) & set(hist['DXY'].keys()))
    
    # Trim to requested days
    common_dates = common_dates[-days_count:]
    if not common_dates:
        print("No overlapping dates found.")
        return None

    # Prepare Lists
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in common_dates]
    g = [hist['Gold'][d] for d in common_dates]
    s = [hist['Silver'][d] for d in common_dates]
    dxy = [hist['DXY'][d] for d in common_dates]
    ratio = [gv/sv for gv, sv in zip(g, s)]
    
    # Calculate SMAs
    win = 20 if days_count < 1000 else 10
    
    # Helper to pad SMA to match Date length (since SMA is shorter by window size)
    def get_padded_sma(raw_data, window):
        sma_vals = calculate_sma(raw_data, window)
        # Pad the beginning with NaNs so plotting aligns with dates
        return [np.nan]*(window-1) + sma_vals

    smas = { 
        'g': get_padded_sma(g, win), 
        's': get_padded_sma(s, win), 
        'r': get_padded_sma(ratio, win), 
        'd': get_padded_sma(dxy, win) 
    }

    # Plot Setup
    plt.style.use('seaborn-v0_8-darkgrid' if 'seaborn-v0_8-darkgrid' in plt.style.available else 'bmh')
    fig, (ax1, ax_d) = plt.subplots(2, 1, figsize=(15, 14), gridspec_kw={'height_ratios': [2.5, 1]})
    plt.subplots_adjust(left=0.15, right=0.85, hspace=0.3)

    # Secondary Axes
    ax_s = ax1.twinx() # Silver (Right)
    ax_s.spines['right'].set_position(('outward', 60)) # Move Silver axis out a bit
    
    ax_r = ax1.twinx() # Ratio (Right default)

    # Plot Configs
    # (Axis, RawData, SMA, Color, Label)
    configs = [
        (ax1, g, smas['g'], '#D4AF37', 'Gold ($)'), 
        (ax_s, s, smas['s'], '#708090', 'Silver ($)'),
        (ax_r, ratio, smas['r'], 'purple', 'Gold/Silver Ratio'), 
        (ax_d, dxy, smas['d'], 'blue', 'DXY Index')
    ]

    for ax, raw, sma, col, label in configs:
        ax.plot(dates, raw, color=col, alpha=0.3, linewidth=1)
        ax.plot(dates, sma, color=col, linestyle='-', linewidth=2, label=label)
        
        # Current Price Annotation
        ax.annotate(f"{raw[-1]:.2f}", xy=(dates[-1], raw[-1]), xytext=(5, 0), 
                    textcoords='offset points', color=col, fontweight='bold', fontsize=9)
        
        # Reversals on SMA
        # Filter None/NaN from SMA for calculation
        clean_sma = [x for x in sma if not np.isnan(x)]
        offset_idx = len(sma) - len(clean_sma)
        
        if len(clean_sma) > 0:
            for idx, kind in find_significant_reversals(clean_sma):
                real_idx = idx + offset_idx
                marker, offset = ('^', 10) if kind == 'trough' else ('v', -15)
                ax.scatter(dates[real_idx], sma[real_idx], color=col, marker=marker, s=80, edgecolors='white', zorder=5)

        ax.set_ylabel(label, color=col, fontweight='bold')
        ax.tick_params(axis='y', colors=col)

    # --- CORRELATION LOGIC ---
    try:
        corr = np.corrcoef(g, dxy)[0, 1]
    except:
        corr = 0
        
    is_strong = abs(corr) > 0.7
    font_weight = 'bold' if is_strong else 'normal'
    
    if corr < -0.2:
        box_color, status = 'red', "Inversion"
    elif corr > 0.2:
        box_color, status = 'green', "Positive"
    else:
        box_color, status = 'black', "Decoupled"

    box_text = f"Gold/DXY Correlation: {corr:.2f}\n({status})"
    ax_d.text(0.02, 0.9, box_text, transform=ax_d.transAxes, 
              bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'), fontsize=10, 
              color=box_color, fontweight=font_weight)

    # --- ROLLING CORRELATION ---
    roll_win = 30
    rolling_corr = []
    for i in range(len(g)):
        if i < roll_win:
            rolling_corr.append(np.nan)
        else:
            segment_g = g[i-roll_win:i]
            segment_d = dxy[i-roll_win:i]
            rolling_corr.append(np.corrcoef(segment_g, segment_d)[0, 1])

    ax_rc = ax_d.twinx()
    ax_rc.plot(dates, rolling_corr, color='red', alpha=0.3, linestyle='--', linewidth=1)
    ax_rc.axhline(0, color='black', alpha=0.2, linewidth=0.8)
    ax_rc.set_ylim(-1.1, 1.1)
    ax_rc.set_ylabel("30D Rolling Corr", color='red', fontsize=8)
    ax_rc.tick_params(axis='y', colors='red', labelsize=8)

    # Titles and Formatting
    ax1.set_title(f"Precious Metals vs Dollar ({period_name.upper()})", fontsize=16, pad=20)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y' if days_count < 500 else '%Y'))
    
    filename = f"Market_{period_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.jpg"
    path = os.path.join(SAVE_DIR, filename)
    plt.savefig(path, format='jpg', dpi=150, bbox_inches='tight')
    plt.close()
    return path

if __name__ == "__main__":
    # Ensure storage permissions
    if not os.access(SAVE_DIR, os.W_OK):
        print(f"!! Error: Cannot write to {SAVE_DIR}.")
        print("!! Run 'termux-setup-storage' in terminal and grant permissions.")
    else:
        paths = []
        for name, days in WINDOWS.items():
            p = plot_market(name, days)
            if p: paths.append(p)

        print(f"Saved {len(paths)} reports to {SAVE_DIR}.")
        
        # Open files
        for p in paths:
            if os.path.exists(p):
                print(f"Opening: {os.path.basename(p)}")
                try:
                    subprocess.run(["termux-open", p])
                except FileNotFoundError:
                    print("termux-open command not found (are you on PC?)")
            time.sleep(1)