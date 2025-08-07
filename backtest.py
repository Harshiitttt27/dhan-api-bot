# import pandas as pd
# from datetime import time
# from typing import List, Dict
# from config import Config
# from strategy import TradingStrategy

# class BacktestEngine:
#     def __init__(self, strategy: TradingStrategy):
#         self.strategy = strategy
#         self.config = Config()
#         self.trades = {}
#         self.performance_metrics = {}

#     # =======================================================
#     # Main Backtest Function
#     # =======================================================
#     def run_backtest(self, df: pd.DataFrame, symbol: str) -> Dict:
#         """Run backtest on historical data with strict SMA50 rejection rules & 1 trade/day"""
#         if df is None or df.empty:
#             return {'error': 'No data provided for backtest'}

#         print(f"\n=== Backtest Starting for {symbol} ===")
#         print(f"Rows: {len(df)} | Dates: {df['timestamp'].min()} → {df['timestamp'].max()}")

#         df = self.strategy.analyze_candle_data(df)
#         trades = []
#         i = 0
#         daily_pnl = {}
#         last_trade_date = None

#         while i < len(df):
#             current_date = df.iloc[i]['timestamp'].date()

#             # Reset daily PnL if new date
#             if current_date not in daily_pnl:
#                 daily_pnl[current_date] = 0

#             # Skip if daily loss exceeded
#             if daily_pnl[current_date] <= -self.config.MAX_DAILY_LOSS:
#                 i += 1
#                 continue

#             # Skip if we already traded today (max 1 trade per day)
#             if last_trade_date == current_date:
#                 i += 1
#                 continue

#             # ===== Check for 10AM setup =====
#             signal = self.strategy.check_10am_signal(df, i)

#             if signal:
#                 print(f"[{symbol}] 10 AM {signal} detected at index {i}")
#                 rejection = self.strategy.find_rejection_candle(df, i, signal)

#                 if rejection:
#                     rej_idx = rejection['index']

#                     # Calculate entry/SL/Target
#                     trade_params = self.strategy.calculate_entry_exit(rejection, signal)

#                     # # --- Dynamic buffer (0.01% of price or 0.05 min) ---
#                     # price = df.iloc[rej_idx]['close']
#                     # buffer = max(0.05, price * 0.0001)
#                     # if signal == "LONG_SETUP":
#                     #     trade_params['entry_price'] += buffer
#                     #     trade_params['stop_loss'] -= buffer
#                     # else:
#                     #     trade_params['entry_price'] -= buffer
#                     #     trade_params['stop_loss'] += buffer

#                     entry_index = rej_idx + 3  # wait 3 candles
#                     if entry_index >= len(df):
#                         i += 1
#                         continue

#                     # ✅ Reject if wick touches SL before entry
#                     sl = trade_params['stop_loss']
#                     if signal == "LONG_SETUP":
#                         if (df.iloc[rej_idx+1 : entry_index]['low'] <= sl).any():
#                             print(f"[{symbol}] ❌ SL wick touched before entry → Skipped")
#                             i = entry_index
#                             continue
#                     else:
#                         if (df.iloc[rej_idx+1 : entry_index]['high'] >= sl).any():
#                             print(f"[{symbol}] ❌ SL wick touched before entry → Skipped")
#                             i = entry_index
#                             continue

#                     # ✅ Check entry time limit
#                     entry_time = df.iloc[entry_index]['timestamp']
#                     if isinstance(entry_time, pd.Timestamp):
#                         entry_time = entry_time.to_pydatetime()
#                     if entry_time.time() > self.config.NO_ENTRY_AFTER:
#                         print(f"[{symbol}] ⏱ Entry after 1PM blocked at {entry_time.time()}")
#                         i = entry_index
#                         continue

#                     # ✅ Execute trade simulation
#                     trade_result = self._simulate_trade(
#                         df, entry_index, trade_params, signal, symbol
#                     )
#                     if trade_result:
#                         trades.append(trade_result)
#                         pnl = trade_result.get('pnl', 0)
#                         daily_pnl[current_date] += pnl
#                         last_trade_date = current_date
#                         print(f"[{symbol}] ✅ Trade executed | {trade_result['entry_time']} → Exit {trade_result['exit_price']} | PnL: {pnl}")
#                         # Strictly skip to next day after a trade
#                         while i < len(df) and df.iloc[i]['timestamp'].date() == current_date:
#                             i += 1
#                         continue
#                     i = trade_result.get('exit_index', entry_index) if trade_result else entry_index
#                 else:
#                     i += 1
#             else:
#                 i += 1

