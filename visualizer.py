import matplotlib.pyplot as plt
import pandas as pd
import os
from datetime import datetime

def generate_trade_card(ticker, df, entry_price, stop_loss, take_profit, signals):
    """
    Generates a visual 'Trade Card' showing the entry setup.
    """
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Plot last 50 bars
    plot_df = df.tail(50)
    ax.plot(plot_df.index, plot_df['Close'], label='Price', color='white', linewidth=2)
    ax.plot(plot_df.index, plot_df['At_k1'], label='AlphaTrend K1', color='cyan', linestyle='--')
    
    # Entry Annotations
    ax.axhline(y=entry_price, color='yellow', linestyle=':', label=f'Entry: {entry_price}')
    ax.axhline(y=stop_loss, color='red', linestyle='-', label=f'Stop: {stop_loss}')
    ax.axhline(y=take_profit, color='lime', linestyle='-', label=f'Target: {take_profit}')
    
    plt.title(f"🚀 ALPHA ENTRY: {ticker} | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    plt.legend()
    plt.grid(alpha=0.2)
    
    # Save chart
    file_path = f"stock-bot/data/charts/{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.png"
    os.makedirs("stock-bot/data/charts", exist_ok=True)
    plt.savefig(file_path)
    plt.close()
    return file_path
