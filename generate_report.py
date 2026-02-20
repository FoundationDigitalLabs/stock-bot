import sys
import os
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Add the current directory to sys.path to allow imports if running from inside stock-bot
sys.path.append(os.getcwd())

from predator_engine import AlphaPredator

# Set timezone
tz = pytz.timezone('America/Chicago')

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

class AlphaPredatorBatched(AlphaPredator):
    async def initialize_data(self):
        """Batched data fetch to avoid timeouts/limits."""
        print("📥 Priming Predator Data Cache (Batched)...", file=sys.stderr)
        start_date = datetime.now() - timedelta(days=100)
        all_tickers = self.watchlist + [self.benchmark]
        
        chunk_size = 20  # Fetch 20 at a time
        total_chunks = (len(all_tickers) + chunk_size - 1) // chunk_size
        
        for i in range(0, len(all_tickers), chunk_size):
            chunk = all_tickers[i:i + chunk_size]
            print(f"  Fetching batch {i//chunk_size + 1}/{total_chunks} ({len(chunk)} tickers)...", file=sys.stderr)
            
            try:
                from alpaca.data.requests import StockBarsRequest
                from alpaca.data.timeframe import TimeFrame
                
                request_params = StockBarsRequest(
                    symbol_or_symbols=chunk,
                    timeframe=TimeFrame.Hour,
                    start=start_date,
                    adjustment='all'
                )
                bars = self.data_client.get_stock_bars(request_params).df
                
                for ticker in chunk:
                    if ticker in bars.index.get_level_values(0):
                        df = bars.xs(ticker).copy()
                        df.columns = [c.capitalize() for c in df.columns]
                        self.data_cache[ticker] = df
            except Exception as e:
                print(f"⚠️ Error fetching batch {i//chunk_size + 1}: {e}", file=sys.stderr)
                
        self.last_sync = datetime.now()
        print("✅ Cache Primed.", file=sys.stderr)

async def main():
    # Suppress normal output to capture just the report
    bot = AlphaPredatorBatched()
    print("Bot initialized.", file=sys.stderr)
    
    # Manually trigger data loading
    # initialize_data is an async method
    print("Loading data for watchlist...", file=sys.stderr)
    await bot.initialize_data()
    print("Data loaded.", file=sys.stderr)
    
    # Get the watchlist
    watchlist = bot.watchlist
    print(f"Scanning {len(watchlist)} tickers...", file=sys.stderr)
    
    report_lines = []
    report_lines.append(f"🦁 **Alpha Predator Morning Briefing**")
    report_lines.append(f"📅 {datetime.now(tz).strftime('%A, %b %d')} | ⏰ 8:30 AM CST")
    report_lines.append(f"🎯 **High-Beta Watchlist Scan (4H)**")
    report_lines.append("")
    
    high_priority = []
    others = []
    
    for i, ticker in enumerate(watchlist):
        if i % 10 == 0:
            print(f"Scanning {i+1}/{len(watchlist)}: {ticker}", file=sys.stderr)
        try:
            score, signals, price, atr = bot.calculate_predator_score(ticker)
            
            # Format: Ticker: Score | Price | Signals
            line = f"• **{ticker}**: Score {score}/12 | ${price:.2f}"
            if signals:
                line += f" | {', '.join(signals)}"
            
            if score >= 8:
                high_priority.append(line)
            else:
                others.append(line)
        except Exception as e:
            # Silently fail for report cleanliness, or log to stderr
            sys.stderr.write(f"Error scanning {ticker}: {e}\n")
            
    if high_priority:
        report_lines.append("🚀 **HIGH PRIORITY (Score 8+)**")
        for line in high_priority:
            report_lines.append(line)
        report_lines.append("")
        
    if others:
        report_lines.append("👀 **Watchlist**")
        # Sort others by score descending
        others.sort(key=lambda x: int(x.split('Score ')[1].split('/')[0]), reverse=True)
        for line in others:
            report_lines.append(line)
            
    print("\n".join(report_lines))

if __name__ == "__main__":
    asyncio.run(main())
