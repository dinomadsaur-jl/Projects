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
TICKERS = {
    'VIX': '^VIX',
    'DXY': 'DX-Y.NYB',
    'Gold': 'GC=F',
    'Silver': 'SI=F'
}

HEADERS = {"User-Agent": "Mozilla/5.0"}
HISTORY_DAYS = 180 
SMA_WINDOW = 20  # 20-day trend line

SAVE_DIR = "/sdcard/Download" 
PLOT_FILENAME = f"market_trends_{datetime.now().strftime('%Y%m%d_%H%M')}.jpg"

def get_historical_closes(ticker, days=HISTORY_DAYS):
    end = datetime.now()
    start = end - timedelta(days=days + 60) # Extra buffer for SMA calculation
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": "1d"}
    
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        result = r.json()['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        return {datetime.fromtimestamp(ts).strftime('%Y-%m-%d'): c for ts, c in zip(timestamps, closes) if c is not None}
    except:
        return {}

def calculate_sma(data, window):
    return [np.mean(data[max(0, i-window+1):i+1]) for i in range(len(data))]

def main():
    print(f"Syncing Market Data...")
    history = {name: get_historical_closes(ticker) for name, ticker in TICKERS.items()}

    common_dates = sorted(set(history['Gold'].keys()) & set(history['Silver'].keys()) & set(history['DXY'].keys()))
    # Trim to requested HISTORY_DAYS
    common_dates = common_dates[-HISTORY_DAYS:]
    
    date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in common_dates]
    g_pts = [history['Gold'][d] for d in common_dates]
    s_pts = [history['Silver'][d] for d in common_dates]
    dxy_pts = [history['DXY'][d] for d in common_dates]
    ratios = [g/s for g, s in zip(g_pts, s_pts)]

    # Calculate Trends (20-day SMA)
    g_sma = calculate_sma(g_pts, SMA_WINDOW)
    s_sma = calculate_sma(s_pts, SMA_WINDOW)
    dxy_sma = calculate_sma(dxy_pts, SMA_WINDOW)
    ratio_sma = calculate_sma(ratios, SMA_WINDOW)

    print(f"\nLatest Gold: ${g_pts[-1]} | Silver: ${s_pts[-1]} | DXY: {dxy_pts[-1]}")

    # ─── Plotting with 4 Independent Y-Axes ──────────────────
    fig, ax_gold = plt.subplots(figsize=(14, 8))
    plt.subplots_adjust(left=0.15, right=0.80) 

    # 1. Gold (Primary Left)
    ax_gold.plot(date_objs, g_pts, color='#D4AF37', alpha=0.3, label='Gold Price')
    ax_gold.plot(date_objs, g_sma, color='#D4AF37', linestyle=':', linewidth=2, label='Gold Trend')
    ax_gold.set_ylabel("Gold (USD)", color='#D4AF37', fontweight='bold')

    # 2. Silver (Secondary Left - Offset)
    ax_silver = ax_gold.twinx()
    ax_silver.spines['left'].set_position(('outward', 60))
    ax_silver.yaxis.set_label_position('left')
    ax_silver.yaxis.set_ticks_position('left')
    ax_silver.plot(date_objs, s_pts, color='#808080', alpha=0.3)
    ax_silver.plot(date_objs, s_sma, color='#808080', linestyle=':', linewidth=2)
    ax_silver.set_ylabel("Silver (USD)", color='#808080')

    # 3. GSR (Primary Right)
    ax_gsr = ax_gold.twinx()
    ax_gsr.plot(date_objs, ratios, color='purple', alpha=0.3)
    ax_gsr.plot(date_objs, ratio_sma, color='purple', linestyle=':', linewidth=2)
    ax_gsr.set_ylabel("G/S Ratio", color='purple')

    # 4. DXY (Secondary Right - Offset)
    ax_dxy = ax_gold.twinx()
    ax_dxy.spines['right'].set_position(('outward', 60))
    ax_dxy.plot(date_objs, dxy_pts, color='blue', alpha=0.3)
    ax_dxy.plot(date_objs, dxy_sma, color='blue', linestyle=':', linewidth=2)
    ax_dxy.set_ylabel("DXY Index", color='blue')

    plt.title(f"Market Trends & {SMA_WINDOW}-Day Moving Averages", fontsize=14, pad=20)
    ax_gold.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax_gold.grid(True, axis='x', alpha=0.2)
    fig.autofmt_xdate()

    # Save and Open
    save_path = os.path.join(SAVE_DIR, PLOT_FILENAME)
    plt.savefig(save_path, format='jpg', dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"File saved to: {save_path}")
    subprocess.run(["termux-open", save_path])

if __name__ == "__main__":
    main()
