import os
import pandas as pd
import numpy as np
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas_ta as ta

# Import our verified indicators
from indicators import calculate_alphatrend, calculate_bb_rsi

class AlphaAccumulatorV2:
    def __init__(self, paper=True):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        # We focus on the "Alpha Vehicles" identified in backtests
        self.watchlist = ["NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AVGO", "SMCI", "ARM", "PLTR", "QCOM", "AAPL"]

    def scan_for_setups(self):
        """
        Scans the watchlist using the 4-Hour Timeframe and the 10-Point Scoring System.
        """
        results = []
        # Need enough data for 200 SMA on 4H (approx 800-1000 bars)
        start_date = datetime.now() - timedelta(days=365)
        
        print(f"Starting 10-Point Alpha Scan on {len(self.watchlist)} tickers...")
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=self.watchlist,
                timeframe=TimeFrame.Hour, # Fetch hour, then resample to 4H
                start=start_date,
                adjustment='all'
            )
            bars = self.data_client.get_stock_bars(request_params).df
            
            for ticker in self.watchlist:
                try:
                    if ticker not in bars.index.get_level_values(0):
                        continue
                    
                    df_hour = bars.xs(ticker).copy()
                    df_hour.columns = [col.capitalize() for col in df_hour.columns]
                    
                    # Resample to 4-Hour "Swing Sweet Spot"
                    df = df_hour.resample('4h').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    
                    if len(df) < 200: continue
                    
                    # 1. Calculate Indicators
                    df['Sma200'] = df['Close'].rolling(200).mean()
                    df = calculate_alphatrend(df)
                    df['rsi'] = ta.rsi(df['Close'], length=14)
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # 2. 10-POINT SCORING SYSTEM
                    score = 0
                    signals = []
                    
                    # A. Macro Trend (+2)
                    if last['Close'] > last['Sma200']:
                        score += 2
                        signals.append("Macro Bullish")
                    
                    # B. Trend Conviction (+3)
                    is_at_bullish = last['At_k1'] > last['At_k2']
                    if is_at_bullish:
                        score += 3
                        signals.append("AlphaTrend Bullish")
                        
                    # C. Early Entry Bonus (+2)
                    at_cross_up = is_at_bullish and (prev['At_k1'] <= prev['At_k2'])
                    if at_cross_up:
                        score += 2
                        signals.append("JUST CROSSED (Entry 1)")
                    
                    # D. Value / Deep Dip (+2)
                    if last['rsi'] < 35:
                        score += 2
                        signals.append("Deep Dip (Sale)")
                    elif last['rsi'] < 45:
                        score += 1
                        signals.append("Moderate Dip")
                        
                    # E. Breakout Confirmation (+1)
                    if last['Close'] > prev['High']:
                        score += 1
                        signals.append("Breaking Prev High")

                    results.append({
                        "Ticker": ticker,
                        "Score": score,
                        "Price": round(last['Close'], 2),
                        "RSI": round(last['rsi'], 1),
                        "Signals": ", ".join(signals),
                        "Status": "STRONG BUY" if score >= 8 else "WATCH" if score >= 5 else "WAIT"
                    })
                except Exception as e:
                    print(f"Error processing {ticker}: {e}")
                    
        except Exception as e:
            print(f"Error fetching data: {e}")
                
        if not results:
            return pd.DataFrame(columns=["Ticker", "Score", "Price", "RSI", "Signals", "Status"])
        return pd.DataFrame(results).sort_values(by="Score", ascending=False)

    def generate_report(self, df):
        if df.empty:
            return "No signals found in the 4-Hour scan."
        
        report = "=== 10-POINT ALPHA ACCUMULATOR SCAN (4-HOUR) ===\n"
        report += df.to_markdown(index=False)
        report += "\n\n*Thresholds: 8+ Strong Buy | 5-7 Watch | <5 Wait*"
        return report

if __name__ == "__main__":
    bot = AlphaAccumulatorV2(paper=True)
    rankings = bot.scan_for_setups()
    print(bot.generate_report(rankings))
    rankings.to_csv("stock-bot/data/latest_4h_rankings.csv", index=False)
