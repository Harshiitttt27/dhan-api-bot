# from fastapi import FastAPI, Request
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict, Optional
# import logging
# import pandas as pd
# from datetime import datetime, timedelta

# from config import Config
# from strategy import TradingStrategy
# from backtest import BacktestEngine
# from dhan_client import DhanClient

# # Setup logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('trading_bot.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)

# app = FastAPI()

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize components
# config = Config()
# dhan_client = DhanClient()
# strategy = TradingStrategy()
# backtest_engine = BacktestEngine(strategy)

# # Mount static files
# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")

# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.post("/api/backtest/run")
# async def run_backtest(symbol: Optional[str] = None, days: int = 30):
#     """Run strategy backtest"""
#     try:
#         results = {}
        
#         symbols_to_test = {symbol: config.WATCHLIST_STOCKS[symbol]} if symbol else config.WATCHLIST_STOCKS
        
#         for sym, security_id in symbols_to_test.items():
#             logger.info(f"Running backtest for {sym}...")
            
#             # Get historical data
#             df_1min = dhan_client.get_historical_data(security_id, days)
#             if df_1min is None:
#                 results[sym] = {'error': 'Failed to fetch historical data'}
#                 continue
                
#             # Convert to 3-minute candles
#             df_3min = dhan_client.get_historical_data(security_id, days)
#             if df_3min is None or len(df_3min) < 100:
#                 results[sym] = {'error': 'Insufficient data for analysis'}
#                 continue
            
#             # Run backtest
#             backtest_result = backtest_engine.run_backtest(df_3min, sym)
#             results[sym] = backtest_result
            
#             logger.info(f"Backtest completed for {sym}: {backtest_result.get('total_trades', 0)} trades")
        
#         return results
        
#     except Exception as e:
#         logger.error(f"Error running backtest: {str(e)}")
#         return {'error': str(e)}

# @app.get("/api/backtest/results")
# async def get_backtest_results():
#     """Get latest backtest results"""
#     return backtest_engine.trades

# @app.get("/api/strategy/performance")
# async def get_strategy_performance():
#     """Get overall strategy performance"""
#     try:
#         if not backtest_engine.trades:
#             return {"error": "No backtest results available"}
        
#         total_trades = 0
#         total_wins = 0
#         total_pnl = 0
#         all_trades = []
        
#         for symbol, result in backtest_engine.trades.items():
#             if 'error' not in result:
#                 total_trades += result.get('total_trades', 0)
#                 total_wins += result.get('winning_trades', 0)
#                 total_pnl += result.get('total_pnl', 0)
#                 all_trades.extend(result.get('trades', []))
        
#         overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
#         return {
#             "overall_trades": total_trades,
#             "overall_wins": total_wins,
#             "overall_win_rate": round(overall_win_rate, 2),
#             "overall_pnl": round(total_pnl, 2),
#             "recent_trades": all_trades[-10:]  # last 10 trades
#         }
#     except Exception as e:
#         return {"error": str(e)}

# @app.get("/api/watchlist")
# async def get_watchlist():
#     """Get trading watchlist"""
#     return {"watchlist": config.WATCHLIST_STOCKS}

# if __name__ == '__main__':
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import logging

from config import Config
from strategy import TradingStrategy
from backtest import BacktestEngine
from dhan_client import DhanClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('trading_bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

config = Config()
dhan_client = DhanClient()
strategy = TradingStrategy()
backtest_engine = BacktestEngine(strategy)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/backtest/run")
async def run_backtest(symbol: Optional[str] = None, days: int = 30):
    """Run strategy backtest"""
    print(7)
    try:
        results = {}
        symbols_to_test = [symbol] if symbol else list(config.WATCHLIST_STOCKS)

        for sym in symbols_to_test:
            logger.info(f"Running backtest for {sym}...")

            security_id = dhan_client.get_security_id(sym)
            if not security_id:
                results[sym] = {'error': f'Security ID not found for {sym}'}
                continue

            df_3min = dhan_client.get_historical_data(security_id, days)
            print(8)
            if df_3min is None:
                logger.error("DataFrame is None — likely due to data fetch failure.")
                results[sym] = {"error": "No data returned from API"}
                print(9)
                continue
            elif df_3min.empty:
                logger.warning("DataFrame is empty.")
                results[sym] = {"error": "Empty data returned from API"}
                print(10)
                continue
            else:
                logger.info(f"Received DataFrame for {sym}:\n{df_3min.head()}")
                logger.info(f"Total rows: {len(df_3min)}")
            print(11)

            if len(df_3min) < 100:
                results[sym] = {'error': 'Insufficient data for analysis'}
                continue

            backtest_result = backtest_engine.run_backtest(df_3min, sym)

            total_trades = backtest_result.get("total_trades", 0)
            winning_trades = backtest_result.get("winning_trades", 0)
            win_rate = round((winning_trades / total_trades * 100), 2) if total_trades else 0

            backtest_result["win_rate"] = win_rate
            backtest_result["total_pnl"] = float(backtest_result.get("total_pnl", 0))

            results[sym] = backtest_result
            logger.info(f"Backtest completed for {sym}: {total_trades} trades, win_rate={win_rate}%")
        print(12)
        return results

    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}")
        return {'error': str(e)}


@app.get("/api/backtest/results")
async def get_backtest_results():
    print(6)
    return backtest_engine.trades

@app.get("/api/strategy/performance")
async def get_strategy_performance():
    if not backtest_engine.trades:
        return {"error": "No backtest results available"}
    
    total_trades = sum(r.get('total_trades', 0) for r in backtest_engine.trades.values() if 'error' not in r)
    total_wins = sum(r.get('winning_trades', 0) for r in backtest_engine.trades.values() if 'error' not in r)
    total_pnl = sum(r.get('total_pnl', 0) for r in backtest_engine.trades.values() if 'error' not in r)
    all_trades = sum((r.get('trades', []) for r in backtest_engine.trades.values() if 'error' not in r), [])

    overall_win_rate = round((total_wins / total_trades * 100), 2) if total_trades else 0

    return {
        "overall_trades": total_trades,
        "overall_wins": total_wins,
        "overall_win_rate": overall_win_rate,
        "overall_pnl": round(total_pnl, 2),
        "recent_trades": all_trades[-10:]
    }

@app.get("/api/watchlist")
async def get_watchlist():
    return {"watchlist": config.WATCHLIST_STOCKS}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