#         self.trades[symbol] = self._calculate_performance_metrics(trades)
#         print(f"[{symbol}] Backtest Completed → {self.trades[symbol]}")
#         return self.trades[symbol]

#     # =======================================================
#     # Trade Simulation
#     # =======================================================
#     def _simulate_trade(self, df: pd.DataFrame, entry_index: int,
#                         trade_params: Dict, signal: str, symbol: str) -> Dict:
#         """Simulate trade execution until SL, Target, or 3 PM exit"""
#         entry_price = trade_params['entry_price']
#         stop_loss = trade_params['stop_loss']
#         target_price = trade_params['target_price']

#         trade = {
#             'symbol': symbol,
#             'signal': signal,
#             'entry_index': entry_index,
#             'entry_time': df.iloc[entry_index]['timestamp'],
#             'entry_price': entry_price,
#             'stop_loss': stop_loss,
#             'target_price': target_price,
#             'quantity': 100,
#             'status': 'OPEN'
#         }

#         for i in range(entry_index, len(df)):
#             candle = df.iloc[i]
#             candle_time = candle['timestamp'].time() if hasattr(candle['timestamp'], 'time') else candle['timestamp']

#             # Exit all trades at 3 PM
#             if candle_time >= self.config.EXIT_ALL_TIME:
#                 trade.update({
#                     'exit_index': i,
#                     'exit_time': candle['timestamp'],
#                     'exit_price': candle['close'],
#                     'exit_reason': 'EOD_EXIT',
#                     'status': 'CLOSED'
#                 })
#                 break

#             # Long Trade Logic
#             if signal == "LONG_SETUP":
#                 if candle['high'] >= target_price:
#                     trade.update({
#                         'exit_index': i,
#                         'exit_time': candle['timestamp'],
#                         'exit_price': target_price,
#                         'exit_reason': 'TARGET_HIT',
#                         'status': 'CLOSED'
#                     })
#                     break
#                 elif candle['low'] <= stop_loss:
#                     trade.update({
#                         'exit_index': i,
#                         'exit_time': candle['timestamp'],
#                         'exit_price': stop_loss,
#                         'exit_reason': 'STOP_LOSS',
#                         'status': 'CLOSED'
#                     })
#                     break
#             # Short Trade Logic
#             else:
#                 if candle['low'] <= target_price:
#                     trade.update({
#                         'exit_index': i,
#                         'exit_time': candle['timestamp'],
#                         'exit_price': target_price,
#                         'exit_reason': 'TARGET_HIT',
#                         'status': 'CLOSED'
#                     })
#                     break
#                 elif candle['high'] >= stop_loss:
#                     trade.update({
#                         'exit_index': i,
#                         'exit_time': candle['timestamp'],
#                         'exit_price': stop_loss,
#                         'exit_reason': 'STOP_LOSS',
#                         'status': 'CLOSED'
#                     })
#                     break

#         # Calculate PnL if trade closed
#         if trade['status'] == 'CLOSED':
#             pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity'] \
#                   if signal == "LONG_SETUP" else \
#                   (trade['entry_price'] - trade['exit_price']) * trade['quantity']
#             trade['pnl'] = round(pnl, 2)
#             return trade
#         return None

#     # =======================================================
#     # Performance Metrics
#     # =======================================================
#     def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
#         """Calculate performance metrics for closed trades"""
#         closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
#         if not closed_trades:
#             return {'error': 'No closed trades'}

#         total_trades = len(closed_trades)
#         winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
#         losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]

#         total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
#         total_wins = len(winning_trades)
#         total_losses = len(losing_trades)

#         win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
#         avg_win = sum(t.get('pnl', 0) for t in winning_trades) / total_wins if total_wins > 0 else 0
#         avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / total_losses if total_losses > 0 else 0

#         # Calculate max drawdown
#         cumulative_pnl = []
#         running_pnl = 0
#         for trade in closed_trades:
#             running_pnl += trade.get('pnl', 0)
#             cumulative_pnl.append(running_pnl)

