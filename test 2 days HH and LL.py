import yfinance as yf
import pandas as pd
import logging
import datetime
import requests

# Suppress yfinance warnings to keep the terminal output clean
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
        "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LALPATHLAB", 
        "LAURUSLABS", "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", 
        "MARICO", "MARUTI", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", 
        "MUTHOOTFIN", "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", 
        "OBEROIRLTY", "OFSS", "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", "PFC", 
        "PIDILITIND", "PIIND", "PNB", "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", 
        "RECLTD", "RELIANCE", "SAIL", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SIEMENS", "SRF", 
        "SUNPHARMA", "SUNTV", "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAMOTORS", 
        "TATAPOWER", "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", 
        "UBL", "ULTRACEMCO", "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZYDUSLIFE", "360ONE", 
        "APLAPOLLO", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "AMBER", "ANGELONE", "BSE", 
        "BAJAJHLDNG", "BANKINDIA", "BDL", "BLUESTARCO", "CGPOWER", "CDSL"
    ]
    return [f"{ticker}.NS" for ticker in fno_fallback]


def scan_all_fno_stocks():
    # Dynamically fetch the list of ALL current NSE F&O Stocks[cite: 12]
    fno_tickers = get_fno_tickers()

    total_stocks = len(fno_tickers)
    print(f"Starting scan for ALL {total_stocks} F&O stocks...")
    
    results = []
    lookback_window = 10 
    
    for idx, ticker_symbol in enumerate(fno_tickers, 1):
        try:
            # Print progress on the same line so it doesn't flood the terminal[cite: 12]
            print(f"\rScanning {idx}/{total_stocks}: {ticker_symbol:<15}", end="", flush=True)
            
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period="40d")
            
            if df.empty or len(df) < (lookback_window + 2):
                continue
                
            df.index = df.index.tz_localize(None)
            
            # Step 1: Calculate the rolling max High and min Low of the PREVIOUS 2 days[cite: 12]
            df['Prev_2D_High'] = df['High'].shift(1).rolling(window=2).max()
            df['Prev_2D_Low'] = df['Low'].shift(1).rolling(window=2).min()
            
            # Step 2: Identify days where the closing price breaks these levels[cite: 12]
            df['Bullish_Breakout'] = df['Close'] > df['Prev_2D_High']
            df['Bearish_Breakdown'] = df['Close'] < df['Prev_2D_Low']
            
            # Step 3: Isolate the last 10 trading sessions[cite: 12]
            last_10_days = df.iloc[-lookback_window:]
            
            latest_session = last_10_days.iloc[-1]
            previous_9_sessions = last_10_days.iloc[:-1]
            
            is_currently_bullish = latest_session['Bullish_Breakout']
            is_currently_bearish = latest_session['Bearish_Breakdown']
            
            was_bullish_recently = previous_9_sessions['Bullish_Breakout'].any()
            was_bearish_recently = previous_9_sessions['Bearish_Breakdown'].any()
            
            setup_type = None
            
            # Step 4: Validate if it fits the pattern for the FIRST time in 10 days[cite: 12]
            if is_currently_bullish and not was_bullish_recently:
                setup_type = "FRESH BULLISH BREAKOUT"
            elif is_currently_bearish and not was_bearish_recently:
                setup_type = "FRESH BEARISH BREAKDOWN"
                
            if setup_type:
                results.append({
                    "Ticker": ticker_symbol.replace(".NS", ""),
                    "Date": latest_session.name.strftime("%Y-%m-%d"),
                    "Setup Type": setup_type,
                    "Close": round(latest_session['Close'], 2),
                    "Prev 2D High": round(latest_session['Prev_2D_High'], 2),
                    "Prev 2D Low": round(latest_session['Prev_2D_Low'], 2)
                })
                
        except Exception as e:
            continue
            
    # Step 5: Output the Results[cite: 12]
    if results:
        results_df = pd.DataFrame(results)
        print("\n\n--- Scan Complete! Found the following setups ---")
        # Format printing so everything aligns nicely[cite: 12]
        print(results_df.to_string(index=False))
        
        # Saves directly to your current folder as an Excel file[cite: 12]
        filename = f"FnO_First_Time_Breakouts_{datetime.datetime.now().strftime('%Y_%m_%d')}.xlsx"
        results_df.to_excel(filename, index=False)
        print(f"\n✅ Results have been successfully saved to {filename}")
    else:
        print("\n\nScan Complete. No stocks met the exact criteria over the last 10 sessions.")

if __name__ == "__main__":
    scan_all_fno_stocks()