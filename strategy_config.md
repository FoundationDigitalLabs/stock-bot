# Strategy Configuration: Hybrid Alpha Accumulator

## Core Parameters
- **Timeframe**: 4h (240 Minutes)
- **Moving Average**: 200 SMA (Simple)
- **RSI Period**: 14
- **RSI Oversold**: 30
- **AlphaTrend Period**: 14
- **AlphaTrend Multiplier**: 1.0
- **Volume Filter**: MFI (Money Flow Index) Period 14, Threshold 50

## Entry Logic (Long Only)
1. **Condition A (Macro)**: `Close > SMA(200)`
2. **Condition B (Opportunity)**: `RSI < 30` OR `Price < Lower Bollinger Band`
3. **Condition C (Trigger)**: `AlphaTrend K1 > AlphaTrend K2` AND `Prev K1 <= Prev K2`

**Final Entry**: `Condition A` AND (`Condition B` OR `Condition C`)

## Exit Logic
1. **Trend Exit**: `AlphaTrend K1 < AlphaTrend K2`
2. **Profit Target**: Optional (Currently trailing via AlphaTrend)
3. **Stop Loss**: Initial stop at recent swing low or AlphaTrend line.

## Target Watchlist
- NVDA, TSLA, AMD, META, NFLX, AMZN, MSFT, GOOGL.
- High-volatility S&P 500 constituents.
