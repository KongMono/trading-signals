import requests
import pandas as pd
import numpy as np
import os
import yfinance as yf

# --- CONFIG FROM ENVIRONMENT VARIABLES ---
SYMBOLS = {"BTC": "BTC-USD", "ETH": "ETH-USD", "DOGE": "DOGE-USD"}
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
    
    # Calculate basic bands
    basic_ub = hl2 + (multiplier * atr)
    basic_lb = hl2 - (multiplier * atr)
    
    # Convert to numpy for performance and avoiding Series issues in loop
    close = df['Close'].values
    ub = basic_ub.values
    lb = basic_lb.values
    
    n = len(df)
    uptrend = np.ones(n, dtype=bool)
    
    # Find first valid index (where ATR is not NaN)
    first_valid = np.argmax(~np.isnan(ub))
    
    for i in range(first_valid + 1, n):
        # Determine trend
        if close[i] > ub[i-1]:
            uptrend[i] = True
        elif close[i] < lb[i-1]:
            uptrend[i] = False
        else:
            uptrend[i] = uptrend[i-1]
            # Trail the stop
            if uptrend[i] and lb[i] < lb[i-1]:
                lb[i] = lb[i-1]
            if not uptrend[i] and ub[i] > ub[i-1]:
                ub[i] = ub[i-1]
    
    df['st_uptrend'] = uptrend
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
            df = ticker.history(period="100d", interval="1d")
            
            if df.empty:
                print(f"Error: No data found for {yf_symbol}")
                continue
            
            df = calculate_supertrend(df)
            current_price = df['Close'].iloc[-1]
            is_uptrend = df['st_uptrend'].iloc[-1]
            was_uptrend = df['st_uptrend'].iloc[-2]
            
            run_type = os.getenv("RUN_TYPE", "manual")
            print(f"DEBUG: run_type detected as '{run_type}'")
            
            print(f"--- {display_symbol} Status ---")
            print(f"Price (USD): {current_price:.4f} | Trend: {'UP' if is_uptrend else 'DOWN'}")
            
            status_msg = f"📊 *{display_symbol}/USD Daily Update*\nPrice: ${current_price:,.4f}\nTrend: {'🟢 BULLISH' if is_uptrend else '🔴 BEARISH'}\n"
            
            if is_uptrend and not was_uptrend:
                alert = "🚀 *SIGNAL: BUY (Green Dot Triggered!)*"
                send_telegram_message(status_msg + alert)
            elif not is_uptrend and was_uptrend:
                alert = "⚠️ *SIGNAL: SELL (Trend flipped to DOWN)*"
                send_telegram_message(status_msg + alert)
            elif run_type in ["workflow_dispatch", "manual", "schedule"]:
                # Send update on manual trigger OR scheduled daily run
                send_telegram_message(status_msg + "_Daily Status Check (No trend change)_")
                
        except Exception as e:
            print(f"Error checking {display_symbol}: {e}")

if __name__ == "__main__":
    run_check()
