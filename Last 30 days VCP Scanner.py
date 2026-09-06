import yfinance as yf
import pandas as pd
import datetime
import os
import logging
import requests

# Suppress yfinance warnings to keep the terminal clean[cite: 2]
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def analyze_vcp_30_days(ticker_symbol, target_date):
    """
    Scans a ticker for VCP setups over the 30 calendar days leading up to target_date[cite: 2].
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Fetch 2 years of data to ensure enough historical data for moving averages[cite: 2]
        df = ticker.history(period="2y")
        
        if df.empty or len(df) < 252:
            return []
            
        # Remove timezone formatting from index to match user input easily[cite: 2]
        df.index = df.index.tz_localize(None)
        
        # Define the 30-day window[cite: 2]
        end_dt = pd.to_datetime(target_date)
        start_dt = end_dt - pd.Timedelta(days=30)
        
        # Filter data up to the chosen end date[cite: 2]
        historical_data = df[df.index <= end_dt].copy()
        if historical_data.empty:
            return []
            
        # Pre-calculate indicators for the entire dataframe for maximum efficiency[cite: 2]
        historical_data['SMA_50'] = historical_data['Close'].rolling(window=50).mean()
        historical_data['SMA_150'] = historical_data['Close'].rolling(window=150).mean()
        historical_data['SMA_200'] = historical_data['Close'].rolling(window=200).mean()
        historical_data['52W_High'] = historical_data['High'].rolling(window=252).max()
        historical_data['52W_Low'] = historical_data['Low'].rolling(window=252).min()
        historical_data['Vol_50_Avg'] = historical_data['Volume'].rolling(window=50).mean()
        historical_data['Daily_Range'] = historical_data['High'] - historical_data['Low']
        
        # Isolate the trading days that fall in our 30-day scan window[cite: 2]
        window_dates = historical_data[(historical_data.index >= start_dt) & (historical_data.index <= end_dt)].index
        
        setups_found = []
        
        # Iterate over each trading day in the 30-day window[cite: 2]
        for eval_date in window_dates:
            idx = historical_data.index.get_loc(eval_date)
            
            # Ensure there is enough preceding data (at least 252 trading days) before this specific date[cite: 2]
            if idx < 252:
                continue
                
            current_close = historical_data['Close'].iloc[idx]
            current_vol = historical_data['Volume'].iloc[idx]
            
            # 1. Fetch Moving Averages & 52-Week High/Low for the specific day[cite: 2]
            sma50 = historical_data['SMA_50'].iloc[idx]
            sma150 = historical_data['SMA_150'].iloc[idx]
            sma200 = historical_data['SMA_200'].iloc[idx]
            sma200_past = historical_data['SMA_200'].iloc[idx - 21]
            high_52w = historical_data['52W_High'].iloc[idx]
            low_52w = historical_data['52W_Low'].iloc[idx]
            
            # 2a. LONG Trend Template (Stage 2 Uptrend)[cite: 2]
            l1 = current_close > sma150 and current_close > sma200
            l2 = sma150 > sma200
            l3 = sma200 > sma200_past 
            l4 = sma50 > sma150 and sma50 > sma200
            l5 = current_close > sma50
            l6 = current_close >= (1.30 * low_52w) 
            l7 = current_close >= (0.75 * high_52w) 
            long_trend_met = l1 and l2 and l3 and l4 and l5 and l6 and l7

            # 2b. SHORT Trend Template (Stage 4 Downtrend)[cite: 2]
            s1 = current_close < sma150 and current_close < sma200
            s2 = sma150 < sma200
            s3 = sma200 < sma200_past 
            s4 = sma50 < sma150 and sma50 < sma200
            s5 = current_close < sma50
            s6 = current_close <= (1.25 * low_52w) 
            s7 = current_close <= (0.70 * high_52w) 
            short_trend_met = s1 and s2 and s3 and s4 and s5 and s6 and s7
            
            # 3. VCP Characteristics (Volatility & Volume Contraction)[cite: 2]
            vol_50_avg = historical_data['Vol_50_Avg'].iloc[idx]
            volume_dry_up = current_vol < (vol_50_avg * 0.9) 
            
            # Volatility contraction (recent 10 days vs previous 20 days)[cite: 2]
            recent_volatility = historical_data['Daily_Range'].iloc[idx-9:idx+1].mean()
            past_volatility = historical_data['Daily_Range'].iloc[idx-29:idx-9].mean()
            price_contraction = recent_volatility < past_volatility
            
            # Pivots based on the last 15 trading days up to the eval_date[cite: 2]
            high_pivot = historical_data['High'].iloc[idx-14:idx+1].max()
            low_pivot = historical_data['Low'].iloc[idx-14:idx+1].min()  
            
            # 4. Generate Recommendation[cite: 2]
            risk_pct = 0.07  
            reward_pct = risk_pct * 3  
            
            rec = None
            if long_trend_met and price_contraction and volume_dry_up:
                rec = "BUY SETUP"
                trigger_price = round(high_pivot + 0.05, 2) 
                sl = round(trigger_price * (1 - risk_pct), 2)
                target = round(trigger_price * (1 + reward_pct), 2)
                
            elif short_trend_met and price_contraction and volume_dry_up:
                rec = "SELL SETUP"
                trigger_price = round(low_pivot - 0.05, 2) 
                sl = round(trigger_price * (1 + risk_pct), 2) 
                target = round(trigger_price * (1 - reward_pct), 2) 
                
            # 5. Package results if a setup was found[cite: 2]
            if rec:
                setups_found.append({
                    "Ticker": ticker_symbol.upper(),
                    "Trading Date Assessed": eval_date.strftime("%Y-%m-%d"),
                    "Setup Type": rec,
                    "Close Price": round(current_close, 2),
                    "Trigger Price": trigger_price,
                    "Stop Loss (7%)": sl,
                    "Target (3R)": target
                })
                
        return setups_found
    except Exception as e:
        return []


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
    
    # 1. Ping the main site to acquire cookies (ignore if it times out)
    try:
        session.get("https://www.nseindia.com", timeout=10)
    except Exception:
        pass 
        
    fno_list = []
    
    # 2. Iterate through the possible NSE URLs
    for url in urls_to_try:
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            
            text_data = response.text.upper()
            
            # WAF Block Check: If the file doesn't contain the standard headers, it's a block page
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
            continue # Try the next URL in the list

    # 3. If all scraping attempts fail, use the hardcoded fallback[cite: 2]
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
        "IOC", "IPCALAB", "IRCTC", "ITC", "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "L&TFH", 
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


if __name__ == "__main__":
    print("--- F&O VCP 30-Day Window Backtester ---")
    
    # User Input for Date[cite: 2]
    user_date_input = input("Enter end date for the 30-day window (YYYY-MM-DD) or press Enter for today: ").strip()
    
    if not user_date_input:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            # Validate input format[cite: 2]
            datetime.datetime.strptime(user_date_input, "%Y-%m-%d")
            target_date = user_date_input
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD (e.g., 2026-05-14). Exiting.")
            exit()

    # Calculate exactly 30 days prior for display purposes
    start_date_str = (datetime.datetime.strptime(target_date, "%Y-%m-%d") - datetime.timedelta(days=30)).strftime("%Y-%m-%d")

    tickers = get_fno_tickers()
    total_tickers = len(tickers)
    
    print(f"\nScanning F&O universe for setups between: {start_date_str} and {target_date}...")
    
    all_valid_setups = []
    for i, ticker in enumerate(tickers, 1):
        print(f"\rScanning {i}/{total_tickers}: {ticker:<15}", end="", flush=True)
        results = analyze_vcp_30_days(ticker, target_date)
        if results:
            # .extend() adds all setups from the 30-day period for this ticker into the master list
            all_valid_setups.extend(results)  
            
    print("\n\nScan Complete!")
    
    if all_valid_setups:
        df_results = pd.DataFrame(all_valid_setups)
        # Sort by Trading Date (newest first), then by Setup Type
        df_results = df_results.sort_values(by=["Trading Date Assessed", "Setup Type"], ascending=[False, True])
        
        # Uses the user-defined date to flag the Excel name clearly[cite: 2]
        clean_date_str = target_date.replace("-", "_")
        file_name = f"FnO_VCP_Last_30Days_Ending_{clean_date_str}.xlsx"
        
        try:
            # Save the entire dataframe into a single Excel sheet[cite: 2]
            df_results.to_excel(file_name, index=False)
            print(f"✅ Found {len(all_valid_setups)} historical setups within the 30-day window! Saved to: {os.path.abspath(file_name)}")
        except Exception as e:
            print(f"Could not save to Excel. Error: {e}")
    else:
        print(f"No valid VCP setups were triggered in the 30 days up to {target_date}.")