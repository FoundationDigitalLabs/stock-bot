import json
import os
from datetime import datetime

TRADES_LOG_PATH = "stock-bot/data/trades_audit.json"

def log_trade_entry(ticker, price, score, signals, qty, sl, tp):
    """
    Records the full technical context of an entry for later performance analysis.
    """
    os.makedirs("stock-bot/data", exist_ok=True)
    
    trade_data = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "action": "ENTRY",
        "price": price,
        "score": score,
        "qty": qty,
        "stop_loss": sl,
        "take_profit": tp,
        "signals": signals
    }
    
    try:
        if os.path.exists(TRADES_LOG_PATH):
            with open(TRADES_LOG_PATH, "r") as f:
                logs = json.load(f)
        else:
            logs = []
            
        logs.append(trade_data)
        
        with open(TRADES_LOG_PATH, "w") as f:
            json.dump(logs, f, indent=4)
            
    except Exception as e:
        print(f"Error logging trade: {e}")

def log_trade_exit(ticker, price, reason):
    """
    Records the exit details to link back to the entry context.
    """
    trade_data = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "action": "EXIT",
        "price": price,
        "reason": reason
    }
    
    try:
        if os.path.exists(TRADES_LOG_PATH):
            with open(TRADES_LOG_PATH, "r") as f:
                logs = json.load(f)
            logs.append(trade_data)
            with open(TRADES_LOG_PATH, "w") as f:
                json.dump(logs, f, indent=4)
    except Exception as e:
        print(f"Error logging exit: {e}")
