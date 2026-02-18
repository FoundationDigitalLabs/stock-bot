import os
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
from indicators import calculate_alphatrend

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def plot_alphatrend(ticker="MSFT"):
    print(f"Fetching data for {ticker}...")
    start_date = datetime.now() - timedelta(days=120)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start_date,
        adjustment='all'
    )
    bars = client.get_stock_bars(request_params).df
    df = bars.xs(ticker).copy()
    df.columns = [col.capitalize() for col in df.columns]
    
    print(f"Calculating AlphaTrend for {ticker}...")
    df = calculate_alphatrend(df)
    
    # Plotting
    plt.figure(figsize=(12, 8))
    plt.title(f"{ticker} - AlphaTrend Indicator (Last 120 Days)")
    
    # Price
    plt.plot(df.index, df['Close'], label='Price', color='black', alpha=0.3)
    
    # AlphaTrend Lines
    plt.plot(df.index, df['at_k1'], label='AlphaTrend (K1)', color='blue', linewidth=2)
    plt.plot(df.index, df['at_k2'], label='Signal (K2 - 2D Offset)', color='red', linestyle='--', linewidth=1.5)
    
    # Fill between for visual trend
    plt.fill_between(df.index, df['at_k1'], df['at_k2'], where=(df['at_k1'] >= df['at_k2']), 
                     color='green', alpha=0.2, label='Bullish Trend')
    plt.fill_between(df.index, df['at_k1'], df['at_k2'], where=(df['at_k1'] < df['at_k2']), 
                     color='red', alpha=0.2, label='Bearish Trend')

    # Mark Buy/Sell signals
    buys = df[df['at_buy']]
    sells = df[df['at_sell']]
    
    plt.scatter(buys.index, buys['Close'], marker='^', color='green', s=100, label='BUY Signal', zorder=5)
    plt.scatter(sells.index, sells['Close'], marker='v', color='red', s=100, label='SELL Signal', zorder=5)

    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_path = f"stock-bot/plots/{ticker}_alphatrend.png"
    os.makedirs("stock-bot/plots", exist_ok=True)
    plt.savefig(output_path)
    plt.close()
    
    return output_path

if __name__ == "__main__":
    # Generate for MSFT as a prime example of a recent trend change
    path = plot_alphatrend("MSFT")
    print(f"Plot saved to {path}")
