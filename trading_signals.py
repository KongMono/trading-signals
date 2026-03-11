import requests
import pandas as pd
import numpy as np
import os

# --- CONFIG FROM ENVIRONMENT VARIABLES ---
SYMBOLS = ["DOGEUSDT", "BTCUSDT"]  # Using USDT for better rate conversion
USD_THB_RATE = 36.5  # Approximate Thai Baht rate
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram config missing. Skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def calculate_atr(df, period=10):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

def calculate_supertrend(df, period=10, multiplier=3):
    atr = calculate_atr(df, period)
    hl2 = (df['high'] + df['low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    df['st_uptrend'] = True
    for i in range(1, len(df)):
        if df['close'].iloc[i] > upper_band.iloc[i-1]:
            df.loc[df.index[i], 'st_uptrend'] = True
        elif df['close'].iloc[i] < lower_band.iloc[i-1]:
            df.loc[df.index[i], 'st_uptrend'] = False
        else:
            df.loc[df.index[i], 'st_uptrend'] = df['st_uptrend'].iloc[i-1]
            if df['st_uptrend'].iloc[i] and lower_band.iloc[i] < lower_band.iloc[i-1]:
                lower_band.iloc[i] = lower_band.iloc[i-1]
            if not df['st_uptrend'].iloc[i] and upper_band.iloc[i] > upper_band.iloc[i-1]:
                upper_band.iloc[i] = upper_band.iloc[i-1]
    return df

def run_check():
    for symbol in SYMBOLS:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol.upper()}&interval=1d&limit=100"
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'])
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            df = calculate_supertrend(df)
            current_price_usd = df['close'].iloc[-1]
            current_price_thb = current_price_usd * USD_THB_RATE
            
            is_uptrend = df['st_uptrend'].iloc[-1]
            was_uptrend = df['st_uptrend'].iloc[-2]
            
            print(f"--- {symbol} Status ---")
            print(f"Price (USD): {current_price_usd} | Price (THB): {current_price_thb:,.2f}")
            print(f"Trend: {'UP' if is_uptrend else 'DOWN'}")
            
            # Formatting symbols for display
            display_symbol = symbol.replace("USDT", "")
            status_msg = f"📊 *{display_symbol}/THB Daily Update*\nPrice (THB): ฿{current_price_thb:,.2f}\nPrice (USD): ${current_price_usd}\nTrend: {'🟢 BULLISH' if is_uptrend else '🔴 BEARISH'}\n"
            
            if is_uptrend and not was_uptrend:
                alert = "🚀 *SIGNAL: BUY (Green Dot Triggered!)*"
                send_telegram_message(status_msg + alert)
            elif not is_uptrend and was_uptrend:
                alert = "⚠️ *SIGNAL: SELL (Trend flipped to DOWN)*"
                send_telegram_message(status_msg + alert)
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    run_check()
