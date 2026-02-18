import vectorbt as vbt
import pandas as pd
import numpy as np
import os
import pandas_ta as ta
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv("stock-bot/.env")
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def calculate_alphatrend_vbt(df, period=14, coeff=1):
    df = df.copy()
    df.columns = [c.capitalize() for c in df.columns]
    tr = ta.true_range(df['High'], df['Low'], df['Close'])
    atr = ta.sma(tr, length=period)
    mfi = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=period)
    upt = df['Low'] - (atr * coeff)
    downT = df['High'] + (atr * coeff)
    alpha_trend = np.zeros(len(df))
    close_vals = df['Close'].values
    mfi_vals = mfi.values
    upt_vals = upt.values
    downT_vals = downT.values
    for i in range(1, len(df)):
        if np.isnan(mfi_vals[i]):
            alpha_trend[i] = close_vals[i]
            continue
        if mfi_vals[i] >= 50:
            alpha_trend[i] = max(upt_vals[i], alpha_trend[i-1])
        else:
            alpha_trend[i] = min(downT_vals[i], alpha_trend[i-1])
    df['At_k1'] = alpha_trend
    df['At_k2'] = pd.Series(alpha_trend).shift(2).values
    return df

def run_active_swing_test(tickers):
    # Fetching 2 years of 4-Hour data
    start_date = datetime.now() - timedelta(days=730)
    request_params = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Hour, start=start_date, adjustment='all')
    bars = client.get_stock_bars(request_params).df
    
    summary = []
    for ticker in tickers:
        try:
            # Resample to 4-Hour to get the "Swing Sweet Spot"
            df_hour = bars.xs(ticker).copy()
            df = df_hour.resample('4H').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            
            df = calculate_alphatrend_vbt(df)
            
            # Entry: AlphaTrend Flip + RSI not overbought
            rsi = ta.rsi(df['Close'], length=14)
            at_bullish = df['At_k1'] > df['At_k2']
            entries = (at_bullish) & (at_bullish.shift(1) == False) & (rsi < 65)
            exits = (at_bullish == False) & (at_bullish.shift(1) == True)
            
            pf = vbt.Portfolio.from_signals(df['Close'], entries, exits, init_cash=10000, fees=0.001, freq='4H')
            
            summary.append({
                "Ticker": ticker,
                "Return %": round(pf.total_return() * 100, 1),
                "Sharpe": round(pf.sharpe_ratio(), 2),
                "Win Rate %": round(pf.trades.win_rate() * 100, 1),
                "Total Trades": pf.trades.count(),
                "Trades/Mo": round(pf.trades.count() / 24, 2), # 24 months
                "Avg Hold (Days)": round(pf.trades.avg_duration.total_seconds() / 86400, 1)
            })
        except Exception as e:
            continue

    return pd.DataFrame(summary)

if __name__ == "__main__":
    active_tickers = ["NVDA", "TSLA", "AMD", "NFLX", "MSFT", "AMZN", "META"]
    print(f"Running 4-Hour Active Swing Backtest (2 Years)...")
    results = run_active_swing_test(active_tickers)
    print("\n=== THE 4-HOUR SWING LEADERBOARD (ACTIVE TRADING) ===")
    print(results.sort_values("Return %", ascending=False).to_markdown(index=False))
