import vectorbt as vbt
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv("stock-bot/.env")
client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))

def get_data(ticker="SPY"):
    start_date = datetime.now() - timedelta(days=365 * 5)
    request_params = StockBarsRequest(symbol_or_symbols=ticker, timeframe=TimeFrame.Day, start=start_date, adjustment='all')
    bars = client.get_stock_bars(request_params).df
    df = bars.xs(ticker).copy()
    df.columns = [col.capitalize() for col in df.columns]
    return df

def run_test(name, df, entries, exits):
    try:
        pf = vbt.Portfolio.from_signals(df['Close'], entries, exits, init_cash=10000, fees=0.001, freq='1D')
        return {
            "Indicator": name,
            "Return %": round(pf.total_return() * 100, 2),
            "Sharpe": round(pf.sharpe_ratio(), 2),
            "MaxDD %": round(pf.max_drawdown() * 100, 2),
            "Trades": pf.trades.count()
        }
    except:
        return None

def batch_1(df):
    results = []
    close = df['Close']
    
    # 1. EMA Cross (9/21)
    ema9 = ta.ema(close, 9)
    ema21 = ta.ema(close, 21)
    results.append(run_test("EMA Cross (9/21)", df, (ema9 > ema21) & (ema9.shift(1) <= ema21.shift(1)), (ema9 < ema21) & (ema9.shift(1) >= ema21.shift(1))))

    # 2. Stochastic RSI
    stoch = ta.stochrsi(close)
    results.append(run_test("Stoch RSI", df, (stoch.iloc[:,0] < 20) & (stoch.iloc[:,0] > stoch.iloc[:,1]), (stoch.iloc[:,0] > 80)))

    # 3. Hull MA (HMA 20)
    hma = ta.hma(close, 20)
    results.append(run_test("Hull MA", df, (close > hma) & (close.shift(1) <= hma.shift(1)), (close < hma)))

    # 4. Williams %R
    will = ta.willr(df['High'], df['Low'], close)
    results.append(run_test("Williams %R", df, (will < -80), (will > -20)))

    # 5. Fisher Transform
    fish = ta.fisher(df['High'], df['Low'])
    results.append(run_test("Fisher Transform", df, (fish.iloc[:,0] > fish.iloc[:,1]), (fish.iloc[:,0] < fish.iloc[:,1])))

    # 6. Donchian Channels (20)
    dc = ta.donchian(df['High'], df['Low'], lower_length=20, upper_length=20)
    results.append(run_test("Donchian Channels", df, (close >= dc.iloc[:,2]), (close <= dc.iloc[:,0])))

    # 7. Keltner Channels
    kc = ta.kc(df['High'], df['Low'], close)
    results.append(run_test("Keltner Channels", df, (close < kc.iloc[:,0]), (close > kc.iloc[:,2])))

    # 8. ADX (Trend Strength)
    adx = ta.adx(df['High'], df['Low'], close)
    results.append(run_test("ADX Trend", df, (adx.iloc[:,0] > 25) & (adx.iloc[:,1] > adx.iloc[:,2]), (adx.iloc[:,2] > adx.iloc[:,1])))

    # 9. RSI Strategy (Standard 30/70)
    rsi = ta.rsi(close)
    results.append(run_test("RSI (30/70)", df, (rsi < 30), (rsi > 70)))
    
    # 10. MFI (Money Flow)
    mfi = ta.mfi(df['High'], df['Low'], close, df['Volume'])
    results.append(run_test("MFI (20/80)", df, (mfi < 20), (mfi > 80)))

    return [r for r in results if r is not None]

