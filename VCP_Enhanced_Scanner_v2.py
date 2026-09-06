import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import os
import logging
import requests
import io

# Suppress yfinance warnings
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

# ============================================================
# CONFIGURATION
# ============================================================
RISK_PCT = 0.07          
REWARD_MULT = 3          
MIN_DATA_DAYS = 252      
VOLUME_THRESHOLD = 0.9   
LOOKBACK_DAYS = 15       # 15 calendar days covers 10 trading sessions for pending bases

global_last_trade_date = None 

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

    # 3. If all scraping attempts fail, use the hardcoded fallback
    print("⚠️ Could not fetch live F&O list from NSE due to strict bot protection. Using hardcoded fallback.")
    fno_fallback = [
        "AARTIIND", "ABB", "ABBOTINDIA", "ABCAPITAL", "ABFRL", "ACC", "ADANIENT", "ADANIPORTS", 
        "ALKEM", "AMBUJACEM", "APOLLOHOSP", "APOLLOTYRE", "ASHOKLEY", "ASIANPAINT", "ASTRAL", 
        "ATUL", "AUBANK", "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", 
        "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BATAINDIA", "BEL", "BERGEPAINT", 
        "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BOSCHLTD", "BPCL", "BRITANNIA", "BSOFT", 
        "CANBK", "CANFINHOME", "CHAMBLFERT", "CHOLAFIN", "CIPLA", "COALINDIA", "COFORGE", "COLPAL", 
        "CONCOR", "COROMANDEL", "CROMPTON", "CUB", "CUMMINSIND", "DABUR", "DALBHARAT", "DEEPAKNTR", 
        "DIVISLAB", "DIXON", "DLF", "DRREDDY", "EICHERMOT", "ESCORTS", "EXIDEIND", "FEDERALBNK", 
        "GAIL", "GLENMARK", "GMRINFRA", "GNFC", "GODREJCP", "GODREJPROP", "GRANULES", "GRASIM", 
        "GUJGASLTD", "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", 
        "HINDALCO", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "ICICIBANK", "ICICIGI", "ICICIPRULI", 
        "IDEA", "IDFCFIRSTB", "IEX", "IGL", "INDHOTEL", "INDIACEM", "INDIAMART", "INDIGO", 
        "INDUSINDBK", "INDUSTOWER", "INFY", "INTELLECT", "IOC", "IPCALAB", "IRCTC", "ITC", 
        "JINDALSTEL", "JSWSTEEL", "JUBLFOOD", "KOTAKBANK", "LTF", "LALPATHLAB", "LAURUSLABS", 
        "LICHSGFIN", "LT", "LTIM", "LTTS", "LUPIN", "M&M", "M&MFIN", "MANAPPURAM", "MARICO", 
        "MARUTI", "MCX", "METROPOLIS", "MFSL", "MGL", "MOTHERSON", "MPHASIS", "MRF", "MUTHOOTFIN", 
        "NATIONALUM", "NAUKRI", "NAVINFLUOR", "NESTLEIND", "NMDC", "NTPC", "OBEROIRLTY", "OFSS", 
        "ONGC", "PAGEIND", "PEL", "PERSISTENT", "PETRONET", "PFC", "PIDILITIND", "PIIND", "PNB", 
        "POLYCAB", "POWERGRID", "PVRINOX", "RAMCOCEM", "RBLBANK", "RECLTD", "RELIANCE", "SAIL", 
        "SBICARD", "SBILIFE", "SBIN", "SHREECEM", "SIEMENS", "SRF", "SUNPHARMA", "SUNTV", 
        "SYNGENE", "TATACHEM", "TATACOMM", "TATACONSUM", "TATAELXSI", "TATAMOTORS", "TATAPOWER", 
        "TATASTEEL", "TCS", "TECHM", "TITAN", "TORNTPHARM", "TRENT", "TVSMOTOR", "UBL", "ULTRACEMCO", 
        "UPL", "VEDL", "VOLTAS", "WIPRO", "ZEEL", "ZOMATO", "ZYDUSLIFE"
    ]
    return [f"{ticker}.NS" for ticker in fno_fallback]

