import pandas as pd
from typing import Dict, Optional
from config import Config

class TradingStrategy:
    def __init__(self):
        self.config = Config()
        self.RR = 5  # 1:5 Risk Reward
        self.position = None
        self.traded_today = False
        self.rejected_day = None
        self.rejection_time = None

    def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()
        df['is_10am_candle'] = (df['timestamp'].dt.hour == 10) & (df['timestamp'].dt.minute == 0)
        return df

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

        if close_price > sma_50 and open_price > sma_50 and low > sma_50:
            return "LONG_SETUP"
        elif close_price < sma_50 and open_price < sma_50 and high < sma_50:
            return "SHORT_SETUP"

        return None

    def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
        for i in range(start_index + 1, len(df)):
            candle = df.iloc[i]
            sma_50 = candle['SMA_50']
            if pd.isna(sma_50):
                continue

            # Choppy market filter – SMA slope
            sma_window = df['SMA_50'].iloc[max(0, i - 5):i + 1]
            sma_slope = sma_window.diff().mean()
            if abs(sma_slope) < 0.01:
                continue  # Market is choppy

            if setup_type == "LONG_SETUP":
                if (
                    candle['low'] <= sma_50 and
                    candle['open'] > sma_50 and
                    candle['close'] > sma_50 and
                    candle['close'] > candle['open']
                ):
                    return {'index': i, 'candle': candle, 'rejection_type': 'LONG_REJECTION'}

            elif setup_type == "SHORT_SETUP":
                if (
                    candle['high'] >= sma_50 and
                    candle['open'] < sma_50 and
                    candle['close'] < sma_50 and
                    candle['close'] < candle['open']
                ):
                    return {'index': i, 'candle': candle, 'rejection_type': 'SHORT_REJECTION'}

        return None

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
    def reset_daily_state(self, now):
        if self.position is None:
            self.traded_today = False
            self.rejected_day = None
            self.rejection_time = None

    def get_sma(self, data, index, period=50):
        if index < period:
            return None
        return sum(data[i]['close'] for i in range(index - period, index)) / period

    def can_trade(self, df, i):
        now = df[i]['timestamp']
        date_str = now.date().isoformat()

        # Reset daily state if new day
        if i > 0 and now.date() != df[i - 1]['timestamp'].date():
            self.reset_daily_state(now)

        # Only one trade per day
        if self.traded_today:
            return False

        # If there was a rejection today, wait for 3 candles
        if self.rejected_day == date_str:
            if (now - self.rejection_time).total_seconds() < 9 * 60:  # 3 candles of 3 min
                return False

        if now.hour != 10 or now.minute != 0:
            return False

        return True

    def entry_rejected(self, df, i, sma):
        # Check if SMA or stop-loss was touched in the first 3 candles after 10:00
        stop_loss_buffer = 0.005  # 0.5% buffer for SL (can be adjusted)
        close_price = df[i]['close']
        for j in range(i + 1, i + 4):
            if j >= len(df):
                break
            low = df[j]['low']
            high = df[j]['high']
            if sma and (low <= sma <= high):
                return True
            if low <= close_price * (1 - stop_loss_buffer):
                return True
        return False

    def should_enter(self, df, i):
        now = df[i]['timestamp']
        date_str = now.date().isoformat()

        if not self.can_trade(df, i):
            return False

        sma = self.get_sma(df, i)
        if sma is None:
            return False

        if self.entry_rejected(df, i, sma):
            self.rejected_day = date_str
            self.rejection_time = now
            return False

        # Passed all checks, can enter trade
        return True

    def enter_trade(self, df, i):
        self.position = {
            'entry_time': df[i + 3]['timestamp'],
            'entry_price': df[i + 3]['close']
        }
        self.traded_today = True
        return self.position

    def check_exit(self, df, i):
        # Placeholder for exit logic
        return None
