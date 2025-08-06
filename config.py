import os
from datetime import time

class Config:
    DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "1100987697")
    DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU2ODc5NjkwLCJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJ3ZWJob29rVXJsIjoiIiwiZGhhbkNsaWVudElkIjoiMTEwMDk4NzY5NyJ9.haEPrZs5n7Z32SkQ3gnkq1rBxqEY64RP4MtzdTVxrqPGoBk4UU6MRUYk3Fho27SqVdF2obg0VruAAx0JqK6TLA")
    
    # Trading Parameters
    WATCHLIST_STOCKS = {
        "RELIANCE": "500325",
        "TCS": "532540", 
        "INFY": "500209",
        "HDFC": "500180",
        "ITC": "500875",
        "ICICIBANK": "532174",
        "BHARTIARTL": "532454",
        "SBIN": "500112",
        "LT": "500510",
        "HCLTECH": "532281"
    }
    
    TIMEFRAME = "3MIN"
    SMA_PERIOD = 50
    RISK_REWARD_RATIO = 5
    MAX_DAILY_LOSS = 5000
    MAX_POSITIONS = 5
    TRADE_START_TIME = time(9, 15)   # 9:15 AM
    TRADE_END_TIME = time(15, 30)    # 3:30 PM
    NO_ENTRY_AFTER = time(13, 0)     # 1:00 PM
    EXIT_ALL_TIME = time(15, 0)      # 3:00 PM