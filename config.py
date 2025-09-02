from dotenv import load_dotenv
import os

# Load .env
load_dotenv()

# --- Keys ---
API_KEY = os.getenv("BYBIT_API_KEY", "")
API_SECRET = os.getenv("BYBIT_API_SECRET", "")

# --- Trading ---
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
EXCHANGE = os.getenv("EXCHANGE", "bybit")

# --- Risk ---
QUOTE_SPEND_PCT = float(os.getenv("QUOTE_SPEND_PCT", 0.1))

# --- Simulation / mode ---
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
TESTNET = os.getenv("TESTNET", "true").lower() == "true"

# --- Strategy ---
SMA_FAST = int(os.getenv("SHORT_WINDOW", 5))
SMA_SLOW = int(os.getenv("LONG_WINDOW", 20))

# --- Loop interval ---
LOOP_SECS = int(os.getenv("SLEEP_INTERVAL", 60))
