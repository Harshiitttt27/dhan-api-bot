# import pandas as pd
# from datetime import time
# from typing import List, Dict, Any
# from config import Config
# from strategy import TradingStrategy

# class BacktestEngine:
#     def __init__(self, strategy: TradingStrategy):
#         self.strategy = strategy
#         self.config = Config()
#         self.trades = []
#         self.performance_metrics = {}
    
#     def run_backtest(self, df: pd.DataFrame, symbol: str) -> Dict:
#         """Run backtest on historical data"""
#         df = self.strategy.analyze_candle_data(df)
#         trades = []
        
#         i = 0
#         while i < len(df):
#             signal = self.strategy.check_10am_signal(df, i)
            
#             if signal:
#                 rejection = self.strategy.find_rejection_candle(df, i, signal)
                
#                 if rejection:
#                     entry_index = rejection['index'] + 3
                    
#                     if entry_index < len(df):
#                         trade_params = self.strategy.calculate_entry_exit(rejection, signal)
                        
#                         # Check if entry time is valid (before 1 PM)
#                         entry_time = df.iloc[entry_index]['timestamp']
#                         if entry_time.time() > self.config.NO_ENTRY_AFTER:
#                             i = entry_index
#                             continue
                        
#                         trade_result = self._simulate_trade(
#                             df, entry_index, trade_params, signal, symbol
#                         )
                        
#                         if trade_result:
#                             trades.append(trade_result)
                        
#                         i = trade_result.get('exit_index', entry_index) if trade_result else entry_index
#                     else:
#                         i += 1
#                 else:
#                     i += 1
#             else:
#                 i += 1
        
#         self.trades = trades
#         return self._calculate_performance_metrics(trades)
    
#     def _simulate_trade(self, df: pd.DataFrame, entry_index: int, 
#                        trade_params: Dict, signal: str, symbol: str) -> Dict:
#         """Simulate individual trade execution"""
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
#             'quantity': 100,  # Default quantity
#             'status': 'OPEN'
#         }
        
#         for i in range(entry_index, len(df)):
#             candle = df.iloc[i]
            
#             # Check for 3 PM exit
#             if candle['timestamp'].time() >= self.config.EXIT_ALL_TIME:
#                 trade.update({
#                     'exit_index': i,
#                     'exit_time': candle['timestamp'],
#                     'exit_price': candle['close'],
#                     'exit_reason': 'EOD_EXIT',
#                     'status': 'CLOSED'
#                 })
#                 break
            
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
            
#             else:  # SHORT_SETUP
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
        
#         if trade['status'] == 'CLOSED':
#             if signal == "LONG_SETUP":
#                 pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity']
#             else:
#                 pnl = (trade['entry_price'] - trade['exit_price']) * trade['quantity']
            
#             trade['pnl'] = pnl
            
#         return trade
    
#     def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
#         """Calculate comprehensive performance metrics"""
#         if not trades:
#             return {'error': 'No trades found'}
        
#         closed_trades = [t for t in trades if t['status'] == 'CLOSED']
        
#         if not closed_trades:
#             return {'error': 'No closed trades found'}
        
#         total_trades = len(closed_trades)
#         winning_trades = [t for t in closed_trades if t['pnl'] > 0]
#         losing_trades = [t for t in closed_trades if t['pnl'] < 0]
        
#         total_pnl = sum(t['pnl'] for t in closed_trades)
#         total_wins = len(winning_trades)
#         total_losses = len(losing_trades)
        
#         win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        
#         avg_win = sum(t['pnl'] for t in winning_trades) / total_wins if total_wins > 0 else 0
#         avg_loss = sum(t['pnl'] for t in losing_trades) / total_losses if total_losses > 0 else 0
        
#         # Calculate drawdown
#         cumulative_pnl = []
#         running_pnl = 0
#         for trade in closed_trades:
#             running_pnl += trade['pnl']
#             cumulative_pnl.append(running_pnl)
        
#         peak = cumulative_pnl[0]
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
#             'trades': closed_trades[-10:]  # Last 10 trades for display
#         }
import pandas as pd
from datetime import time
from typing import List, Dict, Any
from config import Config
from strategy import TradingStrategy

