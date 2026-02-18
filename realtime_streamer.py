import os
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.live import StockDataStream
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# Import our strategy logic
from indicators import calculate_alphatrend
import pandas_ta as ta

class LiveAlphaStreamer:
    def __init__(self, paper=True):
        load_dotenv("stock-bot/.env")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        self.trading_client = TradingClient(self.api_key, self.secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(self.api_key, self.secret_key)
        self.stream_client = StockDataStream(self.api_key, self.secret_key)
        
        self.watchlist = ["NVDA", "TSLA", "AMD", "META", "NFLX", "AMZN", "MSFT", "GOOGL", "AVGO", "SMCI", "ARM", "PLTR", "QCOM", "AAPL"]
        
        # Local cache for price data to avoid constant API calls
        self.price_history = {} # {ticker: dataframe}
        self.last_bar_time = {} # {ticker: timestamp}

    async def on_bar(self, bar):
        """
        This triggers every time a new 1-minute bar is completed for ANY watched stock.
        """
        symbol = bar.symbol
        print(f"Tick received for {symbol}: {bar.close}")
        
        # 1. Update local history
        # (In a production bot, we would append the new bar to our 4H resampler)
        # For now, we trigger our Alpha Scan whenever a stock moves
        
    def start_streaming(self):
        print(f"🚀 Initializing Live Stream for {len(self.watchlist)} stocks...")
        # Subscribe to bars for the watchlist
        self.stream_client.subscribe_bars(self.on_bar, *self.watchlist)
        self.stream_client.run()

if __name__ == "__main__":
    # This is the architectural skeleton for the Real-Time upgrade
    print("Real-Time Streamer concept loaded. Ready for implementation.")
