import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime, timedelta
import subprocess

# ────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────
TICKERS = {'Gold': 'GC=F', 'Silver': 'SI=F', 'DXY': 'DX-Y.NYB'}
SAVE_DIR = "/sdcard/Download"
THRESHOLD = 0.02  # 2% Filter for significant reversals
WINDOWS = {"6mo": 180, "1yr": 365, "5yr": 1825}

def get_data(ticker, days):
    end = datetime.now()
    # Extra buffer for SMA and threshold calculations
    start = end - timedelta(days=days + 150)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    
    # Use weekly interval for 5yr to avoid overcrowding
    interval = "1d" if days < 1000 else "1wk"
    params = {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": interval}
    
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res = r.json()['chart']['result'][0]
        return {datetime.fromtimestamp(ts).strftime('%Y-%m-%d'): c 
                for ts, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']) if c is not None}
    except: return {}

def calculate_sma(data, window=20):
    """Smooths out noise to reveal underlying trends."""
    return [np.mean(data[max(0, i-window+1):i+1]) for i in range(len(data))]

def find_significant_reversals(data_list, threshold=THRESHOLD):
    """Detects peaks/troughs only if change exceeds the % threshold."""
    reversals = []
    if not data_list: return reversals
    
    last_extreme_val = data_list[0]
    trend = 0 # 1 for up, -1 for down
    
    for i in range(1, len(data_list)):
        price = data_list[i]
        pct_change = (price - last_extreme_val) / last_extreme_val
        
        if trend <= 0 and pct_change >= threshold: # Confirm Uptrend
            reversals.append((i, 'trough'))
            last_extreme_val = price
            trend = 1
        elif trend >= 0 and pct_change <= -threshold: # Confirm Downtrend
            reversals.append((i, 'peak'))
            last_extreme_val = price
            trend = -1
        elif (trend == 1 and price > last_extreme_val) or (trend == -1 and price < last_extreme_val):
            last_extreme_val = price
            
    return reversals

def plot_market(period_name, days_count):
    print(f"Analyzing {period_name}...")
    hist = {name: get_data(symbol, days_count) for name, symbol in TICKERS.items()}
    common_dates = sorted(set(hist['Gold'].keys()) & set(hist['Silver'].keys()) & set(hist['DXY'].keys()))
    common_dates = common_dates[-days_count:]
    
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in common_dates]
    g, s, dxy = [[hist[n][d] for d in common_dates] for n in ['Gold', 'Silver', 'DXY']]
    ratio = [gv/sv for gv, sv in zip(g, s)]
    
    win = 20 if days_count < 1000 else 10 # SMA window adjustment
    smas = { 'g': calculate_sma(g, win), 's': calculate_sma(s, win), 
             'r': calculate_sma(ratio, win), 'd': calculate_sma(dxy, win) }

    # Top plot for Metals/GSR, Bottom for DXY
    fig, (ax1, ax_d) = plt.subplots(2, 1, figsize=(15, 13), gridspec_kw={'height_ratios': [2.5, 1]})
    plt.subplots_adjust(left=0.15, right=0.85, hspace=0.3)

    # Secondary scales for Top Plot
    ax_s = ax1.twinx()
    ax_s.spines['left'].set_position(('outward', 70))
    ax_s.yaxis.set_label_position('left')
    ax_s.yaxis.set_ticks_position('left')
    ax_r = ax1.twinx()

    plots = [(ax1, smas['g'], '#D4AF37', 'Gold'), (ax_s, smas['s'], '#808080', 'Silver'),
             (ax_r, smas['r'], 'purple', 'Ratio'), (ax_d, smas['d'], 'blue', 'DXY')]

    for ax, data, col, label in plots:
        ax.plot(dates, data, color=col, linestyle=':', linewidth=2.5, label=label, alpha=0.8)
        # Mark reversal points
        revs = find_significant_reversals(data)
        for idx, kind in revs:
            marker, offset = ('^', 12) if kind == 'trough' else ('v', -18)
            ax.scatter(dates[idx], data[idx], color=col, marker=marker, s=120, edgecolors='black', zorder=5)
            ax.annotate(f"{data[idx]:.1f}", (dates[idx], data[idx]), textcoords="offset points", 
                        xytext=(0, offset), ha='center', fontsize=9, color=col, fontweight='bold')
        ax.set_ylabel(label, color=col, fontweight='bold')

    # Correlation Inversion Label
    corr = np.corrcoef(g, dxy)[0, 1]
    inversion_box = f"Au/DXY Correlation: {corr:.2f}\n(Negative = Strong Inversion)"
    ax_d.text(0.02, 0.9, inversion_box, transform=ax_d.transAxes, 
              bbox=dict(facecolor='white', alpha=0.8), fontsize=10, color='red' if corr < 0 else 'black')

    ax1.set_title(f"Market Analysis ({period_name.upper()}) - {datetime.now().strftime('%Y-%m-%d')}", fontsize=16, pad=20)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y' if days_count < 500 else '%Y'))
    
    # Save with current date in filename
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
    filename = f"Market_{period_name}_{timestamp}.jpg"
    path = os.path.join(SAVE_DIR, filename)
    plt.savefig(path, format='jpg', dpi=180, bbox_inches='tight') #
    plt.close()
    return path

if __name__ == "__main__":
    paths = [plot_market(name, days) for name, days in WINDOWS.items()]
    print(f"\nSaved 3 reports to {SAVE_DIR}. Filenames include today's date.")
    # Auto-open the 6-month view
    subprocess.run(["termux-open", paths[0]])
