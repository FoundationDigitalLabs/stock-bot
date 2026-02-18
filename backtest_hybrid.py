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

# Import logic from indicators.py
from indicators import calculate_alphatrend, calculate_bb_rsi

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def run_hybrid_backtest(ticker="SPY"):
    print(f"Fetching 5 years of data for {ticker}...")
    start_date = datetime.now() - timedelta(days=365 * 5)
    
    request_params = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=TimeFrame.Day,
        start=start_date,
        adjustment='all'
    )
    bars = client.get_stock_bars(request_params).df
    df = bars.xs(ticker).copy()
    df.columns = [col.capitalize() for col in df.columns]
    
    print(f"Calculating Hybrid Signals for {ticker}...")
    # 1. Base Indicators
    df['Sma200'] = df['Close'].rolling(200).mean()
    df = calculate_alphatrend(df)
    df = calculate_bb_rsi(df)
    
    print(f"DEBUG - Final Columns: {df.columns.tolist()}")
    
    # 2. Hybrid Logic Implementation
    # Using Capitalized keys as seen in debug output
    df['is_uptrend'] = df['Close'] > df['Sma200']
    df['at_bullish'] = df['At_k1'] > df['At_k2']
    df['at_cross_up'] = (df['at_bullish']) & (df['at_bullish'].shift(1) == False)
    
    # Entry Logic: Dip + Trend Confirmation
    entries = df['is_uptrend'] & ((df['Rsi'] < 30) | (df['at_cross_up']))
    
    # Exit Logic: AlphaTrend Bearish Breakdown
    exits = (df['At_k1'] < df['At_k2']) & (df['At_k1'].shift(1) >= df['At_k2'].shift(1))
    
    print(f"Running VectorBT simulation...")
    pf = vbt.Portfolio.from_signals(
        df['Close'],
        entries,
        exits,
        init_cash=10000,
        fees=0.001,
        slippage=0.001,
        freq='1D'
    )
    
    benchmark_pf = vbt.Portfolio.from_holding(df['Close'], init_cash=10000, freq='1D')
    
    print("\n" + "="*50)
    print(f"HYBRID 'ALPHA ACCUMULATOR' BACKTEST: {ticker}")
    print("="*50)
    print(f"Hybrid Total Return: {pf.total_return() * 100:.2f}%")
    print(f"Benchmark (B&H) Return: {benchmark_pf.total_return() * 100:.2f}%")
    print(f"Hybrid Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Benchmark Sharpe Ratio: {benchmark_pf.sharpe_ratio():.2f}")
    print(f"Hybrid Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of Trades: {pf.trades.count()}")
    print("="*50)

if __name__ == "__main__":
    run_hybrid_backtest("SPY")
