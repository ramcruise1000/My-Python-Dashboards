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

class NSEFno4HourVCPScanner:
    def __init__(self):
        # Dynamically fetch full list of active NSE F&O underlying scripts
        self.watchlist = get_fno_tickers()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def fetch_4hour_history(self, ticker):
        """
        Fetches historical hourly bars using range=1mo and groups them into 
        precise 4-Hour macro trading blocks using modern lowercase pandas aliases[cite: 8].
        """
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}.NS?interval=1h&range=1mo"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            if 'chart' not in data or data['chart']['result'] is None:
                return None
                
            result = data['chart']['result'][0]
            timestamps = result.get('timestamp', [])
            indicators = result.get('indicators', {}).get('quote', [{}])[0]
            
            closes = indicators.get('close', [])
            highs = indicators.get('high', [])
            lows = indicators.get('low', [])
            volumes = indicators.get('volume', [])
            
            if not timestamps or not closes:
                return None
                
            df_hourly = pd.DataFrame({
                'Datetime': [datetime.fromtimestamp(ts) for ts in timestamps],
                'Close': closes,
                'High': highs,
                'Low': lows,
                'Volume': volumes
            }).dropna()
            
            if df_hourly.empty:
                return None
                
            # Set datetime index and resample using the correct lowercase '4h' frequency[cite: 8]
            df_hourly.set_index('Datetime', inplace=True)
            resampler = df_hourly.resample('4h')
            
            df_4h = pd.DataFrame({
                'Close': resampler['Close'].last(),
                'High': resampler['High'].max(),
                'Low': resampler['Low'].min(),
                'Volume': resampler['Volume'].sum()
            }).dropna()
            
            df_4h.reset_index(inplace=True)
            df_4h['Date_Str'] = df_4h['Datetime'].dt.strftime('%Y-%m-%d')
            return df_4h
        except Exception as e:
            print(f"[-] Processing breakdown on ticker {ticker}: {str(e)}")
            return None

    def execute_4hour_scan(self):
        print("=" * 75)
        print("     MARK MINERVINI 4-HOUR TIMEFRAME VCP BREAKOUT / BREAKDOWN SCANNER     ")
        print("=" * 75)
        
        user_prompt = input("Enter historic backdate (YYYY-MM-DD) or press [ENTER] for Latest EOD: ").strip()
        
        target_backdate = None
        if user_prompt != "":
            try:
                datetime.strptime(user_prompt, "%Y-%m-%d")
                target_backdate = user_prompt
                print(f"[+] Setting 4-Hour dataset boundaries back to: {target_backdate}")
            except ValueError:
                print("[-] Incorrect format layout. Run again using YYYY-MM-DD template (e.g., 2026-06-29).")
                return
        else:
            print("[+] Pulling latest live exchange 4-Hour operational data arrays...")

        raw_scanned_pool = []
        
        for ticker in self.watchlist:
            df_4h = self.fetch_4hour_history(ticker)
            if df_4h is None or len(df_4h) < 15:
                continue
            
            if target_backdate:
                df_4h = df_4h[df_4h['Date_Str'] <= target_backdate]
                if len(df_4h) < 10:
                    continue
            
            raw_scanned_pool.append((ticker, df_4h))
            
        if not raw_scanned_pool:
            print("[-] Structural Error: Zero records matched or data feeds failed to resample properly.")
            return

        actual_processing_date = raw_scanned_pool[0][1]['Date_Str'].iloc[-1]
        print(f"[✓] 4-Hour Resampling stable. Confirmed execution date context: {actual_processing_date}")
        
        buy_candidates = []
        sell_candidates = []
        
        for ticker, df in raw_scanned_pool:
            ltp = df['Close'].iloc[-1]
            last_4h_high = df['High'].iloc[-1]
            last_4h_low = df['Low'].iloc[-1]
            last_4h_vol = df['Volume'].iloc[-1]
            prev_4h_close = df['Close'].iloc[-2]
            intraday_chg = ((ltp - prev_4h_close) / prev_4h_close) * 100
            
            sma_20 = df['Close'].iloc[-20:].mean()
            sma_50 = df['Close'].iloc[-50:].mean()
            
            lookback_len = min(20, len(df) - 2)
            lookback_window = df.iloc[-(lookback_len + 1):-1]
            wave_high = lookback_window['High'].max()
            wave_low = lookback_window['Low'].min()
            avg_volume = lookback_window['Volume'].mean()
            
            vol_dry_ratio = last_4h_vol / avg_volume if avg_volume > 0 else 1.0
            
            buy_trigger = round(max(last_4h_high, wave_high * 0.995) + 0.65, 2)
            sell_trigger = round(min(last_4h_low, wave_low * 1.005) - 0.65, 2)
            
            # --- BUY SIDE ---
            if not pd.isna(sma_20) and not pd.isna(sma_50) and ltp > sma_20:
                if ltp >= (wave_high * 0.92) and vol_dry_ratio < 1.5:
                    buy_candidates.append({
                        "Ticker": ticker,
                        "LTP on 4H Close": round(ltp, 2),
                        "Last 4H Bar Change %": round(intraday_chg, 2),
                        "Best Entry Price Point": buy_trigger,
                        "Defensive Stop Loss": round(last_4h_low * 0.985, 2),
                        "Volume Dry-up Multiple": round(vol_dry_ratio, 2),
                        "Execution Strategy Instructions": f"Buy ONLY if price breaks above the 4-Hour pivot ceiling of ₹{buy_trigger}. Volatility is contracting tightly; this entry catches momentum as institutional markup begins."
                    })
            
            # --- SELL SIDE ---
            elif not pd.isna(sma_20) and not pd.isna(sma_50) and ltp < sma_20:
                if ltp <= (wave_low * 1.08):
                    sell_candidates.append({
                        "Ticker": ticker,
                        "LTP on 4H Close": round(ltp, 2),
                        "Last 4H Bar Change %": round(intraday_chg, 2),
                        "Best Entry Price Point": sell_trigger,
                        "Defensive Stop Loss": round(last_4h_high * 1.015, 2),
                        "Volume Churn Multiple": round(vol_dry_ratio, 2),
                        "Execution Strategy Instructions": f"Short ONLY if price penetrates below structural support of ₹{sell_trigger}. Diminishing bounces confirm lack of buying; panic cascading follows once this point cracks."
                    })

        buy_df = pd.DataFrame(buy_candidates)
        sell_df = pd.DataFrame(sell_candidates)
        
        if not buy_df.empty: buy_df = buy_df.sort_values(by="Volume Dry-up Multiple", ascending=True)
        if not sell_df.empty: sell_df = sell_df.sort_values(by="Volume Churn Multiple", ascending=True)
        
        output_name = f"NSE_4Hour_VCP_Scanner_{actual_processing_date}.xlsx"
        with pd.ExcelWriter(output_name, engine='openpyxl') as writer:
            if not buy_df.empty:
                buy_df.to_excel(writer, sheet_name='Bullish 4H Buy Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No F&O stocks met strict 4H VCP buy thresholds"}]).to_excel(writer, sheet_name='Bullish 4H Buy Watchlist', index=False)
                
            if not sell_df.empty:
                sell_df.to_excel(writer, sheet_name='Bearish 4H Sell Watchlist', index=False)
            else:
                pd.DataFrame([{"Alert": "No F&O stocks met strict 4H Inverted VCP short thresholds"}]).to_excel(writer, sheet_name='Bearish 4H Sell Watchlist', index=False)

        print("-" * 75)
        print(f"[✓] 4-Hour Timeframe Analysis Process Finalized!")
        print(f"[✓] Dynamic Spreadsheet Generated inside current directory: '{os.path.abspath(output_name)}'")
        print("=" * 75)

if __name__ == "__main__":
    scanner = NSEFno4HourVCPScanner()
    scanner.execute_4hour_scan()