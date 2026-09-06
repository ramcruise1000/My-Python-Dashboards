import yfinance as yf
import pandas as pd
import datetime
import os
import logging
import requests

# Suppress yfinance warnings to keep the terminal clean
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def analyze_vcp_for_screener(ticker_symbol, target_date):
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Fetch 2 years of data to ensure enough historical data for moving averages during backtesting[cite: 4]
        df = ticker.history(period="2y")
        
        if df.empty or len(df) < 252:
            return None
            
        # Remove timezone formatting from index to match user input easily[cite: 4]
        df.index = df.index.tz_localize(None)
        target_dt = pd.to_datetime(target_date)
        
        # Filter data up to the chosen backtest date[cite: 4]
        historical_data = df[df.index <= target_dt]
        if historical_data.empty:
            return None
            
        # Get the actual last available trading day up to the target date (handles holidays/weekends)[cite: 4]
        actual_date = historical_data.index[-1]
        idx = df.index.get_loc(actual_date)
        
        # Ensure there is enough preceding data (at least 252 trading days) to calculate 200 SMA and 52W High/Low[cite: 4]
        if idx < 252:
            return None
            
        # Slice the dataframe up to the target trading session[cite: 4]
        df_sliced = df.iloc[:idx + 1].copy()
        
        # 1. Calculate Moving Averages & 52-Week High/Low[cite: 4]
        df_sliced['SMA_50'] = df_sliced['Close'].rolling(window=50).mean()
        df_sliced['SMA_150'] = df_sliced['Close'].rolling(window=150).mean()
        df_sliced['SMA_200'] = df_sliced['Close'].rolling(window=200).mean()
        df_sliced['52W_High'] = df_sliced['High'].rolling(window=252).max()
        df_sliced['52W_Low'] = df_sliced['Low'].rolling(window=252).min()
        
        current_close = df_sliced['Close'].iloc[-1]
        current_vol = df_sliced['Volume'].iloc[-1]
        
        # 2a. LONG Trend Template (Stage 2 Uptrend)[cite: 4]
        l1 = current_close > df_sliced['SMA_150'].iloc[-1] and current_close > df_sliced['SMA_200'].iloc[-1]
        l2 = df_sliced['SMA_150'].iloc[-1] > df_sliced['SMA_200'].iloc[-1]
        l3 = df_sliced['SMA_200'].iloc[-1] > df_sliced['SMA_200'].iloc[-21] 
        l4 = df_sliced['SMA_50'].iloc[-1] > df_sliced['SMA_150'].iloc[-1] and df_sliced['SMA_50'].iloc[-1] > df_sliced['SMA_200'].iloc[-1]
        l5 = current_close > df_sliced['SMA_50'].iloc[-1]
        l6 = current_close >= (1.30 * df_sliced['52W_Low'].iloc[-1]) 
        l7 = current_close >= (0.75 * df_sliced['52W_High'].iloc[-1]) 
        long_trend_met = l1 and l2 and l3 and l4 and l5 and l6 and l7

        # 2b. SHORT Trend Template (Stage 4 Downtrend)[cite: 4]
        s1 = current_close < df_sliced['SMA_150'].iloc[-1] and current_close < df_sliced['SMA_200'].iloc[-1]
        s2 = df_sliced['SMA_150'].iloc[-1] < df_sliced['SMA_200'].iloc[-1]
        s3 = df_sliced['SMA_200'].iloc[-1] < df_sliced['SMA_200'].iloc[-21] 
        s4 = df_sliced['SMA_50'].iloc[-1] < df_sliced['SMA_150'].iloc[-1] and df_sliced['SMA_50'].iloc[-1] < df_sliced['SMA_200'].iloc[-1]
        s5 = current_close < df_sliced['SMA_50'].iloc[-1]
        s6 = current_close <= (1.25 * df_sliced['52W_Low'].iloc[-1]) 
        s7 = current_close <= (0.70 * df_sliced['52W_High'].iloc[-1]) 
        short_trend_met = s1 and s2 and s3 and s4 and s5 and s6 and s7
        
        # 3. VCP Characteristics (Volatility & Volume Contraction)[cite: 4]
        vol_50_avg = df_sliced['Volume'].rolling(window=50).mean().iloc[-1]
        volume_dry_up = current_vol < (vol_50_avg * 0.9) 
        
        df_sliced['Daily_Range'] = df_sliced['High'] - df_sliced['Low']
        recent_volatility = df_sliced['Daily_Range'].iloc[-10:].mean()
        past_volatility = df_sliced['Daily_Range'].iloc[-30:-10].mean()
        price_contraction = recent_volatility < past_volatility
        
        # Pivots based on the last 15 trading days up to the target date[cite: 4]
        high_pivot = df_sliced['High'].iloc[-15:].max()
        low_pivot = df_sliced['Low'].iloc[-15:].min()  
        
        # 4. Generate Recommendation[cite: 4]
        risk_pct = 0.07  
        reward_pct = risk_pct * 3  
        
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
            
        else:
            return None 
            
        # 5. Package results[cite: 4]
        return {
            "Ticker": ticker_symbol.upper(),
            "Trading Date Assessed": actual_date.strftime("%Y-%m-%d"),
            "Setup Type": rec,
            "Close Price": round(current_close, 2),
            "Trigger Price (Next Session Entry)": trigger_price,
            "Stop Loss (7%)": sl,
            "Target (3R)": target
        }
    except Exception as e:
        return None

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

    # 3. Fallback list if scraping fails[cite: 4]
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
    print("--- F&O VCP Historical Backtester ---")
    
    # User Input for Date[cite: 4]
    user_date_input = input("Enter backtest date (YYYY-MM-DD) or press Enter for today: ").strip()
    
    if not user_date_input:
        target_date = datetime.datetime.now().strftime("%Y-%m-%d")
    else:
        try:
            # Validate input format[cite: 4]
            datetime.datetime.strptime(user_date_input, "%Y-%m-%d")
            target_date = user_date_input
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD (e.g., 2026-05-14). Exiting.")
            exit()

    tickers = get_fno_tickers()
    total_tickers = len(tickers)
    
    print(f"\nScanning F&O universe up to: {target_date}...")
    
    valid_setups = []
    for i, ticker in enumerate(tickers, 1):
        print(f"\rScanning {i}/{total_tickers}: {ticker:<15}", end="", flush=True)
        result = analyze_vcp_for_screener(ticker, target_date)
        if result:
            valid_setups.append(result)
            
    print("\n\nScan Complete!")
    
    if valid_setups:
        df_results = pd.DataFrame(valid_setups)
        df_results = df_results.sort_values(by="Setup Type")
        
        # Uses the user-defined date to flag the Excel name clearly[cite: 4]
        clean_date_str = target_date.replace("-", "_")
        file_name = f"FnO_VCP_Setups_{clean_date_str}.xlsx"
        
        try:
            df_results.to_excel(file_name, index=False)
            print(f"✅ Found {len(valid_setups)} historical setups! Saved to: {os.path.abspath(file_name)}")
        except Exception as e:
            print(f"Could not save to Excel. Error: {e}")
    else:
        print(f"No valid VCP setups were triggered on or directly before {target_date}.")