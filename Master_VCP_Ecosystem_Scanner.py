"""
================================================================================
MASTER VCP & MOMENTUM ECOSYSTEM SCANNER
================================================================================
Consolidated scanner that runs all 8 scanner modules:
  1. Strict F&O VCP Backtester
  2. NSE F&O VCP Scanner Daily
  3. Micro-VCP (1:4 RR) Screener
  4. VCP Study from Top Gainers
  5. Dynamic Two-Day Pattern Study
  6. Momentum from Two Days Top Gainers/Losers
  7. Daily Momentum VCP Scanner
  8. 4-Hour Momentum VCP Scanner

Then analyzes confluence across all scanners to produce:
  - Master Buy Recommendations (top 5)
  - Master Sell Recommendations (top 5)
  - Exact entry triggers, stop losses, and targets
  - Confluence score showing scanner agreement

Usage:
    python Master_VCP_Ecosystem_Scanner.py

Dependencies:
    pip install yfinance pandas numpy openpyxl requests
================================================================================
"""

import pandas as pd
import numpy as np
import yfinance as yf
import os
import warnings
from datetime import datetime
import logging
import requests

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


# ==============================================================================
# SECTION 0: DYNAMIC TICKER FETCHING ENGINE
# ==============================================================================

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
    print("⚠️ Could not fetch live F&O list from NSE due to bot protection. Using hardcoded fallback.")
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


# ==============================================================================
# SECTION 1: CONFIGURATION & STOCK UNIVERSES
# ==============================================================================

class Config:
    """Master configuration for all scanner parameters."""

    # Full F&O universe lists populated dynamically at runtime
    FNO_TICKERS_FULL = []

    # --- Specialized Subsets ---
    FNO_TICKERS_30 = [
        "MARUTI.NS", "TITAN.NS", "BAJFINANCE.NS", "ADANIENT.NS", "DIVISLAB.NS",
        "EICHERMOT.NS", "TATACONSUM.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS",
        "BHARTIARTL.NS", "TATASTEEL.NS", "RELIANCE.NS", "CIPLA.NS", "AXISBANK.NS",
        "INFY.NS", "DLF.NS", "INDHOTEL.NS", "LTTS.NS", "PFC.NS",
        "TATACOMM.NS", "HDFCBANK.NS", "ICICIBANK.NS", "JINDALSTEL.NS", "M&M.NS",
        "INDIGO.NS", "COALINDIA.NS", "ITC.NS", "SUNPHARMA.NS", "SBIN.NS"
    ]

    FNO_TICKERS_24 = [
        "MARUTI.NS", "TITAN.NS", "BAJFINANCE.NS", "ADANIENT.NS", "DIVISLAB.NS",
        "EICHERMOT.NS", "TATACONSUM.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS",
        "BHARTIARTL.NS", "TATASTEEL.NS", "RELIANCE.NS", "CIPLA.NS", "AXISBANK.NS",
        "INFY.NS", "DLF.NS", "INDHOTEL.NS", "LTTS.NS", "PFC.NS",
        "TATACOMM.NS", "HDFCBANK.NS", "ICICIBANK.NS", "JINDALSTEL.NS"
    ]

    FNO_TICKERS_20 = [
        "MARUTI.NS", "TITAN.NS", "BAJFINANCE.NS", "ADANIENT.NS", "DIVISLAB.NS",
        "EICHERMOT.NS", "TATACONSUM.NS", "TCS.NS", "WIPRO.NS", "HCLTECH.NS",
        "BHARTIARTL.NS", "TATASTEEL.NS", "RELIANCE.NS", "CIPLA.NS", "AXISBANK.NS",
        "INFY.NS", "DLF.NS", "INDHOTEL.NS", "LTTS.NS", "PFC.NS"
    ]

    FNO_TICKERS_33 = [
        "DRREDDY.NS", "CIPLA.NS", "TORNTPHARM.NS", "NATIONALUM.NS", "MAXHEALTH.NS",
        "PERSISTENT.NS", "ASTRAL.NS", "SUPREMEIND.NS", "WAAREE.NS", "KPITTECH.NS",
        "LUPIN.NS", "MANKIND.NS", "GLENMARK.NS", "MARICO.NS", "NAM-INDIA.NS",
        "PIIND.NS", "UNOMINDA.NS", "SBICARD.NS", "TATACONSUM.NS", "RELIANCE.NS",
        "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",
        "BHARTIARTL.NS", "ITC.NS", "TRENT.NS", "M&M.NS", "MARUTI.NS",
        "INDIGO.NS", "HINDALCO.NS", "KOTAKBANK.NS"
    ]

    # --- Parameters ---
    STRICT_TIGHTNESS = 3.0
    STRICT_VOLUME_RATIO = 0.85
    STRICT_RISK_PCT = 0.07
    STRICT_REWARD_PCT = 0.21

    DAILY_VOLUME_RATIO = 0.90
    DAILY_RECENT_DAYS = 10
    DAILY_PAST_DAYS = 20

    MICRO_TIGHTNESS = 3.5
    MICRO_VOLUME_RATIO = 0.85
    MICRO_RR_MULTIPLIER = 4
    MICRO_LOOKBACK = 40

    DYNAMIC_SQUEEZE_PENALTY = 15
    DYNAMIC_VOLUME_BOOST = 30
    DYNAMIC_VOL_THRESHOLD = 0.90

    MOMENTUM_SQUEEZE_THRESHOLD = 6.0
    MOMENTUM_VOL_EXPANSION = 1.2

    DAILY_MOM_PROXIMITY_BUY = 0.94
    DAILY_MOM_PROXIMITY_SELL = 1.06
    DAILY_MOM_VOLUME_TOLERANCE = 1.25
    DAILY_MOM_ENTRY_BUFFER = 0.55
    DAILY_MOM_SL_PCT = 0.015

    H4_PROXIMITY_BUY = 0.92
    H4_PROXIMITY_SELL = 1.08
    H4_VOLUME_TOLERANCE = 1.5
    H4_ENTRY_BUFFER = 0.65
    H4_SL_PCT = 0.015


