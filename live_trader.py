import os
import pandas as pd
import numpy as np
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

# Import our verified indicators
from indicators import calculate_alphatrend, calculate_bb_rsi

class AlphaAccumulator:
    def __init__(self, paper=True):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        self.universe_path = "stock-bot/data/sp500_tickers.csv"

    def get_universe(self):
        if os.path.exists(self.universe_path):
            with open(self.universe_path, "r") as f:
                tickers = [line.strip() for line in f.readlines() if line.strip()]
            # Alpaca V2 usually prefers . over -
            return [t.replace('-', '.') for t in tickers]
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]

    def scan_and_rank(self):
        tickers = self.get_universe()
        rankings = []
        start_date = datetime.now() - timedelta(days=300)
        
        batch_size = 50
        print(f"Starting Alpha Scan on {len(tickers)} tickers...")
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            try:
                request_params = StockBarsRequest(
                    symbol_or_symbols=batch,
                    timeframe=TimeFrame.Day,
                    start=start_date,
                    adjustment='all'
                )
                bars = self.data_client.get_stock_bars(request_params).df
                
                for ticker in batch:
                    try:
                        if ticker not in bars.index.get_level_values(0):
                            continue
                        
                        df = bars.xs(ticker).copy()
                        df.columns = [col.capitalize() for col in df.columns]
                        
                        if len(df) < 200: continue
                        
                        # Calculate Indicators
                        df['sma200'] = df['Close'].rolling(200).mean()
                        df = calculate_alphatrend(df)
                        df = calculate_bb_rsi(df)
                        
                        last = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        # Score Logic
                        score = 0
                        signals = []
                        
                        if last['Close'] > last['sma200']:
                            score += 2
                            signals.append("Uptrend")
                        
                        if last['rsi'] < 30:
                            score += 3
                            signals.append("Deep Dip")
                        elif last['rsi'] < 20:
                            score += 5
                            signals.append("Extreme Dip")
                            
                        is_at_bullish = last['at_k1'] > last['at_k2']
                        at_cross_up = is_at_bullish and (prev['at_k1'] <= prev['at_k2'])
                        
                        if at_cross_up:
                            score += 4
                            signals.append("Trend Flip BUY")
                        elif is_at_bullish:
                            score += 1
                            signals.append("Trend Bullish")
                            
                        if last['bb_rsi_buy']:
                            score += 3
                            signals.append("BB Crash Support")

                        if score >= 3: # Lowered threshold to see more data in dev
                            rankings.append({
                                "Ticker": ticker,
                                "Score": score,
                                "Price": round(last['Close'], 2),
                                "RSI": round(last['rsi'], 1),
                                "MFI": round(last['mfi'], 1),
                                "Signals": ", ".join(signals)
                            })
                    except Exception as ticker_e:
                        continue
            except Exception as e:
                print(f"Error in batch: {e}")
                
        if not rankings:
            return pd.DataFrame()
        return pd.DataFrame(rankings).sort_values(by="Score", ascending=False)

    def generate_report(self, df):
        if df.empty:
            return "No high-conviction signals found today."
        report = "=== ALPHA ACCUMULATOR DAILY SCAN ===\n"
        report += df.head(20).to_markdown(index=False)
        return report

if __name__ == "__main__":
    bot = AlphaAccumulator(paper=True)
    results = bot.scan_and_rank()
    print(bot.generate_report(results))
    results.to_csv("stock-bot/data/latest_rankings.csv", index=False)
