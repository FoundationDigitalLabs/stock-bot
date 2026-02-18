import vectorbt as vbt
import pandas as pd
import numpy as np

# Config
symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GLD", "TLT"]
data_dir = "stock-bot/data"

def load_data(ticker):
    """Loads CSV and returns Close prices."""
    df = pd.read_csv(f"{data_dir}/{ticker}_1Day.csv", parse_dates=True, index_col=0)
    return df['Close']

print(f"--- Running Edge Hunt on {len(symbols)} Assets ---")

# 1. Load Data
close_prices = {s: load_data(s) for s in symbols}
close_df = pd.DataFrame(close_prices)

# 2. Strategy Tests
# -----------------

# A. Moving Average Crossover (Trend Following)
# Manual loop for robustness or use param_product if available, 
# but simple nested loop logic is clearer for 'run_combs' issues.

# VectorBT's run_combs expects lists of the same length to zip, or use product logic.
# Let's use simple list comprehension to generate all pairs.
import itertools

windows_fast = np.arange(10, 60, 10)
windows_slow = np.arange(50, 210, 20)
ma_pairs = list(itertools.product(windows_fast, windows_slow))

# Split pairs into two lists for vectorbt
fast_windows = [p[0] for p in ma_pairs]
slow_windows = [p[1] for p in ma_pairs]

# Run MAs
fast_ma = vbt.MA.run(close_df, window=fast_windows, short_name='fast')
slow_ma = vbt.MA.run(close_df, window=slow_windows, short_name='slow')

entries = fast_ma.ma_crossed_above(slow_ma)
exits = fast_ma.ma_crossed_below(slow_ma)

pf_ma = vbt.Portfolio.from_signals(close_df, entries, exits, fees=0.001, freq='1D')

print("\n--- Strategy A: MA Crossover (Trend) ---")
print(f"Combinations Tested: {len(ma_pairs)}")
# Show top performing parameters
# VectorBT results are multi-indexed by (param, symbol)
returns = pf_ma.total_return()
# Group by the parameter levels (fast_window, slow_window) and take mean across symbols
stats_ma = returns.groupby(['fast_window', 'slow_window']).mean()
best_idx = stats_ma.idxmax()
print(f"Best Parameters (Avg Return): Fast={best_idx[0]}, Slow={best_idx[1]}")
print(f"Avg Return (All Assets): {stats_ma.max():.2%}")


# B. RSI Mean Reversion (Contrarian)
# Test: Buy < 20-40, Sell > 60-80
lower_thresh = [20, 25, 30, 35, 40]
upper_thresh = [60, 65, 70, 75, 80]
# Product of parameters
rsi_pairs = list(itertools.product(lower_thresh, upper_thresh))
lows = [p[0] for p in rsi_pairs]
highs = [p[1] for p in rsi_pairs]

# Run RSI once
rsi = vbt.RSI.run(close_df, window=14)

# Create signal frames manually to handle the broadcasting correctly
# We want to test each (low, high) pair against all assets
entries_list = []
exits_list = []

# This is a bit inefficient loop-wise but safe for vectorbt's strict shape rules
for l, h in rsi_pairs:
    entries_list.append(rsi.rsi_crossed_below(l))
    exits_list.append(rsi.rsi_crossed_above(h))

# Stack them? No, simpler to just run Portfolio on the list of DataFrames if VBT allows,
# or run in a loop. For this "Edge Hunt", a loop is fine.

best_rsi_ret = -1.0
best_rsi_params = (0, 0)

print("\n--- Strategy B: RSI Mean Reversion ---")
print(f"Combinations Tested: {len(rsi_pairs)}")

for i, (l, h) in enumerate(rsi_pairs):
    entries = rsi.rsi_crossed_below(l)
    exits = rsi.rsi_crossed_above(h)
    pf = vbt.Portfolio.from_signals(close_df, entries, exits, fees=0.001, freq='1D')
    avg_ret = pf.total_return().mean()
    
    if avg_ret > best_rsi_ret:
        best_rsi_ret = avg_ret
        best_rsi_params = (l, h)

print(f"Best Parameters (Avg Return): Buy < {best_rsi_params[0]}, Sell > {best_rsi_params[1]}")
print(f"Avg Return (All Assets): {best_rsi_ret:.2%}")


# C. Volatility Breakout (Bollinger Bands)
# Buy when price crosses above Upper Band (momentum)
bb = vbt.BBANDS.run(close_df, window=20, alpha=2.0)
# Ensure columns match for comparison
# VectorBT results (bb.upper) might have different column names or index types
# Aligning manually
entries_bb = close_df > bb.upper.values
exits_bb = close_df < bb.middle.values # Exit at mean

pf_bb = vbt.Portfolio.from_signals(close_df, entries_bb, exits_bb, fees=0.001, freq='1D')
print("\n--- Strategy C: Bollinger Breakout (Momentum) ---")
print(f"Avg Return (All Assets): {pf_bb.total_return().mean():.2%}")

# Summary
print("\n--- Summary ---")
# Compare the best of each
# Note: Benchmark is Buy & Hold
benchmark = close_df.iloc[-1] / close_df.iloc[0] - 1
print(f"Benchmark (Buy & Hold) Avg: {benchmark.mean():.2%}")
