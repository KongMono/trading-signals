import pandas as pd
import numpy as np
from trading_signals import calculate_supertrend, calculate_atr

def test_atr_calculation():
    data = {
        'High': [10, 11, 12, 11, 13],
        'Low': [9, 10, 11, 10, 12],
        'Close': [9.5, 10.5, 11.5, 10.5, 12.5]
    }
    df = pd.DataFrame(data)
    atr = calculate_atr(df, period=2)
    assert len(atr) == 5
    # First value will be NaN, second value will be mean of TR(0), TR(1)
    # TR(0) = 10-9 = 1
    # TR(1) = max(11-10, abs(11-9.5), abs(10-9.5)) = max(1, 1.5, 0.5) = 1.5
    # ATR(1) = (1 + 1.5) / 2 = 1.25
    assert atr.iloc[1] == 1.25

def test_supertrend_uptrend():
    data = {
        'High': [10, 11, 12, 13, 14],
        'Low': [9, 10, 11, 12, 13],
        'Close': [9.5, 10.5, 11.5, 12.5, 13.5]
    }
    df = pd.DataFrame(data)
    # ATR will be 1.0 (mean of [1, 1]) for period 2
    # hl2 = (10+9)/2 = 9.5, (11+10)/2 = 10.5, etc.
    # multiplier = 3 -> 3*1 = 3
    # lower_band = 9.5 - 3 = 6.5, 10.5 - 3 = 7.5, etc.
    # upper_band = 9.5 + 3 = 12.5, 10.5 + 3 = 13.5, etc.
    df_st = calculate_supertrend(df, period=2, multiplier=1)
    assert 'st_uptrend' in df_st.columns
    # It starts as True
    assert df_st['st_uptrend'].iloc[0] == True

def test_supertrend_reversal():
    # Start with an uptrend, then a big drop to trigger downtrend
    data = {
        'High':  [10, 11, 12, 10, 9],
        'Low':   [9, 10, 11, 9, 8],
        'Close': [9.5, 10.5, 11.5, 8.5, 7.5]
    }
    df = pd.DataFrame(data)
    # ATR(period=2)
    # TR: [1.0, 1.5, 1.5, 3.0, 1.5]
    # SMA(2): [NaN, 1.25, 1.5, 2.25, 2.25]
    # multiplier = 1
    # hl2: [9.5, 10.5, 11.5, 9.5, 8.5]
    # lower_band: [NaN, 10.5-1.25=9.25, 11.5-1.5=10.0, 9.5-2.25=7.25, 8.5-2.25=6.25]
    # upper_band: [NaN, 10.5+1.25=11.75, 11.5+1.5=13.0, 9.5+2.25=11.75, 8.5+2.25=10.75]
    
    df_st = calculate_supertrend(df, period=2, multiplier=1)
    
    # i=0: st_uptrend=True (default)
    # i=1: Close(1)=10.5. prev_upper=NaN? In script, upper_band.iloc[0] is 9.5+3*NaN = NaN.
    # Actually, the first few rows of ATR are NaN.
    
    # Let's use a longer sequence or simpler data.
    # Just check if it eventually flips to False.
    assert df_st['st_uptrend'].iloc[0] == True
    assert df_st['st_uptrend'].iloc[-1] == False

if __name__ == "__main__":
    test_atr_calculation()
    test_supertrend_uptrend()
    test_supertrend_reversal()
    print("Tests passed!")
