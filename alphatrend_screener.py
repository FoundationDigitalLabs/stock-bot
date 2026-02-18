import os
import pandas as pd
import numpy as np
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
from indicators import calculate_alphatrend
import time

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def get_sp500_tickers():
    try:
        with open("stock-bot/data/sp500_tickers.csv", "r") as f:
            tickers = [line.strip() for line in f.readlines() if line.strip()]
        # Alpaca often has issues with - tickers, . is usually better for their v2 API
        # but for the REST client, sometimes it needs to be specific.
        # Let's try replacing - back with . for standard Alpaca usage
        return [t.replace('-', '.') for t in tickers]
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]

def scan_alphatrend():
    tickers = get_sp500_tickers()
    results = []
    
    # We need enough data for ATR(14) and shifts
    start_date = datetime.now() - timedelta(days=60)
    
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}: {batch[0]} to {batch[-1]}...")
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start_date,
                adjustment='all'
            )
            bars = client.get_stock_bars(request_params).df
            
            # Print columns once to debug
            if i == 0:
                print(f"DEBUG - DataFrame columns: {bars.columns.tolist()}")

            for ticker in batch:
                try:
                    if ticker not in bars.index.get_level_values(0):
                        continue
                        
                    df_ticker = bars.xs(ticker).copy()
                    
                    # Standardize column names to Title Case for indicators.py
                    df_ticker.columns = [col.capitalize() for col in df_ticker.columns]
                    
                    if len(df_ticker) < 30: # Need enough for ATR/MFI
                        continue
                    
                    # Ensure columns exist
                    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
                    if not all(col in df_ticker.columns for col in required_cols):
                        print(f"Missing columns for {ticker}")
                        continue

                        df_at = None
                    df_at = calculate_alphatrend(df_ticker)
                    
                    if df_at is None or df_at.empty:
                        continue
                
                    last_row = df_at.iloc[-1]
                    prev_row = df_at.iloc[-2]
                    
                    # Check for recent signals (last 2 days)
                    is_buy = last_row['at_buy'] or prev_row['at_buy']
                    is_sell = last_row['at_sell'] or prev_row['at_sell']
                    
                    # Also capture trend state
                    trend = "Bullish" if last_row['at_k1'] > last_row['at_k2'] else "Bearish"
                    
                    if is_buy or is_sell:
                        results.append({
                            "Ticker": ticker,
                            "Price": round(last_row['Close'], 2),
                            "Signal": "BUY" if is_buy else "SELL",
                            "Trend": trend,
                            "MFI": round(last_row['mfi'], 1),
                            "RSI": round(last_row['rsi'], 1)
                        })
                except Exception as e:
                    print(f"Error processing {ticker}: {e}")
                    continue
        except Exception as e:
            print(f"Error in batch: {e}")
            time.sleep(1)

    return pd.DataFrame(results)

if __name__ == "__main__":
    print("Starting AlphaTrend S&P 500 Scan...")
    df_results = scan_alphatrend()
    
    if not df_results.empty:
        print("\n=== AlphaTrend Scan Results (Recent Signals) ===")
        print(df_results.sort_values(by="Signal").to_markdown(index=False))
        
        # Save results
        df_results.to_csv("stock-bot/data/alphatrend_signals.csv", index=False)
    else:
        print("No recent AlphaTrend signals found.")
