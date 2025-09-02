from typing import List, Dict
from pybit.unified_trading import HTTP
import config




def get_exchange() -> HTTP:
    """Create Bybit HTTP client (Unified V5)."""
    return HTTP(
    testnet=config.TESTNET,
    api_key=config.API_KEY,
    api_secret=config.API_SECRET,
)




def parse_candle(candle) -> Dict[str, float]:
    """Normalize Bybit candle (list or dict) into {open, high, low, close, volume, ts}."""
    # V5 usually returns list: [start, open, high, low, close, volume, turnover]
    if isinstance(candle, list) and len(candle) >= 6:
        return {
        "ts": int(candle[0]),
        "open": float(candle[1]),
        "high": float(candle[2]),
        "low": float(candle[3]),
        "close": float(candle[4]),
        "volume": float(candle[5]),
        }
    # Support dict fallback (rare)
    if isinstance(candle, dict):
        return {
        "ts": int(candle.get("start", candle.get("t", 0)) or 0),
        "open": float(candle.get("o", candle.get("open"))),
        "high": float(candle.get("h", candle.get("high"))),
        "low": float(candle.get("l", candle.get("low"))),
        "close": float(candle.get("c", candle.get("close"))),
        "volume": float(candle.get("v", candle.get("volume", 0))),
        }
    raise ValueError(f"Unknown candle format: {candle}")




def get_candles(client: HTTP, limit: int = 200) -> List[dict]:
    """Fetch latest candles (normalized)."""
    resp = client.get_kline(
    category=config.CATEGORY,
    symbol=config.SYMBOL,
    interval=config.INTERVAL,
    limit=limit,
    )
    if "result" not in resp or "list" not in resp["result"]:
        raise RuntimeError(f"Unexpected kline response: {resp}")
    raw = resp["result"]["list"]
    candles = [parse_candle(c) for c in raw]
    candles.sort(key=lambda x: x["ts"]) # ensure ascending
    return candles




def get_last_price(client: HTTP) -> float:
    """Fetch last traded price (LTP)."""
    resp = client.get_tickers(category=config.CATEGORY, symbol=config.SYMBOL)
    price = float(resp["result"]["list"][0]["lastPrice"])
    return price




def get_quote_balance(client: HTTP) -> float:
    """Return quote balance (USDT). If DRY_RUN, use DEFAULT_BALANCE."""
    if config.DRY_RUN:
        return config.DEFAULT_BALANCE
    try:
    # accountType: UNIFIED | CONTRACT | SPOT ; coin optional
        resp = client.get_wallet_balance(accountType="UNIFIED", coin="USDT")
        coins = resp["result"]["list"][0]["coin"]
        for c in coins:
            if c["coin"] == "USDT":
            # availableToWithdraw is a good proxy for free balance
                return float(c.get("availableToWithdraw", c.get("walletBalance", 0)))
    except Exception:
        pass
    return 0.0