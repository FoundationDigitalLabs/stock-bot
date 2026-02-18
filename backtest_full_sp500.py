import vectorbt as vbt
import pandas as pd
import numpy as np
import os
import pandas_ta as ta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

load_dotenv("stock-bot/.env")
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def calculate_alphatrend_vbt(df, period=14, coeff=1):
    df = df.copy()
    # Ensure Title Case
    df.columns = [c.capitalize() for c in df.columns]
    
    tr = ta.true_range(df['High'], df['Low'], df['Close'])
    atr = ta.sma(tr, length=period)
    mfi = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=period)
    
    # Fill NaNs for the start of the series
    atr = atr.fillna(0)
    mfi = mfi.fillna(50)
    
    upt = df['Low'] - (atr * coeff)
    downT = df['High'] + (atr * coeff)
    
    alpha_trend = np.zeros(len(df))
    close_vals = df['Close'].values
    mfi_vals = mfi.values
    upt_vals = upt.values
    downT_vals = downT.values
    
    for i in range(1, len(df)):
        if mfi_vals[i] >= 50:
            alpha_trend[i] = max(upt_vals[i], alpha_trend[i-1])
        else:
            alpha_trend[i] = min(downT_vals[i], alpha_trend[i-1])
            
    df['At_k1'] = alpha_trend
    df['At_k2'] = pd.Series(alpha_trend).shift(2).values
    return df

def run_full_universe_scan():
    # Load tickers
    tickers_path = "stock-bot/data/sp500_tickers.csv"
    if os.path.exists(tickers_path):
        with open(tickers_path, "r") as f:
            tickers = [line.strip().replace('-', '.') for line in f.readlines() if line.strip()]
    else:
        tickers = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]

    start_date = datetime.now() - timedelta(days=730) # 2 Years
    batch_size = 50
    results = []
    
    print(f"Scanning {len(tickers)} S&P 500 stocks on 4-Hour timeframe...")
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=batch,
                timeframe=TimeFrame.Hour,
                start=start_date,
                adjustment='all'
            )
            bars = client.get_stock_bars(request_params).df
            
            for ticker in batch:
                try:
                    if ticker not in bars.index.get_level_values(0): continue
                    
                    df_hour = bars.xs(ticker).copy()
                    # Resample to 4-Hour
                    df = df_hour.resample('4h').agg({
                        'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'
                    }).dropna()
                    
                    if len(df) < 50: continue
                    
                    df = calculate_alphatrend_vbt(df)
                    
                    # Logic
                    at_bullish = df['At_k1'] > df['At_k2']
                    entries = (at_bullish) & (at_bullish.shift(1) == False)
                    exits = (at_bullish == False) & (at_bullish.shift(1) == True)
                    
                    pf = vbt.Portfolio.from_signals(
                        df['close'], entries, exits, 
                        init_cash=10000, fees=0.001, freq='4h'
                    )
                    
                    b_ret = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                    
                    results.append({
                        "Ticker": ticker,
                        "Return %": round(pf.total_return() * 100, 1),
                        "B&H %": round(b_ret, 1),
                        "Win Rate %": round(pf.trades.win_rate() * 100, 1) if pf.trades.count() > 0 else 0,
                        "Trades/Mo": round(pf.trades.count() / 24, 2),
                        "Sharpe": round(pf.sharpe_ratio(), 2),
                        "MaxDD %": round(pf.max_drawdown() * 100, 2)
                    })
                except Exception:
                    continue
            print(f"Processed batch {i//batch_size + 1}/{(len(tickers)//batch_size)+1}")
        except Exception as e:
            print(f"Error in batch: {e}")
            
    return pd.DataFrame(results)

if __name__ == "__main__":
    df_results = run_full_universe_scan()
    if not df_results.empty:
        # Filter for quality: Must have trades and positive return
        top_performers = df_results[df_results['Trades/Mo'] > 0.5].sort_values("Return %", ascending=False)
        print("\n=== TOP 20 S&P 500 SWING VEHICLES (4-HOUR ALPHATREND) ===")
        print(top_performers.head(20).to_markdown(index=False))
        df_results.to_csv("stock-bot/data/full_sp500_backtest_4h.csv", index=False)
    else:
        print("No results generated.")
