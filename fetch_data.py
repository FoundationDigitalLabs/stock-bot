import pandas as pd
import yfinance as yf
from datetime import datetime

def download_ticker(ticker, start_date="2020-01-01", end_date=None):
    """Downloads daily data for a ticker and saves to CSV."""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"Downloading {ticker} from {start_date} to {end_date}...")
    data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    
    if data.empty:
        print(f"Error: No data found for {ticker}")
        return
    
    # Flatten MultiIndex columns if present (yfinance update quirk)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    filename = f"stock-bot/data/{ticker}.csv"
    data.to_csv(filename)
    print(f"Saved {len(data)} rows to {filename}")

if __name__ == "__main__":
    # Download a few major tickers for initial testing
    tickers = ["SPY", "QQQ", "AAPL", "MSFT", "TSLA", "AMD", "NVDA"]
    for t in tickers:
        download_ticker(t)
