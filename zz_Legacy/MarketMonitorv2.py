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
TICKERS = {'VIX': '^VIX', 'DXY': 'DX-Y.NYB', 'Gold': 'GC=F', 'Silver': 'SI=F'}
HEADERS = {"User-Agent": "Mozilla/5.0"}
HISTORY_DAYS = 180 
SMA_WINDOW = 20  
SAVE_DIR = "/sdcard/Download" 
PLOT_FILENAME = f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.jpg"

def get_historical_closes(ticker, days=HISTORY_DAYS):
    end = datetime.now()
    start = end - timedelta(days=days + 60)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"period1": int(start.timestamp()), "period2": int(end.timestamp()), "interval": "1d"}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        result = r.json()['chart']['result'][0]
        timestamps = result['timestamp']
        closes = result['indicators']['quote'][0]['close']
        return {datetime.fromtimestamp(ts).strftime('%Y-%m-%d'): c for ts, c in zip(timestamps, closes) if c is not None}
    except: return {}

def calculate_sma(data, window):
    return [np.mean(data[max(0, i-window+1):i+1]) for i in range(len(data))]

def annotate_extremes(ax, x, y, color, label):
    # Annotate Last Price
    ax.annotate(f'{label}: {y[-1]:.2f}', xy=(x[-1], y[-1]), xytext=(5, 0), 
                textcoords='offset points', color=color, fontweight='bold', fontsize=9)

def main():
    print("Fetching Market Data & Calculating Inversions...")
    history = {name: get_historical_closes(ticker) for name, ticker in TICKERS.items()}
    common_dates = sorted(set(history['Gold'].keys()) & set(history['Silver'].keys()) & set(history['DXY'].keys()))
    common_dates = common_dates[-HISTORY_DAYS:]
    
    date_objs = [datetime.strptime(d, '%Y-%m-%d') for d in common_dates]
    g_pts = [history['Gold'][d] for d in common_dates]
    s_pts = [history['Silver'][d] for d in common_dates]
    dxy_pts = [history['DXY'][d] for d in common_dates]
    ratios = [g/s for g, s in zip(g_pts, s_pts)]

    # Trends
    g_sma, s_sma, dxy_sma, r_sma = [calculate_sma(x, SMA_WINDOW) for x in [g_pts, s_pts, dxy_pts, ratios]]

    # ─── Plotting ──────────────────────────────────────────
    fig, (ax_gold, ax_dxy) = plt.subplots(2, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [2.5, 1]})
    plt.subplots_adjust(left=0.15, right=0.85, hspace=0.3)

    # --- TOP PLOT: GOLD, SILVER, GSR ---
    # 1. Gold
    ax_gold.plot(date_objs, g_pts, color='#D4AF37', alpha=0.15)
    ax_gold.plot(date_objs, g_sma, color='#D4AF37', linestyle=':', linewidth=2, label='Gold')
    ax_gold.set_ylabel("Gold (USD)", color='#D4AF37', fontweight='bold')
    annotate_extremes(ax_gold, date_objs, g_sma, '#D4AF37', 'Au')

    # 2. Silver
    ax_silver = ax_gold.twinx()
    ax_silver.spines['left'].set_position(('outward', 65))
    ax_silver.yaxis.set_label_position('left')
    ax_silver.yaxis.set_ticks_position('left')
    ax_silver.plot(date_objs, s_pts, color='#808080', alpha=0.15)
    ax_silver.plot(date_objs, s_sma, color='#808080', linestyle=':', linewidth=2)
    ax_silver.set_ylabel("Silver (USD)", color='#808080')
    annotate_extremes(ax_silver, date_objs, s_sma, '#555555', 'Ag')

    # 3. GSR
    ax_gsr = ax_gold.twinx()
    ax_gsr.plot(date_objs, ratios, color='purple', alpha=0.15)
    ax_gsr.plot(date_objs, r_sma, color='purple', linestyle=':', linewidth=2)
    ax_gsr.set_ylabel("G/S Ratio", color='purple')
    annotate_extremes(ax_gsr, date_objs, r_sma, 'purple', 'Ratio')

    # --- BOTTOM PLOT: DXY ---
    ax_dxy.plot(date_objs, dxy_pts, color='blue', alpha=0.2)
    ax_dxy.plot(date_objs, dxy_sma, color='blue', linestyle=':', linewidth=2)
    ax_dxy.set_ylabel("DXY Index", color='blue', fontweight='bold')
    annotate_extremes(ax_dxy, date_objs, dxy_sma, 'blue', 'DXY')

    # --- Correlation Inversion Annotation ---
    corr = np.corrcoef(g_pts, dxy_pts)[0, 1]
    inversion_text = f"Au/DXY Correlation: {corr:.2f}\n(Negative = Strong Inversion)"
    ax_dxy.text(0.02, 0.9, inversion_text, transform=ax_dxy.transAxes, 
                bbox=dict(facecolor='white', alpha=0.8), fontsize=10, color='red' if corr < 0 else 'black')

    # General Formatting
    for ax in [ax_gold, ax_dxy]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.grid(True, linestyle=':', alpha=0.4)
    
    fig.autofmt_xdate()
    save_path = os.path.join(SAVE_DIR, PLOT_FILENAME)
    plt.savefig(save_path, format='jpg', dpi=200, bbox_inches='tight')
    plt.close()
    
    print(f"File saved to Downloads: {PLOT_FILENAME}")
    subprocess.run(["termux-open", save_path])

if __name__ == "__main__":
    main()
