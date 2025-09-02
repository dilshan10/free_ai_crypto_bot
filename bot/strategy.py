import config




def sma(values, length):
    if len(values) < length:
        return None
    return sum(values[-length:]) / float(length)




def generate_signal(candles):
    """Return "BUY" | "SELL" | None based on SMA cross."""
    closes = [c["close"] for c in candles]
    fast = sma(closes, config.SMA_FAST)
    slow = sma(closes, config.SMA_SLOW)
    if fast is None or slow is None:
        return None, fast, slow
    if fast > slow:
        return "BUY", fast, slow
    if fast < slow:
        return "SELL", fast, slow
    return None, fast, slow




def compute_sl_tp(entry_price: float):
    sl = entry_price * (1.0 - config.STOP_LOSS_PCT)
    tp = entry_price * (1.0 + config.TAKE_PROFIT_PCT)
    return sl, tp