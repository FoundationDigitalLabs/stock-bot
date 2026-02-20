import duckdb
import pandas as pd
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

# --- CONFIG ---
DB_PATH = "stock-bot/data/market_data.duckdb"
WATCHLIST_PATH = "stock-bot/data/watchlist_expanded.csv"
load_dotenv("stock-bot/.env")

client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def init_db():
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bars (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            trade_count DOUBLE,
            vwap DOUBLE,
            PRIMARY KEY (symbol, timestamp)
        )
    """)
    conn.close()

def get_last_dates():
    if not os.path.exists(DB_PATH):
        return {}
    conn = duckdb.connect(DB_PATH)
    res = conn.execute("SELECT symbol, MAX(timestamp) FROM bars GROUP BY symbol").fetchall()
    conn.close()
    return {r[0]: r[1] for r in res}

def sync_market_data():
    init_db()
    with open(WATCHLIST_PATH, "r") as f:
        tickers = [line.strip() for line in f.readlines() if line.strip()]
    
    last_dates = get_last_dates()
    batch_size = 100
    
    conn = duckdb.connect(DB_PATH)
    
    print(f"🔄 Syncing market data for {len(tickers)} tickers...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        
        # Determine the earliest date we need for this batch
        # If any ticker is new, we need 1 year. Otherwise, we just need from the last timestamp.
        min_last_date = None
        for t in batch:
            if t not in last_dates:
                min_last_date = datetime.now() - timedelta(days=365)
                break
            if min_last_date is None or last_dates[t] < min_last_date:
                min_last_date = last_dates[t]
        
        # Buffer of 1 day to ensure no gaps
        start_dt = min_last_date + timedelta(minutes=1) if min_last_date else datetime.now() - timedelta(days=365)
        
        if start_dt > datetime.now() - timedelta(hours=1):
            continue # Already up to date
            
        print(f"  Batch {i//batch_size + 1}: Fetching from {start_dt.strftime('%Y-%m-%d')}...")
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Day,
                start=start_dt,
                adjustment='all'
            )
            bars = client.get_stock_bars(request_params).df
            
            if not bars.empty:
                # Prepare for DuckDB insertion
                df = bars.reset_index()
                # DuckDB can register pandas dataframes as tables
                conn.register("temp_df", df)
                conn.execute("""
                    INSERT OR IGNORE INTO bars 
                    SELECT symbol, timestamp, "open", "high", "low", "close", "volume", "trade_count", "vwap" 
                    FROM temp_df
                """)
                conn.unregister("temp_df")
                
        except Exception as e:
            print(f"  ❌ Error in batch: {e}")
        
        time.sleep(0.3)
        
    conn.close()
    print("✅ Market Data Sync Complete.")

if __name__ == "__main__":
    sync_market_data()