# ==============================================================================
# SECTION 2: DATA FETCHING ENGINE
# ==============================================================================

class DataEngine:
    """Unified data fetching for daily and intraday timeframes."""

    @staticmethod
    def fetch_daily(symbol, target_date, period="2y", min_bars=252):
        """Fetch daily OHLCV data via yfinance."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1d")
            if df.empty or len(df) < min_bars:
                return None
            df.columns = [c.capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[df.index <= target_date]
            if len(df) < 20:
                return None
            return df
        except Exception:
            return None

    @staticmethod
    def fetch_hourly(symbol, target_date, period="1mo", min_bars=100):
        """Fetch 1-hour data and resample to 4H."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1h")
            if df.empty or len(df) < min_bars:
                return None
            df.columns = [c.capitalize() for c in df.columns]
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[df.index <= target_date]
            if len(df) < 40:
                return None
            df_4h = df.resample('4h').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()
            return df_4h
        except Exception:
            return None


# ==============================================================================
# SECTION 3: SCANNER MODULES
# ==============================================================================

class ScannerModule:
    """Base class for all scanner modules."""

    def __init__(self, name, tickers, target_date):
        self.name = name
        self.tickers = tickers
        self.target_date = target_date
        self.results = []

    def run(self):
        raise NotImplementedError


class StrictVCPScanner(ScannerModule):
    """Scanner 1: Strict F&O VCP Backtester"""

    def run(self):
        print(f"    [1/8] Running Strict VCP Scanner on {len(self.tickers)} stocks...")
        setups = []
        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="2y", min_bars=252)
            if df is None or len(df) < 252:
                continue
            try:
                close = df['Close'].iloc[-1]
                sma50 = df['Close'].rolling(50).mean().iloc[-1]
                sma150 = df['Close'].rolling(150).mean().iloc[-1]
                sma200 = df['Close'].rolling(200).mean().iloc[-1]
                sma200_21 = df['Close'].rolling(200).mean().iloc[-22]
                high_52w = df['High'].rolling(252).max().iloc[-1]
                low_52w = df['Low'].rolling(252).min().iloc[-1]
                vol_50 = df['Volume'].rolling(50).mean().iloc[-1]

                vol_contract = df['Volume'].iloc[-1] < vol_50 * Config.STRICT_VOLUME_RATIO
                if not vol_contract:
                    continue

                recent5 = df.iloc[-5:]
                range_pct = ((recent5['High'].max() - recent5['Low'].min()) / recent5['Low'].min()) * 100
                if range_pct > Config.STRICT_TIGHTNESS:
                    continue

                high_pivot = df['High'].iloc[-16:-1].max()
                low_pivot = df['Low'].iloc[-16:-1].min()

                if (close > sma150 and close > sma200 and sma150 > sma200 and 
                    sma200 > sma200_21 and sma50 > sma150 and sma50 > sma200 and
                    close > sma50 and close >= 1.30 * low_52w and close >= 0.75 * high_52w):

                    trigger = high_pivot + 0.05
                    sl = trigger * (1 - Config.STRICT_RISK_PCT)
                    target = trigger * (1 + Config.STRICT_REWARD_PCT)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'Strict_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(trigger, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:3',
                        '5DayRangePct': round(range_pct, 2),
                        'Score': 100
                    })

                elif (close < sma150 and close < sma200 and sma150 < sma200 and
                      sma200 < sma200_21 and sma50 < sma150 and sma50 < sma200 and
                      close < sma50 and close <= 1.25 * low_52w and close <= 0.70 * high_52w):

                    trigger = low_pivot - 0.05
                    sl = trigger * (1 + Config.STRICT_RISK_PCT)
                    target = trigger * (1 - Config.STRICT_REWARD_PCT)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'Strict_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(trigger, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:3',
                        '5DayRangePct': round(range_pct, 2),
                        'Score': 100
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


