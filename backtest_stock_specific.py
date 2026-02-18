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

# Load credentials
load_dotenv("stock-bot/.env")
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def calculate_alphatrend_vbt(df, period=14, coeff=1):
    """VBT-compatible AlphaTrend logic"""
    df = df.copy()
    # Ensure column casing
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
        if np.isnan(mfi_vals[i]) or i == 0:
            alpha_trend[i] = close_vals[i]
            continue
            
        if mfi_vals[i] >= 50:
            alpha_trend[i] = max(upt_vals[i], alpha_trend[i-1])
        else:
            alpha_trend[i] = min(downT_vals[i], alpha_trend[i-1])
                
    at_k1 = alpha_trend
    at_k2 = pd.Series(at_k1).shift(2).values
    
    df['At_k1'] = at_k1
    df['At_k2'] = at_k2
    return df

def run_stock_specific_backtest(tickers):
    start_date = datetime.now() - timedelta(days=365 * 5)
    request_params = StockBarsRequest(symbol_or_symbols=tickers, timeframe=TimeFrame.Day, start=start_date, adjustment='all')
    bars = client.get_stock_bars(request_params).df
    
    summary = []
    
    for ticker in tickers:
        try:
            df = bars.xs(ticker).copy()
            df = calculate_alphatrend_vbt(df)
            
            # 1. AlphaTrend (Trend Follower)
            at_entries = (df['At_k1'] > df['At_k2']) & (pd.Series(df['At_k1']).shift(1) <= pd.Series(df['At_k2']).shift(1)).values
            at_exits = (df['At_k1'] < df['At_k2']) & (pd.Series(df['At_k1']).shift(1) >= pd.Series(df['At_k2']).shift(1)).values
            
            # 2. Aggressive RSI Swing (Higher Frequency)
            # Buy when RSI < 45, Sell when RSI > 65
            rsi = ta.rsi(df['Close'], length=14)
            rsi_entries = (rsi < 45) & (rsi.shift(1) >= 45)
            rsi_exits = (rsi > 65) & (rsi.shift(1) <= 65)
            
            # 3. Hybrid: Trend-Aligned RSI
            # Only buy the RSI dip if AlphaTrend is Bullish
            hybrid_entries = rsi_entries & (df['At_k1'] > df['At_k2'])
            hybrid_exits = at_exits | rsi_exits
            
            # Run Portfolios
            pf_at = vbt.Portfolio.from_signals(df['Close'], at_entries, at_exits, init_cash=10000, fees=0.001, freq='1D')
            pf_rsi = vbt.Portfolio.from_signals(df['Close'], rsi_entries, rsi_exits, init_cash=10000, fees=0.001, freq='1D')
            pf_hybrid = vbt.Portfolio.from_signals(df['Close'], hybrid_entries, hybrid_exits, init_cash=10000, fees=0.001, freq='1D')
            
            summary.append({
                "Ticker": ticker,
                "AT Return %": round(pf_at.total_return() * 100, 1),
                "RSI Return %": round(pf_rsi.total_return() * 100, 1),
                "Hybrid Return %": round(pf_hybrid.total_return() * 100, 1),
                "Avg Trades/Mo": round(pf_rsi.trades.count() / 60, 1), # 60 months in 5 years
                "B&H %": round((df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100, 1)
            })
        except Exception as e:
            print(f"Error on {ticker}: {e}")

    return pd.DataFrame(summary)

if __name__ == "__main__":
    growth_stocks = ["NVDA", "TSLA", "AMD", "NFLX", "MSFT", "AMZN", "META", "GOOGL"]
    print(f"Running backtest on high-beta growth stocks...")
    results = run_stock_specific_backtest(growth_stocks)
    print("\n=== STOCK-SPECIFIC SWING PERFORMANCE (5 YEARS) ===")
    print(results.to_markdown(index=False))
