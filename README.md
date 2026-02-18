# US Equities Swing Bot (Alpaca)

## Strategy Overview
**Type:** Swing Trading (Mean Reversion)
**Instrument:** US Equities (Stocks/ETFs)
**Timeframe:** Daily/Weekly
**Logic:**
- **Entry:** Oversold (RSI < 30)
- **Exit:** Overbought (RSI > 70)
- **Broker:** Alpaca (Paper Trading first)

## Setup
1.  **Dependencies:** `alpaca-py`, `pandas`, `ta-lib`
2.  **Auth:** Requires `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in `.env`
