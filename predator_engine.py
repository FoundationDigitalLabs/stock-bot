import os
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

import pandas_ta as ta
from indicators import calculate_alphatrend
from visualizer import generate_trade_card

class AlphaPredator:
    def __init__(self, paper=True):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        self.watchlist = ["NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AVGO", "SMCI", "ARM", "PLTR", "QCOM", "AAPL"]
        self.benchmark = "SPY"
        self.sectors = {
            "SEMIS": ["NVDA", "AMD", "AVGO", "ARM", "QCOM"],
            "BIG_TECH": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NFLX"],
            "EXOTIC": ["TSLA", "SMCI", "PLTR"]
        }
        
        self.data_cache = {} # {ticker: dataframe}
        self.last_sync = None

    async def initialize_data(self):
        """Initial data fill: Fetch last 100 days of 1-hour data for the watchlist + SPY."""
        print("📥 Initializing Predator Data Cache...")
        start_date = datetime.now() - timedelta(days=100)
        all_tickers = self.watchlist + [self.benchmark]
        
        request_params = StockBarsRequest(
            symbol_or_symbols=all_tickers,
            timeframe=TimeFrame.Hour,
            start=start_date,
            adjustment='all'
        )
        bars = self.data_client.get_stock_bars(request_params).df
        
        for ticker in all_tickers:
            if ticker in bars.index.get_level_values(0):
                df = bars.xs(ticker).copy()
                df.columns = [c.capitalize() for c in df.columns]
                self.data_cache[ticker] = df
        
        self.last_sync = datetime.now()
        print("✅ Data Cache Ready.")

    def calculate_predator_score(self, ticker):
        """Calculates the 10-point score + new Institutional filters."""
        if ticker not in self.data_cache or self.benchmark not in self.data_cache:
            return 0, []

        # 1. Resample to 4H
        df_hour = self.data_cache[ticker]
        df = df_hour.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(df) < 200: return 0, []
        
        # 2. Indicators
        df['Sma200'] = df['Close'].rolling(200).mean()
        df = calculate_alphatrend(df)
        df['rsi'] = ta.rsi(df['Close'], length=14)
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0
        signals = []
        
        # --- ORIGINAL 10-POINT LOGIC ---
        if last['Close'] > last['Sma200']:
            score += 2
            signals.append("Macro Bullish")
        
        is_at_bullish = last['At_k1'] > last['At_k2']
        if is_at_bullish:
            score += 3
            signals.append("AlphaTrend Bullish")
            
        if is_at_bullish and (prev['At_k1'] <= prev['At_k2']):
            score += 2
            signals.append("JUST CROSSED")
        
        if last['rsi'] < 35:
            score += 2
            signals.append("Deep Dip")
        elif last['rsi'] < 45:
            score += 1
            signals.append("Moderate Dip")
            
        if last['Close'] > prev['High']:
            score += 1
            signals.append("Breakout")

        # --- NEW PREDATOR FILTERS ---
        
        # 1. Relative Strength (vs SPY)
        spy_df = self.data_cache[self.benchmark].resample('4h').agg({'Close': 'last'}).dropna()
        stock_perf = (last['Close'] / df.iloc[-5]['Close']) - 1 # 1-day perf
        spy_perf = (spy_df['Close'].iloc[-1] / spy_df.iloc[-5]['Close']) - 1
        
        if stock_perf > spy_perf:
            score += 1
            signals.append("Relative Strength")
            
        # 2. Sector Tailwind (Symmetry)
        sector = next((s for s, tks in self.sectors.items() if ticker in tks), None)
        if sector:
            bullish_peers = 0
            for peer in self.sectors[sector]:
                if peer == ticker or peer not in self.data_cache: continue
                peer_df = self.data_cache[peer].resample('4h').agg({'Close': 'last'}).dropna()
                # Basic check: Is peer in an uptrend (Close > SMA50)?
                sma50 = peer_df['Close'].rolling(50).mean()
                if peer_df['Close'].iloc[-1] > sma50.iloc[-1]:
                    bullish_peers += 1
            
            if bullish_peers >= 2: # At least 2 peers are bullish
                score += 1
                signals.append(f"{sector} Tailwind")

        return score, signals, last['Close'], last['atr']

    async def execution_loop(self):
        """The 'Tick-by-Tick' simulation loop."""
        print("🚀 PREDATOR ENGINE LIVE. Watching for Alpha...")
        while True:
            try:
                # 1. Sync Latest Data (High-frequency polling)
                await self.initialize_data()
                
                # 2. Get Positions
                positions = {p.symbol: p for p in self.trading_client.get_all_positions()}
                account = self.trading_client.get_account()
                equity = float(account.equity)
                
                # 3. Process Watchlist
                scores_summary = []
                for ticker in self.watchlist:
                    score, signals, price, atr = self.calculate_predator_score(ticker)
                    scores_summary.append(f"{ticker}: {score}")
                    
                    # ENTRY: Score >= 9 (Ultra-High Conviction)
                    if score >= 9 and ticker not in positions:
                        qty = int((equity * 0.05) / price)
                        if qty > 0:
                            stop_loss_price = round(price - (atr * 2.5), 2)
                            take_profit_price = round(price + (atr * 7.5), 2)
                            
                            print(f"🎯 PREDATOR ENTRY: {ticker} | Price: {price} | Score: {score}")
                            self.trading_client.submit_order(
                                MarketOrderRequest(
                                    symbol=ticker,
                                    qty=qty,
                                    side=OrderSide.BUY,
                                    time_in_force=TimeInForce.GTC,
                                    order_class="bracket",
                                    stop_loss={'stop_price': stop_loss_price},
                                    take_profit={'limit_price': take_profit_price}
                                )
                            )
                            # Generate Trade Card Chart
                            df_plot = self.data_cache[ticker].resample('4h').agg({
                                'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                            }).dropna()
                            df_plot = calculate_alphatrend(df_plot)
                            chart = generate_trade_card(ticker, df_plot, price, stop_loss_price, take_profit_price, signals)
                            print(f"📸 Trade Card Generated: {chart}")

                    # EXIT: Score drops or Trend Breakdown
                    elif ticker in positions:
                        # Fetch the same indicators used for entry
                        # If AlphaTrend flips, we close immediately
                        if "AlphaTrend Bullish" not in signals:
                            print(f"⚠️ PREDATOR EXIT: {ticker} | Trend Breakdown | Score: {score}")
                            self.trading_client.close_position(ticker)

                # Wait for next minute
                await asyncio.sleep(60)
            except Exception as e:
                print(f"❌ Predator Engine Error: {e}")
                await asyncio.sleep(10)

if __name__ == "__main__":
    bot = AlphaPredator()
    asyncio.run(bot.execution_loop())
