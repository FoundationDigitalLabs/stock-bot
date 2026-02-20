import pandas as pd
import numpy as np
import vectorbt as vbt
import duckdb
import os
import time
from rsi_alpha import find_bullish_divergence
from trend_alpha import calculate_trend_quality

# --- CONFIG ---
DB_PATH = "stock-bot/data/market_data.duckdb"

def get_duckdb_candidates():
    print(f"🚀 Initializing Fast Local Scan from {DB_PATH}...")
    start_time = time.time()
    
    conn = duckdb.connect(DB_PATH)
    
    # 1. Fetch all data from local DB
    # We load it into a DataFrame to process with our existing Alpha logic
    df_all = conn.execute("SELECT * FROM bars ORDER BY symbol, timestamp").df()
    conn.close()
    
    tickers = df_all['symbol'].unique()
    results = []
    
    print(f"📊 Processing {len(tickers)} tickers locally...")
    
    for symbol in tickers:
        df = df_all[df_all['symbol'] == symbol].copy()
        if len(df) < 200: continue
        
        # Standardize columns for our indicators
        df.columns = [col.capitalize() for col in df.columns]
        close = df['Close']
        price = close.iloc[-1]
        
        # 1. Primary Filter: Macro Uptrend (SMA 200)
        sma200 = vbt.MA.run(close, window=200).ma.iloc[-1]
        if price <= sma200: continue

        # 2. Secondary Filter: RSI Threshold
        rsi_series = vbt.RSI.run(close, window=14).rsi
        rsi = rsi_series.iloc[-1]
        if rsi > 75: continue 

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

    report = pd.DataFrame(results)
    end_time = time.time()
    
    print(f"✅ Local Scan Complete in {end_time - start_time:.2f} seconds.")
    
    if not report.empty:
        return report.sort_values(
            by=["Divergence", "Trend_Score", "Perf_1M"], 
            ascending=[False, False, False]
        )
    return report

if __name__ == "__main__":
    candidates = get_duckdb_candidates()
    if not candidates.empty:
        print("\n" + "="*50)
        print(f"TOP 20 LOCAL CANDIDATES")
        print("="*50)
        print(candidates.head(20).to_markdown(index=False))
