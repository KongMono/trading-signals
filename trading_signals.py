import requests
import pandas as pd
import numpy as np
import os

import yfinance as yf

# --- CONFIG FROM ENVIRONMENT VARIABLES ---
# Yahoo Finance uses different symbol names
SYMBOLS = {"BTC": "BTC-USD", "DOGE": "DOGE-USD"}
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
        response = requests.post(url, json=payload)
        print(f"Telegram Response Status: {response.status_code}")
        response.raise_for_status()
    except Exception as e:
        print(f"Telegram ERROR: {e}")

def calculate_atr(df, period=10):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window=period).mean()

def calculate_supertrend(df, period=10, multiplier=3):
    atr = calculate_atr(df, period)
    hl2 = (df['High'] + df['Low']) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    df['st_uptrend'] = True
    for i in range(1, len(df)):
        if df['Close'].iloc[i] > upper_band.iloc[i-1]:
            df.loc[df.index[i], 'st_uptrend'] = True
        elif df['Close'].iloc[i] < lower_band.iloc[i-1]:
            df.loc[df.index[i], 'st_uptrend'] = False
        else:
            df.loc[df.index[i], 'st_uptrend'] = df['st_uptrend'].iloc[i-1]
            if df['st_uptrend'].iloc[i] and lower_band.iloc[i] < lower_band.iloc[i-1]:
                lower_band.iloc[i] = lower_band.iloc[i-1]
            if not df['st_uptrend'].iloc[i] and upper_band.iloc[i] > upper_band.iloc[i-1]:
                upper_band.iloc[i] = upper_band.iloc[i-1]
    return df

def run_check():
    # TEST TELEGRAM CONNECTION IMMEDIATELY
    print("--- DEBUG: Starting Telegram Connection Test ---")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("CRITICAL ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from GitHub Secrets!")
    else:
        send_telegram_message("🔍 *Bot Connection Test:* The script is starting now...")

    for display_symbol, yf_symbol in SYMBOLS.items():
        try:
            print(f"Fetching data for {yf_symbol} from Yahoo Finance...")
            ticker = yf.Ticker(yf_symbol)
            # Fetch last 100 days of daily data
            df = ticker.history(period="100d", interval="1d")
            
            if df.empty:
                print(f"Error: No data found for {yf_symbol}")
                continue
            
            df = calculate_supertrend(df)
            current_price_usd = df['Close'].iloc[-1]
            current_price_thb = current_price_usd * USD_THB_RATE
            
            is_uptrend = df['st_uptrend'].iloc[-1]
            was_uptrend = df['st_uptrend'].iloc[-2]
            
            # Check if this is a manual run from GitHub Actions
            run_type = os.getenv("RUN_TYPE", "manual")
            print(f"DEBUG: run_type detected as '{run_type}'")
            
            print(f"--- {display_symbol} Status ---")
            print(f"Price (USD): {current_price_usd:.4f} | Price (THB): {current_price_thb:,.2f}")
            print(f"Trend: {'UP' if is_uptrend else 'DOWN'}")
            
            status_msg = f"📊 *{display_symbol}/THB Daily Update*\nPrice (THB): ฿{current_price_thb:,.2f}\nPrice (USD): ${current_price_usd:,.4f}\nTrend: {'🟢 BULLISH' if is_uptrend else '🔴 BEARISH'}\n"
            
            if is_uptrend and not was_uptrend:
                alert = "🚀 *SIGNAL: BUY (Green Dot Triggered!)*"
                send_telegram_message(status_msg + alert)
            elif not is_uptrend and was_uptrend:
                alert = "⚠️ *SIGNAL: SELL (Trend flipped to DOWN)*"
                send_telegram_message(status_msg + alert)
            else:
                # Always send on manual check for testing
                print(f"Sending manual update for {display_symbol}...")
                send_telegram_message(status_msg + "_Manual Status Check (No trend change)_")
                
        except Exception as e:
            print(f"Error checking {display_symbol}: {e}")
                
        except Exception as e:
            print(f"Error checking {symbol}: {e}")

if __name__ == "__main__":
    run_check()
