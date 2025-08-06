# from dhanhq import dhanhq
# import pandas as pd
# from datetime import datetime, time, timedelta
# from typing import Dict, Optional
# from config import Config

# class DhanClient:
#     def __init__(self):
#         self.config = Config()
#         self.client = dhanhq(self.config.DHAN_CLIENT_ID, self.config.DHAN_ACCESS_TOKEN)
    
#     def get_historical_data(self, security_id: str, days: int = 30) -> Optional[pd.DataFrame]:
#         """Get historical data for backtesting"""
#         try:
#             to_date = datetime.now().date()
#             from_date = to_date - timedelta(days=days)

#             from_date_str = from_date.strftime("%Y-%m-%d 09:15:00")
#             to_date_str = to_date.strftime("%Y-%m-%d 15:30:00")
            
#             data = self.client.intraday_minute_data(
#                 security_id=security_id,
#                 exchange_segment="NSE_EQ",
#                 instrument_type="EQUITY",
#                 interval="1",
#                 from_date=from_date_str,
#                 to_date=to_date_str
#             )
            
#             if data['status'] == 'success' and data['data']:
#                 df = pd.DataFrame(data['data'])
#                 df['timestamp'] = pd.to_datetime(df['start_Time'])
#                 return df
            
#             return None
#         except Exception as e:
#             print(f"Error fetching historical data: {e}")
#             return None
    
#     def create_3min_candles(self, df_1min: pd.DataFrame) -> Optional[pd.DataFrame]:
#         """Convert 1-minute data to 3-minute candles"""
#         try:
#             df_1min = df_1min.sort_values('timestamp').reset_index(drop=True)
#             df_1min['date'] = df_1min['timestamp'].dt.date
            
#             candles_3min = []
            
#             for date, day_data in df_1min.groupby('date'):
#                 market_start = pd.Timestamp.combine(date, time(9, 15))
                
#                 i = 0
#                 while i < len(day_data):
#                     minutes_since_start = (day_data.iloc[i]['timestamp'] - market_start).total_seconds() / 60
#                     interval_number = int(minutes_since_start // 3)
#                     interval_start = market_start + pd.Timedelta(minutes=interval_number * 3)
#                     interval_end = interval_start + pd.Timedelta(minutes=3)
                    
#                     interval_data = day_data[
#                         (day_data['timestamp'] >= interval_start) & 
#                         (day_data['timestamp'] < interval_end)
#                     ]
                    
#                     if len(interval_data) > 0:
#                         candle_3min = {
#                             'timestamp': interval_start,
#                             'open': interval_data.iloc[0]['open'],
#                             'high': interval_data['high'].max(),
#                             'low': interval_data['low'].min(),
#                             'close': interval_data.iloc[-1]['close'],
#                             'volume': interval_data['volume'].sum()
#                         }
#                         candles_3min.append(candle_3min)
                    
#                     i += len(interval_data)
#                     if len(interval_data) == 0:
#                         i += 1
            
#             df_3min = pd.DataFrame(candles_3min)
#             return df_3min.sort_values('timestamp').reset_index(drop=True)
            
#         except Exception as e:
#             print(f"Error creating 3-minute candles: {e}")
#             return None
from dhanhq import dhanhq
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from config import Config

class DhanClient:
    def __init__(self):
        self.config = Config()
        self.client = dhanhq(self.config.DHAN_CLIENT_ID, self.config.DHAN_ACCESS_TOKEN)

    def get_historical_data(self, security_id: str, days: int = 30) -> Optional[pd.DataFrame]:
        """Fetch 1-min data and convert to 3-min candles"""
        try:
            to_date = datetime.now().date()
            from_date = to_date - timedelta(days=days)

            from_date_str = from_date.strftime("%Y-%m-%d 09:15:00")
            to_date_str = to_date.strftime("%Y-%m-%d 15:30:00")
            print("DEBUG CALL >>>", security_id, "NSE_EQ", "EQUITY", "1", from_date_str, to_date_str)
            # Fetch 1-minute data (smallest allowed interval)
            data = self.client.intraday_minute_data(
                security_id=security_id,
                exchange_segment="NSE_EQ",
                instrument_type="EQUITY",
                interval='1',  # Must be '1' (DHAN only allows 1,5,15,25,60)
                from_date=from_date_str,
                to_date=to_date_str
            )

            if data['status'] == 'success' and data['data']:
                df = pd.DataFrame(data['data'])

                # Rename columns to standard OHLCV format
                df = df.rename(columns={
                    'start_Time': 'timestamp',
                    'open_price': 'open',
                    'high_price': 'high',
                    'low_price': 'low',
                    'close_price': 'close',
                    'volume': 'volume'
                })

                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')  # Ensure chronological order
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

                # Convert 1-minute data to 3-minute candles
                df = self._resample_to_3min(df)
                return df
            return None
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

    def _resample_to_3min(self, df_1min: pd.DataFrame) -> pd.DataFrame:
        """Convert 1-minute data to 3-minute candles"""
        if df_1min.empty:
            return df_1min

        df_1min = df_1min.set_index('timestamp')
        df_3min = df_1min.resample('3T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        return df_3min.reset_index()
    