class DailyVCPScanner(ScannerModule):
    """Scanner 2: NSE F&O VCP Scanner Daily (Relative Contraction)"""

    def run(self):
        print(f"    [2/8] Running Daily VCP Scanner on {len(self.tickers)} stocks...")
        setups = []
        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="2y", min_bars=252)
            if df is None or len(df) < 60:
                continue
            try:
                close = df['Close'].iloc[-1]
                sma50 = df['Close'].rolling(50).mean().iloc[-1]
                sma150 = df['Close'].rolling(150).mean().iloc[-1]
                sma200 = df['Close'].rolling(200).mean().iloc[-1]
                sma200_21 = df['Close'].rolling(200).mean().iloc[-22]
                high_52w = df['High'].rolling(252).max().iloc[-1]
                low_52w = df['Low'].rolling(252).min().iloc[-1]
                vol_50 = df['Volume'].rolling(50).mean().iloc[-1]

                vol_contract = df['Volume'].iloc[-1] < vol_50 * Config.DAILY_VOLUME_RATIO
                if not vol_contract:
                    continue

                df['DailyRange'] = df['High'] - df['Low']
                recent_vol = df['DailyRange'].iloc[-10:].mean()
                past_vol = df['DailyRange'].iloc[-30:-10].mean()
                if recent_vol >= past_vol:
                    continue

                high_pivot = df['High'].iloc[-16:-1].max()
                low_pivot = df['Low'].iloc[-16:-1].min()

                if (close > sma150 and close > sma200 and sma150 > sma200 and
                    sma200 > sma200_21 and sma50 > sma150 and sma50 > sma200 and
                    close > sma50 and close >= 1.30 * low_52w and close >= 0.75 * high_52w):

                    trigger = high_pivot + 0.05
                    sl = trigger * (1 - Config.STRICT_RISK_PCT)
                    target = trigger * (1 + Config.STRICT_REWARD_PCT)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'Daily_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(trigger, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:3',
                        'RecentVol': round(recent_vol, 2),
                        'PastVol': round(past_vol, 2),
                        'Score': 90
                    })

                elif (close < sma150 and close < sma200 and sma150 < sma200 and
                      sma200 < sma200_21 and sma50 < sma150 and sma50 < sma200 and
                      close < sma50 and close <= 1.25 * low_52w and close <= 0.70 * high_52w):

                    trigger = low_pivot - 0.05
                    sl = trigger * (1 + Config.STRICT_RISK_PCT)
                    target = trigger * (1 - Config.STRICT_REWARD_PCT)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'Daily_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(trigger, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:3',
                        'RecentVol': round(recent_vol, 2),
                        'PastVol': round(past_vol, 2),
                        'Score': 90
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


class MicroVCPScanner(ScannerModule):
    """Scanner 3: Micro-VCP (1:4 RR) Screener"""

    def run(self):
        print(f"    [3/8] Running Micro-VCP Scanner on {len(self.tickers)} stocks...")
        setups = []
        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="3mo", min_bars=40)
            if df is None or len(df) < 35:
                continue
            try:
                df = df.tail(Config.MICRO_LOOKBACK)
                close = df['Close'].iloc[-1]
                sma20 = df['Close'].rolling(20).mean().iloc[-1]
                vol_sma20 = df['Volume'].rolling(20).mean().iloc[-1]

                recent5 = df.iloc[-5:]
                range_pct = ((recent5['High'].max() - recent5['Low'].min()) / recent5['Low'].min()) * 100
                if range_pct > Config.MICRO_TIGHTNESS:
                    continue

                recent_vol_avg = recent5['Volume'].mean()
                if recent_vol_avg >= vol_sma20 * Config.MICRO_VOLUME_RATIO:
                    continue

                five_high = recent5['High'].max()
                five_low = recent5['Low'].min()

                if close > sma20:
                    entry = five_high + 0.05
                    sl = five_low - 0.05
                    risk = entry - sl
                    target = entry + (Config.MICRO_RR_MULTIPLIER * risk)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'Micro_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(entry, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:4',
                        '5DayRangePct': round(range_pct, 2),
                        'Score': 85
                    })

                elif close < sma20:
                    entry = five_low - 0.05
                    sl = five_high + 0.05
                    risk = sl - entry
                    target = entry - (Config.MICRO_RR_MULTIPLIER * risk)
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'Micro_VCP',
                        'Close': round(close, 2),
                        'Trigger': round(entry, 2),
                        'StopLoss': round(sl, 2),
                        'Target': round(target, 2),
                        'RR': '1:4',
                        '5DayRangePct': round(range_pct, 2),
                        'Score': 85
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


