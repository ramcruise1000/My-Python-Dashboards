import yfinance as yf
import pandas as pd
import logging
import datetime
import os
import requests

# Suppress yfinance warnings to keep terminal output clean
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def get_fno_tickers():
    """
    Dynamically fetches the latest F&O stock list from the official NSE archives.
    Uses multi-domain fallbacks, referer headers, and session cookies to bypass WAFs.
    """
    urls_to_try = [
        "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv",
        "https://archives.nseindia.com/content/fo/fo_mktlots.csv"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    # 1. Ping the main site to acquire cookies
    try:
        session.get("https://www.nseindia.com", timeout=10)
    except Exception:
        pass 
        
    fno_list = []
    
    # 2. Iterate through possible NSE URLs
    for url in urls_to_try:
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            text_data = response.text.upper()
            
            # WAF Block Check: Verify table header presence
            if "SYMBOL" not in text_data and "UNDERLYING" not in text_data:
                continue 
                
            lines = response.text.strip().split('\n')
            symbols = []
            symbol_idx = None
            
            for line in lines:
                if not line.strip():
                    continue
                    
                parts = [p.strip().upper() for p in line.split(',')]
                
                if symbol_idx is None:
                    if 'SYMBOL' in parts:
                        symbol_idx = parts.index('SYMBOL')
                    elif 'UNDERLYING' in parts:
                        symbol_idx = parts.index('UNDERLYING')
                    continue
                    
                if symbol_idx is not None and len(parts) > symbol_idx:
                    sym = parts[symbol_idx]
                    if sym and sym not in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NAN"]:
                        symbols.append(sym)
                        
            if symbols:
                fno_list = list(dict.fromkeys(symbols))
                domain = url.split('/')[2]
                print(f"✅ Successfully fetched {len(fno_list)} F&O tickers dynamically from {domain}.")
                return [f"{ticker}.NS" for ticker in fno_list]
                
        except Exception:
            continue

    # 3. Fallback list if scraping fails
    print("⚠️ Could not fetch live F&O list from NSE due to strict bot protection. Using hardcoded fallback.")
    fno_fallback = [
        "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", 
        "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", 
        "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", 
        "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", 
        "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "CANBK", 
        "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", "CONCOR", 
        "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", "DIVISLAB", 
        "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", "GAIL", 
        "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", "GUJGASLTD", 
        "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", 
        "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", "IEX", "IGL", 
        "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", "INTELLECT", 
        "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LTF", 
        "LALPATHLAB", "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", 
        "MANAPPURAM", "MARICO", "MARUTI", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", 
        "MRF", "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", 
        "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", 
        "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", 
        "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", 
        "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", "TATAPOWER", "TATASTEEL", 
        "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", "UPL", 
        "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE"
    ]
    return [f"{ticker}.NS" for ticker in fno_fallback]

def scan_micro_vcp_1to4(target_date=None):
    # Dynamically fetch the list of ALL current NSE F&O Stocks
    fno_tickers = get_fno_tickers()

    total_stocks = len(fno_tickers)
    
    if target_date:
        print(f"\nStarting Micro-VCP Backtest for {total_stocks} F&O stocks up to target date: {target_date}...")
        target_dt = pd.to_datetime(target_date)
        # Fetch extra buffer days to slice historical window accurately[cite: 11]
        fetch_end = (target_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        print(f"\nStarting Micro-VCP Scan for {total_stocks} F&O stocks (Latest Session)...")
        fetch_end = None

    results = []

    for idx, ticker_symbol in enumerate(fno_tickers, 1):
        try:
            print(f"\rScanning {idx}/{total_stocks}: {ticker_symbol:<15}", end="", flush=True)

            ticker = yf.Ticker(ticker_symbol)

            # Fetch historical data dynamically based on mode[cite: 11]
            if target_date:
                df = ticker.history(end=fetch_end, period="60d")
                if df.empty:
                    continue
                df.index = df.index.tz_localize(None)
                df = df[df.index <= target_dt]
            else:
                df = ticker.history(period="40d")
                if df.empty:
                    continue
                df.index = df.index.tz_localize(None)

            # Restrict to 40 trading sessions[cite: 11]
            df = df.tail(40)

            if len(df) < 35:
                continue

            actual_trading_date = df.index[-1].strftime("%Y-%m-%d")

            # --- 1. BASELINE CALCULATIONS (20-Day Averages) ---[cite: 11]
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()

            current_close = df['Close'].iloc[-1]

            # --- 2. MICRO-VCP CONTRACTION (Last 5 Days) ---[cite: 11]
            recent_5_days = df.iloc[-5:]
            consolidation_high = recent_5_days['High'].max()
            consolidation_low = recent_5_days['Low'].min()

            range_pct = ((consolidation_high - consolidation_low) / consolidation_low) * 100

            # Volume Dry-up Check (15% below 20-day average)[cite: 11]
            recent_vol_avg = recent_5_days['Volume'].mean()
            volume_dry_up = recent_vol_avg < (df['Vol_SMA_20'].iloc[-1] * 0.85)

            # Max 3.5% swing high to low over 5 days[cite: 11]
            is_tight = range_pct <= 3.5

            # --- 3. TREND DIRECTION & SETUP GENERATION ---[cite: 11]
            is_uptrend = current_close > df['SMA_20'].iloc[-1]
            is_downtrend = current_close < df['SMA_20'].iloc[-1]

            setup_type = None
            entry_price = 0
            stop_loss = 0
            target = 0

            buffer = 0.05  # 5 paise buffer[cite: 11]

            if is_tight and volume_dry_up:
                if is_uptrend:
                    setup_type = "BUY"
                    entry_price = consolidation_high + buffer
                    stop_loss = consolidation_low - buffer
                    risk = entry_price - stop_loss

                    if risk > 0:
                        target = entry_price + (4 * risk)  # 1:4 Risk-to-Reward[cite: 11]
                    else:
                        continue

                elif is_downtrend:
                    setup_type = "SELL"
                    entry_price = consolidation_low - buffer
                    stop_loss = consolidation_high + buffer
                    risk = stop_loss - entry_price

                    if risk > 0:
                        target = entry_price - (4 * risk)  # 1:4 Risk-to-Reward[cite: 11]
                    else:
                        continue

            if setup_type:
                actual_risk = abs(entry_price - stop_loss)

                results.append({
                    "Ticker": ticker_symbol.replace(".NS", ""),
                    "Assessed Date": actual_trading_date,
                    "Setup": setup_type,
                    "Close": round(current_close, 2),
                    "5-Day Volatility %": round(range_pct, 2),
                    "Entry Trigger": round(entry_price, 2),
                    "Stop Loss": round(stop_loss, 2),
                    "Target (1:4 RR)": round(target, 2),
                    "Risk per Share": round(actual_risk, 2)
                })

        except Exception as e:
            continue

    # --- 4. OUTPUT ---[cite: 11]
    if results:
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(by=["Setup", "5-Day Volatility %"])

        print("\n\n--- Scan Complete! Best Micro-VCP Setups ---")
        print(results_df.to_string(index=False))

        date_suffix = target_date.replace("-", "_") if target_date else datetime.datetime.now().strftime('%Y_%m_%d')
        filename = f"MicroVCP_1to4_{date_suffix}.xlsx"
        
        results_df.to_excel(filename, index=False)
        print(f"\n✅ Results saved to {filename}")
    else:
        date_str = target_date if target_date else "the latest trading session"
        print(f"\n\nScan Complete. No stocks met the strict Micro-VCP criteria on or prior to {date_str}.")

if __name__ == "__main__":
    print("=== Micro-VCP (1:4 RR) Stock Screener & Backtester ===")
    user_input = input("Enter backtest date (YYYY-MM-DD) or press Enter for latest session: ").strip()

    target_date = None
    if user_input:
        try:
            # Validate input date string format[cite: 11]
            datetime.datetime.strptime(user_input, "%Y-%m-%d")
            target_date = user_input
        except ValueError:
            print("❌ Invalid date format! Please use YYYY-MM-DD (e.g., 2026-05-14). Exiting.")
            exit()

    scan_micro_vcp_1to4(target_date)