def extract_ticker_context(ticker_symbol, target_date):
    global global_last_trade_date
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="2y")
        if df.empty or len(df) < MIN_DATA_DAYS:
            return None
            
        df.index = df.index.tz_localize(None)
        end_dt = pd.to_datetime(target_date)
        start_dt = end_dt - pd.Timedelta(days=40) 
        
        historical_data = df[df.index <= end_dt].copy()
        if historical_data.empty:
            return None
            
        # Dynamically updates to guarantee the absolute latest trading session is tracked
        max_date_str = historical_data.index.max().strftime('%Y-%m-%d')
        if global_last_trade_date is None or max_date_str > global_last_trade_date:
            global_last_trade_date = max_date_str
            
        historical_data['SMA_50'] = historical_data['Close'].rolling(window=50).mean()
        historical_data['SMA_150'] = historical_data['Close'].rolling(window=150).mean()
        historical_data['SMA_200'] = historical_data['Close'].rolling(window=200).mean()
        historical_data['52W_High'] = historical_data['High'].rolling(window=252).max()
        historical_data['52W_Low'] = historical_data['Low'].rolling(window=252).min()
        historical_data['Vol_50_Avg'] = historical_data['Volume'].rolling(window=50).mean()
        historical_data['Daily_Range'] = historical_data['High'] - historical_data['Low']
        
        window_dates = historical_data[(historical_data.index >= start_dt) & (historical_data.index <= end_dt)].index
        setups_history = []
        latest_close_overall = historical_data['Close'].iloc[-1]
        
        for eval_date in window_dates:
            idx = historical_data.index.get_loc(eval_date)
            if idx < MIN_DATA_DAYS: continue
                
            current_close = historical_data['Close'].iloc[idx]
            sma50 = historical_data['SMA_50'].iloc[idx]
            sma150 = historical_data['SMA_150'].iloc[idx]
            sma200 = historical_data['SMA_200'].iloc[idx]
            sma200_past = historical_data['SMA_200'].iloc[idx - 21]
            high_52w = historical_data['52W_High'].iloc[idx]
            low_52w = historical_data['52W_Low'].iloc[idx]
            
            # Trend Rules (Broadened slightly to catch deep VCP bases)
            long_trend_met = (current_close > sma150 and current_close > sma200 and sma150 > sma200 
                              and sma200 > sma200_past and sma50 > sma150 and sma50 > sma200 
                              and current_close > sma50 and current_close >= (1.30 * low_52w) 
                              and current_close >= (0.75 * high_52w))

            short_trend_met = (current_close < sma150 and current_close < sma200 and sma150 < sma200 
                               and sma200 <= sma200_past and sma50 < sma150 and sma50 < sma200 
                               and current_close < sma50 and current_close <= (1.35 * low_52w) 
                               and current_close <= (0.85 * high_52w))
                               
            vol_50_avg = historical_data['Vol_50_Avg'].iloc[idx]
            volume_dry_up = historical_data['Volume'].iloc[idx] < (vol_50_avg * VOLUME_THRESHOLD)
            
            recent_volatility = historical_data['Daily_Range'].iloc[idx-9:idx+1].mean()
            past_volatility = historical_data['Daily_Range'].iloc[idx-29:idx-9].mean()
            price_contraction = recent_volatility < past_volatility
            
            high_pivot = historical_data['High'].iloc[idx-14:idx+1].max()
            low_pivot = historical_data['Low'].iloc[idx-14:idx+1].min()
            
            rec = None
            orig_trigger = np.nan
            trap_trigger = np.nan
            
            if long_trend_met and price_contraction and volume_dry_up:
                rec, orig_trigger, trap_trigger = "BUY SETUP", round(high_pivot + 0.05, 2), round(low_pivot - 0.05, 2)
            elif short_trend_met and price_contraction and volume_dry_up:
                rec, orig_trigger, trap_trigger = "SELL SETUP", round(low_pivot - 0.05, 2), round(high_pivot + 0.05, 2)
                
            if rec:
                gap_pct = ((orig_trigger - current_close) / current_close) * 100
                forward_data = historical_data.iloc[idx+1:]
                
                min_low = forward_data['Low'].min() if not forward_data.empty else np.nan
                max_high = forward_data['High'].max() if not forward_data.empty else np.nan
                
                norm_triggered = False
                trap_triggered = False
                trap_return_pct = np.nan
                
                if rec == "SELL SETUP":
                    if not pd.isna(min_low) and min_low <= orig_trigger: norm_triggered = True
                    if not pd.isna(max_high) and max_high >= trap_trigger: trap_triggered = True
                    if not norm_triggered and trap_triggered:
                        trap_return_pct = ((latest_close_overall - trap_trigger) / trap_trigger) * 100
                        
                elif rec == "BUY SETUP":
                    if not pd.isna(max_high) and max_high >= orig_trigger: norm_triggered = True
                    if not pd.isna(min_low) and min_low <= trap_trigger: trap_triggered = True
                    if not norm_triggered and trap_triggered:
                        trap_return_pct = ((trap_trigger - latest_close_overall) / trap_trigger) * 100

                setups_history.append({
                    "Ticker": ticker_symbol.upper(),
                    "Date": eval_date.strftime('%Y-%m-%d'), 
                    "Type": rec, 
                    "Close": round(current_close, 2), 
                    "Latest_Close": round(latest_close_overall, 2), # ADDED for pending gap calc
                    "Orig_Trigger": orig_trigger,
                    "Trap_Trigger": trap_trigger,
                    "Gap %": round(gap_pct, 2), 
                    "Norm_Triggered?": norm_triggered,
                    "Trap_Triggered?": trap_triggered,
                    "Trap_Return_%": round(trap_return_pct, 2) if not pd.isna(trap_return_pct) else np.nan
                })
                
        return setups_history
    except Exception:
        return None

