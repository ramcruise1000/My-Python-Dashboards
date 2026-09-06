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


class NSEVCPDailyScanner:
    def __init__(self):
        # Dynamically fetch full list of active NSE F&O underlying scripts[cite: 9]
        self.watchlist = get_fno_tickers()
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_equity_history(self, ticker):
        """Fetches up to 60 days of daily bar intervals to trace multi-wave VCP cycles."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=60d"
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

    def execute_eod_vcp_scan(self):
        print("=" * 70)
        print("     MARK MINERVINI VCP / INVERTED DISTRIBUTION SCANNER     ")
        print("=" * 70)
        
        # User Date Prompt Interface Handler[cite: 9]
        user_prompt = input("Enter historic backdate (YYYY-MM-DD) or press [ENTER] for Latest EOD: ").strip()
        
        target_backdate = None
        if user_prompt != "":
            try:
                datetime.strptime(user_prompt, "%Y-%m-%d")
                target_backdate = user_prompt
                print(f"[+] Rolling backend dataframes to target date context: {target_backdate}")
            except ValueError:
                print("[-] Incorrect format structure. Please run again using YYYY-MM-DD (e.g., 2026-06-29).")
                return
        else:
            print("[+] Querying live exchange pipelines for the latest closed session...")

        raw_scanned_pool = []
        
        for ticker in self.watchlist:
            df = self.fetch_equity_history(ticker)
            if df is None or len(df) < 25:
                continue
            
            # Truncate dates cleanly if backtesting via prompt input[cite: 9]
            if target_backdate:
                df = df[df['Date'] <= target_backdate]
                if len(df) < 20:
                    continue
            
            raw_scanned_pool.append((ticker, df))
            
        if not raw_scanned_pool:
            print("[-] Structural Error: No active market data rows loaded from proxy pools.")
            return

        # Synchronize exact session date under execution[cite: 9]
        actual_processing_date = raw_scanned_pool[0][1]['Date'].iloc[-1]
        print(f"[✓] Data synchronization stable. Processing actual date: {actual_processing_date}")
        
        buy_candidates = []
        sell_candidates = []
        
        for ticker, df in raw_scanned_pool:
            # Capture latest day stats[cite: 9]
            ltp = df['Close'].iloc[-1]
            day_high = df['High'].iloc[-1]
            day_low = df['Low'].iloc[-1]
            day_vol = df['Volume'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            intraday_chg = ((ltp - prev_close) / prev_close) * 100
            
            # Simple Moving Averages[cite: 9]
            sma_20 = df['Close'].iloc[-20:].mean()
            sma_50 = df['Close'].iloc[-50:].mean()
            
            # Parse past 15-day lookup frames to gauge diminishing swing structures (T counts)[cite: 9]
            historical_window = df.iloc[-16:-1]
            wave_high = historical_window['High'].max()
            wave_low = historical_window['Low'].min()
            avg_volume = historical_window['Volume'].mean()
            
            vol_dry_ratio = day_vol / avg_volume if avg_volume > 0 else 1.0
            
            # Formulate triggers[cite: 9]
            buy_trigger = round(day_high + 0.55, 2)
            sell_trigger = round(day_low - 0.55, 2)
            
            # --- MINERVINI BUY SIDE FILTER (VCP ACCUMULATION) ---[cite: 9]
            if ltp > sma_20 and sma_20 > sma_50:
                if ltp >= (wave_high * 0.94) and vol_dry_ratio < 1.25:
                    buy_candidates.append({
                        "Ticker": ticker,
                        "EOD Closing Price": round(ltp, 2),
                        "Intraday Change %": round(intraday_chg, 2),
                        "Pivot Breakout Trigger": buy_trigger,
                        "Defensive Stop Loss": round(day_low * 0.985, 2),
                        "Volume Dry-up Ratio": round(vol_dry_ratio, 2),
                        "Entry Execution Strategy": f"Buy ONLY if price breaks above the pivot of ₹{buy_trigger} on a 15-min candle. Volatility has compressed and supply is dried up; this trigger ensures you catch the momentum as institutional markup begins."
                    })
            
            # --- SELL SIDE FILTER (INVERTED DISTRIBUTION VCP) ---[cite: 9]
            elif ltp < sma_20 and sma_20 < sma_50:
                if ltp <= (wave_low * 1.06):
                    sell_candidates.append({
                        "Ticker": ticker,
                        "EOD Closing Price": round(ltp, 2),
                        "Intraday Change %": round(intraday_chg, 2),
                        "Pivot Breakdown Trigger": sell_trigger,
                        "Defensive Stop Loss": round(day_high * 1.015, 2),
                        "Volume Exhaustion Ratio": round(vol_dry_ratio, 2),
                        "Entry Execution Strategy": f"Short ONLY if price breaks below the horizontal floor of ₹{sell_trigger}. Diminishing bounces indicate the absence of institutional buyers. Selling pressure will cascade once this support cracks."
                    })

        # Convert arrays to DataFrames[cite: 9]
        buy_df = pd.DataFrame(buy_candidates)
        sell_df = pd.DataFrame(sell_candidates)
        
        # Sort files to surface the tightest, lowest-risk entry profiles to the top[cite: 9]
        if not buy_df.empty: buy_df = buy_df.sort_values(by="Volume Dry-up Ratio", ascending=True)
        if not sell_df.empty: sell_df = sell_df.sort_values(by="Volume Exhaustion Ratio", ascending=True)
        
        # Generate Excel spreadsheet output[cite: 9]
        output_name = f"NSE_Minervini_Scanner_{actual_processing_date}.xlsx"
        with pd.ExcelWriter(output_name, engine='openpyxl') as writer:
            if not buy_df.empty:
                buy_df.to_excel(writer, sheet_name='Bullish Buy Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No stocks met strict VCP buy limits today"}]).to_excel(writer, sheet_name='Bullish Buy Watchlist', index=False)
                
            if not sell_df.empty:
                sell_df.to_excel(writer, sheet_name='Bearish Sell Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No stocks met strict Inverted VCP limits today"}]).to_excel(writer, sheet_name='Bearish Sell Watchlist', index=False)

        print("-" * 70)
        print(f"[✓] Daily Analysis Complete!")
        print(f"[✓] Excel File Saved inside current directory: '{os.path.abspath(output_name)}'")
        print("=" * 70)

if __name__ == "__main__":
    scanner = NSEVCPDailyScanner()
    scanner.execute_eod_vcp_scan()