import sys
import subprocess

# 1. Auto-Install Dependencies (Now includes xlsxwriter for Excel formatting)
try:
    import pandas as pd
    from nselib import derivatives
    import xlsxwriter
except ImportError:
    print("[!] Missing or outdated libraries. Installing nselib, pandas, and xlsxwriter...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "nselib", "xlsxwriter", "--upgrade", "--quiet"])
    import pandas as pd
    from nselib import derivatives
    import xlsxwriter

from datetime import datetime, timedelta
import warnings

# Suppress pandas chained assignment warnings
warnings.filterwarnings('ignore')

def get_user_date():
    while True:
        user_input = input("Enter the end date for the scan (YYYY-MM-DD) or press Enter for today: ").strip()
        
        if not user_input:
            today = datetime.today()
            print(f"No date entered. Defaulting to today: {today.strftime('%Y-%m-%d')}")
            return today
            
        try:
            return datetime.strptime(user_input, "%Y-%m-%d")
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

def standardize_columns(df, trade_date):
    """
    Standardizes column names and strictly isolates options using robust logic.
    """
    df.columns = df.columns.astype(str).str.strip().str.upper().str.replace(' ', '_')
    df = df.loc[:, ~df.columns.duplicated()]
    
    col_mapping = {
        'TCKRSYMB': 'SYMBOL',
        'XPRYDT': 'EXPIRY_DT',
        'EXPIRY_DATE': 'EXPIRY_DT',
        'STRKPRIC': 'STRIKE_PR',
        'STRIKE_PRICE': 'STRIKE_PR',
        'OPTNTP': 'OPTION_TYP',
        'OPTION_TYPE': 'OPTION_TYP',
        'HGHPRIC': 'HIGH',
        'LWPRIC': 'LOW',
        'CLSPRIC': 'CLOSE',
        'CLOSE_PRICE': 'CLOSE',
        'HIGH_PRICE': 'HIGH',
        'LOW_PRICE': 'LOW'
    }
    df = df.rename(columns=col_mapping)
    
    essential_cols = ['SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP', 'HIGH', 'LOW', 'CLOSE']
    missing = [c for c in essential_cols if c not in df.columns]
    if missing:
        print(f"      [Debug] Missing columns: {missing}. Available headers: {list(df.columns)}")
        return pd.DataFrame()
        
    for col in ['SYMBOL', 'OPTION_TYP', 'EXPIRY_DT']:
        df[col] = df[col].astype(str).str.strip().str.upper()
        
    # Standardize Option Types (Handles 'CALL' -> 'CE', 'PUT' -> 'PE')
    df['OPTION_TYP'] = df['OPTION_TYP'].replace({'CALL': 'CE', 'PUT': 'PE', 'C': 'CE', 'P': 'PE'})
    
    # 1. Filter: Keep only CE and PE options
    df = df[df['OPTION_TYP'].isin(['CE', 'PE'])]
    if df.empty:
        return df
        
    # 2. Filter: Safely parse dates 
    df['EXPIRY_DT'] = pd.to_datetime(df['EXPIRY_DT'], errors='coerce').dt.strftime('%Y-%m-%d')
    df = df.dropna(subset=['EXPIRY_DT'])
    if df.empty:
        return df
    
    # 3. Convert numeric columns
    for col in ['HIGH', 'LOW', 'CLOSE', 'STRIKE_PR']:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
        
    # 4. Filter: Actively traded contracts only (Prices > 0)
    df = df[(df['CLOSE'] > 0) & (df['HIGH'] > 0) & (df['LOW'] > 0)]
    if df.empty:
        return df
        
    # Create unified Contract ID for perfect 10-day alignment
    df['CONTRACT_ID'] = (
        df['SYMBOL'] + "_" + 
        df['EXPIRY_DT'] + "_" + 
        df['STRIKE_PR'].astype(str) + "_" + 
        df['OPTION_TYP']
    )
    
    df['DATE'] = pd.to_datetime(trade_date)
    return df[['DATE', 'CONTRACT_ID', 'SYMBOL', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP', 'HIGH', 'LOW', 'CLOSE']]

def fetch_and_process_last_10_days(end_date):
    valid_dfs = []
    current_date = end_date
    attempts = 0
    max_lookback = 25
    
    print(f"\nFetching NSE F&O Data for the 10 trading sessions ending {end_date.strftime('%Y-%m-%d')} using nselib...")
    
    while len(valid_dfs) < 10 and attempts < max_lookback:
        attempts += 1
        
        if current_date.weekday() < 5:
            date_str = current_date.strftime('%Y-%m-%d')
            nselib_date = current_date.strftime('%d-%m-%Y')
            
            try:
                df = derivatives.fno_bhav_copy(trade_date=nselib_date)
                
                if df is not None and not df.empty:
                    clean_df = standardize_columns(df, current_date.date())
                    if not clean_df.empty:
                        valid_dfs.append(clean_df)
                        print(f" -> Fetched and processed {len(clean_df)} valid options for {date_str}")
                    else:
                        pass # Silently skip days with no valid options
                else:
                    print(f" x Skipped {date_str} (Market Holiday / Data empty)")
                    
            except Exception as e:
                error_msg = str(e).split('\n')[0][:60]
                print(f" x Skipped {date_str} (Exception: {error_msg})")
                
        current_date -= timedelta(days=1)
        
    if len(valid_dfs) < 10:
        print(f"\n[!] WARNING: Only found {len(valid_dfs)} trading days in the last {max_lookback} days.")
        
    return valid_dfs

def main():
    target_date = get_user_date()
    dfs = fetch_and_process_last_10_days(target_date)
    
    if not dfs:
        print("\n[-] No data was successfully downloaded. Exiting.")
        sys.exit(1)
    
    print("\nProcessing 2-Day High (HH) and Low (LL) breakout logic...")
    
    master_df = pd.concat(dfs, ignore_index=True)
    master_df = master_df.sort_values(by=['CONTRACT_ID', 'DATE']).reset_index(drop=True)
    
    # 1. Calculate Previous 2-Day Highest High
    master_df['PREV_2D_HIGH'] = master_df.groupby('CONTRACT_ID')['HIGH'].transform(
        lambda x: x.shift(1).rolling(window=2).max()
    )
    
    # 2. Calculate Previous 2-Day Lowest Low
    master_df['PREV_2D_LOW'] = master_df.groupby('CONTRACT_ID')['LOW'].transform(
        lambda x: x.shift(1).rolling(window=2).min()
    )
    
    master_df = master_df.dropna(subset=['PREV_2D_HIGH', 'PREV_2D_LOW'])
    
    # 3. Filter for the LATEST available date in the dataset
    latest_date_in_data = master_df['DATE'].max()
    latest_date_str = latest_date_in_data.strftime('%Y-%m-%d')
    latest_df = master_df[master_df['DATE'] == latest_date_in_data].copy()
    
    # 4. Classify Signals
    latest_df['SIGNAL'] = 'NORMAL'
    latest_df.loc[latest_df['CLOSE'] > latest_df['PREV_2D_HIGH'], 'SIGNAL'] = 'ABOVE_2D_HH'
    latest_df.loc[latest_df['CLOSE'] < latest_df['PREV_2D_LOW'], 'SIGNAL'] = 'BELOW_2D_LL'
    
    # Filter out normal price action (keep only breakout & breakdown options)
    breakout_df = latest_df[latest_df['SIGNAL'] != 'NORMAL'].copy()
    breakout_df = breakout_df.sort_values(by=['SIGNAL', 'SYMBOL', 'STRIKE_PR'])
    
    print("\n" + "="*95)
    print("OPTIONS SCANNER: 2-DAY HIGHER HIGH (HH) & LOWER LOW (LL) BREAKOUTS".center(95))
    print("="*95)
    
    if breakout_df.empty:
        print(f"No option contracts met the 2-Day HH or LL breakout criteria for {latest_date_str}.")
    else:
        results = breakout_df[['DATE', 'SYMBOL', 'OPTION_TYP', 'STRIKE_PR', 'EXPIRY_DT', 'PREV_2D_HIGH', 'PREV_2D_LOW', 'CLOSE', 'SIGNAL']].copy()
        results['DATE'] = results['DATE'].dt.strftime('%Y-%m-%d')
        
        print(results.to_string(index=False))
        
        # EXCEL EXPORT LOGIC (Replaces CSV export)
        excel_filename = f"Breakout_HH_LL_Options_{latest_date_str}.xlsx"
        
        # Use Pandas ExcelWriter with the xlsxwriter engine
        with pd.ExcelWriter(excel_filename, engine='xlsxwriter') as writer:
            results.to_excel(writer, index=False, sheet_name='Breakouts')
            
            # Access the underlying workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['Breakouts']
            
            # Freeze the first row
            worksheet.freeze_panes(1, 0)
            
            # Add a slight format to the header (bold)
            header_format = workbook.add_format({'bold': True, 'bottom': 1, 'bg_color': '#F2F2F2'})
            for col_num, value in enumerate(results.columns.values):
                worksheet.write(0, col_num, value, header_format)
            
            # Auto-adjust column widths for readability
            for i, col in enumerate(results.columns):
                column_width = max(results[col].astype(str).map(len).max(), len(col)) + 3
                worksheet.set_column(i, i, column_width)
                
        print(f"\n[+] Processing complete! Scan ran successfully for the date: {latest_date_str}")
        print(f"[+] Saved {len(results)} breakout/breakdown contracts to '{excel_filename}'.")

if __name__ == "__main__":
    main()