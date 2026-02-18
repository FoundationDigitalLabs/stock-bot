import pandas as pd
import numpy as np
import vectorbt as vbt
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time

# Load credentials
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY:
    print("Error: Alpaca API Key missing in .env")
    exit(1)

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_sp500_tickers():
    """Reads the S&P 500 list from the local CSV."""
    try:
        with open("stock-bot/data/sp500_tickers.csv", "r") as f:
            tickers = [line.strip() for line in f.readlines() if line.strip()]
        return tickers
    except Exception as e:
        print(f"Error reading local S&P 500 list: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "NFLX", "JPM"]

def screen_stocks(tickers, limit=None):
    if limit:
        tickers = tickers[:limit]
    
    results = []
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=300)

    print(f"--- Scanning {len(tickers)} stocks for Alpha Signals ---")

    # Batch symbols to avoid too many small API calls (Alpaca handles batches well)
    # We'll do batches of 50
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}...")
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
                adjustment='all'
            )
            
            bars_response = client.get_stock_bars(request_params)
            bars_df = bars_response.df
            
            if bars_df.empty:
                continue

            for symbol in batch:
                if symbol not in bars_df.index.get_level_values(0):
                    continue
                
                df = bars_df.xs(symbol)
                
                if len(df) < 20: continue
                
                close = df['close']
                volume = df['volume']

                # 1. Trend Filter (Price > 200 SMA)
                sma200 = vbt.MA.run(close, window=200).ma.iloc[-1]
                price = close.iloc[-1]
                in_uptrend = price > sma200 if not np.isnan(sma200) else False

                # 2. Volume Breakout (RVOL)
                avg_vol = volume.rolling(20).mean().iloc[-1]
                current_vol = volume.iloc[-1]
                rvol = current_vol / avg_vol if avg_vol > 0 else 0

                # 3. RSI (Dip Detection)
                rsi = vbt.RSI.run(close, window=14).rsi.iloc[-1]

                # 4. Momentum / Strength
                perf_5d = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) > 5 else 0

                # Scoring Logic
                score = 0
                signals = []

                if in_uptrend:
                    score += 2
                    signals.append("Uptrend")
                
                if rsi < 35:
                    score += 3
                    signals.append("Dip")
                elif rsi < 45:
                    score += 1
                    signals.append("Pullback")
                elif rsi > 75:
                    score -= 2
                    signals.append("Overbought")

                if rvol > 2.0:
                    score += 3
                    signals.append("Vol Spike!")
                elif rvol > 1.5:
                    score += 1
                    signals.append("High Vol")

                if score >= 3: # Only keep interesting setups
                    results.append({
                        "Ticker": symbol,
                        "Price": f"${price:.2f}",
                        "Score": score,
                        "RSI": round(rsi, 1),
                        "RVOL": round(rvol, 2),
                        "5D %": f"{perf_5d:.2%}",
                        "Signals": ", ".join(signals)
                    })
        
        except Exception as e:
            print(f"Error in batch: {e}")
        
        time.sleep(0.5) # Avoid rate limiting

    report = pd.DataFrame(results)
    if not report.empty:
        return report.sort_values(by="Score", ascending=False)
    return report

if __name__ == "__main__":
    sp500 = get_sp500_tickers()
    # Let's run the full S&P 500
    df_results = screen_stocks(sp500)
    
    print("\n" + "="*90)
    print(f"S&P 500 ALPHA SCREENER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*90)
    
    if not df_results.empty:
        # Show top 25 results
        print(df_results.head(25).to_markdown(index=False))
    else:
        print("No high-signal setups found today.")
    print("="*90)
