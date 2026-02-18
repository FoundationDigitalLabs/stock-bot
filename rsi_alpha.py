import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

def find_bullish_divergence(price, rsi, window=50, order=5):
    """
    Detects Bullish Divergence: Price makes a Lower Low, but RSI makes a Higher Low.
    
    Args:
        price (pd.Series): Series of closing prices.
        rsi (pd.Series): Series of RSI values.
        window (int): Lookback window to search for peaks/troughs.
        order (int): Number of points on each side to use for local minima detection.
        
    Returns:
        bool: True if bullish divergence is detected in the recent window.
    """
    if len(price) < window:
        return False
        
    # Get the last 'window' bars
    p_segment = price.tail(window).values
    r_segment = rsi.tail(window).values
    
    # Find local minima (troughs) in Price and RSI
    p_min_idx = argrelextrema(p_segment, np.less, order=order)[0]
    r_min_idx = argrelextrema(r_segment, np.less, order=order)[0]
    
    # We need at least two troughs to compare
    if len(p_min_idx) < 2 or len(r_min_idx) < 2:
        return False
        
    # Get the last two troughs
    # Price lows
    p_low1 = p_segment[p_min_idx[-2]]
    p_low2 = p_segment[p_min_idx[-1]]
    
    # RSI lows at those same time indices (matching the price troughs)
    # Note: True divergence often has RSI troughs slightly offset, 
    # but checking RSI at price troughs is a robust starting point.
    r_low1 = r_segment[p_min_idx[-2]]
    r_low2 = r_segment[p_min_idx[-1]]
    
    # Condition: Price makes Lower Low, RSI makes Higher Low
    if p_low2 < p_low1 and r_low2 > r_low1:
        # Also ensure the second RSI low is still relatively "low" (< 45)
        if r_low2 < 45:
            return True
            
    return False

def check_rsi_support_bounce(rsi, threshold=40, tolerance=2):
    """
    Detects if RSI is 'bouncing' off a support level (typically 40 in a bull market).
    """
    if len(rsi) < 3:
        return False
        
    # Last 3 values
    prev2 = rsi.iloc[-3]
    prev1 = rsi.iloc[-2]
    current = rsi.iloc[-1]
    
    # Check if we were near the threshold and are now turning up
    # 1. Previous value was within tolerance of threshold (e.g., 38 to 42)
    # 2. Current value is higher than previous
    if abs(prev1 - threshold) <= tolerance and current > prev1:
        return True
        
    return False