class VCPStudyScanner(ScannerModule):
    """Scanner 4: VCP Study from Top Gainers (Predictive Scorer)"""

    def run(self):
        print(f"    [4/8] Running VCP Study from Top Gainers on {len(self.tickers)} stocks...")
        universe_data = {}
        performances = []

        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="6mo", min_bars=35)
            if df is not None and len(df) >= 20:
                universe_data[sym] = df
                two_day = ((df['Close'].iloc[-1] - df['Close'].iloc[-3]) / df['Close'].iloc[-3]) * 100
                performances.append({'Symbol': sym, 'TwoDayReturn': two_day})

        if not performances:
            print(f"          -> No data available")
            return []

        perf_df = pd.DataFrame(performances)
        gainers = perf_df.sort_values('TwoDayReturn', ascending=False).head(5)['Symbol'].tolist()
        losers = perf_df.sort_values('TwoDayReturn', ascending=True).head(5)['Symbol'].tolist()

        gainer_depths = []
        for sym in gainers:
            hist_15 = universe_data[sym].iloc[:-2].tail(15)
            seg3 = hist_15.iloc[10:15]
            depth = ((seg3['High'].max() - seg3['Low'].min()) / seg3['Low'].min()) * 100
            gainer_depths.append(depth)
        benchmark_depth = np.mean(gainer_depths) if gainer_depths else 4.0

        setups = []
        exclude = gainers + losers
        for sym, df in universe_data.items():
            if sym in exclude:
                continue
            try:
                recent_15 = df.tail(15)
                seg1 = recent_15.iloc[0:5]
                seg2 = recent_15.iloc[5:10]
                seg3 = recent_15.iloc[10:15]

                r1 = ((seg1['High'].max() - seg1['Low'].min()) / seg1['Low'].min()) * 100
                r2 = ((seg2['High'].max() - seg2['Low'].min()) / seg2['Low'].min()) * 100
                r3 = ((seg3['High'].max() - seg3['Low'].min()) / seg3['Low'].min()) * 100

                tightening = (r1 > r2) or (r2 > r3)
                vol_dry = seg3['Volume'].mean() < seg1['Volume'].mean()

                score = 40
                if tightening: score += 30
                if vol_dry: score += 30
                depth_var = abs(r3 - benchmark_depth)
                score = max(0, score - int(depth_var * 4))

                if score <= 0:
                    continue

                close = df['Close'].iloc[-1]
                ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                pct_change = df['Close'].pct_change().iloc[-1] * 100

                long_entry = seg3['High'].max() * 1.002
                long_sl = seg3['Low'].min() * 0.995
                short_entry = seg3['Low'].min() * 0.998
                short_sl = seg3['High'].max() * 1.005

                if close >= ema20 and pct_change >= 0:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'VCP_Study',
                        'Close': round(close, 2),
                        'Trigger': round(long_entry, 2),
                        'StopLoss': round(long_sl, 2),
                        'Target': round(long_entry * 1.06, 2),
                        'RR': '~1:2',
                        'Score': score,
                        'BenchmarkDepth': round(benchmark_depth, 2)
                    })
                elif close < ema20 and pct_change < 0:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'VCP_Study',
                        'Close': round(close, 2),
                        'Trigger': round(short_entry, 2),
                        'StopLoss': round(short_sl, 2),
                        'Target': round(short_entry * 0.94, 2),
                        'RR': '~1:2',
                        'Score': score,
                        'BenchmarkDepth': round(benchmark_depth, 2)
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups (Benchmark Depth: {benchmark_depth:.2f}%)")
        return setups


class DynamicTwoDayScanner(ScannerModule):
    """Scanner 5: Dynamic Two-Day Pattern Study"""

    def run(self):
        print(f"    [5/8] Running Dynamic Two-Day Pattern Study on {len(self.tickers)} stocks...")
        universe_data = {}
        performances = []

        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="6mo", min_bars=30)
            if df is not None and len(df) >= 18:
                universe_data[sym] = df
                two_day = ((df['Close'].iloc[-1] - df['Close'].iloc[-3]) / df['Close'].iloc[-3]) * 100
                performances.append({'Symbol': sym, 'TwoDayReturn': two_day})

        if not performances:
            print(f"          -> No data available")
            return []

        perf_df = pd.DataFrame(performances)
        gainers = perf_df.sort_values('TwoDayReturn', ascending=False).head(5)['Symbol'].tolist()
        losers = perf_df.sort_values('TwoDayReturn', ascending=True).head(5)['Symbol'].tolist()

        gainer_ranges = []
        for sym in gainers:
            hist_15 = universe_data[sym].iloc[:-2].tail(15)
            gainer_ranges.append(((hist_15['High'].max() - hist_15['Low'].min()) / hist_15['Low'].min()) * 100)
        target_compression = np.mean(gainer_ranges) if gainer_ranges else 5.0

        setups = []
        exclude = gainers + losers
        for sym, df in universe_data.items():
            if sym in exclude:
                continue
            try:
                recent_15 = df.tail(15)
                max_p = recent_15['High'].max()
                min_p = recent_15['Low'].min()
                current_range = ((max_p - min_p) / min_p) * 100
                avg_vol = recent_15['Volume'].mean()

                squeeze_score = max(0, 100 - abs(current_range - target_compression) * Config.DYNAMIC_SQUEEZE_PENALTY)
                if squeeze_score <= 0:
                    continue

                close = df['Close'].iloc[-1]
                ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                pct_change = df['Close'].pct_change().iloc[-1] * 100
                vol_boost = Config.DYNAMIC_VOLUME_BOOST if df['Volume'].iloc[-1] > avg_vol * Config.DYNAMIC_VOL_THRESHOLD else 0

                is_bullish = (close >= ema20) and (pct_change >= 0)
                is_bearish = (close < ema20) and (pct_change < 0)

                upside = (squeeze_score + vol_boost) if is_bullish else 0
                downside = (squeeze_score + vol_boost) if is_bearish else 0

                if upside > 0:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'Dynamic_2Day',
                        'Close': round(close, 2),
                        'Trigger': round(close * 1.01, 2),
                        'StopLoss': round(close * 0.985, 2),
                        'Target': round(close * 1.03, 2),
                        'RR': '~1:2',
                        'Score': upside,
                        '15DayRangePct': round(current_range, 2),
                        'TargetCompression': round(target_compression, 2)
                    })
                if downside > 0:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'Dynamic_2Day',
                        'Close': round(close, 2),
                        'Trigger': round(close * 0.99, 2),
                        'StopLoss': round(close * 1.015, 2),
                        'Target': round(close * 0.97, 2),
                        'RR': '~1:2',
                        'Score': downside,
                        '15DayRangePct': round(current_range, 2),
                        'TargetCompression': round(target_compression, 2)
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups (Target Compression: {target_compression:.2f}%)")
        return setups


