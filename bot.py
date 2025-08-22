import ccxt, pandas as pd, time, os, csv, threading
from dotenv import load_dotenv

load_dotenv()

EXCHANGE_NAME = os.getenv("EXCHANGE", "binance").lower()
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")
QUOTE_SPEND_PCT = float(os.getenv("QUOTE_SPEND_PCT", "0.1"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

exchange_class = getattr(ccxt, EXCHANGE_NAME)
exchange = exchange_class({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True
})

trade_log = []  # memory store for UI
bot_status = {"in_position": False, "last_action": None, "entry_price": None}

def fetch_data(symbol=SYMBOL, timeframe="5m", limit=200):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts","o","h","l","c","v"])
    df["ema21"] = df["c"].ewm(span=21).mean()
    df["ema200"] = df["c"].ewm(span=200).mean()
    df["rsi"] = compute_rsi(df["c"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_balance(asset="USDT"):
    if DRY_RUN:
        return 1000.0
    balance = exchange.fetch_balance()
    return balance[asset]["free"]

def log_trade(side, price, amount):
    row = {"side": side, "price": price, "amount": amount, "ts": pd.Timestamp.now()}
    trade_log.append(row)

    file = "trades_log.csv"
    exists = os.path.exists(file)
    with open(file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not exists:
            writer.writeheader()
        writer.writerow(row)

def run_bot():
    in_position, entry_price = False, 0
    while True:
        try:
            df = fetch_data()
            last = df.iloc[-1]
            price = last["c"]

            if not in_position:
                if last["ema21"] > last["ema200"] and last["rsi"] > 50:
                    spend = get_balance() * QUOTE_SPEND_PCT
                    in_position, entry_price = True, price
                    log_trade("BUY", price, spend/price)
                    bot_status.update({"in_position": True, "last_action": "BUY", "entry_price": entry_price})
                    print(f"BUY @ {price}")
            else:
                if last["ema21"] < last["ema200"] or last["rsi"] < 45 or price < entry_price*0.97 or price > entry_price*1.05:
                    in_position = False
                    log_trade("SELL", price, "all")
                    bot_status.update({"in_position": False, "last_action": "SELL", "entry_price": None})
                    print(f"SELL @ {price}")

            time.sleep(60)
        except Exception as e:
            print("Error:", e)
            time.sleep(60)

def start_bot():
    t = threading.Thread(target=run_bot, daemon=True)
    t.start()
