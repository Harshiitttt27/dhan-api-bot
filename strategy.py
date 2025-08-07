# import pandas as pd
# from datetime import time
# from typing import Dict, Optional
# from config import Config

# class TradingStrategy:
#     def __init__(self):
#         self.config = Config()
    
#     def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add technical indicators to candle data"""
#         df = df.copy()
#         df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()
        
#         # Identify 10 AM candle (3-minute intervals starting from 9:15)
#         df['is_10am_candle'] = False
#         ten_am_mask = (df['timestamp'].dt.hour == 10) & (df['timestamp'].dt.minute == 0)
#         df.loc[ten_am_mask, 'is_10am_candle'] = True
        
#         return df
    
#     def check_10am_signal(self, df: pd.DataFrame, index: int) -> Optional[str]:
#         """Check 10 AM candle signal"""
#         if not df.iloc[index]['is_10am_candle']:
#             return None
        
#         close_price = df.iloc[index]['close']
#         sma_50 = df.iloc[index]['SMA_50']
        
#         if pd.isna(sma_50):
#             return None
        
#         if close_price > sma_50:
#             return "LONG_SETUP"
#         elif close_price < sma_50:
#             return "SHORT_SETUP"
        
#         return None
    
#     def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
#         """Find the first rejection candle after 10 AM setup"""
#         for i in range(start_index + 1, len(df)):
#             candle = df.iloc[i]
#             sma_50 = candle['SMA_50']
            
#             if pd.isna(sma_50):
#                 continue
            
#             if setup_type == "LONG_SETUP":
#                 # Look for rejection from above SMA
#                 if (candle['low'] <= sma_50 and candle['close'] > sma_50 and
#                     candle['high'] > sma_50):
#                     return {
#                         'index': i,
#                         'candle': candle,
#                         'rejection_type': 'LONG_REJECTION'
#                     }
            
#             elif setup_type == "SHORT_SETUP":
#                 # Look for rejection from below SMA
#                 if (candle['high'] >= sma_50 and candle['close'] < sma_50 and
#                     candle['low'] < sma_50):
#                     return {
#                         'index': i,
#                         'candle': candle,
#                         'rejection_type': 'SHORT_REJECTION'
#                     }
        
#         return None
    
#     def calculate_entry_exit(self, rejection_candle: Dict, setup_type: str) -> Dict:
#         """Calculate entry, stop loss, and target prices"""
#         candle = rejection_candle['candle']
        
#         if setup_type == "LONG_SETUP":
#             entry_price = candle['high'] + 0.01
#             stop_loss = candle['low'] - 0.01
#             candle_size = candle['high'] - candle['low']
#             target_price = entry_price + (candle_size * self.config.RISK_REWARD_RATIO)
            
#         else:  # SHORT_SETUP
#             entry_price = candle['low'] - 0.01
#             stop_loss = candle['high'] + 0.01
#             candle_size = candle['high'] - candle['low']
#             target_price = entry_price - (candle_size * self.config.RISK_REWARD_RATIO)
        
#         return {
#             'entry_price': entry_price,
#             'stop_loss': stop_loss,
#             'target_price': target_price,
#             'candle_size': candle_size
#         }
# strategy.py
import pandas as pd
from typing import Dict, Optional
from config import Config

class TradingStrategy:
    def __init__(self):
        self.config = Config()
        self.RR = 5  # 1:5 Risk Reward

    # Step 3: Mark 10 AM candle & Calculate SMA50
    def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()
        df['is_10am_candle'] = (df['timestamp'].dt.hour == 10) & (df['timestamp'].dt.minute == 0)
        return df

    # Step 3: Check 10AM setup
    def check_10am_signal(self, df: pd.DataFrame, index: int) -> Optional[str]:
        if not df.iloc[index]['is_10am_candle']:
            return None

        row = df.iloc[index]
        close_price = row['close']
        open_price = row['open']
        high = row['high']
        low = row['low']
        sma_50 = row['SMA_50']

        if pd.isna(sma_50):
            return None

    # Long setup: body above SMA and wick doesn't touch
        if close_price > sma_50 and open_price > sma_50 and low > sma_50:
            return "LONG_SETUP"

    # Short setup: body below SMA and wick doesn't touch
        elif close_price < sma_50 and open_price < sma_50 and high < sma_50:
            return "SHORT_SETUP"

        return None


    # Step 4: Find first rejection candle
    def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
        for i in range(start_index + 1, len(df)):
            candle = df.iloc[i]
            sma_50 = candle['SMA_50']
            if pd.isna(sma_50):
                continue

            if setup_type == "LONG_SETUP":
                # Wick touches SMA from above, body above SMA
                if candle['low'] <= sma_50 and candle['open'] > sma_50 and candle['close'] > sma_50:
                    return {'index': i, 'candle': candle, 'rejection_type': 'LONG_REJECTION'}

            elif setup_type == "SHORT_SETUP":
                # Wick touches SMA from below, body below SMA
                if candle['high'] >= sma_50 and candle['open'] < sma_50 and candle['close'] < sma_50:
                    return {'index': i, 'candle': candle, 'rejection_type': 'SHORT_REJECTION'}
        return None

    # Step 5: Calculate Entry, SL, Target
    def calculate_entry_exit(self, rejection_candle: Dict, setup_type: str) -> Dict:
        candle = rejection_candle['candle']
        candle_size = candle['high'] - candle['low']

        if setup_type == "LONG_SETUP":
            entry_price = candle['high'] + 0.01
            stop_loss = candle['low'] - 0.01
            target_price = entry_price + (candle_size * self.RR)
        else:
            entry_price = candle['low'] - 0.01
            stop_loss = candle['high'] + 0.01
            target_price = entry_price - (candle_size * self.RR)

        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'candle_size': candle_size,
        }