def apply_actionable_grading(row, enable_bear_traps, enable_bull_traps, is_today, is_pending_norm, is_pending_trap):
    actions = []
    
    tck = row['Ticker']
    dt = row['Date']
    
    cls = row['Latest_Close'] if not is_today and 'Latest_Close' in row else row['Close']
    orig_trig = row['Orig_Trigger']
    trap_trig = row['Trap_Trigger']
    
    orig_gap = ((orig_trig - cls) / cls) * 100
    abs_orig_gap = abs(orig_gap)
    
    if abs_orig_gap <= 1.5: orig_grade = "A"
    elif abs_orig_gap <= 4.0: orig_grade = "B"
    elif abs_orig_gap <= 8.0: orig_grade = "C"
    else: orig_grade = "D"
    
    if is_today or is_pending_norm:
        if row['Type'] == "BUY SETUP":
            actions.append({"Date": dt, "Ticker": tck, "Action": "STANDARD BUY", "Grade": orig_grade, "Close": round(cls, 2), "Trigger": orig_trig, "Gap %": round(orig_gap, 2), "SL": round(orig_trig * (1 - RISK_PCT), 2), "Target": round(orig_trig * (1 + (RISK_PCT * REWARD_MULT)), 2)})
        elif row['Type'] == "SELL SETUP":
            actions.append({"Date": dt, "Ticker": tck, "Action": "STANDARD SELL", "Grade": orig_grade, "Close": round(cls, 2), "Trigger": orig_trig, "Gap %": round(orig_gap, 2), "SL": round(orig_trig * (1 + RISK_PCT), 2), "Target": round(orig_trig * (1 - (RISK_PCT * REWARD_MULT)), 2)})

    if is_today or is_pending_trap:
        rev_gap = ((trap_trig - cls) / cls) * 100
        abs_rev = abs(rev_gap)
        trap_grade = "A" if abs_rev <= 1.5 else "B" if abs_rev <= 4.0 else "C" if abs_rev <= 8.0 else "D"
        
        if row['Type'] == "BUY SETUP" and enable_bull_traps:
            actions.append({"Date": dt, "Ticker": tck, "Action": "REVERSAL SELL (BULL TRAP)", "Grade": trap_grade, "Close": round(cls, 2), "Trigger": trap_trig, "Gap %": round(rev_gap, 2), "SL": round(trap_trig * (1 + RISK_PCT), 2), "Target": round(trap_trig * (1 - (RISK_PCT * REWARD_MULT)), 2)})
            
        elif row['Type'] == "SELL SETUP" and enable_bear_traps:
            actions.append({"Date": dt, "Ticker": tck, "Action": "REVERSAL BUY (BEAR TRAP)", "Grade": trap_grade, "Close": round(cls, 2), "Trigger": trap_trig, "Gap %": round(rev_gap, 2), "SL": round(trap_trig * (1 - RISK_PCT), 2), "Target": round(trap_trig * (1 + (RISK_PCT * REWARD_MULT)), 2)})
            
    return actions

