from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import os

load_dotenv()

# Config
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
DATA_DIR = "stock-bot/data"

if not API_KEY or not SECRET_KEY:
    print("Error: API Keys missing.")
    exit(1)

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def fetch_data(symbol, timeframe=TimeFrame.Day, days_back=1500):
    print(f"Fetching {symbol}...")
    
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days_back)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=timeframe,
        start=start_dt,
        end=end_dt,
        adjustment='all' # Adjusted for splits and dividends
    )
    
    try:
        bars = client.get_stock_bars(request_params)
        df = bars.df
        
        # Reset index to get 'timestamp' as a column, then format
        df = df.reset_index()
        
        # Filter for the specific symbol (Alpaca returns MultiIndex sometimes)
        if 'symbol' in df.columns:
            df = df[df['symbol'] == symbol]
            
        # Clean up for VectorBT/Backtrader
        # Rename columns to standard lowercase
        df = df.rename(columns={
            "timestamp": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
            "trade_count": "Trades",
            "vwap": "VWAP"
        })
        
        # Set Date as index
        df.set_index("Date", inplace=True)
        
        # Save
        filename = f"{DATA_DIR}/{symbol}_{timeframe}.csv"
        df.to_csv(filename)
        print(f"Saved {len(df)} rows to {filename}")
        
    except Exception as e:
        print(f"Failed to fetch {symbol}: {e}")

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Universe: Major Indices + Liquid Tech + Volatility
    tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GLD", "TLT"]
    
    print("--- Starting Data Download (Alpaca) ---")
    for ticker in tickers:
        fetch_data(ticker, TimeFrame.Day, days_back=365*5) # 5 Years of Daily Data
        # fetch_data(ticker, TimeFrame.Hour, days_back=700) # Optional: Hourly data later