# import pandas as pd
# from typing import Dict, Optional
# from config import Config

# class TradingStrategy:
#     def __init__(self):
#         self.config = Config()
#         self.RR = 5


#     # 1️⃣ Add SMA and mark 10AM candle
#     def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
#         df = df.copy()
#         df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()
#         df['is_10am_candle'] = (df['timestamp'].dt.hour == 10) & (df['timestamp'].dt.minute == 0)
#         return df

#     # 2️⃣ Check 10AM setup (LONG/SHORT)
#     def check_10am_signal(self, df: pd.DataFrame, index: int) -> Optional[str]:
#         if not df.iloc[index]['is_10am_candle']:
#             return None

#         close_price = df.iloc[index]['close']
#         sma_50 = df.iloc[index]['SMA_50']
#         if pd.isna(sma_50):
#             return None

#         open_price = df.iloc[index]['open']
#         # Body should be on one side of SMA
#         if close_price > sma_50 and open_price > sma_50:
#             return "LONG_SETUP"
#         elif close_price < sma_50 and open_price < sma_50:
#             return "SHORT_SETUP"
#         return None

#     # 3️⃣ Find first rejection candle
#     def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
#         for i in range(start_index + 1, len(df)):
#             candle = df.iloc[i]
#             sma_50 = candle['SMA_50']
#             if pd.isna(sma_50):
#                 continue

#             if setup_type == "LONG_SETUP":
#                 # Wick touches SMA from above, body above SMA
#                 if candle['low'] <= sma_50 and candle['open'] > sma_50 and candle['close'] > sma_50:
#                     return {'index': i, 'candle': candle, 'rejection_type': 'LONG_REJECTION'}

#             elif setup_type == "SHORT_SETUP":
#                 # Wick touches SMA from below, body below SMA
#                 if candle['high'] >= sma_50 and candle['open'] < sma_50 and candle['close'] < sma_50:
#                     return {'index': i, 'candle': candle, 'rejection_type': 'SHORT_REJECTION'}
#         return None

#     # 4️⃣ Calculate entry/SL/Target
#     def calculate_entry_exit(self, rejection_candle: Dict, setup_type: str) -> Dict:
#         candle = rejection_candle['candle']
#         candle_size = candle['high'] - candle['low']

#         if setup_type == "LONG_SETUP":
#             entry_price = candle['high'] + 0.01
#             stop_loss = candle['low'] - 0.01
#             target_price = entry_price + (candle_size * self.RR)
#         else:
#             entry_price = candle['low'] - 0.01
#             stop_loss = candle['high'] + 0.01
#             target_price = entry_price - (candle_size * self.RR)

#         return {
#             'entry_price': entry_price,
#             'stop_loss': stop_loss,
#             'target_price': target_price,
#             'candle_size': candle_size,
#         }

#     # 5️⃣ Validate entry conditions (3-candle wait, 1PM block, SL wick check)
#     def validate_entry(self, df: pd.DataFrame, rejection_index: int, setup_type: str, entry_price: float, stop_loss: float) -> Optional[int]:
#         # Entry after 3rd candle from rejection
#         entry_index = rejection_index + 3
#         if entry_index >= len(df):
#             return None

#         entry_time = df.iloc[entry_index]['timestamp']
#         if entry_time.hour >= self.config.ENTRY_END_HOUR:
#             # Block entries after 1 PM
#             return None

#         # Check if wick touches SL before entry
#         slice_df = df.iloc[rejection_index + 1:entry_index + 1]
#         for _, row in slice_df.iterrows():
#             if setup_type == "LONG_SETUP" and row['low'] <= stop_loss:
#                 return None
#             elif setup_type == "SHORT_SETUP" and row['high'] >= stop_loss:
#                 return None

#         return entry_index

#     # 6️⃣ Simulate trade exit (TP/SL/EOD)
#     def simulate_trade_exit(self, df: pd.DataFrame, entry_index: int, setup_type: str, entry_price: float, stop_loss: float, target_price: float) -> Dict:
#         exit_index = None
#         exit_price = None
#         exit_reason = None

