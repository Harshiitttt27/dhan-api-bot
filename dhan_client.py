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
        """Fetch security ID for a given symbol"""
        symbol = symbol.strip().upper()
        if self.security_master_df is None or self.security_master_df.empty:
            logger.warning("Security master is empty.")
            return None

        # Exact match
        row = self.security_master_df[self.security_master_df['symbol'] == symbol]
        if not row.empty:
            return str(row.iloc[0]['security_id'])

        # Fallback: substring match
        row = self.security_master_df[self.security_master_df['symbol'].str.contains(symbol)]
        if not row.empty:
            return str(row.iloc[0]['security_id'])

        logger.warning(f"Security ID not found for {symbol}")
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

                # Ensure timestamp column exists
                if 'timestamp' not in df.columns:
                    raise KeyError("No timestamp column detected in API response")

                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

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

        df_1min = df_1min.set_index('timestamp')
        df_3min = df_1min.resample('3min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

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
    