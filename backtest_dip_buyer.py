import vectorbt as vbt
import pandas as pd
import numpy as np

# Config
symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GLD", "TLT"]
data_dir = "stock-bot/data"

def load_data():
    """Loads all CSVs and returns a DataFrame of Close prices."""
    close_prices = {}
    for s in symbols:
        try:
            df = pd.read_csv(f"{data_dir}/{s}_1Day.csv", parse_dates=True, index_col=0)
            close_prices[s] = df['Close']
        except FileNotFoundError:
            print(f"Warning: {s} data not found.")
    return pd.DataFrame(close_prices)

def run_dip_buyer(close_df):
    """
    Dip Buying Strategy:
    1. Filter: Price must be > 200 SMA (Bull Trend)
    2. Entry: RSI < 30 (Oversold Dip)
    3. Exit: RSI > 70 (Overbought Peak)
    """
    
    # Calculate Indicators
    sma_200 = vbt.MA.run(close_df, window=200)
    rsi = vbt.RSI.run(close_df, window=14)
    
    # Logic
    # 1. Bull Trend Filter
    # Extract values to avoid MultiIndex column issues
    is_uptrend = close_df.values > sma_200.ma.values
    
    # 2. Entries (Dip + Uptrend)
    entries = rsi.rsi_crossed_below(30).values & is_uptrend
    
    # 3. Exits (Peak)
    exits = rsi.rsi_crossed_above(70).values
    
    # Portfolio
    pf = vbt.Portfolio.from_signals(
        close_df, 
        entries, 
        exits, 
        fees=0.001, 
        freq='1D',
        init_cash=10000
    )
    
    return pf

print("--- Bull Market Dip Buyer Backtest ---")
close_df = load_data()

# Run Strategy
pf = run_dip_buyer(close_df)

# Results per Asset
print("\n[Per-Asset Performance]")
stats = pf.stats(agg_func=None)

# Extract metrics safely from stats Series/DataFrame
# VectorBT stats() returns a Series with multi-index if agg_func=None is not supported fully in this context, 
# or a DataFrame if called differently.
# Let's use direct accessors which are safer in newer VBT.
total_return = pf.total_return()
benchmark_return = (close_df.iloc[-1] / close_df.iloc[0]) - 1

# Calculate Win Rate manually if method missing
trades = pf.trades
win_rate = trades.win_rate()

results = pd.DataFrame({
    "Strategy Return": total_return,
    "Buy & Hold": benchmark_return,
    "Win Rate": win_rate,
    "Trades": pf.trades.count()
})

# Add "Alpha" (Strategy - Benchmark)
results["Alpha"] = results["Strategy Return"] - results["Buy & Hold"]

print(results.sort_values(by="Alpha", ascending=False).to_markdown())

# Portfolio Aggregate
print("\n[Portfolio Aggregate Stats]")
print(f"Avg Strategy Return: {total_return.mean():.2%}")
print(f"Avg Buy & Hold: {benchmark_return.mean():.2%}")
print(f"Avg Win Rate: {win_rate.mean():.2%}")

# Highlight the winners
winners = results[results["Alpha"] > 0]
if not winners.empty:
    print(f"\n✅ Assets where Dip Buying works best: {', '.join(winners.index)}")
else:
    print("\n❌ Strategy underperformed Buy & Hold on ALL assets.")