class MomentumTwoDayScanner(ScannerModule):
    """Scanner 6: Momentum from Two Days Top Gainers/Losers (Universal Scoring)"""

    def run(self):
        print(f"    [6/8] Running Momentum Two-Day Scanner on {len(self.tickers)} stocks...")
        setups = []

        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="6mo", min_bars=25)
            if df is None or len(df) < 18:
                continue
            try:
                close = df['Close'].iloc[-1]
                today_perf = df['Close'].pct_change().iloc[-1] * 100

                history_pool = df.iloc[:-2].tail(15)
                max_price = history_pool['High'].max()
                min_price = history_pool['Low'].min()
                consolidation_range = ((max_price - min_price) / min_price) * 100
                avg_hist_vol = history_pool['Volume'].mean()

                ema20 = df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]

                is_squeezed = consolidation_range <= Config.MOMENTUM_SQUEEZE_THRESHOLD
                volume_breakout = df['Volume'].iloc[-1] > avg_hist_vol * Config.MOMENTUM_VOL_EXPANSION
                price_breakout = close > history_pool['Close'].max()

                long_score = 0
                if is_squeezed: long_score += 40
                if volume_breakout: long_score += 30
                if price_breakout: long_score += 30

                lower_highs = df['High'].iloc[-2] < history_pool['High'].max()
                below_ema = close < ema20
                heavy_down_vol = (today_perf < 0) and (df['Volume'].iloc[-1] > avg_hist_vol)

                short_score = 0
                if lower_highs: short_score += 35
                if below_ema: short_score += 35
                if heavy_down_vol: short_score += 30

                if long_score >= 30:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'BUY',
                        'Scanner': 'Momentum_2Day',
                        'Close': round(close, 2),
                        'Trigger': round(close * 1.005, 2),
                        'StopLoss': round(close * 0.98, 2),
                        'Target': round(close * 1.04, 2),
                        'RR': '~1:2',
                        'Score': long_score,
                        'LongPatternScore': long_score,
                        'ShortPatternScore': short_score,
                        '15DayRangePct': round(consolidation_range, 2)
                    })

                if short_score >= 30:
                    setups.append({
                        'Symbol': sym.replace('.NS', ''),
                        'Direction': 'SELL',
                        'Scanner': 'Momentum_2Day',
                        'Close': round(close, 2),
                        'Trigger': round(close * 0.995, 2),
                        'StopLoss': round(close * 1.02, 2),
                        'Target': round(close * 0.96, 2),
                        'RR': '~1:2',
                        'Score': short_score,
                        'LongPatternScore': long_score,
                        'ShortPatternScore': short_score,
                        '15DayRangePct': round(consolidation_range, 2)
                    })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


class DailyMomentumScanner(ScannerModule):
    """Scanner 7: Daily Momentum VCP Scanner"""

    def run(self):
        print(f"    [7/8] Running Daily Momentum Scanner on {len(self.tickers)} stocks...")
        setups = []

        for sym in self.tickers:
            df = DataEngine.fetch_daily(sym, self.target_date, period="3mo", min_bars=50)
            if df is None or len(df) < 25:
                continue
            try:
                close = df['Close'].iloc[-1]
                day_high = df['High'].iloc[-1]
                day_low = df['Low'].iloc[-1]
                day_vol = df['Volume'].iloc[-1]
                prev_close = df['Close'].iloc[-2]
                intraday_chg = ((close - prev_close) / prev_close) * 100

                sma20 = df['Close'].iloc[-20:].mean()
                sma50 = df['Close'].iloc[-50:].mean()

                historical_window = df.iloc[-16:-1]
                wave_high = historical_window['High'].max()
                wave_low = historical_window['Low'].min()
                avg_volume = historical_window['Volume'].mean()

                vol_ratio = day_vol / avg_volume if avg_volume > 0 else 1.0
                if vol_ratio >= Config.DAILY_MOM_VOLUME_TOLERANCE:
                    continue

                buy_trigger = round(day_high + Config.DAILY_MOM_ENTRY_BUFFER, 2)
                sell_trigger = round(day_low - Config.DAILY_MOM_ENTRY_BUFFER, 2)

                if close > sma20 and sma20 > sma50:
                    if close >= wave_high * Config.DAILY_MOM_PROXIMITY_BUY:
                        setups.append({
                            'Symbol': sym.replace('.NS', ''),
                            'Direction': 'BUY',
                            'Scanner': 'Daily_Momentum',
                            'Close': round(close, 2),
                            'Trigger': buy_trigger,
                            'StopLoss': round(day_low * (1 - Config.DAILY_MOM_SL_PCT), 2),
                            'Target': round(buy_trigger * 1.045, 2),
                            'RR': '~1:3',
                            'Score': 80,
                            'VolRatio': round(vol_ratio, 2),
                            'IntradayChg': round(intraday_chg, 2)
                        })

                elif close < sma20 and sma20 < sma50:
                    if close <= wave_low * Config.DAILY_MOM_PROXIMITY_SELL:
                        setups.append({
                            'Symbol': sym.replace('.NS', ''),
                            'Direction': 'SELL',
                            'Scanner': 'Daily_Momentum',
                            'Close': round(close, 2),
                            'Trigger': sell_trigger,
                            'StopLoss': round(day_high * (1 + Config.DAILY_MOM_SL_PCT), 2),
                            'Target': round(sell_trigger * 0.955, 2),
                            'RR': '~1:3',
                            'Score': 80,
                            'VolRatio': round(vol_ratio, 2),
                            'IntradayChg': round(intraday_chg, 2)
                        })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


