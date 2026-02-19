# US Equities Alpha Predator Swing Bot

A robust, statistically-driven swing trading system for US Equities using Python, `vectorbt`, and `alpaca-py`.

## 🚀 Overview
The "Alpha Predator" engine is designed for high-conviction swing trading (4H timeframe) across a broad universe of ~2,500 tickers (S&P 500, Nasdaq 100, Dow 30, Russell 2000).

## 🛠 Features
- **Filter & Focus Pipeline**: Weekly macro screening of 2,400+ tickers to identify top candidates, reducing live API load.
- **12-Point Predator Scorecard**: A multi-factor scoring system including:
    - **AlphaTrend**: Core trend-following indicator.
    - **Trend Quality Alpha**: ADX (Intensity), R² (Smoothness), and Linear Regression Slope (Acceleration).
    - **RSI Alpha**: Automated detection of Bullish Momentum Divergence.
    - **Relative Strength**: Outperformance vs. SPY.
    - **Sector Tailwinds**: Peer group correlation analysis.
- **Automated Execution**: Bracket orders (Stop Loss & Take Profit) via Alpaca Paper/Live API.
- **Limit Order Protection**: Automated Limit Order logic with price-gap protection for market opens.
- **Technical Auditing**: Full lifecycle tracking of every trade in `data/trades_audit.json`, including entry scores, specific indicator signals, and exit reasons for strategy optimization.

## 📁 Structure
- `predator_engine.py`: The live execution engine (resamples 1H to 4H).
- `alpha_screener_expanded.py`: The weekly batch screener.
- `trend_alpha.py`: Logic for Trend Quality metrics.
- `rsi_alpha.py`: Logic for RSI Divergence and support bounces.
- `indicators.py`: Implementation of the AlphaTrend indicator.
- `visualizer.py`: Generates trade cards for entry signals.
- `logger_alpha.py`: Handles structured technical auditing and performance logging.

## 📊 Strategy: The Alpha Predator
**Goal**: Identify "Institutional-Quality Runners" or "Elite Reversal Coils."
- **Entry**: Score ≥ 9/12 on the 4-Hour timeframe.
- **Exit**: AlphaTrend trend breakdown or bracket closure.
- **Risk Management**: Dynamic ATR-based stop-loss and profit targets.
