import vectorbt as vbt
import pandas as pd
import numpy as np
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas_ta as ta
from indicators import calculate_alphatrend

load_dotenv("stock-bot/.env")
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def get_ticker_data(ticker):
    start_date = datetime.now() - timedelta(days=365 * 5)
    request_params = StockBarsRequest(symbol_or_symbols=ticker, timeframe=TimeFrame.Day, start=start_date, adjustment='all')
    bars = client.get_stock_bars(request_params).df
    df = bars.xs(ticker).copy()
    
    # Ensure column names are capitalized
    df.columns = [col.capitalize() for col in df.columns]
    
    # Debug: Check for mandatory columns
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Missing column {r}")
            
    return df

def run_ticker_backtest(ticker):
    try:
        df = get_ticker_data(ticker)
        print(f"DEBUG: Processing {ticker}, rows: {len(df)}")
        
        # 1. AlphaTrend (Our best balance)
        df = calculate_alphatrend(df)
        at_entries = (df['At_k1'] > df['At_k2']) & (df['At_k1'].shift(1) <= df['At_k2'].shift(1))
        at_exits = (df['At_k1'] < df['At_k2']) & (df['At_k1'].shift(1) >= df['At_k2'].shift(1))
        
        # 2. ADX Trend (Our momentum leader)
        adx = ta.adx(df['High'], df['Low'], df['Close'])
        adx_entries = (adx.iloc[:,0] > 25) & (adx.iloc[:,1] > adx.iloc[:,2])
        adx_exits = (adx.iloc[:,2] > adx.iloc[:,1])
        
        # 3. Simple RSI Swing (Higher frequency)
        rsi = ta.rsi(df['Close'], length=14)
        rsi_entries = (rsi < 40) # Buy the dip
        rsi_exits = (rsi > 65)  # Sell the rip
        
        pf_at = vbt.Portfolio.from_signals(df['Close'], at_entries, at_exits, init_cash=10000, fees=0.001, freq='1D')
        pf_adx = vbt.Portfolio.from_signals(df['Close'], adx_entries, adx_exits, init_cash=10000, fees=0.001, freq='1D')
        pf_rsi = vbt.Portfolio.from_signals(df['Close'], rsi_entries, rsi_exits, init_cash=10000, fees=0.001, freq='1D')
        
        benchmark = vbt.Portfolio.from_holding(df['Close'], init_cash=10000, freq='1D')
        
        return {
            "Ticker": ticker,
            "AlphaTrend %": round(pf_at.total_return() * 100, 2),
            "ADX Trend %": round(pf_adx.total_return() * 100, 2),
            "RSI Swing %": round(pf_rsi.total_return() * 100, 2),
            "B&H %": round(benchmark.total_return() * 100, 2),
            "AT Trades": pf_at.trades.count(),
            "RSI Trades": pf_rsi.trades.count()
        }
    except Exception as e:
        print(f"Error on {ticker}: {e}")
        return None

if __name__ == "__main__":
    tickers = ["AAPL", "NVDA", "TSLA", "AMD", "NFLX", "MSFT", "GOOGL", "META"]
    results = []
    print(f"Backtesting {len(tickers)} high-growth tickers...")
    for t in tickers:
        try:
            results.append(run_ticker_backtest(t))
        except:
            print(f"Error on {t}")
            
    df_res = pd.DataFrame(results)
    print("\n=== THE SWING TRADER LEADERBOARD (5 Years) ===")
    print(df_res.to_markdown(index=False))
