from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

print("Alpaca Verification")
print("-" * 20)

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

if not api_key or not secret_key:
    print("Error: API Keys not found in .env")
    exit(1)

# Connect to Alpaca (Paper Trading)
client = TradingClient(api_key, secret_key, paper=True)

try:
    account = client.get_account()
    print("Connection Successful!")
    print(f"Status: {account.status}")
    print(f"Buying Power: ${account.buying_power}")
    print(f"Equity: ${account.equity}")
    print(f"Cash: ${account.cash}")
except Exception as e:
    print(f"Connection Failed: {e}")
