from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import logging
import pandas as pd
from datetime import datetime, timedelta

from config import Config
from strategy import TradingStrategy
from backtest import BacktestEngine
from dhan_client import DhanClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config()
dhan_client = DhanClient()
strategy = TradingStrategy()
backtest_engine = BacktestEngine(strategy)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/backtest/run")
async def run_backtest(symbol: Optional[str] = None, days: int = 30):
    """Run strategy backtest"""
    try:
        results = {}
        
        symbols_to_test = {symbol: config.WATCHLIST_STOCKS[symbol]} if symbol else config.WATCHLIST_STOCKS
        
        for sym, security_id in symbols_to_test.items():
            logger.info(f"Running backtest for {sym}...")
            
            # Get historical data
            df_1min = dhan_client.get_historical_data(security_id, days)
            if df_1min is None:
                results[sym] = {'error': 'Failed to fetch historical data'}
                continue
                
            # Convert to 3-minute candles
            df_3min = dhan_client.get_historical_data(security_id, days)
            if df_3min is None or len(df_3min) < 100:
                results[sym] = {'error': 'Insufficient data for analysis'}
                continue
            
            # Run backtest
            backtest_result = backtest_engine.run_backtest(df_3min, sym)
            results[sym] = backtest_result
            
            logger.info(f"Backtest completed for {sym}: {backtest_result.get('total_trades', 0)} trades")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}")
        return {'error': str(e)}

@app.get("/api/backtest/results")
async def get_backtest_results():
    """Get latest backtest results"""
    return backtest_engine.trades

@app.get("/api/strategy/performance")
async def get_strategy_performance():
    """Get overall strategy performance"""
    try:
        if not backtest_engine.trades:
            return {"error": "No backtest results available"}
        
        total_trades = 0
        total_wins = 0
        total_pnl = 0
        all_trades = []
        
        for symbol, result in backtest_engine.trades.items():
            if 'error' not in result:
                total_trades += result.get('total_trades', 0)
                total_wins += result.get('winning_trades', 0)
                total_pnl += result.get('total_pnl', 0)
                all_trades.extend(result.get('trades', []))
        
        overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "overall_trades": total_trades,
            "overall_wins": total_wins,
            "overall_win_rate": round(overall_win_rate, 2),
            "overall_pnl": round(total_pnl, 2),
            "recent_trades": all_trades[-10:]  # last 10 trades
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/watchlist")
async def get_watchlist():
    """Get trading watchlist"""
    return {"watchlist": config.WATCHLIST_STOCKS}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")