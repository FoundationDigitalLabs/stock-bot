import os
import pandas as pd
import numpy as np
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas_ta as ta
import time

# Import our verified indicators
from indicators import calculate_alphatrend
from visualizer import generate_trade_card

class ActiveAlphaTrader:
    def __init__(self):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        # Explicitly setting paper=True for safety
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=True)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        
        self.watchlist = ["NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AVGO", "SMCI", "ARM", "PLTR", "QCOM", "AAPL"]
        self.log_file = "stock-bot/data/paper_trade_log.csv"

    def get_signals(self):
        results = []
        start_date = datetime.now() - timedelta(days=100) # Enough for 200 SMA on 4H
        
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=self.watchlist,
                timeframe=TimeFrame.Hour,
                start=start_date,
                adjustment='all'
            )
            bars = self.data_client.get_stock_bars(request_params).df
            
            for ticker in self.watchlist:
                try:
                    if ticker not in bars.index.get_level_values(0): continue
                    
                    df_hour = bars.xs(ticker).copy()
                    df_hour.columns = [col.capitalize() for col in df_hour.columns]
                    
                    df = df_hour.resample('4h').agg({
                        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                    }).dropna()
                    
                    if len(df) < 200: continue
                    
                    df['Sma200'] = df['Close'].rolling(200).mean()
                    df = calculate_alphatrend(df)
                    df['rsi'] = ta.rsi(df['Close'], length=14)
                    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
                    
                    last = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    # 10-POINT SCORING
                    score = 0
                    if last['Close'] > last['Sma200']: score += 2
                    if last['At_k1'] > last['At_k2']: score += 3
                    if (last['At_k1'] > last['At_k2']) and (prev['At_k1'] <= prev['At_k2']): score += 2
                    if last['rsi'] < 35: score += 2
                    elif last['rsi'] < 45: score += 1
                    if last['Close'] > prev['High']: score += 1

                    results.append({
                        "Ticker": ticker,
                        "Score": score,
                        "Price": last['Close'],
                        "At_Bullish": last['At_k1'] > last['At_k2'],
                        "ATR": last['atr']
                    })
                except Exception as e:
                    print(f"Error signal {ticker}: {e}")
        except Exception as e:
            print(f"Error fetching data: {e}")
        return results

    def execute_trades(self, signals):
        # Get current positions
        positions = {p.symbol: p for p in self.trading_client.get_all_positions()}
        account = self.trading_client.get_account()
        equity = float(account.equity)
        
        for sig in signals:
            symbol = sig['Ticker']
            score = sig['Score']
            price = sig['Price']
            is_bullish = sig['At_Bullish']
            atr = sig.get('ATR', price * 0.03) # Fallback to 3% if ATR fails
            
            # 1. EXIT LOGIC (For Trend Breakdown)
            if symbol in positions:
                if not is_bullish:
                    print(f"EXIT: {symbol} - AlphaTrend Bearish Flip.")
                    self.trading_client.close_position(symbol)
                    self.log_trade(symbol, "SELL_TREND", price, 0, score)
                    # Note: Bracket Stop Loss is handled by the exchange, 
                    # but we exit manually if the TREND snaps before the stop.

            # 2. ENTRY LOGIC (With Bracket Orders & ATR Stops)
            elif score >= 8 and symbol not in positions:
                qty = int((equity * 0.05) / price)
                
                if qty > 0:
                    # PRO FEATURE: ATR-Based Stop Loss (2.5 * ATR)
                    # We set a Take Profit at 3x the risk (Risk/Reward 1:3)
                    stop_loss_price = round(price - (atr * 2.5), 2)
                    take_profit_price = round(price + (atr * 7.5), 2)
                    
                    print(f"ENTRY: {symbol} at {price} (Score: {score})")
                    print(f"BRACKET: Stop at {stop_loss_price}, Target at {take_profit_price}")
                    
                    try:
                        self.trading_client.submit_order(
                            MarketOrderRequest(
                                symbol=symbol,
                                qty=qty,
                                side=OrderSide.BUY,
                                time_in_force=TimeInForce.GTC,
                                order_class="bracket",
                                stop_loss={'stop_price': stop_loss_price},
                                take_profit={'limit_price': take_profit_price}
                            )
                        )
                        self.log_trade(symbol, "BUY_BRACKET", price, qty, score)
                        # Feature #4: Generate and send Trade Card
                        chart_path = generate_trade_card(symbol, df, price, stop_loss_price, take_profit_price, signals)
                        print(f"CHART GENERATED: {chart_path}")
                    except Exception as e:
                        print(f"Failed to place bracket order for {symbol}: {e}")

    def log_trade(self, symbol, side, price, qty, score):
        log_entry = pd.DataFrame([{
            "Timestamp": datetime.now(),
            "Symbol": symbol,
            "Side": side,
            "Price": price,
            "Qty": qty,
            "Score": score
        }])
        log_entry.to_csv(self.log_file, mode='a', header=not os.path.exists(self.log_file), index=False)

if __name__ == "__main__":
    trader = ActiveAlphaTrader()
    print("Running Active Trader Cycle...")
    signals = trader.get_signals()
    trader.execute_trades(signals)
    print("Cycle Complete.")