#         peak = cumulative_pnl[0] if cumulative_pnl else 0
#         max_drawdown = 0
#         for pnl in cumulative_pnl:
#             if pnl > peak:
#                 peak = pnl
#             drawdown = peak - pnl
#             if drawdown > max_drawdown:
#                 max_drawdown = drawdown

#         return {
#             'total_trades': total_trades,
#             'winning_trades': total_wins,
#             'losing_trades': total_losses,
#             'win_rate': round(win_rate, 2),
#             'total_pnl': round(total_pnl, 2),
#             'avg_win': round(avg_win, 2),
#             'avg_loss': round(avg_loss, 2),
#             'profit_factor': round(abs(avg_win/avg_loss), 2) if avg_loss != 0 else 0,
#             'max_drawdown': round(max_drawdown, 2),
#             'trades': closed_trades[-10:]  # Last 10 trades for inspection
#         }
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
        self.daily_trades = {}  # Store one trade per day per symbol

    def run_backtest(self, df: pd.DataFrame, symbol: str) -> Dict:
        """Run backtest on historical data as per strict SMA50 rejection strategy, one trade per day"""
        if df is None or df.empty:
            return {'error': 'No data provided for backtest'}

        print(f"\n=== Backtest Starting for {symbol} ===")
        df = self.strategy.analyze_candle_data(df)
        trades = []
        daily_trades = {}  # date -> trade
        i = 0
        last_trade_date = {}  # symbol -> date

        while i < len(df):
            row = df.iloc[i]
            trade_date = row['timestamp'].date()

            # Skip if already traded today for this symbol
            if symbol in last_trade_date and last_trade_date[symbol] == trade_date:
                i += 1
                continue

            # Check 10AM Setup
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
                        # Record last trade date for this symbol
                        last_trade_date[symbol] = trade_date
                        # Store only one trade per day
                        daily_trades[trade_date] = trade_result
                        i = trade_result['exit_index']  # Move to exit candle
                        continue
            i += 1

        self.trades[symbol] = self._calculate_performance_metrics(trades)
        self.daily_trades[symbol] = daily_trades
        print(f"[{symbol}] Backtest Completed → {self.trades[symbol]}")
        # Add daily_trades to result for UI display
        result = self.trades[symbol]
        result['daily_trades'] = list(daily_trades.values())
        return result

    def _simulate_trade(self, df: pd.DataFrame, entry_index: int,
                        trade_params: Dict, signal: str, symbol: str) -> Dict:
        """Simulate trade execution until SL, Target, or 3 PM exit"""
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

            # Exit all trades at 3 PM
            if candle_time >= self.config.EXIT_ALL_TIME:
                trade.update({
                    'exit_index': i,
                    'exit_time': candle['timestamp'],
                    'exit_price': candle['close'],
                    'exit_reason': 'EOD_EXIT',
                    'status': 'CLOSED'
                })
                break

            # Check exit conditions
            if signal == "LONG_SETUP":
                if candle['high'] >= target_price:
                    trade.update({
                        'exit_index': i, 'exit_time': candle['timestamp'],
                        'exit_price': target_price, 'exit_reason': 'TARGET_HIT', 'status': 'CLOSED'
                    })
                    break
                elif candle['low'] <= stop_loss:
                    trade.update({
                        'exit_index': i, 'exit_time': candle['timestamp'],
                        'exit_price': stop_loss, 'exit_reason': 'STOP_LOSS', 'status': 'CLOSED'
                    })
                    break
            else:
                if candle['low'] <= target_price:
                    trade.update({
                        'exit_index': i, 'exit_time': candle['timestamp'],
                        'exit_price': target_price, 'exit_reason': 'TARGET_HIT', 'status': 'CLOSED'
                    })
                    break
                elif candle['high'] >= stop_loss:
                    trade.update({
                        'exit_index': i, 'exit_time': candle['timestamp'],
                        'exit_price': stop_loss, 'exit_reason': 'STOP_LOSS', 'status': 'CLOSED'
                    })
                    break

        # Calculate PnL
        if trade['status'] == 'CLOSED':
            pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity'] \
                  if signal == "LONG_SETUP" else \
                  (trade['entry_price'] - trade['exit_price']) * trade['quantity']
            trade['pnl'] = round(pnl, 2)
            return trade
        return None

    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate performance metrics for closed trades"""
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
