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
from rsi_alpha import find_bullish_divergence, check_rsi_support_bounce
from trend_alpha import calculate_trend_quality
from visualizer import generate_trade_card
# Notification hook placeholder

class AlphaPredator:
    def __init__(self, paper=True):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        # Load watchlist from weekly candidates if available, otherwise fallback
        self.watchlist = self.load_watchlist()
        self.benchmark = "SPY"
        self.sectors = {
            "SEMIS": ["NVDA", "AMD", "AVGO", "ARM", "QCOM"],
            "BIG_TECH": ["AAPL", "MSFT", "GOOGL", "META", "AMZN", "NFLX"],
            "EXOTIC": ["TSLA", "SMCI", "PLTR"]
        }
        
        self.data_cache = {} 
        self.last_sync = None

    def load_watchlist(self):
        """Loads tickers from weekly_candidates.csv or defaults to high-beta list."""
        path = "stock-bot/data/weekly_candidates.csv"
        if os.path.exists(path):
            try:
                tickers = pd.read_csv(path, header=None)[0].tolist()
                print(f"📋 Loaded {len(tickers)} tickers from weekly candidates.")
                return tickers
            except Exception as e:
                print(f"⚠️ Error loading candidates: {e}. Using default list.")
        
        return ["NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AVGO", "SMCI", "ARM", "PLTR", "QCOM", "AAPL"]

    async def initialize_data(self):
        """Fetch last 100 days to prime the cache."""
        print("📥 Priming Predator Data Cache...")
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
        print("✅ Cache Primed.")

    async def update_latest_data(self):
        """Optimized: Only fetch the last few hours of data to update the cache."""
        start_date = datetime.now() - timedelta(hours=6)
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
                new_df = bars.xs(ticker).copy()
                new_df.columns = [c.capitalize() for c in new_df.columns]
                # Combine and drop duplicates to keep cache fresh
                self.data_cache[ticker] = pd.concat([self.data_cache[ticker], new_df]).drop_duplicates().tail(1000)

    def calculate_predator_score(self, ticker):
        if ticker not in self.data_cache or self.benchmark not in self.data_cache:
            return 0, [], 0, 0

        df_hour = self.data_cache[ticker]
        df = df_hour.resample('4h').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(df) < 200: return 0, [], 0, 0
        
        df['Sma200'] = df['Close'].rolling(200).mean()
        df = calculate_alphatrend(df)
        df['rsi'] = ta.rsi(df['Close'], length=14)
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 0
        signals = []
        
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

        # RSI Alpha Logic
        if find_bullish_divergence(df['Close'], df['rsi']):
            score += 4
            signals.append("Bullish Divergence (Elite)")
        
        if check_rsi_support_bounce(df['rsi']):
            score += 2
            signals.append("RSI 40 Bounce")

        # Trend Quality Integration
        t_score, t_signals, adx, r2, slope = calculate_trend_quality(df)
        score += t_score
        signals.extend(t_signals)

        # Relative Strength
        spy_df = self.data_cache[self.benchmark].resample('4h').agg({'Close': 'last'}).dropna()
        stock_perf = (last['Close'] / df.iloc[-5]['Close']) - 1
        spy_perf = (spy_df['Close'].iloc[-1] / spy_df.iloc[-5]['Close']) - 1
        if stock_perf > spy_perf:
            score += 1
            signals.append("Relative Strength")
            
        # Sector Tailwind
        sector = next((s for s, tks in self.sectors.items() if ticker in tks), None)
        if sector:
            bullish_peers = 0
            for peer in self.sectors[sector]:
                if peer == ticker or peer not in self.data_cache: continue
                peer_df = self.data_cache[peer].resample('4h').agg({'Close': 'last'}).dropna()
                sma50 = peer_df['Close'].rolling(50).mean()
                if peer_df['Close'].iloc[-1] > sma50.iloc[-1]:
                    bullish_peers += 1
            if bullish_peers >= 2:
                score += 1
                signals.append(f"{sector} Tailwind")

        return score, signals, last['Close'], last['atr']

    async def execution_loop(self):
        print("🚀 PREDATOR ENGINE LIVE. Watching for Alpha...")
        await self.initialize_data()
        
        while True:
            try:
                # 1. Optimized Update
                await self.update_latest_data()
                
                # 2. Sync Equity (Positions synced inside loop)
                account = self.trading_client.get_account()
                equity = float(account.equity)
                
                # 3. Process Watchlist
                for ticker in self.watchlist:
                    # REAL-TIME INVENTORY CHECK (Added inside the loop)
                    current_positions = {p.symbol: p for p in self.trading_client.get_all_positions()}
                    
                    score, signals, price, atr = self.calculate_predator_score(ticker)
                    
                    if score >= 9:
                        if ticker not in current_positions:
                            qty = int((equity * 0.02) / price)
                            if qty > 0:
                                # Final check for existing pending orders for this specific ticker
                                existing_orders = self.trading_client.get_orders()
                                if any(o.symbol == ticker for o in existing_orders):
                                    print(f"⏳ Order already pending for {ticker}. Skipping.")
                                    continue
                                    
                                stop_loss_price = round(price - (atr * 2.5), 2)
                                take_profit_price = round(price + (atr * 7.5), 2)
                                print(f"🎯 PREDATOR ENTRY: {ticker} | Score: {score}")
                                try:
                                    self.trading_client.submit_order(
                                        MarketOrderRequest(
                                            symbol=ticker, qty=qty, side=OrderSide.BUY,
                                            time_in_force=TimeInForce.GTC, order_class="bracket",
                                            stop_loss={'stop_price': stop_loss_price},
                                            take_profit={'limit_price': take_profit_price}
                                        )
                                    )
                                    # Trade Card logic
                                    df_plot = self.data_cache[ticker].resample('4h').agg({
                                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                                    }).dropna()
                                    df_plot = calculate_alphatrend(df_plot)
                                    card_path = generate_trade_card(ticker, df_plot, price, stop_loss_price, take_profit_price, signals)
                                    print(f"📊 Trade Card generated: {card_path}")
                                    
                                    # ADD TO LOCAL POSITIONS TO PREVENT DOUBLE-DIP IN SAME LOOP
                                    positions[ticker] = True 
                                    
                                except Exception as e:
                                    print(f"❌ Order failed for {ticker}: {e}")

                    elif ticker in current_positions:
                        if "AlphaTrend Bullish" not in signals:
                            print(f"⚠️ PREDATOR EXIT: {ticker} | Trend Breakdown")
                            self.trading_client.close_position(ticker)

                await asyncio.sleep(300) # Check every 5 minutes instead of 1 minute
            except Exception as e:
                print(f"❌ Predator Engine Error: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    bot = AlphaPredator()
    asyncio.run(bot.execution_loop())
