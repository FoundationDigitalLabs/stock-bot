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

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def calculate_alphatrend_vbt(close, high, low, volume, period=14, coeff=1):
    # AlphaTrend involves a loop that depends on previous values,
    # so we'll use a standard loop and wrap it for VBT.
    
    tr = ta.true_range(high, low, close)
    atr = ta.sma(tr, length=period)
    mfi = ta.mfi(high, low, close, volume, length=period)
    
    upt = low - (atr * coeff)
    downT = high + (atr * coeff)
    
    alpha_trend = np.zeros(len(close))
    
    for i in range(1, len(close)):
        # Handle NaN from start of series
        if np.isnan(mfi.iloc[i]) or np.isnan(atr.iloc[i]):
            alpha_trend[i] = close.iloc[i]
            continue
            
        if mfi.iloc[i] >= 50:
            if upt.iloc[i] < alpha_trend[i-1]:
                alpha_trend[i] = alpha_trend[i-1]
            else:
                alpha_trend[i] = upt.iloc[i]
        else:
            if downT.iloc[i] > alpha_trend[i-1]:
                alpha_trend[i] = alpha_trend[i-1]
            else:
                alpha_trend[i] = downT.iloc[i]
    
    at_k1 = alpha_trend
    at_k2 = pd.Series(at_k1).shift(2).fillna(at_k1[0]).values
    
    entries = (at_k1 > at_k2) & (pd.Series(at_k1).shift(1) <= pd.Series(at_k2).shift(1)).values
    exits = (at_k1 < at_k2) & (pd.Series(at_k1).shift(1) >= pd.Series(at_k2).shift(1)).values
    
    return entries, exits

def run_backtest(ticker="SPY"):
    print(f"Fetching data for {ticker}...")
    start_date = datetime.now() - timedelta(days=365 * 5) # 5 years
    
    request_params = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start_date,
        adjustment='all'
    )
    bars = client.get_stock_bars(request_params).df
    df = bars.xs(ticker)
    
    print(f"Calculating AlphaTrend for {ticker}...")
    entries, exits = calculate_alphatrend_vbt(df['close'], df['high'], df['low'], df['volume'])
    
    print(f"Running VectorBT simulation for {ticker}...")
    pf = vbt.Portfolio.from_signals(
        df['close'],
        entries,
        exits,
        init_cash=10000,
        fees=0.001, # 0.1% fee
        slippage=0.001, # 0.1% slippage
        freq='1D'
    )
    
    # Run Benchmark (Buy & Hold)
    benchmark_pf = vbt.Portfolio.from_holding(df['close'], init_cash=10000, freq='1D')
    
    print("\n" + "="*50)
    print(f"BACKTEST RESULTS: {ticker} (5 Years)")
    print("="*50)
    print(f"AlphaTrend Total Return: {pf.total_return() * 100:.2f}%")
    print(f"Benchmark (B&H) Return: {benchmark_pf.total_return() * 100:.2f}%")
    print(f"AlphaTrend Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Benchmark Sharpe Ratio: {benchmark_pf.sharpe_ratio():.2f}")
    print(f"Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of Trades: {pf.trades.count()}")
    print("="*50)

if __name__ == "__main__":
    run_backtest("SPY")
    # You can add more tickers here like "QQQ", "AAPL", etc.
