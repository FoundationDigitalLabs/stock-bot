import vectorbt as vbt
import pandas as pd
import numpy as np
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def calculate_smc_signals(df, window=5):
    """
    Simplified SMC Signal Logic:
    1. Identify Swing Highs/Lows.
    2. Detect CHoCH (Trend Reversal).
    3. Identify Order Blocks (OB).
    4. Signal when price returns to OB.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # 1. Swing Points
    df['swing_high'] = high[(high == high.rolling(window=window*2+1, center=True).max())]
    df['swing_low'] = low[(low == low.rolling(window=window*2+1, center=True).min())]
    
    # 2. Market Structure
    last_sh = 0
    last_sl = 0
    structure = 0 # 1: Bullish, -1: Bearish
    
    entries = np.zeros(len(df), dtype=bool)
    exits = np.zeros(len(df), dtype=bool)
    
    order_block_low = 0
    order_block_high = 0
    
    for i in range(window*2, len(df)):
        # Update last known swings
        if not np.isnan(df['swing_high'].iloc[i-window]):
            last_sh = df['swing_high'].iloc[i-window]
        if not np.isnan(df['swing_low'].iloc[i-window]):
            last_sl = df['swing_low'].iloc[i-window]
            
        # Detect CHoCH (Change of Character)
        if structure <= 0 and close.iloc[i] > last_sh and last_sh != 0:
            structure = 1 # Shift to Bullish
            # Order Block is the low of the move that caused the break
            order_block_low = last_sl
            order_block_high = (last_sl + close.iloc[i]) / 2 # Simplified zone
            
        elif structure >= 0 and close.iloc[i] < last_sl and last_sl != 0:
            structure = -1 # Shift to Bearish
            exits[i] = True # Exit longs on Bearish CHoCH
            
        # Entry Logic: If Bullish, wait for price to return to the Order Block
        if structure == 1 and order_block_low != 0:
            if low.iloc[i] <= order_block_high and close.iloc[i] > order_block_low:
                entries[i] = True
                order_block_low = 0 # Reset after entry to avoid double entry
                
    return entries, exits

def run_smc_backtest(ticker="SPY"):
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
    
    print(f"Calculating SMC Signals for {ticker}...")
    entries, exits = calculate_smc_signals(df)
    
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
    print(f"SMC (SMART MONEY CONCEPTS) BACKTEST: {ticker}")
    print("="*50)
    print(f"SMC Total Return: {pf.total_return() * 100:.2f}%")
    print(f"Benchmark (B&H) Return: {benchmark_pf.total_return() * 100:.2f}%")
    print(f"SMC Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Benchmark Sharpe Ratio: {benchmark_pf.sharpe_ratio():.2f}")
    print(f"SMC Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of Trades: {pf.trades.count()}")
    print("="*50)

if __name__ == "__main__":
    run_smc_backtest("SPY")
