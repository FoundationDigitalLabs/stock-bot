import pandas as pd
import numpy as np
import vectorbt as vbt
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load credentials
load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

if not API_KEY:
    print("Error: Alpaca API Key missing in .env")
    exit(1)

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

def get_sp500_lite():
    """Returns a subset of liquid leaders for the prototype scan."""
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AMD", "NFLX", "JPM", 
            "V", "UNH", "HD", "PG", "DIS", "ADBE", "CRM", "XOM", "COST", "AVGO"]

def screen_stocks(tickers):
    results = []
    
    # Time window for technicals (6 months is enough for 200 SMA)
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=300)

    print(f"--- Scanning {len(tickers)} stocks for Alpha Signals ---")

    for symbol in tickers:
        try:
            # Fetch Data
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=TimeFrame.Day,
                start=start_dt,
                end=end_dt,
                adjustment='all'
            )
            bars = client.get_stock_bars(request_params).df
            if bars.empty: continue
            
            # Clean dataframe
            df = bars.reset_index()
            if 'symbol' in df.columns:
                df = df[df['symbol'] == symbol]
            df.set_index('timestamp', inplace=True)
            
            close = df['close']
            volume = df['volume']

            # 1. Trend Filter (Price > 200 SMA)
            sma200 = vbt.MA.run(close, window=200).ma.iloc[-1]
            price = close.iloc[-1]
            in_uptrend = price > sma200

            # 2. Relative Volume (RVOL) - Current vol vs 20-day avg
            avg_vol = volume.rolling(20).mean().iloc[-1]
            current_vol = volume.iloc[-1]
            rvol = current_vol / avg_vol if avg_vol > 0 else 0

            # 3. RSI (Dip Detection)
            rsi = vbt.RSI.run(close, window=14).rsi.iloc[-1]

            # 4. Relative Strength (vs SPY) - Proxy calculation
            # Simplified: % change over last 5 days
            perf_5d = (close.iloc[-1] / close.iloc[-5] - 1) if len(close) > 5 else 0

            # Scoring Logic
            score = 0
            signals = []

            if in_uptrend:
                score += 2
                signals.append("Uptrend")
            
            if rsi < 35:
                score += 3
                signals.append("Oversold (Dip)")
            elif rsi > 70:
                score -= 1
                signals.append("Overbought")

            if rvol > 1.5:
                score += 2
                signals.append("High RVOL")

            results.append({
                "Ticker": symbol,
                "Price": f"${price:.2f}",
                "Score": score,
                "RSI": round(rsi, 1),
                "RVOL": round(rvol, 2),
                "5D Perf": f"{perf_5d:.2%}",
                "Signals": ", ".join(signals)
            })

        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

    # Create Summary Table
    report = pd.DataFrame(results)
    if not report.empty:
        return report.sort_values(by="Score", ascending=False)
    return report

if __name__ == "__main__":
    watchlist = get_sp500_lite()
    df_results = screen_stocks(watchlist)
    print("\n" + "="*80)
    print("ALPHA SCREENER RESULTS")
    print("="*80)
    print(df_results.to_markdown(index=False))
    print("="*80)
