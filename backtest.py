import pandas as pd
from datetime import time
from typing import List, Dict
from config import Config
from strategy import TradingStrategy
from dhan_client import DhanClient

class BacktestEngine:
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
        self.config = Config()
        self.trades = {}
        self.daily_trades = {}

    def run_backtest(self, df: pd.DataFrame, symbol: str) -> Dict:
        if df is None or df.empty:
            return {'error': 'No data provided for backtest'}

        print(f"\n=== Backtest Starting for {symbol} ===")
        df = self.strategy.analyze_candle_data(df)
        trades = []
        daily_trades = {}
        i = 0
        last_trade_date = {}

        while i < len(df):
            row = df.iloc[i]
            trade_date = row['timestamp'].date()

            if symbol in last_trade_date and last_trade_date[symbol] == trade_date:
                i += 1
                continue

            signal = self.strategy.check_10am_signal(df, i)
            if signal:
                rejection = self.strategy.find_rejection_candle(df, i, signal)
                if rejection:
                    rej_idx = rejection['index']
                    trade_params = self.strategy.calculate_entry_exit(rejection, signal)

                    entry_index = rej_idx + 3
                    if entry_index >= len(df):
                        i += 1
                        continue

                    # ✅ Check if any of the next 3 candles touch SMA_50
                    sma_touched = False
                    for j in range(rej_idx + 1, entry_index):
                        row_j = df.iloc[j]
                        sma = row_j.get('SMA_50', None)
                        if pd.isna(sma):
                            continue
                        if signal == "LONG_SETUP" and row_j['low'] <= sma:
                            sma_touched = True
                            break
                        elif signal == "SHORT_SETUP" and row_j['high'] >= sma:
                            sma_touched = True
                            break

                    if sma_touched:
                        i = entry_index
                        continue

                    # Skip trade if wick hits SL before entry
                    sl = trade_params['stop_loss']
                    pre_entry_slice = df.iloc[rej_idx+1 : entry_index]
                    if signal == "LONG_SETUP" and (pre_entry_slice['low'] <= sl).any():
                        i = entry_index
                        continue
                    elif signal == "SHORT_SETUP" and (pre_entry_slice['high'] >= sl).any():
                        i = entry_index
                        continue

                    # Skip entry if after 1PM
                    entry_time = df.iloc[entry_index]['timestamp']
                    if entry_time.time() > self.config.NO_ENTRY_AFTER:
                        i = entry_index
                        continue

                    # Simulate trade
                    trade_result = self._simulate_trade(df, entry_index, trade_params, signal, symbol)
                    if trade_result:
                        trades.append(trade_result)
                        last_trade_date[symbol] = trade_date
                        daily_trades[trade_date] = trade_result
                        i = trade_result['exit_index']
                        continue
            i += 1

        self.trades[symbol] = self._calculate_performance_metrics(trades)
        self.daily_trades[symbol] = daily_trades
        print(f"[{symbol}] Backtest Completed → {self.trades[symbol]}")
        result = self.trades[symbol]
        result['daily_trades'] = list(daily_trades.values())
        return result

    def _simulate_trade(self, df: pd.DataFrame, entry_index: int,
                        trade_params: Dict, signal: str, symbol: str) -> Dict:
        entry_price = trade_params['entry_price']
        stop_loss = trade_params['stop_loss']
        target_price = trade_params['target_price']

        trade = {
            'symbol': symbol,
            'signal': signal,
            'entry_index': entry_index,
            'entry_time': df.iloc[entry_index]['timestamp'],
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'quantity': 100,
            'status': 'OPEN'
        }

        for i in range(entry_index, len(df)):
            candle = df.iloc[i]
            candle_time = candle['timestamp'].time()

            if candle_time >= self.config.EXIT_ALL_TIME:
                trade.update({
                    'exit_index': i,
                    'exit_time': candle['timestamp'],
                    'exit_price': candle['close'],
                    'exit_reason': 'EOD_EXIT',
                    'status': 'CLOSED'
                })
                break

            if signal == "LONG_SETUP":
                if candle['high'] >= target_price:
                    trade.update({
                        'exit_index': i,
                        'exit_time': candle['timestamp'],
                        'exit_price': target_price,
                        'exit_reason': 'TARGET_HIT',
                        'status': 'CLOSED'
                    })
                    break
                elif candle['low'] <= stop_loss:
                    trade.update({
                        'exit_index': i,
                        'exit_time': candle['timestamp'],
                        'exit_price': stop_loss,
                        'exit_reason': 'STOP_LOSS',
                        'status': 'CLOSED'
                    })
                    break
            else:
                if candle['low'] <= target_price:
                    trade.update({
                        'exit_index': i,
                        'exit_time': candle['timestamp'],
                        'exit_price': target_price,
                        'exit_reason': 'TARGET_HIT',
                        'status': 'CLOSED'
                    })
                    break
                elif candle['high'] >= stop_loss:
                    trade.update({
                        'exit_index': i,
                        'exit_time': candle['timestamp'],
                        'exit_price': stop_loss,
                        'exit_reason': 'STOP_LOSS',
                        'status': 'CLOSED'
                    })
                    break

        if trade['status'] == 'CLOSED':
            pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity'] \
                  if signal == "LONG_SETUP" else \
                  (trade['entry_price'] - trade['exit_price']) * trade['quantity']
            trade['pnl'] = round(pnl, 2)
            return trade
        return None

    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
        if not closed_trades:
            return {'error': 'No closed trades'}

        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]

        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'trades': closed_trades[-10:]
        }