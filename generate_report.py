import sys
import os
import asyncio
import pandas as pd
from datetime import datetime
import pytz

# Add the current directory to sys.path to allow imports if running from inside stock-bot
sys.path.append(os.getcwd())

from predator_engine import AlphaPredator

# Set timezone
tz = pytz.timezone('America/Chicago')

async def main():
    # Suppress normal output to capture just the report
    bot = AlphaPredator()
    
    # Manually trigger data loading
    # initialize_data is an async method
    await bot.initialize_data()
    
    # Get the watchlist
    watchlist = bot.watchlist
    
    report_lines = []
    report_lines.append(f"🦁 **Alpha Predator Morning Briefing**")
    report_lines.append(f"📅 {datetime.now(tz).strftime('%A, %b %d')} | ⏰ 8:30 AM CST")
    report_lines.append(f"🎯 **High-Beta Watchlist Scan (4H)**")
    report_lines.append("")
    
    high_priority = []
    others = []
    
    for ticker in watchlist:
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
