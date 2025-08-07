import pandas as pd
from typing import Dict, Optional
from config import Config

class TradingStrategy:
    def __init__(self):
        self.config = Config()
        self.RR = 5  # 1:5 Risk Reward

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