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
from rsi_alpha import find_bullish_divergence
from trend_alpha import calculate_trend_quality

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY:
    print("Error: Alpaca API Key missing in .env")
    exit(1)

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_expanded_tickers():
    """Reads the full universe from the expanded watchlist."""
    try:
        with open("stock-bot/data/watchlist_expanded.csv", "r") as f:
            tickers = [line.strip() for line in f.readlines() if line.strip()]
        return tickers
    except Exception as e:
        print(f"Error reading expanded watchlist: {e}")
        return []

def screen_weekly_candidates(tickers):
    results = []
    end_dt = datetime.now()
    # Need 200+ days for SMA 200
    start_dt = end_dt - timedelta(days=365)

    print(f"--- Weekly Alpha Scan: {len(tickers)} tickers ---")

    batch_size = 100 # Alpaca handles 100 well
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        print(f"Scanning batch {i//batch_size + 1}/{len(tickers)//batch_size + 1}...")
        
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
                
                df = bars_df.xs(symbol).copy()
                df.columns = [col.capitalize() for col in df.columns]
                if len(df) < 200: continue
                
                close = df['Close']
                price = close.iloc[-1]
                
                # 1. Primary Filter: Macro Uptrend (SMA 200)
                sma200 = vbt.MA.run(close, window=200).ma.iloc[-1]
                if price <= sma200: continue

                # 2. Secondary Filter: Not excessively overbought on weekly/daily scale
                rsi_series = vbt.RSI.run(close, window=14).rsi
                rsi = rsi_series.iloc[-1]
                if rsi > 75: continue # Skip the blow-off tops

                # 3. Liquidity Filter: Average daily volume > 500k
                avg_vol = df['Volume'].tail(20).mean()
                if avg_vol < 500000: continue

                # 4. Momentum Score
                perf_1m = (close.iloc[-1] / close.iloc[-21] - 1) if len(close) > 21 else 0
                
                # 5. Bullish Divergence Detection
                has_divergence = find_bullish_divergence(close, rsi_series)
                
                # 6. Trend Quality Metrics
                t_score, t_signals, adx, r2, slope = calculate_trend_quality(df)
                
                results.append({
                    "Ticker": symbol,
                    "Price": round(price, 2),
                    "SMA200": round(sma200, 2),
                    "RSI": round(rsi, 1),
                    "Perf_1M": round(perf_1m * 100, 2),
                    "Divergence": has_divergence,
                    "Trend_Score": t_score,
                    "ADX": round(adx, 1) if adx else 0,
                    "R2": round(r2, 2) if r2 else 0
                })
        
        except Exception as e:
            print(f"Error in batch: {e}")
        
        time.sleep(0.3) # Gentle pacing

    report = pd.DataFrame(results)
    if not report.empty:
        # Primary Sort: Divergence (Elite Reversals)
        # Secondary Sort: Trend Score (High Quality Runners)
        # Tertiary Sort: Momentum
        return report.sort_values(
            by=["Divergence", "Trend_Score", "Perf_1M"], 
            ascending=[False, False, False]
        )
    return report

if __name__ == "__main__":
    universe = get_expanded_tickers()
    candidates = screen_weekly_candidates(universe)
    
    if not candidates.empty:
        # Take the top 100 most promising candidates for the week
        top_candidates = candidates.head(100)
        output_path = "stock-bot/data/weekly_candidates.csv"
        top_candidates['Ticker'].to_csv(output_path, index=False, header=False)
        
        print("\n" + "="*50)
        print(f"WEEKLY SCAN COMPLETE: {len(candidates)} total passed filters.")
        print(f"TOP 100 CANDIDATES SAVED TO: {output_path}")
        print("="*50)
        print(top_candidates.head(20).to_markdown(index=False))
    else:
        print("No candidates met the criteria this week.")
