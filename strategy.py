import pandas as pd
from datetime import time
from typing import Dict, Optional
from config import Config

class TradingStrategy:
    def __init__(self):
        self.config = Config()
    
    def analyze_candle_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to candle data"""
        df = df.copy()
        df['SMA_50'] = df['close'].rolling(window=self.config.SMA_PERIOD).mean()
        
        # Identify 10 AM candle (3-minute intervals starting from 9:15)
        df['is_10am_candle'] = False
        ten_am_mask = (df['timestamp'].dt.hour == 10) & (df['timestamp'].dt.minute == 0)
        df.loc[ten_am_mask, 'is_10am_candle'] = True
        
        return df
    
    def check_10am_signal(self, df: pd.DataFrame, index: int) -> Optional[str]:
        """Check 10 AM candle signal"""
        if not df.iloc[index]['is_10am_candle']:
            return None
        
        close_price = df.iloc[index]['close']
        sma_50 = df.iloc[index]['SMA_50']
        
        if pd.isna(sma_50):
            return None
        
        if close_price > sma_50:
            return "LONG_SETUP"
        elif close_price < sma_50:
            return "SHORT_SETUP"
        
        return None
    
    def find_rejection_candle(self, df: pd.DataFrame, start_index: int, setup_type: str) -> Optional[Dict]:
        """Find the first rejection candle after 10 AM setup"""
        for i in range(start_index + 1, len(df)):
            candle = df.iloc[i]
            sma_50 = candle['SMA_50']
            
            if pd.isna(sma_50):
                continue
            
            if setup_type == "LONG_SETUP":
                # Look for rejection from above SMA
                if (candle['low'] <= sma_50 and candle['close'] > sma_50 and
                    candle['high'] > sma_50):
                    return {
                        'index': i,
                        'candle': candle,
                        'rejection_type': 'LONG_REJECTION'
                    }
            
            elif setup_type == "SHORT_SETUP":
                # Look for rejection from below SMA
                if (candle['high'] >= sma_50 and candle['close'] < sma_50 and
                    candle['low'] < sma_50):
                    return {
                        'index': i,
                        'candle': candle,
                        'rejection_type': 'SHORT_REJECTION'
                    }
        
        return None
    
    def calculate_entry_exit(self, rejection_candle: Dict, setup_type: str) -> Dict:
        """Calculate entry, stop loss, and target prices"""
        candle = rejection_candle['candle']
        
        if setup_type == "LONG_SETUP":
            entry_price = candle['high'] + 0.01
            stop_loss = candle['low'] - 0.01
            candle_size = candle['high'] - candle['low']
            target_price = entry_price + (candle_size * self.config.RISK_REWARD_RATIO)
            
        else:  # SHORT_SETUP
            entry_price = candle['low'] - 0.01
            stop_loss = candle['high'] + 0.01
            candle_size = candle['high'] - candle['low']
            target_price = entry_price - (candle_size * self.config.RISK_REWARD_RATIO)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'candle_size': candle_size
        }