#         for i in range(entry_index + 1, len(df)):
#             row = df.iloc[i]
#             ts = row['timestamp']

#             # 3 PM exit
#             if ts.hour >= self.config.EXIT_HOUR:
#                 exit_index = i
#                 exit_price = row['close']
#                 exit_reason = "EOD_EXIT"
#                 break

#             if setup_type == "LONG_SETUP":
#                 if row['low'] <= stop_loss:
#                     exit_index = i
#                     exit_price = stop_loss
#                     exit_reason = "STOP_LOSS"
#                     break
#                 if row['high'] >= target_price:
#                     exit_index = i
#                     exit_price = target_price
#                     exit_reason = "TARGET_HIT"
#                     break

#             elif setup_type == "SHORT_SETUP":
#                 if row['high'] >= stop_loss:
#                     exit_index = i
#                     exit_price = stop_loss
#                     exit_reason = "STOP_LOSS"
#                     break
#                 if row['low'] <= target_price:
#                     exit_index = i
#                     exit_price = target_price
#                     exit_reason = "TARGET_HIT"
#                     break

#         if exit_index is None:
#             # Fallback to last candle
#             exit_index = len(df) - 1
#             exit_price = df.iloc[-1]['close']
#             exit_reason = "EOD_EXIT"

#         return {
#             'exit_index': exit_index,
#             'exit_price': exit_price,
#             'exit_reason': exit_reason
#         }

# import pandas as pd
# from typing import Dict, Optional
# from config import Config

# class TradingStrategy:
#     def __init__(self):
#         self.config = Config()
#         self.RR = 5  # Fixed 1:5 Risk Reward

#     def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
#         """Add technical indicators to candle data"""
#         df = df.copy()
#         df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()

#         # Mark 10 AM candle
#         df['is_10am_candle'] = (
#             (df['timestamp'].dt.hour == 10) & 
#             (df['timestamp'].dt.minute == 0)
#         )
#         return df

#     def check_10am_signal(self, df: pd.DataFrame, index: int) -> Optional[str]:
#         """Check 10 AM candle signal"""
#         if not df.iloc[index]['is_10am_candle']:
#             return None
        
#         close_price = df.iloc[index]['close']
#         open_price = df.iloc[index]['open']
#         high_price = df.iloc[index]['high']
#         low_price = df.iloc[index]['low']
#         sma_50 = df.iloc[index]['SMA_50']
#         if pd.isna(sma_50):
#             return None
        
#         if (close_price > sma_50 and open_price > sma_50 and 
#             low_price > sma_50):  # Low must also be above SMA
#             return "LONG_SETUP"
    
#     # For SHORT setup: entire candle (including wicks) must be below SMA  
#         elif (close_price < sma_50 and open_price < sma_50 and 
#               high_price < sma_50):  # High must also be below SMA
#               return "SHORT_SETUP"
    
#         return None
#         # # 10AM candle should NOT cross SMA → body on one side
#         # candle_open = df.iloc[index]['open']
#         # if close_price > sma_50 and candle_open > sma_50:
#         #     return "LONG_SETUP"
#         # elif close_price < sma_50 and candle_open < sma_50:
#         #     return "SHORT_SETUP"
        
#         # return None

#     def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
#         """Find the first rejection candle after 10 AM setup"""
#         for i in range(start_index + 1, len(df)):
#             candle = df.iloc[i]
#             sma_50 = candle['SMA_50']
#             if pd.isna(sma_50):
#                 continue

#             # Rejection logic: Wick touches SMA but body remains on one side
#             if setup_type == "LONG_SETUP":
#                 if (
#                     candle['low'] <= sma_50 and
#                     candle['close'] > sma_50 and
#                     candle['open'] > sma_50  # Body above SMA
#                 ):
#                     return {'index': i, 'candle': candle, 'rejection_type': 'LONG_REJECTION'}

#             elif setup_type == "SHORT_SETUP":
#                 if (
#                     candle['high'] >= sma_50 and
#                     candle['close'] < sma_50 and
#                     candle['open'] < sma_50  # Body below SMA
#                 ):
#                     return {'index': i, 'candle': candle, 'rejection_type': 'SHORT_REJECTION'}
        
#         return None

#     def calculate_entry_exit(self, rejection_candle: Dict, setup_type: str) -> Dict:
#         """Calculate entry, stop loss, and target prices"""
#         candle = rejection_candle['candle']
#         candle_size = candle['high'] - candle['low']

#         if setup_type == "LONG_SETUP":
#             entry_price = candle['high'] + 0.01
#             stop_loss = candle['low'] - 0.01
#             target_price = entry_price + (candle_size * self.RR)
#         else:  # SHORT_SETUP
#             entry_price = candle['low'] - 0.01
#             stop_loss = candle['high'] + 0.01
#             target_price = entry_price - (candle_size * self.RR)

#         return {
#             'entry_price': entry_price,
#             'stop_loss': stop_loss,
#             'target_price': target_price,
#             'candle_size': candle_size
#         }
