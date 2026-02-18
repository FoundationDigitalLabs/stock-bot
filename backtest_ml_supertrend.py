import vectorbt as vbt
import pandas as pd
import numpy as np
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
from indicators import calculate_machine_learning_supertrend

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def run_ml_backtest(ticker="SPY"):
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
    
    print(f"Calculating ML Adaptive SuperTrend for {ticker} (this may take a moment due to K-Means loops)...")
    df_ml = calculate_machine_learning_supertrend(df)
    
    print(f"Running VectorBT simulation...")
    pf = vbt.Portfolio.from_signals(
        df_ml['Close'],
        df_ml['ml_buy'],
        df_ml['ml_sell'],
        init_cash=10000,
        fees=0.001,
        slippage=0.001,
        freq='1D'
    )
    
    benchmark_pf = vbt.Portfolio.from_holding(df_ml['Close'], init_cash=10000, freq='1D')
    
    print("\n" + "="*50)
    print(f"ML ADAPTIVE SUPERTREND BACKTEST: {ticker}")
    print("="*50)
    print(f"ML Total Return: {pf.total_return() * 100:.2f}%")
    print(f"Benchmark (B&H) Return: {benchmark_pf.total_return() * 100:.2f}%")
    print(f"ML Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Benchmark Sharpe Ratio: {benchmark_pf.sharpe_ratio():.2f}")
    print(f"ML Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of Trades: {pf.trades.count()}")
    print("="*50)

if __name__ == "__main__":
    run_ml_backtest("SPY")
