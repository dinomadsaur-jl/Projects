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
THRESHOLD = 0.02
WINDOWS = {"6mo": 180, "1yr": 365, "5yr": 1825}

def get_data(ticker, days):
    end = datetime.now()
    start = end - timedelta(days=days + 150)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    interval = "1d" if days < 1000 else "1wk"
    params = {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": interval}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        res = r.json()['chart']['result'][0]
        return {datetime.fromtimestamp(ts).strftime('%Y-%m-%d'): c 
                for ts, c in zip(res['timestamp'], res['indicators']['quote'][0]['close']) if c is not None}
    except: return {}

def calculate_sma(data, window=20):
    return [np.mean(data[max(0, i-window+1):i+1]) for i in range(len(data))]

def find_significant_reversals(data_list, threshold=THRESHOLD):
    reversals = []
    if not data_list: return reversals
    last_extreme_val, trend = data_list[0], 0
    for i in range(1, len(data_list)):
        price = data_list[i]
        pct_change = (price - last_extreme_val) / last_extreme_val
        if trend <= 0 and pct_change >= threshold:
            reversals.append((i, 'trough'))
            last_extreme_val, trend = price, 1
        elif trend >= 0 and pct_change <= -threshold:
            reversals.append((i, 'peak'))
            last_extreme_val, trend = price, -1
        elif (trend == 1 and price > last_extreme_val) or (trend == -1 and price < last_extreme_val):
            last_extreme_val = price
    return reversals

def plot_market(period_name, days_count):
    print(f"Plotting {period_name} with original data & SMA...")
    hist = {name: get_data(symbol, days_count) for name, symbol in TICKERS.items()}
    common_dates = sorted(set(hist['Gold'].keys()) & set(hist['Silver'].keys()) & set(hist['DXY'].keys()))[-days_count:]
    
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in common_dates]
    g, s, dxy = [[hist[n][d] for d in common_dates] for n in ['Gold', 'Silver', 'DXY']]
    ratio = [gv/sv for gv, sv in zip(g, s)]
    
    win = 20 if days_count < 1000 else 10
    smas = { 'g': calculate_sma(g, win), 's': calculate_sma(s, win), 'r': calculate_sma(ratio, win), 'd': calculate_sma(dxy, win) }

    fig, (ax1, ax_d) = plt.subplots(2, 1, figsize=(15, 14), gridspec_kw={'height_ratios': [2.5, 1]})
    plt.subplots_adjust(left=0.15, right=0.85, hspace=0.3)

    ax_s = ax1.twinx()
    ax_s.spines['left'].set_position(('outward', 70))
    ax_s.yaxis.set_label_position('left')
    ax_s.yaxis.set_ticks_position('left')
    ax_r = ax1.twinx()

    # Data plotting structure: (Axis, Raw Data, SMA Data, Color, Label)
    plot_configs = [
        (ax1, g, smas['g'], '#D4AF37', 'Gold'),
        (ax_s, s, smas['s'], '#808080', 'Silver'),
        (ax_r, ratio, smas['r'], 'purple', 'Ratio'),
        (ax_d, dxy, smas['d'], 'blue', 'DXY Index')
    ]

    for ax, raw, sma, col, label in plot_configs:
        # Plot ORIGINAL data (thin/light)
        ax.plot(dates, raw, color=col, alpha=0.15, linewidth=1)
        # Plot SMA Trend (bold dotted)
        ax.plot(dates, sma, color=col, linestyle=':', linewidth=2.5, label=f"{label} Trend")
        
        # Annotate TODAY'S price at the end
        ax.annotate(f"Now: {raw[-1]:.2f}", xy=(dates[-1], raw[-1]), xytext=(8, 0), 
                    textcoords='offset points', color=col, fontweight='bold', fontsize=9)
        
        # Significant Reversal Markers
        revs = find_significant_reversals(sma)
        for idx, kind in revs:
            marker, offset = ('^', 12) if kind == 'trough' else ('v', -18)
            ax.scatter(dates[idx], sma[idx], color=col, marker=marker, s=100, edgecolors='black', zorder=5)

        ax.set_ylabel(label, color=col, fontweight='bold')

    ax1.set_title(f"Market Monitoring: {period_name.upper()} (SMA + Original Data)", fontsize=16, pad=20)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y' if days_count < 500 else '%Y'))
    
    filename = f"Market_Analysis_{period_name}_{datetime.now().strftime('%Y-%m-%d')}.jpg"
    path = os.path.join(SAVE_DIR, filename)
    plt.savefig(path, format='jpg', dpi=180, bbox_inches='tight')
    plt.close()
    return path

if __name__ == "__main__":
    paths = [plot_market(name, days) for name, days in WINDOWS.items()]
    print(f"Reports saved to {SAVE_DIR}.")
    subprocess.run(["termux-open", paths[0]])
