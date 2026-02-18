import vectorbt as vbt
import pandas as pd
import numpy as np

# Config
symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GLD", "TLT"]
data_dir = "stock-bot/data"

def load_data(ticker):
    try:
        df = pd.read_csv(f"{data_dir}/{ticker}_1Day.csv", parse_dates=True, index_col=0)
        return df
    except FileNotFoundError:
        return None

def TD_Sequential(close):
    """
    Calculates TD Sequential Setup (The '9' Count).
    - Buy Setup (Green 9): 9 consecutive closes LOWER than the close 4 bars earlier.
    - Sell Setup (Red 9): 9 consecutive closes HIGHER than the close 4 bars earlier.
    """
    close_arr = close.values
    buy_setup = np.zeros(len(close), dtype=int)
    sell_setup = np.zeros(len(close), dtype=int)
    
    # TD Setup
    # Loop is necessary for sequential counting logic (or complex rolling windows)
    # Simple loop is fast enough for daily data
    
    b_count = 0
    s_count = 0
    
    for i in range(4, len(close)):
        # Buy Setup Logic (Price < Price[i-4])
        if close_arr[i] < close_arr[i-4]:
            b_count += 1
        else:
            b_count = 0
            
        # Sell Setup Logic (Price > Price[i-4])
        if close_arr[i] > close_arr[i-4]:
            s_count += 1
        else:
            s_count = 0
            
        # Record 9s
        if b_count == 9:
            buy_setup[i] = 1
            # Optional: Reset count after 9? 
            # DeMark rules say a 'Perfected' 9 ends the setup, but let's just mark the 9.
            # Some versions restart, some continue to 13. We'll stick to the "9" signal.
            b_count = 0 
            
        if s_count == 9:
            sell_setup[i] = 1
            s_count = 0
            
    return pd.Series(buy_setup, index=close.index), pd.Series(sell_setup, index=close.index)

print("--- TD Sequential (DeMark 9) Backtest ---")
print("Logic: Buy on Green 9, Sell on Red 9")
print("-" * 65)
print(f"{'Ticker':<6} | {'Strategy':<10} | {'Buy&Hold':<10} | {'Alpha':<10} | {'Trades':<6}")
print("-" * 65)

for s in symbols:
    df = load_data(s)
    if df is None: continue
    
    # Run Indicator
    buy_signals, sell_signals = TD_Sequential(df['Close'])
    
    # Run Portfolio
    # Note: TD Sequential is often a *contrarian* indicator.
    # Green 9 = Buy (Dip). Red 9 = Sell (Top).
    pf = vbt.Portfolio.from_signals(
        df['Close'], 
        buy_signals.astype(bool), 
        sell_signals.astype(bool), 
        fees=0.001, 
        freq='1D',
        init_cash=10000
    )
    
    total_ret = pf.total_return()
    benchmark = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
    alpha = total_ret - benchmark
    trades = pf.trades.count()
    
    print(f"{s:<6} | {total_ret:>9.2%} | {benchmark:>9.2%} | {alpha:>9.2%} | {trades:>6}")

print("-" * 65)
