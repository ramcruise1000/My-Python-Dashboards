import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import requests

def get_fno_symbols():
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

def get_target_date():
    """
    Prompts the user for a backdate. Defaults to today's date if empty[cite: 7].
    """
    print("=" * 60)
    user_input = input("Enter target date for analysis (YYYY-MM-DD) [Press Enter for Today]: ").strip()
    
    if not user_input:
        target_dt = datetime.today()
        print(f"[#] No date entered. Defaulting to Today: {target_dt.strftime('%Y-%m-%d')}")
        return target_dt
    
    try:
        target_dt = datetime.strptime(user_input, "%Y-%m-%d")
        print(f"[#] Backdating analysis to: {target_dt.strftime('%Y-%m-%d')}")
        return target_dt
    except ValueError:
        print("[!] Invalid date format! Please use YYYY-MM-DD. Defaulting to Today.")
        return datetime.today()

def analyze_stock_patterns(symbol, target_date):
    """
    Downloads data, cuts off rows after the target_date to simulate historical EOD,
    and evaluates structural patterns over a 15-day lookback window[cite: 7].
    """
    try:
        ticker_obj = yf.Ticker(symbol)
        
        # Fetch up to 6 months of data to ensure we have enough history prior to the backdate[cite: 7]
        df = ticker_obj.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 25:
            return None
        
        # Standardize column names to avoid case mismatches[cite: 7]
        df.columns = [col.capitalize() for col in df.columns]
        
        # --- HISTORICAL BACKDATING CUTOFF ---
        # Make the dataframe index timezone-naive to match the target_date calculation cleanly[cite: 7]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        # Filter out all rows ahead of the selected target analysis date[cite: 7]
        df = df[df.index <= target_date]
        
        if len(df) < 25:
            print(f"[-] Warning: Not enough historical data for {symbol} prior to {target_date.strftime('%Y-%m-%d')}")
            return None
        
        # Rebuild clean 1D frame[cite: 7]
        df_cleaned = pd.DataFrame({
            'Close': df['Close'].values.astype(float),
            'High': df['High'].values.astype(float),
            'Low': df['Low'].values.astype(float),
            'Volume': df['Volume'].values.astype(float)
        }, index=df.index)
        
        # Calculate trailing indicators[cite: 7]
        df_cleaned['Pct_Change'] = df_cleaned['Close'].pct_change() * 100
        df_cleaned['Vol_MA'] = df_cleaned['Volume'].rolling(window=5).mean()
        df_cleaned['EMA20'] = df_cleaned['Close'].ewm(span=20, adjust=False).mean()
        
        df_cleaned = df_cleaned.dropna()
        
        if len(df_cleaned) < 18:
            return None
            
        # Isolate session indexes relative to the cutoff date[cite: 7]
        today_idx = -1       # The target date session (EOD)[cite: 7]
        yesterday_idx = -2   # The session immediately before it[cite: 7]
        
        today_perf = df_cleaned['Pct_Change'].iloc[today_idx]
        yesterday_perf = df_cleaned['Pct_Change'].iloc[yesterday_idx]
        current_price = df_cleaned['Close'].iloc[today_idx]
        
        # Extract the 15-day baseline incubator pool (prior to target date and its previous session)[cite: 7]
        history_pool = df_cleaned.iloc[:-2].tail(15)
        
        max_price = history_pool['High'].max()
        min_price = history_pool['Low'].min()
        consolidation_range = ((max_price - min_price) / min_price) * 100
        avg_hist_vol = history_pool['Volume'].mean()
        
        # 1. Evaluate Long Setup: Compression Squeeze + Volume Expansion Breakout[cite: 7]
        is_squeezed = consolidation_range <= 6.0  
        volume_breakout = df_cleaned['Volume'].iloc[today_idx] > (avg_hist_vol * 1.2)
        price_breakout = df_cleaned['Close'].iloc[today_idx] > history_pool['Close'].max()
        
        long_score = 0
        if is_squeezed: long_score += 40
        if volume_breakout: long_score += 30
        if price_breakout: long_score += 30
        
        # 2. Evaluate Short Setup: Distribution Decay Pattern[cite: 7]
        lower_highs = df_cleaned['High'].iloc[yesterday_idx] < history_pool['High'].max()
        below_ema = df_cleaned['Close'].iloc[today_idx] < df_cleaned['EMA20'].iloc[today_idx]
        heavy_down_vol = (df_cleaned['Pct_Change'].iloc[today_idx] < 0) and (df_cleaned['Volume'].iloc[today_idx] > avg_hist_vol)
        
        short_score = 0
        if lower_highs: short_score += 35
        if below_ema: short_score += 35
        if heavy_down_vol: short_score += 30

        return {
            "Symbol": symbol.replace(".NS", ""),
            "Price_At_Date": round(float(current_price), 2),
            "Target_Date_Return_%": round(float(today_perf), 2),
            "Prev_Session_Return_%": round(float(yesterday_perf), 2),
            "15Day_Range_%": round(float(consolidation_range), 2),
            "Long_Pattern_Score": int(long_score),
            "Short_Pattern_Score": int(short_score)
        }
    except Exception as e:
        print(f"[-] Error processing {symbol}: {str(e)}")
        return None

def main():
    # Prompt the user for a backdate right at the start[cite: 7]
    target_date = get_target_date()
    
    print("\nInitiating NSE F&O Pattern Structural Scan...")
    tickers = get_fno_symbols()
    processed_data = []
    
    for ticker in tickers:
        metrics = analyze_stock_patterns(ticker, target_date)
        if metrics:
            processed_data.append(metrics)
            
    if not processed_data:
        print("\n[!] Critical Error: No data could be processed for the selected date window.")
        return

    master_df = pd.DataFrame(processed_data)
    
    # Sort and slice out the top setups based on score formulas[cite: 7]
    top_gainers_predictive = master_df.sort_values(by="Long_Pattern_Score", ascending=False).head(5)
    top_losers_predictive = master_df.sort_values(by="Short_Pattern_Score", ascending=False).head(5)
    
    # Generate unique spreadsheet title containing the targeted date[cite: 7]
    date_str = target_date.strftime("%Y%m%d")
    output_filename = f"FnO_Predictive_Output_{date_str}.xlsx"
    
    with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
        top_gainers_predictive.to_excel(writer, sheet_name="Top 5 Upside Potential", index=False)
        top_losers_predictive.to_excel(writer, sheet_name="Top 5 Downside Potential", index=False)
        master_df.to_excel(writer, sheet_name="Complete Scanned Universe", index=False)
        
    print(f"\n[+] Success! Backdated analysis saved to: {output_filename}")

if __name__ == "__main__":
    main()