def batch_2(df):
    results = []
    close = df['Close']
    high = df['High']
    low = df['Low']
    vol = df['Volume']
    
    # 1. Chaikin Money Flow (CMF)
    cmf = ta.cmf(high, low, close, vol)
    results.append(run_test("CMF (Trend)", df, (cmf > 0.1), (cmf < -0.1)))

    # 2. OBV (On-Balance Volume)
    obv = ta.obv(close, vol)
    results.append(run_test("OBV Breakout", df, (obv > obv.rolling(20).mean()), (obv < obv.rolling(20).mean())))

    # 3. CCI (Commodity Channel Index)
    cci = ta.cci(high, low, close)
    results.append(run_test("CCI (100/-100)", df, (cci < -100), (cci > 100)))

    # 4. TRIX
    trix = ta.trix(close)
    results.append(run_test("TRIX", df, (trix.iloc[:,0] > 0), (trix.iloc[:,0] < 0)))

    # 5. Vortex Indicator
    vortex = ta.vortex(high, low, close)
    results.append(run_test("Vortex", df, (vortex.iloc[:,0] > vortex.iloc[:,1]), (vortex.iloc[:,0] < vortex.iloc[:,1])))

    # 6. Awesome Oscillator
    ao = ta.ao(high, low)
    results.append(run_test("Awesome Osc", df, (ao > 0) & (ao.shift(1) <= 0), (ao < 0)))

    # 7. Parabolic SAR
    psar = ta.psar(high, low, close)
    results.append(run_test("Parabolic SAR", df, (close > psar.iloc[:,0]), (close < psar.iloc[:,2])))

    # 8. Aroon
    aroon = ta.aroon(high, low)
    results.append(run_test("Aroon Trend", df, (aroon.iloc[:,0] > 70), (aroon.iloc[:,1] > 70)))

    # 9. RVI (Relative Vigor Index)
    # results.append(run_test("RVI Osc", df, (rvi.iloc[:,0] > rvi.iloc[:,1]), (rvi.iloc[:,0] < rvi.iloc[:,1])))
    # RVI can be tricky in pandas-ta, skipping for speed

    # 10. Coppock Curve
    coppock = ta.coppock(close)
    results.append(run_test("Coppock Curve", df, (coppock > 0), (coppock < 0)))

    return [r for r in results if r is not None]

def batch_3(df):
    results = []
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # 1. DEMA (9/21 Cross)
    dema9 = ta.dema(close, 9)
    dema21 = ta.dema(close, 21)
    results.append(run_test("DEMA Cross", df, (dema9 > dema21), (dema9 < dema21)))

    # 2. TEMA (9/21 Cross)
    tema9 = ta.tema(close, 9)
    tema21 = ta.tema(close, 21)
    results.append(run_test("TEMA Cross", df, (tema9 > tema21), (tema9 < tema21)))

    # 3. Kaufman Adaptive MA (KAMA)
    kama = ta.kama(close)
    results.append(run_test("KAMA Trend", df, (close > kama), (close < kama)))

    # 4. Linear Regression Slope
    slope = ta.slope(close)
    results.append(run_test("LinReg Slope", df, (slope > 0), (slope < 0)))

    # 5. Balance of Power (BOP)
    bop = ta.bop(df['Open'], high, low, close)
    results.append(run_test("Balance of Power", df, (bop > 0), (bop < 0)))

    # 6. TSI (True Strength Index)
    tsi = ta.tsi(close)
    results.append(run_test("TSI Osc", df, (tsi.iloc[:,0] > tsi.iloc[:,1]), (tsi.iloc[:,0] < tsi.iloc[:,1])))

    # 7. Mass Index
    mass = ta.massi(high, low)
    results.append(run_test("Mass Index", df, (mass < 27), (mass > 27)))

    # 8. QStick
    qstick = ta.qstick(df['Open'], close)
    results.append(run_test("QStick", df, (qstick > 0), (qstick < 0)))

    # 9. Median Price
    med = ta.median(close)
    results.append(run_test("Median Price", df, (close > med), (close < med)))

    # 10. CMO (Chande Momentum Osc)
    cmo = ta.cmo(close)
    results.append(run_test("CMO (Buy/Sell)", df, (cmo < -50), (cmo > 50)))

    return [r for r in results if r is not None]

def batch_4(df):
    results = []
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # 1. Z-Score (Buy < -2, Sell > 2)
    zscore = ta.zscore(close, length=20)
    results.append(run_test("Z-Score", df, (zscore < -2), (zscore > 2)))

    # 2. Know Sure Thing (KST)
    kst = ta.kst(close)
    results.append(run_test("KST", df, (kst.iloc[:,0] > kst.iloc[:,1]), (kst.iloc[:,0] < kst.iloc[:,1])))

    # 3. PPO (Percentage Price Osc)
    ppo = ta.ppo(close)
    results.append(run_test("PPO Cross", df, (ppo.iloc[:,0] > ppo.iloc[:,1]), (ppo.iloc[:,0] < ppo.iloc[:,1])))

    # 4. Elder Ray Index (Bull Power)
    # bull = ta.eri(high, low, close)
    # skipping eri due to pandas-ta implementation variance

    # 5. VHF (Vertical Horizontal Filter)
    vhf = ta.vhf(close)
    results.append(run_test("VHF Trend", df, (vhf > 0.4), (vhf < 0.2)))

    # 6. Chande Kroll Stop
    ck = ta.cksp(high, low, close)
    results.append(run_test("Chande Kroll", df, (close > ck.iloc[:,1]), (close < ck.iloc[:,0])))

    # 7. NATR (Normalized ATR)
    natr = ta.natr(high, low, close)
    results.append(run_test("NATR Filter", df, (natr < 2), (natr > 4)))

    # 8. CTI (Correlation Trend Indicator)
    cti = ta.cti(close)
    results.append(run_test("CTI Trend", df, (cti > 0.5), (cti < -0.5)))

    # 9. squeeze (TTM Squeeze)
    sqz = ta.squeeze(high, low, close)
    results.append(run_test("TTM Squeeze", df, (sqz.iloc[:,3] > 0), (sqz.iloc[:,3] < 0)))

    # 10. SuperTrend (10/3) - explicitly using ta.supertrend
    st = ta.supertrend(high, low, close)
    results.append(run_test("Standard SuperTrend", df, (st.iloc[:,1] == 1), (st.iloc[:,1] == -1)))

    return [r for r in results if r is not None]

