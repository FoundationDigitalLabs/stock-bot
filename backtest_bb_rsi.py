import vectorbt as vbt
import pandas as pd
import numpy as np
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
from indicators import calculate_bb_rsi

# Load credentials
load_dotenv("stock-bot/.env")
API_KEY = os.getenv("ALPACA_API_KEY")
API_SECRET = os.getenv("ALPACA_SECRET_KEY")

client = StockHistoricalDataClient(API_KEY, API_SECRET)

def run_bb_rsi_backtest(ticker="SPY"):
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
    
    print(f"Calculating Bollinger + RSI Signals for {ticker}...")
    df_bb = calculate_bb_rsi(df)
    
    print(f"Running VectorBT simulation...")
    pf = vbt.Portfolio.from_signals(
        df_bb['Close'],
        df_bb['bb_rsi_buy'],
        df_bb['bb_rsi_sell'],
        init_cash=10000,
        fees=0.001,
        slippage=0.001,
        freq='1D'
    )
    
    benchmark_pf = vbt.Portfolio.from_holding(df_bb['Close'], init_cash=10000, freq='1D')
    
    print("\n" + "="*50)
    print(f"BOLLINGER + RSI BACKTEST: {ticker}")
    print("="*50)
    print(f"BB+RSI Total Return: {pf.total_return() * 100:.2f}%")
    print(f"Benchmark (B&H) Return: {benchmark_pf.total_return() * 100:.2f}%")
    print(f"BB+RSI Sharpe Ratio: {pf.sharpe_ratio():.2f}")
    print(f"Benchmark Sharpe Ratio: {benchmark_pf.sharpe_ratio():.2f}")
    print(f"BB+RSI Max Drawdown: {pf.max_drawdown() * 100:.2f}%")
    print(f"Number of Trades: {pf.trades.count()}")
    print("="*50)

if __name__ == "__main__":
    run_bb_rsi_backtest("SPY")