class BacktestEngine:
    def __init__(self, strategy: TradingStrategy):
        self.strategy = strategy
        self.config = Config()
        self.trades = {}
        self.performance_metrics = {}
    
    def run_backtest(self, df: pd.DataFrame, symbol: str) -> Dict:
        print(df)
        """Run backtest on historical data"""
        print(f"✅ Loading data for symbol: {symbol}")
        print(f"✅ Loaded {len(df)} rows before filtering.")
        print(f"✅ Dates: {df['timestamp'].min()} to {df['timestamp'].max()}")

# After applying date filter:
        # print(f"✅ Filtered rows (after {days} days): {len(df_filtered)}")
        # print(f"✅ Filtered dates: {df_filtered['timestamp'].min()} to {df_filtered['timestamp'].max()}")

        if df is None or df.empty:
            return {'error': 'No data provided for backtest'}
            
        try:
            df = self.strategy.analyze_candle_data(df)
            trades = []
            
            i = 0
            while i < len(df):
                signal = self.strategy.check_10am_signal(df, i)
                
                if signal:
                    rejection = self.strategy.find_rejection_candle(df, i, signal)
                    
                    if rejection:
                        entry_index = rejection['index'] + 3
                        
                        if entry_index < len(df):
                            trade_params = self.strategy.calculate_entry_exit(rejection, signal)
                            
                            # Check if entry time is valid (before 1 PM)
                            entry_time = df.iloc[entry_index]['timestamp']
                            if isinstance(entry_time, pd.Timestamp):
                                entry_time = entry_time.to_pydatetime()
                                
                            if entry_time.time() > self.config.NO_ENTRY_AFTER:
                                i = entry_index
                                continue
                            
                            trade_result = self._simulate_trade(
                                df, entry_index, trade_params, signal, symbol
                            )
                            
                            if trade_result:
                                trades.append(trade_result)
                            
                            i = trade_result.get('exit_index', entry_index) if trade_result else entry_index
                        else:
                            i += 1
                    else:
                        i += 1
                else:
                    i += 1
            
            self.trades[symbol] = self._calculate_performance_metrics(trades)
            return self.trades[symbol]
            
        except Exception as e:
            return {'error': f'Backtest failed: {str(e)}'}
    
    def _simulate_trade(self, df: pd.DataFrame, entry_index: int, 
                       trade_params: Dict, signal: str, symbol: str) -> Dict:
        """Simulate individual trade execution"""
        try:
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
                'quantity': 100,  # Default quantity
                'status': 'OPEN'
            }
            
            for i in range(entry_index, len(df)):
                candle = df.iloc[i]
                candle_time = candle['timestamp'].time() if hasattr(candle['timestamp'], 'time') else candle['timestamp']
                
                # Check for 3 PM exit
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
                
                else:  # SHORT_SETUP
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
                if signal == "LONG_SETUP":
                    pnl = (trade['exit_price'] - trade['entry_price']) * trade['quantity']
                else:
                    pnl = (trade['entry_price'] - trade['exit_price']) * trade['quantity']
                
                trade['pnl'] = round(pnl, 2)
                return trade
            return None
            
        except Exception as e:
            print(f"Error simulating trade: {e}")
            return None
    
    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {'error': 'No trades executed'}
        
        closed_trades = [t for t in trades if t.get('status') == 'CLOSED']
        
        if not closed_trades:
            return {'error': 'No closed trades'}
        
        try:
            total_trades = len(closed_trades)
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            total_wins = len(winning_trades)
            total_losses = len(losing_trades)
            
            win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
            
            avg_win = sum(t.get('pnl', 0) for t in winning_trades) / total_wins if total_wins > 0 else 0
            avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / total_losses if total_losses > 0 else 0
            
            # Calculate drawdown
            cumulative_pnl = []
            running_pnl = 0
            for trade in closed_trades:
                running_pnl += trade.get('pnl', 0)
                cumulative_pnl.append(running_pnl)
            
            peak = cumulative_pnl[0] if cumulative_pnl else 0
            max_drawdown = 0
            for pnl in cumulative_pnl:
                if pnl > peak:
                    peak = pnl
                drawdown = peak - pnl
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return {
                'total_trades': total_trades,
                'winning_trades': total_wins,
                'losing_trades': total_losses,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(abs(avg_win/avg_loss), 2) if avg_loss != 0 else 0,
                'max_drawdown': round(max_drawdown, 2),
                'trades': closed_trades[-10:]  # Last 10 trades for display
            }
        except Exception as e:
            return {'error': f'Performance calculation failed: {str(e)}'}