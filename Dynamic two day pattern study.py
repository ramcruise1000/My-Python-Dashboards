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
    print("=" * 70)
    user_input = input("Enter Target Analysis Date (YYYY-MM-DD) [Leave blank for Today]: ").strip()
    if not user_input:
        return datetime.today()
    try:
        return datetime.strptime(user_input, "%Y-%m-%d")
    except ValueError:
        print("[!] Invalid format. Defaulting to Today.")
        return datetime.today()

def fetch_and_clean_data(symbol, target_date):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo", interval="1d")
        if df.empty or len(df) < 30:
            return None
            
        df.columns = [col.capitalize() for col in df.columns]
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
            
        df = df[df.index <= target_date]
        if len(df) < 20:
            return None
            
        df_clean = pd.DataFrame({
            'Close': df['Close'].values.astype(float),
            'High': df['High'].values.astype(float),
            'Low': df['Low'].values.astype(float),
            'Volume': df['Volume'].values.astype(float)
        }, index=df.index)
        
        df_clean['Pct_Change'] = df_clean['Close'].pct_change() * 100
        df_clean['Vol_MA'] = df_clean['Volume'].rolling(window=5).mean()
        df_clean['EMA20'] = df_clean['Close'].ewm(span=20, adjust=False).mean()
        
        return df_clean.dropna()
    except Exception:
        return None

def main():
    target_date = get_target_date()
    tickers = get_fno_symbols()
    
    universe_data = {}
    baseline_performances = []
    
    print("\n[1/3] Downloading market data and identifying active leaders...")
    for ticker in tickers:
        df = fetch_and_clean_data(ticker, target_date)
        if df is not None and len(df) >= 18:
            universe_data[ticker] = df
            two_day_return = ((df['Close'].iloc[-1] - df['Close'].iloc[-3]) / df['Close'].iloc[-3]) * 100
            baseline_performances.append({
                'Symbol': ticker,
                'TwoDayReturn': two_day_return
            })
            
    if not baseline_performances:
        print("[!] Critical Error: No data available for this date window.")
        return
        
    perf_df = pd.DataFrame(baseline_performances)
    
    actual_gainers = perf_df.sort_values(by='TwoDayReturn', ascending=False).head(5)['Symbol'].tolist()
    actual_losers = perf_df.sort_values(by='TwoDayReturn', ascending=True).head(5)['Symbol'].tolist()
    
    print(f"\n[+] Identified Top 2-Day Gainers: {', '.join([x.replace('.NS','') for x in actual_gainers])}")
    print(f"[+] Identified Top 2-Day Losers:  {', '.join([x.replace('.NS','') for x in actual_losers])}")
    
    print("\n[2/3] Quantitative modeling of the patterns that caused these moves...")
    gainer_ranges = []
    for ticker in actual_gainers:
        hist_15 = universe_data[ticker].iloc[:-2].tail(15)
        gainer_ranges.append(((hist_15['High'].max() - hist_15['Low'].min()) / hist_15['Low'].min()) * 100)
    target_compression = np.mean(gainer_ranges) if gainer_ranges else 5.0
    
    print("[3/3] Scanning market for hidden candidates matching these precise criteria...")
    predictive_scoring = []
    exclude_list = actual_gainers + actual_losers
    
    for ticker, df in universe_data.items():
        if ticker in exclude_list:
            continue
            
        recent_15 = df.tail(15)
        max_p = recent_15['High'].max()
        min_p = recent_15['Low'].min()
        current_range = ((max_p - min_p) / min_p) * 100
        avg_vol = recent_15['Volume'].mean()
        
        # Base structural pattern alignment score
        squeeze_score = max(0, 100 - abs(current_range - target_compression) * 15)
        
        # --- STRENGTHENED DIRECTIONAL GATES ---
        # Upside Gate: Must close above EMA20 and demonstrate a positive close day
        is_bullish = (df['Close'].iloc[-1] >= df['EMA20'].iloc[-1]) and (df['Pct_Change'].iloc[-1] >= 0)
        
        # Downside Gate: Must close below EMA20 and demonstrate a negative close day
        is_bearish = (df['Close'].iloc[-1] < df['EMA20'].iloc[-1]) and (df['Pct_Change'].iloc[-1] < 0)
        
        # Volume acceleration indicator booster
        vol_boost = 30 if (df['Volume'].iloc[-1] > avg_vol * 0.9) else 0
        
        # Hard enforcement: If it fails the directional gate, its score drop to ZERO
        upside_potential = (squeeze_score + vol_boost) if is_bullish else 0
        downside_potential = (squeeze_score + vol_boost) if is_bearish else 0
        
        predictive_scoring.append({
            'Symbol': ticker.replace('.NS', ''),
            'Price': round(df['Close'].iloc[-1], 2),
            '15Day_Range_%': round(current_range, 2),
            'Upside_Match_Score': int(upside_potential),
            'Downside_Match_Score': int(downside_potential)
        })
        
    predictive_df = pd.DataFrame(predictive_scoring)
    
    # Filter out entries that scored 0 due to gate failures before extracting top 5
    potential_gainers = predictive_df[predictive_df['Upside_Match_Score'] > 0].sort_values(by='Upside_Match_Score', ascending=False).head(5)
    potential_losers = predictive_df[predictive_df['Downside_Match_Score'] > 0].sort_values(by='Downside_Match_Score', ascending=True).head(5)
    
    date_suffix = target_date.strftime("%Y%m%d")
    filename = f"FnO_Dynamic_Patterns_{date_suffix}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        potential_gainers.to_excel(writer, sheet_name="Potential Gainers Tomorrow", index=False)
        potential_losers.to_excel(writer, sheet_name="Potential Losers Tomorrow", index=False)
        
    print(f"\n[+] Success! Mutually exclusive lists saved to: {filename}")

if __name__ == "__main__":
    main()