if __name__ == "__main__":
    print(f"--- F&O VCP ADAPTIVE SCANNER v10.0 (Zero-Deletion Trap Engine) ---")
    user_date = input("Enter target end date (YYYY-MM-DD) or press Enter for today: ").strip()
    target_date = user_date if user_date else datetime.date.today().strftime("%Y-%m-%d")

    tickers = get_fno_tickers()
    all_historical = []
    
    print(f"\nPhase 1: Scanning {len(tickers)} stocks...")
    for i, ticker in enumerate(tickers, 1):
        print(f"\rProcessing {i}/{len(tickers)}: {ticker:<15}", end="", flush=True)
        hist = extract_ticker_context(ticker, target_date)
        if hist: all_historical.extend(hist)
        
    df_hist = pd.DataFrame(all_historical)
    if df_hist.empty:
        print("\nNo setups found. Exiting.")
        exit()
        
    last_trade_date = global_last_trade_date

    # ---------------------------------------------------------
    # PHASE 2: BEAR TRAP / MARKET REGIME STUDY
    # ---------------------------------------------------------
    print("\n\n" + "="*60)
    print("📈 30-DAY TRAP PERFORMANCE STUDY")
    print("="*60)
    
    bear_traps = df_hist[(df_hist['Type'] == 'SELL SETUP') & (df_hist['Norm_Triggered?'] == False) & (df_hist['Trap_Triggered?'] == True)]
    enable_bear_traps = True # Default enabled so you never miss a PIIND
    
    if not bear_traps.empty:
        bt_perf = bear_traps['Trap_Return_%'].mean()
        print(f"Study: Found {len(bear_traps)} Untriggered Sell Bases that sprung Bear Traps (Broke upwards).")
        print(f"Avg Profitability of buying the Trap Breakout: {bt_perf:.2f}%")
        if bt_perf > 0: print(">> BEAR TRAPS CONFIRMED PROFITABLE.")
    else:
        print("Study: No historically confirmed Bear Traps found in lookback window.")

    print("-" * 60)
    
    bull_traps = df_hist[(df_hist['Type'] == 'BUY SETUP') & (df_hist['Norm_Triggered?'] == False) & (df_hist['Trap_Triggered?'] == True)]
    enable_bull_traps = True # Default enabled
    if not bull_traps.empty:
        bull_perf = bull_traps['Trap_Return_%'].mean()
        print(f"Study: Found {len(bull_traps)} Untriggered Buy Bases that sprung Bull Traps (Broke downwards).")
        print(f"Avg Profitability of shorting the Trap Breakdown: {bull_perf:.2f}%")
        if bull_perf > 0: print(">> BULL TRAPS CONFIRMED PROFITABLE.")
    else:
        print("Study: No historically confirmed Bull Traps found in lookback window.")

    # ---------------------------------------------------------
    # PHASE 3: ACTIONABLE GRADING & 15-DAY PENDING ENGINE
    # ---------------------------------------------------------
    lookback_cutoff = (pd.to_datetime(last_trade_date) - pd.Timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')
    recent_setups = df_hist[df_hist['Date'] >= lookback_cutoff].copy()
    
    actionable_recs = []
    for _, row in recent_setups.iterrows():
        is_today = (row['Date'] == last_trade_date)
        is_pending_norm = (row['Norm_Triggered?'] == False)
        is_pending_trap = (row['Trap_Triggered?'] == False)
        
        if is_today or is_pending_norm or is_pending_trap:
            graded_actions = apply_actionable_grading(row, enable_bear_traps, enable_bull_traps, is_today, is_pending_norm, is_pending_trap)
            actionable_recs.extend(graded_actions)
            
    df_final_to_save = pd.DataFrame()
    
    if actionable_recs:
        df_all_acts = pd.DataFrame(actionable_recs)
        
        # 1. Print Last Session Actions
        df_today_acts = df_all_acts[df_all_acts['Date'] == last_trade_date].sort_values(by=['Grade', 'Ticker'])
        print("\n" + "="*60)
        print(f"🎯 LATEST TRADING SESSION SETUPS ({last_trade_date})")
        print("="*60)
        if not df_today_acts.empty:
            print(df_today_acts.to_string(index=False))
            df_final_to_save = pd.concat([df_final_to_save, df_today_acts], ignore_index=True)
        else:
            print("No new setups formed during the final session.")
            
        # 2. Print Pending Bases (15-Calendar-Day Window)
        df_pending_acts = df_all_acts[df_all_acts['Date'] < last_trade_date].sort_values(by=['Date', 'Ticker'], ascending=[False, True])
        df_pending_acts = df_pending_acts.drop_duplicates(subset=['Ticker', 'Action'], keep='first')
        
        print("\n" + "="*60)
        print(f"⏳ PENDING UNTRIGGERED BASES / TRAPS (LAST {LOOKBACK_DAYS} DAYS)")
        print("="*60)
        if not df_pending_acts.empty:
            print(df_pending_acts.to_string(index=False))
            df_final_to_save = pd.concat([df_final_to_save, df_pending_acts], ignore_index=True)
        else:
            print("No pending bases found.")
            
    # EXCEL EXPORT
    file_name = f"VCP_Master_Scanner_{target_date.replace('-', '_')}.xlsx"
    with pd.ExcelWriter(file_name) as writer:
        if not df_final_to_save.empty:
            df_final_to_save.to_excel(writer, sheet_name='Actionable_&_Pending', index=False)
            
        df_hist.sort_values(by=['Date', 'Ticker'], ascending=[False, True]).to_excel(writer, sheet_name='30_Day_Study_Log', index=False)
        
    print(f"\n✅ Scan, Study, and Export Complete! Saved to {file_name}")