import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging
from config import Config
from dhanhq import dhanhq

logger = logging.getLogger(__name__)

class DhanClient:
    def __init__(self):
        self.config = Config()
        self.client = dhanhq(self.config.DHAN_CLIENT_ID, self.config.DHAN_ACCESS_TOKEN)
        self.security_master_file = "security_master.csv"
        self.security_master_df = self._load_security_master()

    # =======================================================
    # Security Master Loader
    # =======================================================
    def _load_security_master(self) -> pd.DataFrame:
        """Load or fetch Dhan Security Master for NSE Equity"""
        if not os.path.exists(self.security_master_file):
            logger.info("Downloading Security Master...")
            url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            df = pd.read_csv(url, low_memory=False)

            # Normalize column names
            df.columns = df.columns.str.strip().str.lower()
            logger.info(f"CSV Columns Detected: {df.columns.tolist()}")

            # Detect exchange column dynamically
            exch_col = next((c for c in df.columns if 'exm' in c or 'exchange' in c), None)
            if exch_col:
                df[exch_col] = df[exch_col].astype(str).str.upper()
                df = df[df[exch_col].str.contains("NSE")]

            # Detect symbol & security_id columns
            symbol_col = next((c for c in df.columns if 'symbol' in c), None)
            secid_col = next((c for c in df.columns if 'security' in c and 'id' in c), None)

            if not symbol_col or not secid_col:
                logger.error("❌ Could not detect symbol/security_id columns!")
                return pd.DataFrame()

            df = df[[secid_col, symbol_col]].rename(columns={
                secid_col: 'security_id',
                symbol_col: 'symbol'
            })

            # Clean up symbols
            df['symbol'] = df['symbol'].astype(str).str.strip().str.upper()
            df.drop_duplicates(subset='symbol', inplace=True)

            df.to_csv(self.security_master_file, index=False)
            logger.info(f"✅ Saved {len(df)} NSE security IDs to {self.security_master_file}")
            return df
        else:
            logger.info("Loading existing Security Master...")
            return pd.read_csv(self.security_master_file)

    # =======================================================
    # Security ID Lookup
    # =======================================================
    def get_security_id(self, symbol: str) -> Optional[str]:
        """Fetch equity security ID for a given symbol (e.g., HDFC)"""
        symbol = symbol.strip().upper()
        
        if self.security_master_df is None or self.security_master_df.empty:
            logger.warning("Security master is empty.")
            print("DEBUG: Security master is empty or not loaded.")
            return None

        # Filter for equity only: exclude derivatives
        equity_df = self.security_master_df[
            self.security_master_df['symbol'].str.startswith(symbol) &
            (~self.security_master_df['symbol'].str.contains(
                r'FUT|CE|PE|CALL|PUT|OPT|AUG|JAN|FEB|MAR|APR|MAY|JUN|JUL|SEP|OCT|NOV|DEC',
                case=False, na=False))
        ]
        print(f"DEBUG: Filtered equity_df for symbol '{symbol}': {equity_df.shape[0]} rows")

        # Exact match if exists
        row = equity_df[equity_df['symbol'] == symbol]
        if not row.empty:
            print(f"DEBUG: Exact match found for symbol '{symbol}'")
            return str(row.iloc[0]['security_id'])

        # Fallback: first close match
        if not equity_df.empty:
            logger.warning(f"Using fallback match for symbol: {symbol}")
            print(f"DEBUG: Fallback match used for symbol '{symbol}'")
            print(equity_df.iloc[0]['security_id'])
            return str(equity_df.iloc[0]['security_id'])

        logger.warning(f"Security ID not found for {symbol}")
        print(f"DEBUG: No match found for symbol '{symbol}'")
        return None

    # =======================================================
    # Historical Data Fetch
    # =======================================================
    def get_historical_data(self, security_id: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Fetch 1-min data and convert to 3-min candles"""
        try:
            to_date = datetime.now().date()
            from_date = to_date - timedelta(days=days)

            from_date_str = from_date.strftime("%Y-%m-%d 09:15:00")
            to_date_str = to_date.strftime("%Y-%m-%d 15:30:00")

            logger.info(f"DEBUG CALL >>> {security_id} NSE_EQ EQUITY 1 {from_date_str} {to_date_str}")
            print(13)
            # Fetch 1-minute data (must pass numeric security_id)
            data = self.client.intraday_minute_data(
                security_id=security_id,
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
                interval=1,  # valid intervals: ['1','5','15','25','60']
                from_date=from_date_str,
                to_date=to_date_str
            )

            if data.get('status') == 'success' and data.get('data'):
                df = pd.DataFrame(data['data'])

                # Normalize columns
                rename_map = {
                    'start_Time': 'timestamp',
                    'start_time': 'timestamp',
                    'starttime': 'timestamp',
                    'open_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close',
                    'volume': 'volume'
                }
                df.rename(columns=rename_map, inplace=True)
                print(14)
                if 'timestamp' not in df.columns:
                    raise KeyError("No timestamp column detected in API response")

                # === Robust timestamp parsing ===
                try:
                    sample_ts = df['timestamp'].iloc[0]

                    if isinstance(sample_ts, (int, float)):
                        print(15)
                        if sample_ts > 1e12:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                        else:
                            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                    else:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
                except Exception as e:
                    print(16)
                    logger.error(f"[TimestampParseError] Could not parse timestamps: {e}")
                    return None

                df = df.sort_values('timestamp')
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                print(17)
                print(df)
                # Convert 1-minute data to 3-minute candles
                return self._resample_to_3min(df)

            logger.warning(f"No data returned for security ID {security_id}")
            return None

        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return None

    # =======================================================
    # Resample 1-min → 3-min
    # =======================================================
    def _resample_to_3min(self, df_1min: pd.DataFrame) -> pd.DataFrame:
        """Convert 1-minute data to 3-minute candles"""

        if df_1min.empty:
            return df_1min

        print("[DEBUG] Raw data before resample:", df_1min.head(10))
        print(f"[DEBUG] Raw row count: {len(df_1min)}")
        
        # Convert to datetime and filter out bad timestamps
        df_1min['timestamp'] = pd.to_datetime(df_1min['timestamp'],  utc=True)
        print(f"[DEBUG] Parsed timestamps: {df_1min['timestamp'].head(10)}")
        # Remove timestamps before year 2000 (optional cutoff)
        df_1min = df_1min[df_1min['timestamp'] >= pd.Timestamp('2000-01-01').tz_localize('UTC')]


        # Check again after filtering
        if df_1min.empty:
            logger.warning("Filtered data is empty after removing bad timestamps.")
            return pd.DataFrame()

        df_1min = df_1min.set_index('timestamp')

        # Resample to 3-minute candles
        df_3min = df_1min.resample('3min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        if df_3min is None or df_3min.empty:
            logger.warning(f"No data after resampling.")
            return pd.DataFrame()  # Explicitly return empty DataFrame
        print(18)
        return df_3min.reset_index()



# from dhanhq import dhanhq
# import pandas as pd
# from datetime import datetime, timedelta
# from typing import Optional
# from config import Config

# class DhanClient:
#     def __init__(self):
#         self.config = Config()
#         self.client = dhanhq(self.config.DHAN_CLIENT_ID, self.config.DHAN_ACCESS_TOKEN)

#     def get_historical_data(self, security_id: str, days: int = 30) -> Optional[pd.DataFrame]:
#         """Fetch 1-min data and convert to 3-min candles"""
#         try:
#             to_date = datetime.now().date()
#             from_date = to_date - timedelta(days=days)

#             from_date_str = from_date.strftime("%Y-%m-%d 09:15:00")
#             to_date_str = to_date.strftime("%Y-%m-%d 15:30:00")
#             print("DEBUG CALL >>>", security_id, "NSE_EQ", "EQUITY", "1", from_date_str, to_date_str)
#             # Fetch 1-minute data (smallest allowed interval)
#             data = self.client.intraday_minute_data(
#                 security_id=security_id,
#                 exchange_segment="NSE_EQ",
#                 instrument_type="EQUITY",
#                 interval='1',  # Must be '1' (DHAN only allows 1,5,15,25,60)
#                 from_date=from_date_str,
#                 to_date=to_date_str
#             )

#             if data['status'] == 'success' and data['data']:
#                 df = pd.DataFrame(data['data'])

#                 # Rename columns to standard OHLCV format
#                 df = df.rename(columns={
#                     'start_Time': 'timestamp',
#                     'open_price': 'open',
#                     'high_price': 'high',
#                     'low_price': 'low',
#                     'close_price': 'close',
#                     'volume': 'volume'
#                 })

#                 df['timestamp'] = pd.to_datetime(df['timestamp'])
#                 df = df.sort_values('timestamp')  # Ensure chronological order
#                 df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

#                 # Convert 1-minute data to 3-minute candles
#                 df = self._resample_to_3min(df)
#                 return df
#             return None
#         except Exception as e:
#             print(f"Error fetching historical data: {e}")
#             return None

#     def _resample_to_3min(self, df_1min: pd.DataFrame) -> pd.DataFrame:
#         """Convert 1-minute data to 3-minute candles"""
#         if df_1min.empty:
#             return df_1min

#         df_1min = df_1min.set_index('timestamp')
#         df_3min = df_1min.resample('3T').agg({
#             'open': 'first',
#             'high': 'max',
#             'low': 'min',
#             'close': 'last',
#             'volume': 'sum'
#         }).dropna()

#         return df_3min.reset_index()
    