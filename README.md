# Alpha Accumulator: Elite 4H Swing Bot 🚀

A professional-grade US Equities swing trading bot built for high-conviction momentum trading on the **4-Hour (240 min)** timeframe. It combines mean-reversion dip buying with volume-supported trend confirmation to target 5-8 high-alpha trades per month.

## 🧠 The Strategy: Hybrid Alpha Accumulator
The bot uses a proprietary **10-Point Scoring System** to filter the S&P 500 for the highest probability setups.

### 1. The 10-Point Scorecard
| Layer | Criteria | Score | Purpose |
| :--- | :--- | :---: | :--- |
| **Macro** | Price > SMA 200 | **+2** | Filter for long-term bull markets. |
| **Trend** | AlphaTrend K1 > K2 | **+3** | Confirms momentum is bullish. |
| **Trigger** | Bullish Cross (Bar 1-2) | **+2** | Bonus for early entry. |
| **Value** | RSI < 35 | **+2** | "Buying the Sale" (Deep Dip). |
| **Breakout** | Price > Prev Day High | **+1** | Confirms price is reclaiming levels. |

### 2. Guardrails (Elite Edition)
- **ATR-Based Stops**: Automatically sets stop losses at `2.5 x ATR` below entry to adjust for individual stock volatility.
- **Bracket Orders**: Submits Take Profit and Stop Loss directly to the Alpaca exchange for second-by-second protection.
- **Risk Management**: Strictly limited to **5% equity per position**.

## 🛠️ Infrastructure
- **Broker**: Alpaca (Paper/Live)
- **Timeframe**: 4-Hour (The Swing "Sweet Spot")
- **Universe**: High-Beta Growth Tickers (`NVDA, TSLA, AMD, META, NFLX, AMZN, MSFT, GOOGL, AVGO, SMCI, ARM, PLTR, QCOM, AAPL`)
- **Execution**: Automated via `active_trader.py` on a 4-hour cron cycle (Market Hours).

## 📂 File Structure
- `active_trader.py`: The main execution engine.
- `indicators.py`: Central library for AlphaTrend, RSI, and Bollinger logic.
- `visualizer.py`: Generates professional trade cards (charts) for every entry.
- `backtest_4h_swing.py`: 2-year performance evaluator for 4H logic.
- `strategy_config.md`: Detailed parameters and entry/exit rules.

## 🚀 Quick Start
1. Clone the repo.
2. Add your `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` to a `.env` file.
3. Run the scanner: `python3 active_trader.py`.

## 📈 Performance Summary (4H NVDA Backtest)
- **Total Return**: 231.2%
- **Trades/Month**: ~1.5 per ticker
- **Avg Hold**: 10.2 Days

---
*Disclaimer: For educational and paper trading purposes only.*
