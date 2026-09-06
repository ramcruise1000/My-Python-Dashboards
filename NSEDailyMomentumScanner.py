import os
import pandas as pd
import requests
from datetime import datetime

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
                return fno_list
                
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
    return fno_fallback

class NSEHistoricalMomentumScanner:
    def __init__(self):
        # Dynamically fetch full list of active NSE F&O underlying scripts
        self.watchlist = get_fno_tickers()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_market_history(self, ticker):
        """
        Fetches up to 60 days of historical bar trends to allow 
        seamless calculation of deep historical dates[cite: 10].
        """
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.NS?interval=1d&range=60d"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            result = data['chart']['result'][0]
            timestamps = result['timestamp']
            indicators = result['indicators']['quote'][0]
            
            df = pd.DataFrame({
                'Date': [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps],
                'Close': indicators['close'],
                'High': indicators['high'],
                'Low': indicators['low'],
                'Volume': indicators['volume']
            }).dropna()
            return df
        except Exception:
            return None

    def execute_scan(self):
        print("=" * 60)
        print("          NSE F&O INTRADAY MOMENTUM ENGINE          ")
        print("=" * 60)
        
        # 1. Capture user choice input for dynamic date processing[cite: 10]
        user_input = input("Enter target backdate (YYYY-MM-DD) or press [ENTER] for Latest Live Session: ").strip()
        
        target_date = None
        if user_input != "":
            try:
                # Validate date format structural strings[cite: 10]
                datetime.strptime(user_input, "%Y-%m-%d")
                target_date = user_input
                print(f"[+] Initializing Backdate Time-Machine to study: {target_date}")
            except ValueError:
                print("[-] Invalid format. Exiting run. Please use standard YYYY-MM-DD layout (e.g. 2026-06-25).")
                return
        else:
            print("[+] No date entered. Processing latest completed market session data...")

        all_data = []
        print("[*] Contacting exchange server pipelines...")
        
        for ticker in self.watchlist:
            df = self.fetch_market_history(ticker)
            if df is None or len(df) < 15:
                continue
            
            # 2. Dynamic Time-Machine Truncation Logic[cite: 10]
            if target_date:
                # Slice away data rows that occurred AFTER the targeted historical prompt date[cite: 10]
                df = df[df['Date'] <= target_date]
                if len(df) < 9:
                    continue
            
            all_data.append((ticker, df))
            
        if not all_data:
            print("[-] Critical Error: No data logs retrieved matching the date criteria constraints.")
            return

        # Isolate the exact runtime session date we are evaluating[cite: 10]
        actual_study_date = all_data[0][1]['Date'].iloc[-1]
        print(f"[✓] Data arrays aligned. Confirmed actual target date under calculation: {actual_study_date}")
        
        # --- PHASE 1: IDENTIFY THE SELECTED DAY'S EXTREME GAINERS/LOSERS ---[cite: 10]
        session_performance = []
        for ticker, df in all_data:
            study_close = df['Close'].iloc[-1]
            study_prev_close = df['Close'].iloc[-2]
            pct_change = ((study_close - study_prev_close) / study_prev_close) * 100
            
            session_performance.append({
                'Ticker': ticker,
                'Close': study_close,
                '% Change': pct_change,
                'df': df
            })
            
        perf_df = pd.DataFrame(session_performance)
        top_gainers = perf_df.sort_values(by='% Change', ascending=False).head(5)
        top_losers = perf_df.sort_values(by='% Change', ascending=True).head(5)
        
        # --- PHASE 2 & 3: HISTORICAL LOOKBACK & NEXT-SESSION PATTERN DETECTION ---[cite: 10]
        predictions = []
        
        for item in session_performance:
            ticker = item['Ticker']
            df = item['df']
            
            # Isolate the exact 7-day trailing lookback right before our targeted execution day[cite: 10]
            lookback_window = df.iloc[-8:-1]
            lb_max_high = lookback_window['High'].max()
            lb_min_low = lookback_window['Low'].min()
            lb_avg_vol = lookback_window['Volume'].mean()
            
            # Targeted active day records[cite: 10]
            latest_close = df['Close'].iloc[-1]
            latest_vol = df['Volume'].iloc[-1]
            latest_pct_val = item['% Change']
            
            vol_expansion = latest_vol / lb_avg_vol if lb_avg_vol > 0 else 1.0
            
            momentum_bias = "Neutral Consolidation"
            priority_score = 0.0
            
            # Pattern Alpha: Volatility Compression Upside Outbreak[cite: 10]
            if latest_close > lb_max_high and latest_vol > lb_avg_vol:
                momentum_bias = "Pattern Alpha Breakout (Bullish Momentum Target)"
                priority_score = latest_pct_val * vol_expansion
                
            # Pattern Beta: Support Level Capitulation Breakdown[cite: 10]
            elif latest_close < lb_min_low and latest_vol > lb_avg_vol:
                momentum_bias = "Pattern Beta Breakdown (Bearish Momentum Target)"
                priority_score = latest_pct_val * vol_expansion
                
            predictions.append({
                "Ticker Symbol": ticker,
                "LTP on Studied Session (INR)": round(latest_close, 2),
                "Intraday Change %": round(latest_pct_val, 2),
                "7-Session Looking Ceiling": round(lb_max_high, 2),
                "7-Session Looking Floor": round(lb_min_low, 2),
                "Volume Multiple Expansion": round(vol_expansion, 2),
                "Structural Signature": momentum_bias,
                "Next Session Priority Score": round(priority_score, 2)
            })

        predict_df = pd.DataFrame(predictions)
        
        potential_gainers = predict_df[predict_df['Next Session Priority Score'] > 0].sort_values(by='Next Session Priority Score', ascending=False).head(5)
        potential_losers = predict_df[predict_df['Next Session Priority Score'] < 0].sort_values(by='Next Session Priority Score', ascending=True).head(5)

        # --- PHASE 4: REFORMAT OUTPUT FILE DISTRIBUTIONS ---[cite: 10]
        output_filename = f"NSE_Momentum_Scan_{actual_study_date}.xlsx"
        
        with pd.ExcelWriter(output_filename, engine='openpyxl') as writer:
            # Sheet 1: Summary mapping profiles[cite: 10]
            summary_sheets = []
            for idx, r in top_gainers.iterrows():
                summary_sheets.append({"Ticker": r['Ticker'], "Type": "Top Gainer", "% Change": round(r['% Change'], 2), "LTP": round(r['Close'], 2)})
            for idx, r in top_losers.iterrows():
                summary_sheets.append({"Ticker": r['Ticker'], "Type": "Top Loser", "% Change": round(r['% Change'], 2), "LTP": round(r['Close'], 2)})
            
            pd.DataFrame(summary_sheets).to_excel(writer, sheet_name='Study Session Summary', index=False)
            
            # Sheet 2 & 3: Pattern Calculations for the Following Day[cite: 10]
            potential_gainers[["Ticker Symbol", "LTP on Studied Session (INR)", "Intraday Change %", "Volume Multiple Expansion", "Structural Signature"]].to_excel(writer, sheet_name='Potential Next-Day Gainers', index=False)
            potential_losers[["Ticker Symbol", "LTP on Studied Session (INR)", "Intraday Change %", "Volume Multiple Expansion", "Structural Signature"]].to_excel(writer, sheet_name='Potential Next-Day Losers', index=False)
            
            # Sheet 4: Complete Underlying Logs[cite: 10]
            predict_df.to_excel(writer, sheet_name='All Scanned Derivatives', index=False)

        print("-" * 60)
        print(f"[✓] Processing Complete for targeted reference date context!")
        print(f"[✓] Dynamic Spreadsheet Generated: '{os.path.abspath(output_filename)}'")
        print("-" * 60)

if __name__ == "__main__":
    scanner = NSEHistoricalMomentumScanner()
    scanner.execute_scan()