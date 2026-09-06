import yfinance as yf
import pandas as pd
import datetime
import os
import logging

# Suppress yfinance warnings to keep the terminal clean
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def get_fno_tickers():
    fno_list = [
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
    return [f"{ticker}.NS" for ticker in fno_list]

def run_adaptive_scanner(target_date):
    tickers = get_fno_tickers()
    total_tickers = len(tickers)
    
    end_dt = pd.to_datetime(target_date)
    start_dt = end_dt - pd.Timedelta(days=30)
    
    all_setups = []
    
    print(f"\n1. Scanning & Analyzing F&O universe for {start_dt.strftime('%Y-%m-%d')} to {target_date}...")
    
    for i, ticker_symbol in enumerate(tickers, 1):
        print(f"\rScanning {i}/{total_tickers}: {ticker_symbol:<15}", end="", flush=True)
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period="2y")
            if df.empty or len(df) < 252:
                continue
                
            df.index = df.index.tz_localize(None)
            historical_data = df[df.index <= end_dt].copy()
            if historical_data.empty:
                continue
                
            historical_data['SMA_50'] = historical_data['Close'].rolling(window=50).mean()
            historical_data['SMA_150'] = historical_data['Close'].rolling(window=150).mean()
            historical_data['SMA_200'] = historical_data['Close'].rolling(window=200).mean()
            historical_data['52W_High'] = historical_data['High'].rolling(window=252).max()
            historical_data['52W_Low'] = historical_data['Low'].rolling(window=252).min()
            historical_data['Vol_50_Avg'] = historical_data['Volume'].rolling(window=50).mean()
            historical_data['Daily_Range'] = historical_data['High'] - historical_data['Low']
            
            window_dates = historical_data[(historical_data.index >= start_dt) & (historical_data.index <= end_dt)].index
            
            for eval_date in window_dates:
                idx = historical_data.index.get_loc(eval_date)
                if idx < 252:
                    continue
                    
                current_close = historical_data['Close'].iloc[idx]
                current_vol = historical_data['Volume'].iloc[idx]
                
                sma50 = historical_data['SMA_50'].iloc[idx]
                sma150 = historical_data['SMA_150'].iloc[idx]
                sma200 = historical_data['SMA_200'].iloc[idx]
                sma200_past = historical_data['SMA_200'].iloc[idx - 21]
                high_52w = historical_data['52W_High'].iloc[idx]
                low_52w = historical_data['52W_Low'].iloc[idx]
                
                # Standard VCP (Long)
                long_trend_met = (current_close > sma150 and current_close > sma200 and sma150 > sma200 
                                  and sma200 > sma200_past and sma50 > sma150 and sma50 > sma200 
                                  and current_close > sma50 and current_close >= (1.30 * low_52w) 
                                  and current_close >= (0.75 * high_52w))

                # Reverse VCP (Short)
                short_trend_met = (current_close < sma150 and current_close < sma200 and sma150 < sma200 
                                   and sma200 < sma200_past and sma50 < sma150 and sma50 < sma200 
                                   and current_close < sma50 and current_close <= (1.25 * low_52w) 
                                   and current_close <= (0.70 * high_52w))
                
                vol_50_avg = historical_data['Vol_50_Avg'].iloc[idx]
                volume_dry_up = current_vol < (vol_50_avg * 0.9)
                
                recent_volatility = historical_data['Daily_Range'].iloc[idx-9:idx+1].mean()
                past_volatility = historical_data['Daily_Range'].iloc[idx-29:idx-9].mean()
                price_contraction = recent_volatility < past_volatility
                
                high_pivot = historical_data['High'].iloc[idx-14:idx+1].max()
                low_pivot = historical_data['Low'].iloc[idx-14:idx+1].min()  
                
                risk_pct = 0.07  
                reward_pct = risk_pct * 3  
                
                # Fetch Forward EOD Return (from setup day to target_date)
                latest_close = historical_data['Close'].iloc[-1]
                forward_return = ((latest_close - current_close) / current_close) * 100
                
                if long_trend_met and price_contraction and volume_dry_up:
                    trigger_price = round(high_pivot + 0.05, 2)
                    sl = round(trigger_price * (1 - risk_pct), 2)
                    target = round(trigger_price * (1 + reward_pct), 2)
                    all_setups.append({"Ticker": ticker_symbol, "Date": eval_date, "Type": "BUY SETUP", "Close": current_close, "Trigger": trigger_price, "SL": sl, "Target": target, "Forward_Return": forward_return})
                    
                elif short_trend_met and price_contraction and volume_dry_up:
                    trigger_price_short = round(low_pivot - 0.05, 2)
                    sl_short = round(trigger_price_short * (1 + risk_pct), 2)
                    target_short = round(trigger_price_short * (1 - reward_pct), 2)
                    all_setups.append({"Ticker": ticker_symbol, "Date": eval_date, "Type": "SELL SETUP", "Close": current_close, "Trigger": trigger_price_short, "SL": sl_short, "Target": target_short, "Forward_Return": forward_return})
        except Exception:
            pass

    print("\n\n2. Analyzing Setup Performance Over Last 30 Days...")
    df_results = pd.DataFrame(all_setups)
    
    if df_results.empty:
        print("No setups found in the window.")
        return
        
    # Isolate outcome tracking
    buy_setups = df_results[df_results['Type'] == 'BUY SETUP']
    sell_setups = df_results[df_results['Type'] == 'SELL SETUP']
    
    buy_perf = buy_setups['Forward_Return'].mean() if not buy_setups.empty else 0
    sell_perf = sell_setups['Forward_Return'].mean() if not sell_setups.empty else 0
    
    print(f"Average Forward Return for BUY Setups: {buy_perf:.2f}%")
    print(f"Average Forward Return for SELL Setups (Reverse VCP): {sell_perf:.2f}%")
    
    # Adaptation Flags
    buy_reversal_flag = True if buy_perf < 0 else False
    sell_reversal_flag = True if sell_perf > 0 else False
    
    print("\n--- Strategy Adaptation Matrix ---")
    if not buy_reversal_flag:
        print(">> LONG MARKET: Buy breakouts are working. Scanner will issue BUY SETUPs.")
    else:
        print(">> BULL TRAPS: Breakouts are failing (returns < 0). Scanner will issue REVERSAL SELLs.")
        
    if not sell_reversal_flag:
        print(">> SHORT MARKET: Breakdowns are working. Scanner will issue Reverse VCP SELL SETUPs.")
    else:
        print(">> BEAR TRAPS: Breakdowns are failing (returns > 0). Scanner will issue REVERSAL BUYs.")
    
    # 3. Generate Next Session Recommendations
    print(f"\n3. Generating Final Recommendations for Next Trading Session (Based on {target_date})...")
    latest_date_available = df_results['Date'].max()
    todays_setups = df_results[df_results['Date'] == latest_date_available].copy()
    
    final_recs = []
    for _, row in todays_setups.iterrows():
        if row['Type'] == 'BUY SETUP':
            if buy_reversal_flag:
                # Convert to Reversal Sell (Bull Trap)
                row['Type'] = 'REVERSAL SELL (BULL TRAP)'
                pivot = row['Trigger'] - 0.05
                row['Trigger'] = round(pivot - 0.05, 2) # Short if it fails the pivot
                row['SL'] = round(row['Trigger'] * (1 + 0.07), 2)
                row['Target'] = round(row['Trigger'] * (1 - 0.21), 2)
            final_recs.append(row)
            
        elif row['Type'] == 'SELL SETUP':
            if sell_reversal_flag:
                # Convert to Reversal Buy (Bear Trap)
                row['Type'] = 'REVERSAL BUY (BEAR TRAP)'
                pivot = row['Trigger'] + 0.05
                row['Trigger'] = round(pivot + 0.05, 2) # Buy if it bounces off the pivot
                row['SL'] = round(row['Trigger'] * (1 - 0.07), 2)
                row['Target'] = round(row['Trigger'] * (1 + 0.21), 2)
            final_recs.append(row)
            
    final_df = pd.DataFrame(final_recs)
    
    # Clean output display
    if not final_df.empty:
        final_df = final_df.drop(columns=['Forward_Return'])
        final_df['Date'] = final_df['Date'].dt.strftime('%Y-%m-%d')
        print(final_df.to_string(index=False))
    else:
        print("No active setups generated for the next session.")
    
    # Save the study log and recommendations to Excel
    clean_date_str = target_date.replace("-", "_")
    file_name = f"FnO_Symmetric_Adaptive_Scan_{clean_date_str}.xlsx"
    with pd.ExcelWriter(file_name) as writer:
        if not final_df.empty:
            final_df.to_excel(writer, sheet_name='Next_Session_Recs', index=False)
        df_results.to_excel(writer, sheet_name='30_Day_Study_Log', index=False)
    
    print(f"\n✅ Scan and Study Complete! Results saved to {file_name}")


if __name__ == "__main__":
    print("--- F&O VCP Symmetric Adaptive Scanner ---")
    user_date_input = input("Enter target end date (YYYY-MM-DD) or press Enter for today: ").strip()
    
    if not user_date_input:
        target_date = datetime.date.today().strftime("%Y-%m-%d")
        print(f"No date provided. Defaulting to today: {target_date}")
    else:
        try:
            datetime.datetime.strptime(user_date_input, "%Y-%m-%d")
            target_date = user_date_input
        except ValueError:
            print("Invalid format. Please use YYYY-MM-DD (e.g., 2026-05-14). Exiting.")
            exit()
            
    run_adaptive_scanner(target_date)