class FourHourMomentumScanner(ScannerModule):
    """Scanner 8: 4-Hour Momentum VCP Scanner"""

    def run(self):
        print(f"    [8/8] Running 4H Momentum Scanner on {len(self.tickers)} stocks...")
        setups = []

        for sym in self.tickers:
            df = DataEngine.fetch_hourly(sym, self.target_date, period="1mo", min_bars=100)
            if df is None or len(df) < 40:
                continue
            try:
                close = df['Close'].iloc[-1]
                last_4h_high = df['High'].iloc[-1]
                last_4h_low = df['Low'].iloc[-1]
                last_4h_vol = df['Volume'].iloc[-1]

                sma20 = df['Close'].iloc[-20:].mean()
                sma50 = df['Close'].iloc[-50:].mean()
                if pd.isna(sma20) or pd.isna(sma50):
                    continue

                lookback = min(20, len(df) - 2)
                wave_high = df['High'].iloc[-lookback-1:-1].max()
                wave_low = df['Low'].iloc[-lookback-1:-1].min()
                avg_vol = df['Volume'].iloc[-lookback-1:-1].mean()

                vol_ratio = last_4h_vol / avg_vol if avg_vol > 0 else 1.0
                if vol_ratio >= Config.H4_VOLUME_TOLERANCE:
                    continue

                if close > sma20:
                    if close >= wave_high * Config.H4_PROXIMITY_BUY:
                        trigger = max(last_4h_high, wave_high * 0.995) + Config.H4_ENTRY_BUFFER
                        sl = last_4h_low * (1 - Config.H4_SL_PCT)
                        setups.append({
                            'Symbol': sym.replace('.NS', ''),
                            'Direction': 'BUY',
                            'Scanner': '4H_Momentum',
                            'Close': round(close, 2),
                            'Trigger': round(trigger, 2),
                            'StopLoss': round(sl, 2),
                            'Target': round(trigger * 1.045, 2),
                            'RR': '~1:3',
                            'Score': 75,
                            'VolRatio': round(vol_ratio, 2),
                            'WaveHigh': round(wave_high, 2)
                        })

                elif close < sma20:
                    if close <= wave_low * Config.H4_PROXIMITY_SELL:
                        trigger = min(last_4h_low, wave_low * 1.005) - Config.H4_ENTRY_BUFFER
                        sl = last_4h_high * (1 + Config.H4_SL_PCT)
                        setups.append({
                            'Symbol': sym.replace('.NS', ''),
                            'Direction': 'SELL',
                            'Scanner': '4H_Momentum',
                            'Close': round(close, 2),
                            'Trigger': round(trigger, 2),
                            'StopLoss': round(sl, 2),
                            'Target': round(trigger * 0.955, 2),
                            'RR': '~1:3',
                            'Score': 75,
                            'VolRatio': round(vol_ratio, 2),
                            'WaveLow': round(wave_low, 2)
                        })
            except Exception:
                continue
        self.results = setups
        print(f"          -> Found {len(setups)} setups")
        return setups


# ==============================================================================
# SECTION 4: CONFLUENCE ENGINE
# ==============================================================================

