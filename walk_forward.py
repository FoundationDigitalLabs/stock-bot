import vectorbt as vbt
import pandas as pd
import numpy as np
import itertools

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

def optimize_ma(close_df):
    """Finds best Fast/Slow MA params on the given data."""
    windows_fast = np.arange(10, 60, 10)
    windows_slow = np.arange(50, 210, 20)
    
    # Generate all pairs
    ma_pairs = list(itertools.product(windows_fast, windows_slow))
    fast_windows = [p[0] for p in ma_pairs]
    slow_windows = [p[1] for p in ma_pairs]

    # Run VectorBT
    fast_ma = vbt.MA.run(close_df, window=fast_windows, short_name='fast')
    slow_ma = vbt.MA.run(close_df, window=slow_windows, short_name='slow')

    entries = fast_ma.ma_crossed_above(slow_ma)
    exits = fast_ma.ma_crossed_below(slow_ma)

    pf = vbt.Portfolio.from_signals(close_df, entries, exits, fees=0.001, freq='1D')
    
    # Get mean return across all assets for each param combination
    results = pf.total_return().groupby(['fast_window', 'slow_window']).mean()
    
    best_idx = results.idxmax()
    best_return = results.max()
    
    return best_idx, best_return

print("--- Walk-Forward Analysis (Robustness Check) ---")

# 1. Load Data
full_data = load_data()

# 2. Split Data (Train: 2020-2023, Test: 2024-2026)
# Ensure we have data in range
start_date = full_data.index.min()
# Make split_date timezone aware if data is aware, or naive if naive
tz = full_data.index.tz
if tz:
    split_date = pd.Timestamp("2024-01-01").tz_localize(tz)
else:
    split_date = pd.Timestamp("2024-01-01")

train_data = full_data.loc[:split_date]
test_data = full_data.loc[split_date:]

print(f"Training Period: {start_date.date()} -> {split_date.date()} ({len(train_data)} days)")
print(f"Testing Period:  {split_date.date()} -> {full_data.index.max().date()} ({len(test_data)} days)")

# 3. Optimize on Training Data
print("\n[Phase 1] Optimizing on Training Data...")
best_params, train_return = optimize_ma(train_data)
print(f"Best Train Params: Fast={best_params[0]}, Slow={best_params[1]}")
print(f"In-Sample Return: {train_return:.2%}")

# 4. Validate on Testing Data (Out-of-Sample)
print("\n[Phase 2] Validating on Testing Data...")
# Run ONLY the best params on the test set
fast_ma_test = vbt.MA.run(test_data, window=best_params[0])
slow_ma_test = vbt.MA.run(test_data, window=best_params[1])

entries_test = fast_ma_test.ma_crossed_above(slow_ma_test)
exits_test = fast_ma_test.ma_crossed_below(slow_ma_test)

pf_test = vbt.Portfolio.from_signals(test_data, entries_test, exits_test, fees=0.001, freq='1D')
test_return = pf_test.total_return().mean()

# Benchmark (Buy & Hold) on Test Set
benchmark_return = (test_data.iloc[-1] / test_data.iloc[0] - 1).mean()

print(f"Out-of-Sample Return: {test_return:.2%}")
print(f"Benchmark (Buy & Hold): {benchmark_return:.2%}")

# 5. Conclusion
print("\n--- Verdict ---")
if test_return > benchmark_return:
    print("✅ PASS: Strategy beat the market in the unknown future.")
elif test_return > 0:
    print("⚠️ OKAY: Strategy made money, but less than Buy & Hold.")
else:
    print("❌ FAIL: Strategy lost money in the unknown future.")

ratio = test_return / train_return if train_return != 0 else 0
print(f"Robustness Ratio (Test/Train): {ratio:.2f} (Target > 0.5)")
