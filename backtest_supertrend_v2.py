import vectorbt as vbt
import pandas as pd
import pandas_ta as ta

# Config
symbols = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "GLD", "TLT"]
data_dir = "stock-bot/data"

def load_data(ticker):
    try:
        # Load Data
        df = pd.read_csv(f"{data_dir}/{ticker}_1Day.csv", parse_dates=True, index_col=0)
        return df
    except FileNotFoundError:
        return None

print("--- SuperTrend Backtest (Using pandas-ta) ---")
print("Settings: Period=10, Multiplier=3")
print("-" * 65)
print(f"{'Ticker':<6} | {'Strategy':<10} | {'Buy&Hold':<10} | {'Alpha':<10} | {'Trades':<6}")
print("-" * 65)

for s in symbols:
    df = load_data(s)
    if df is None: continue

    # Calculate SuperTrend using pandas-ta
    # Returns a DataFrame with columns like: SUPERT_7_3.0, SUPERTd_7_3.0, ...
    st = df.ta.supertrend(length=10, multiplier=3)
    
    # Check if calculation worked
    if st is None or st.empty:
        print(f"{s:<6} | Error calculating SuperTrend")
        continue

    # Extract Direction (1 = Uptrend/Green, -1 = Downtrend/Red)
    # Column name depends on params. Usually 'SUPERTd_10_3.0'
    trend_col = f"SUPERTd_10_3.0" 
    if trend_col not in st.columns:
        # Fallback to finding the 'd' column
        trend_col = [c for c in st.columns if c.startswith('SUPERTd')][0]
    
    direction = st[trend_col]

    # Generate Signals
    # Buy when direction flips from -1 to 1
    entries = (direction == 1) & (direction.shift(1) == -1)
    
    # Sell when direction flips from 1 to -1
    exits = (direction == -1) & (direction.shift(1) == 1)

    # Run Portfolio
    pf = vbt.Portfolio.from_signals(
        df['Close'], 
        entries, 
        exits, 
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
