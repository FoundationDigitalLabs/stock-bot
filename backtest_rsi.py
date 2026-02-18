import vectorbt as vbt
import pandas as pd
import numpy as np

def run_rsi_strategy(ticker, rsi_window=14, entry_threshold=30, exit_threshold=70):
    print(f"\n--- Backtesting RSI Strategy on {ticker} ---")
    
    # Load data
    try:
        data = pd.read_csv(f"stock-bot/data/{ticker}.csv", index_col=0, parse_dates=True)
        # Handle Yahoo Finance multi-header mess if present
        if "Price" in data.columns and "Ticker" in data.columns: # Skip new yfinance header rows
             data = pd.read_csv(f"stock-bot/data/{ticker}.csv", index_col=0, parse_dates=True, header=2)
             
        # Select Close price. Adjust column name if needed based on CSV format.
        # VectorBT expects a Series for single asset
        if 'Close' in data.columns:
            close = data['Close']
        elif 'Adj Close' in data.columns:
            close = data['Adj Close']
        else:
            print(f"Error: No Close column found in {ticker}.csv")
            return

    except FileNotFoundError:
        print(f"Error: Data file for {ticker} not found.")
        return

    # Calculate RSI
    rsi = vbt.RSI.run(close, window=rsi_window)

    # Generate Signals
    entries = rsi.rsi_crossed_below(entry_threshold)
    exits = rsi.rsi_crossed_above(exit_threshold)

    # Run Portfolio
    portfolio = vbt.Portfolio.from_signals(
        close, 
        entries, 
        exits, 
        init_cash=10000,
        fees=0.001, # 0.1% fee/slippage
        freq='1D'
    )

    # Print Stats
    # VectorBT methods vary by version.
    # Using stats() dictionary for robustness.
    stats = portfolio.stats()
    
    print(f"Total Return: {stats['Total Return [%]']:.2f}%")
    print(f"Benchmark Return: {stats['Benchmark Return [%]']:.2f}%")
    print(f"Max Drawdown: {stats['Max Drawdown [%]']:.2f}%")
    print(f"Win Rate: {stats['Win Rate [%]']:.2f}%")
    print(f"Total Trades: {stats['Total Trades']}")
    
    return portfolio

if __name__ == "__main__":
    # Test on a volatile stock
    run_rsi_strategy("TSLA")
    run_rsi_strategy("SPY")