class ConfluenceEngine:
    """
    Analyzes outputs from all 8 scanners to find high-probability setups.

    Scoring weights:
      - Strict VCP:     10 points
      - Daily VCP:       8 points
      - VCP Study:       7 points
      - Daily Momentum:  6 points
      - 4H Momentum:     6 points
      - Micro-VCP:       5 points
      - Dynamic 2-Day:   4 points
      - Momentum 2-Day:  3 points
    """

    SCANNER_WEIGHTS = {
        'Strict_VCP': 10,
        'Daily_VCP': 8,
        'VCP_Study': 7,
        'Daily_Momentum': 6,
        '4H_Momentum': 6,
        'Micro_VCP': 5,
        'Dynamic_2Day': 4,
        'Momentum_2Day': 3
    }

    @classmethod
    def analyze(cls, all_results):
        print("\n[+] Running Confluence Engine...")

        all_setups = []
        for scanner_name, setups in all_results.items():
            for s in setups:
                s['Weight'] = cls.SCANNER_WEIGHTS.get(scanner_name, 1)
                all_setups.append(s)

        if not all_setups:
            print("    [!] No setups found across any scanner.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame(all_setups)

        buy_confluence = {}
        sell_confluence = {}

        for _, row in df.iterrows():
            sym = row['Symbol']
            direction = row['Direction']
            weight = row['Weight']
            score = row.get('Score', 0)

            if row['Scanner'] in ['VCP_Study', 'Dynamic_2Day', 'Momentum_2Day'] and score < 50:
                weight = weight // 2

            target = buy_confluence if direction == 'BUY' else sell_confluence

            if sym not in target:
                target[sym] = {
                    'Symbol': sym,
                    'Direction': direction,
                    'ConfluenceScore': 0,
                    'Scanners': [],
                    'Scores': [],
                    'Triggers': [],
                    'StopLosses': [],
                    'Targets': [],
                    'Closes': [],
                    'BestScanner': None,
                    'BestWeight': 0
                }

            target[sym]['ConfluenceScore'] += weight
            target[sym]['Scanners'].append(row['Scanner'])
            target[sym]['Scores'].append(score)
            target[sym]['Triggers'].append(row['Trigger'])
            target[sym]['StopLosses'].append(row['StopLoss'])
            target[sym]['Targets'].append(row['Target'])
            target[sym]['Closes'].append(row['Close'])

            if weight > target[sym]['BestWeight']:
                target[sym]['BestWeight'] = weight
                target[sym]['BestScanner'] = row['Scanner']

        def build_recommendations(confluence_dict, direction):
            if not confluence_dict:
                return pd.DataFrame()

            rows = []
            for sym, data in confluence_dict.items():
                best_idx = 0
                best_priority = -1
                scanner_priority = {
                    'VCP_Study': 4,
                    'Daily_Momentum': 3,
                    '4H_Momentum': 3,
                    'Micro_VCP': 2,
                    'Strict_VCP': 1,
                    'Daily_VCP': 1,
                    'Dynamic_2Day': 0,
                    'Momentum_2Day': 0
                }

                for i, scanner in enumerate(data['Scanners']):
                    prio = scanner_priority.get(scanner, 0)
                    if prio > best_priority:
                        best_priority = prio
                        best_idx = i

                avg_trigger = np.mean(data['Triggers'])
                avg_sl = np.mean(data['StopLosses'])
                avg_target = np.mean(data['Targets'])

                cs = data['ConfluenceScore']
                if cs >= 20:
                    confidence = 'VERY HIGH'
                elif cs >= 15:
                    confidence = 'HIGH'
                elif cs >= 10:
                    confidence = 'MEDIUM'
                elif cs >= 5:
                    confidence = 'LOW'
                else:
                    confidence = 'SPECULATIVE'

                trigger = data['Triggers'][best_idx]
                sl = data['StopLosses'][best_idx]
                target = data['Targets'][best_idx]

                if direction == 'BUY':
                    rr = f"1:{round(abs(target - trigger) / abs(trigger - sl), 1)}" if abs(trigger - sl) > 0 else "N/A"
                else:
                    rr = f"1:{round(abs(trigger - target) / abs(sl - trigger), 1)}" if abs(sl - trigger) > 0 else "N/A"

                rows.append({
                    'Symbol': sym,
                    'Direction': direction,
                    'ConfluenceScore': cs,
                    'Confidence': confidence,
                    'ScannersAgree': ', '.join(data['Scanners']),
                    'NumScanners': len(data['Scanners']),
                    'ClosePrice': round(data['Closes'][best_idx], 2),
                    'EntryTrigger': round(trigger, 2),
                    'StopLoss': round(sl, 2),
                    'Target': round(target, 2),
                    'RiskReward': rr,
                    'PrimaryScanner': data['BestScanner'],
                    'AvgTrigger': round(avg_trigger, 2),
                    'AvgSL': round(avg_sl, 2),
                    'AvgTarget': round(avg_target, 2)
                })

            rec_df = pd.DataFrame(rows)
            rec_df = rec_df.sort_values('ConfluenceScore', ascending=False)
            return rec_df

        buy_recs = build_recommendations(buy_confluence, 'BUY')
        sell_recs = build_recommendations(sell_confluence, 'SELL')

        # Build confluence matrix
        all_symbols = set(list(buy_confluence.keys()) + list(sell_confluence.keys()))
        matrix_rows = []
        for sym in all_symbols:
            row = {'Symbol': sym}
            if sym in buy_confluence:
                row['BuyConfluence'] = buy_confluence[sym]['ConfluenceScore']
                row['BuyScanners'] = ', '.join(buy_confluence[sym]['Scanners'])
            else:
                row['BuyConfluence'] = 0
                row['BuyScanners'] = ''

            if sym in sell_confluence:
                row['SellConfluence'] = sell_confluence[sym]['ConfluenceScore']
                row['SellScanners'] = ', '.join(sell_confluence[sym]['Scanners'])
            else:
                row['SellConfluence'] = 0
                row['SellScanners'] = ''

            row['NetConfluence'] = row['BuyConfluence'] - row['SellConfluence']
            matrix_rows.append(row)

        matrix_df = pd.DataFrame(matrix_rows).sort_values('NetConfluence', ascending=False)

        print(f"    [+] Buy candidates: {len(buy_recs)} | Sell candidates: {len(sell_recs)}")
        return buy_recs, sell_recs, matrix_df


# ==============================================================================
# SECTION 5: MASTER OUTPUT GENERATOR
# ==============================================================================

class MasterOutput:
    """Generates final Excel and console output."""

    @staticmethod
    def generate(buy_recs, sell_recs, matrix_df, all_results, target_date):
        date_str = target_date.strftime("%Y%m%d")
        filename = f"Master_VCP_Ecosystem_Recommendations_{date_str}.xlsx"

        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # Sheet 1: Master Buy Recommendations
            if not buy_recs.empty:
                top_buy = buy_recs.head(10)
                top_buy.to_excel(writer, sheet_name='MASTER_BUY_TOP10', index=False)
            else:
                pd.DataFrame([{'Alert': 'No buy setups found across ecosystem'}]).to_excel(
                    writer, sheet_name='MASTER_BUY_TOP10', index=False)

            # Sheet 2: Master Sell Recommendations
            if not sell_recs.empty:
                top_sell = sell_recs.head(10)
                top_sell.to_excel(writer, sheet_name='MASTER_SELL_TOP10', index=False)
            else:
                pd.DataFrame([{'Alert': 'No sell setups found across ecosystem'}]).to_excel(
                    writer, sheet_name='MASTER_SELL_TOP10', index=False)

            # Sheet 3: Confluence Matrix
            if not matrix_df.empty:
                matrix_df.to_excel(writer, sheet_name='Confluence_Matrix', index=False)

            # Sheet 4: All Raw Results
            all_raw = []
            for scanner, setups in all_results.items():
                for s in setups:
                    s_copy = s.copy()
                    s_copy['Scanner'] = scanner
                    all_raw.append(s_copy)
            if all_raw:
                pd.DataFrame(all_raw).to_excel(writer, sheet_name='All_Raw_Results', index=False)

        return filename

    @staticmethod
    def print_summary(buy_recs, sell_recs, filename):
        print("\n" + "="*80)
        print("     MASTER VCP ECOSYSTEM SCANNER - FINAL RECOMMENDATIONS")
        print("="*80)

        print("\n" + "-"*80)
        print("  TOP BUY RECOMMENDATIONS (Next Trading Session)")
        print("-"*80)
        if buy_recs.empty:
            print("  No high-confluence buy setups found.")
        else:
            for i, row in buy_recs.head(5).iterrows():
                print(f"\n  [{i+1}] {row['Symbol']}  |  Confidence: {row['Confidence']}")
                print(f"       Confluence Score: {row['ConfluenceScore']} | Scanners: {row['NumScanners']} ({row['ScannersAgree']})")
                print(f"       Close: ₹{row['ClosePrice']}  →  Entry: ₹{row['EntryTrigger']}  →  Target: ₹{row['Target']}")
                print(f"       Stop Loss: ₹{row['StopLoss']}  |  R:R = {row['RiskReward']}  |  Source: {row['PrimaryScanner']}")

        print("\n" + "-"*80)
        print("  TOP SELL RECOMMENDATIONS (Next Trading Session)")
        print("-"*80)
        if sell_recs.empty:
            print("  No high-confluence sell setups found.")
        else:
            for i, row in sell_recs.head(5).iterrows():
                print(f"\n  [{i+1}] {row['Symbol']}  |  Confidence: {row['Confidence']}")
                print(f"       Confluence Score: {row['ConfluenceScore']} | Scanners: {row['NumScanners']} ({row['ScannersAgree']})")
                print(f"       Close: ₹{row['ClosePrice']}  →  Entry: ₹{row['EntryTrigger']}  →  Target: ₹{row['Target']}")
                print(f"       Stop Loss: ₹{row['StopLoss']}  |  R:R = {row['RiskReward']}  |  Source: {row['PrimaryScanner']}")

        print("\n" + "="*80)
        print(f"  Output saved to: {os.path.abspath(filename)}")
        print("="*80)


# ==============================================================================
# SECTION 6: MAIN EXECUTION
# ==============================================================================

def main():
    print("="*80)
    print("     MASTER VCP & MOMENTUM ECOSYSTEM SCANNER")
    print("     Unified 8-Scanner Confluence Engine")
    print("="*80)

    # Get target date
    user_input = input("\nEnter Target Analysis Date (YYYY-MM-DD) [Leave blank for Today]: ").strip()
    if not user_input:
        target_date = datetime.today()
    else:
        try:
            target_date = datetime.strptime(user_input, "%Y-%m-%d")
        except ValueError:
            print("[!] Invalid format. Defaulting to Today.")
            target_date = datetime.today()

    # Dynamically fetch latest F&O tickers from NSE
    print("\n[#] Fetching latest official NSE F&O ticker list...")
    Config.FNO_TICKERS_FULL = get_fno_tickers()

    print(f"\n[#] Analysis date: {target_date.strftime('%Y-%m-%d')}")
    print("[#] This will take 3-8 minutes depending on internet speed...\n")

    # Initialize all scanners with the dynamic F&O list
    scanners = [
        StrictVCPScanner("Strict_VCP", Config.FNO_TICKERS_FULL, target_date),
        DailyVCPScanner("Daily_VCP", Config.FNO_TICKERS_FULL, target_date),
        MicroVCPScanner("Micro_VCP", Config.FNO_TICKERS_FULL, target_date),
        VCPStudyScanner("VCP_Study", Config.FNO_TICKERS_30, target_date),
        DynamicTwoDayScanner("Dynamic_2Day", Config.FNO_TICKERS_24, target_date),
        MomentumTwoDayScanner("Momentum_2Day", Config.FNO_TICKERS_20, target_date),
        DailyMomentumScanner("Daily_Momentum", Config.FNO_TICKERS_33, target_date),
        FourHourMomentumScanner("4H_Momentum", Config.FNO_TICKERS_33, target_date),
    ]

    # Run all scanners
    all_results = {}
    for scanner in scanners:
        try:
            results = scanner.run()
            all_results[scanner.name] = results
        except Exception as e:
            print(f"    [!] Error in {scanner.name}: {str(e)}")
            all_results[scanner.name] = []

    # Run confluence engine
    buy_recs, sell_recs, matrix_df = ConfluenceEngine.analyze(all_results)

    # Generate output
    filename = MasterOutput.generate(buy_recs, sell_recs, matrix_df, all_results, target_date)
    MasterOutput.print_summary(buy_recs, sell_recs, filename)


if __name__ == "__main__":
    main()