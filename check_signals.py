
import os
import pandas as pd
from active_trader import ActiveAlphaTrader

if __name__ == "__main__":
    try:
        trader = ActiveAlphaTrader()
        print("Fetching signals...")
        signals = trader.get_signals()
        
        print(f"\nFound {len(signals)} signals.")
        
        # Sort by score descending
        signals.sort(key=lambda x: x['Score'], reverse=True)
        
        print("\n--- WATCHLIST REPORT ---")
        for sig in signals:
            status = "BULLISH" if sig['At_Bullish'] else "BEARISH"
            print(f"{sig['Ticker']}: Score {sig['Score']} | Price ${sig['Price']:.2f} | {status} | ATR {sig['ATR']:.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
