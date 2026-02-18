import pandas as pd
import numpy as np
import pandas_ta as ta

def calculate_trend_quality(df, window=20):
    """
    Calculates Trend Intensity (ADX), Smoothness (R-Squared), and Acceleration (Slope).
    """
    if len(df) < window + 14:
        return 0, [], 0, 0, 0

    # 1. ADX (Intensity)
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    adx = adx_df['ADX_14'].iloc[-1]
    
    # 2. Linear Regression (Smoothness & Slope)
    # Using a more robust manual calculation to avoid version-specific pandas_ta issues
    y = df['Close'].tail(window).values
    x = np.arange(window)
    
    # Linear Regression: y = mx + b
    # m (slope), b (intercept)
    m, b = np.polyfit(x, y, 1)
    
    # R-Squared
    y_pred = m * x + b
    r_squared = 1 - (np.sum((y - y_pred)**2) / np.sum((y - np.mean(y))**2))
    
    # Prev Slope (last 5 bars shift)
    y_prev = df['Close'].iloc[-(window+5):-5].values
    m_prev, _ = np.polyfit(x, y_prev, 1) if len(y_prev) == window else (m, 0)
    
    # Normalize slope by price
    price = df['Close'].iloc[-1]
    norm_slope = (m / price) * 100
    accelerating = m > m_prev
    
    score = 0
    signals = []
    
    if adx > 25:
        score += 2
        signals.append(f"Strong Trend (ADX:{int(adx)})")
    
    if r_squared > 0.7:
        score += 2
        signals.append("High Quality Trend (Smooth)")
    elif r_squared > 0.5:
        score += 1
        signals.append("Decent Trend")
        
    if norm_slope > 0.1:
        if accelerating:
            score += 2
            signals.append("Trend Accelerating")
        else:
            score += 1
            signals.append("Trend Stable")
            
    if norm_slope > 1.5:
        score -= 2
        signals.append("PARABOLIC DANGER")

    return score, signals, adx, r_squared, norm_slope
