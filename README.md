# Alpha Predator: Real-Time 4H Swing Bot 🦅

A high-performance autonomous trading daemon designed for **Tick-by-Tick monitoring** of US Equities. It evolves the Alpha Accumulator into a persistent "Predator" engine that executes high-conviction swings with institutional-grade filters.

## 🚀 The Predator Upgrade (New)
- **Real-Time Monitoring**: Moves from 4-hour polling to 1-minute stateful scanning.
- **Rolling Resampler**: Maintains a live 4-hour window updated every 60 seconds for precision execution.
- **Institutional Filters**: 
    - **Relative Strength**: Automatic outperformance check against SPY.
    - **Sector Tailwinds**: Symmetry check across SEMIS and BIG_TECH cohorts.
- **Elite Execution**: Hard-coded ATR-based Bracket Orders with exchange-side safety.

## 🧠 The 12-Point Predator Scorecard
The scoring system now incorporates macro and sector intelligence:

| Layer | Criteria | Score |
| :--- | :--- | :---: |
| **Macro** | Price > SMA 200 | **+2** |
| **Trend** | AlphaTrend K1 > K2 | **+3** |
| **Trigger** | Bullish Cross (Bar 1-2) | **+2** |
| **Value** | RSI < 35 | **+2** |
| **Breakout** | Price > Prev Day High | **+1** |
| **Strength** | Outperforming SPY (1D) | **+1** |
| **Sector** | 2+ Peers Bullish | **+1** |

**Thresholds**: 9+ Predator Entry | 5-8 Watch | <5 Ignore

## 📂 New Core Engine
- `predator_engine.py`: The persistent trading daemon.
- `visualizer.py`: Automated "Trade Card" chart generation.
- `strategy_config.md`: Updated rules for real-time operation.

---
*Disclaimer: For educational and paper trading purposes only.*