def batch_5(df):
    results = []
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # 1. WaveTrend (LazyBear logic simplified)
    ap = (high + low + close) / 3
    esa = ta.ema(ap, 10)
    d = ta.ema(abs(ap - esa), 10)
    ci = (ap - esa) / (0.015 * d)
    wt1 = ta.ema(ci, 21)
    wt2 = ta.sma(wt1, 4)
    results.append(run_test("WaveTrend", df, (wt1 < -60) & (wt1 > wt2), (wt1 > 60)))

    # 2. Squeeze Momentum (Simplified)
    # Already tested TTM Squeeze which is the basis
    
    # 3. Ichimoku Cloud (Full)
    ichi = ta.ichimoku(high, low, close)[0]
    # Span A (col 2) > Span B (col 3)
    results.append(run_test("Ichimoku Cloud", df, (ichi.iloc[:,0] > ichi.iloc[:,1]) & (close > ichi.iloc[:,0]), (close < ichi.iloc[:,1])))

    # 4. SSL Channel (Simplified)
    sma_h = ta.sma(high, 10)
    sma_l = ta.sma(low, 10)
    results.append(run_test("SSL Channel", df, (close > sma_h), (close < sma_l)))

    # 5. McGinley Dynamic
    # Not in pandas-ta, but we can approximate with a very smooth EMA
    mcg = ta.ema(close, 20) # Approximation
    results.append(run_test("McGinley (Approx)", df, (close > mcg), (close < mcg)))

    # 6. ALMA (Arnaud Legoux Moving Average)
    alma = ta.alma(close)
    results.append(run_test("ALMA Trend", df, (close > alma), (close < alma)))

    # 7. VIDYA (Variable Index Dynamic Average)
    vidya = ta.vidya(close)
    results.append(run_test("VIDYA Trend", df, (close > vidya), (close < vidya)))

    # 8. Sinewave
    # sine = ta.sinewave(close)
    # results.append(run_test("Sinewave", df, (sine.iloc[:,0] > sine.iloc[:,1]), (sine.iloc[:,0] < sine.iloc[:,1])))

    # 9. TRAMA (Trend Regularity Adaptive)
    # trama = ta.trama(close)
    # results.append(run_test("TRAMA Trend", df, (close > trama), (close < trama)))

    # 10. RVGI (Relative Vigor Index)
    rvgi = ta.rvgi(df['Open'], high, low, close)
    results.append(run_test("RVGI Osc", df, (rvgi.iloc[:,0] > rvgi.iloc[:,1]), (rvgi.iloc[:,0] < rvgi.iloc[:,1])))

    return [r for r in results if r is not None]

if __name__ == "__main__":
    print("Fetching data...")
    df = get_data()
    print("Running Batch 1...")
    res = batch_1(df)
    print("Running Batch 2...")
    res.extend(batch_2(df))
    print("Running Batch 3...")
    res.extend(batch_3(df))
    print("Running Batch 4...")
    res.extend(batch_4(df))
    print("Running Batch 5...")
    res.extend(batch_5(df))
    
    # Add B&H Benchmark
    benchmark_pf = vbt.Portfolio.from_holding(df['Close'], init_cash=10000, freq='1D')
    res.append({
        "Indicator": "BUY & HOLD (Benchmark)",
        "Return %": round(benchmark_pf.total_return() * 100, 2),
        "Sharpe": round(benchmark_pf.sharpe_ratio(), 2),
        "MaxDD %": round(benchmark_pf.max_drawdown() * 100, 2),
        "Trades": 1
    })
    
    print(pd.DataFrame(res).sort_values(by="Sharpe", ascending=False).to_markdown(index=False))
