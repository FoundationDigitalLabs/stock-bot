import pandas as pd
import pandas_ta as ta
import numpy as np

from sklearn.cluster import KMeans

def calculate_bb_rsi(df, bb_period=200, bb_std=2.0, rsi_period=14, rsi_low=30, rsi_high=70):
    """
    Implementation of Bollinger + RSI, Double Strategy (by ChartArt) v1.1.
    """
    df = df.copy()
    df.columns = [col.capitalize() for col in df.columns]
    
    # Bollinger Bands
    bb = ta.bbands(df['Close'], length=bb_period, std=bb_std)
    # pandas-ta can sometimes use different naming for floats
    col_l = [c for c in bb.columns if c.startswith('BBL')][0]
    col_u = [c for c in bb.columns if c.startswith('BBU')][0]
    df['bb_lower'] = bb[col_l]
    df['bb_upper'] = bb[col_u]
    
    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=rsi_period)
    
    # Logic: Buy when price < lower BB AND RSI < 30
    df['bb_rsi_buy'] = (df['Close'] < df['bb_lower']) & (df['rsi'] < rsi_low)
    
    # Logic: Sell when price > upper BB AND RSI > 70
    df['bb_rsi_sell'] = (df['Close'] > df['bb_upper']) & (df['rsi'] > rsi_high)
    
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Standard MACD implementation using pandas-ta.
    """
    df = df.copy()
    df.columns = [col.capitalize() for col in df.columns]
    
    macd_df = ta.macd(df['Close'], fast=fast, slow=slow, signal=signal)
    
    # pandas-ta returns columns like MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
    col_macd = f'MACD_{fast}_{slow}_{signal}'
    col_signal = f'MACDs_{fast}_{slow}_{signal}'
    
    df['macd'] = macd_df[col_macd]
    df['macd_signal'] = macd_df[col_signal]
    
    # Crosses
    df['macd_buy'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['macd_sell'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
    
    return df

def calculate_alphatrend(df, period=14, coeff=1):
    """
    Python implementation of the AlphaTrend indicator by KivancOzbilgic.
    """
    df = df.copy()
    
    # Calculate components
    df['tr'] = ta.true_range(df['High'], df['Low'], df['Close'])
    df['atr'] = ta.sma(df['tr'], length=period)
    df['rsi'] = ta.rsi(df['Close'], length=period)
    df['mfi'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=period)
    
    upt = df['Low'] - (df['atr'] * coeff)
    downT = df['High'] + (df['atr'] * coeff)
    
    alpha_trend = [0.0] * len(df)
    
    # Use MFI as the primary trend filter (as per the TradingView script)
    # If no volume data, it defaults to RSI
    for i in range(1, len(df)):
        mfi_val = df['mfi'].iloc[i]
        
        if mfi_val >= 50:
            # Uptrend logic: Trailing stop that can only move up
            if upt.iloc[i] < alpha_trend[i-1]:
                alpha_trend[i] = alpha_trend[i-1]
            else:
                alpha_trend[i] = upt.iloc[i]
        else:
            # Downtrend logic: Trailing stop that can only move down
            if downT.iloc[i] > alpha_trend[i-1]:
                alpha_trend[i] = alpha_trend[i-1]
            else:
                alpha_trend[i] = downT.iloc[i]
                
    df['At_k1'] = alpha_trend
    df['At_k2'] = df['At_k1'].shift(2)
    
    # Buy signal: k1 crosses above k2
    df['at_buy'] = (df['At_k1'] > df['At_k2']) & (df['At_k1'].shift(1) <= df['At_k2'].shift(1))
    # Sell signal: k1 crosses below k2
    df['at_sell'] = (df['At_k1'] < df['At_k2']) & (df['At_k1'].shift(1) >= df['At_k2'].shift(1))
    
    return df

if __name__ == "__main__":
    # Test with a dummy DF or local data if available
    print("AlphaTrend logic loaded.")
