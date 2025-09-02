import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime

import config
from bot.data_fetcher import (
    get_exchange,
    get_candles,
    get_last_price,
    get_quote_balance,
)
from bot.strategy import generate_signal, compute_sl_tp


@dataclass
class Position:
    side: Optional[str] = None  # "LONG" or None
    entry_price: float = 0.0
    qty: float = 0.0
    sl: float = 0.0
    tp: float = 0.0


@dataclass
class BotState:
    running: bool = False
    candles: List[Dict] = field(default_factory=list)
    fast: Optional[float] = None
    slow: Optional[float] = None
    last_signal: Optional[str] = None
    balance: float = 0.0
    position: Position = field(default_factory=Position)
    logs: List[str] = field(default_factory=list)
    pnl_realized: float = 0.0
    signals: List[Dict] = field(default_factory=list)   # <-- NEW


state = BotState()


def log(msg: str):
    print(msg)
    state.logs.append(msg)
    if len(state.logs) > 500:
        state.logs.pop(0)


def _calc_order_qty(entry_price: float, balance: float) -> float:
    if balance <= 0 or entry_price <= 0:
        return 0.0
    spend = balance * config.QUOTE_SPEND_PCT
    qty = round(spend / entry_price, 6)  # adjust precision if needed
    return max(qty, 0.0)


def _place_order(client, side: str, qty: float):
    if config.DRY_RUN:
        log(f"[DRY_RUN] Place {side} qty={qty}")
        return {"retCode": 0, "result": {"dryRun": True}}
    # Live order
    return client.place_order(
        category=config.CATEGORY,
        symbol=config.SYMBOL,
        side="Buy" if side == "BUY" else "Sell",
        orderType="Market",
        qty=qty,
        timeInForce="IOC",
        reduceOnly=False,
    )


def _maybe_close_position(client, price: float):
    pos = state.position
    if not pos.side:
        return
    # Check SL/TP
    if price <= pos.sl or price >= pos.tp:
        side = "SELL"  # closing long
        result = _place_order(client, side, pos.qty)
        if result.get("retCode") == 0:
            # Realized PnL (approx)
            pnl = (price - pos.entry_price) * pos.qty
            state.pnl_realized += pnl
            log(f"Closed LONG at {price:.2f} | PnL {pnl:.2f} USDT")
            state.position = Position()  # reset
        else:
            log(f"Close failed: {result}")


def step_once(client):
    # 1) Fetch market data
    candles = get_candles(client, limit=config.MAX_CANDLES)
    state.candles = candles

    # 2) Compute signal
    signal, fast, slow = generate_signal(candles)
    state.fast, state.slow = fast, slow
    state.last_signal = signal

    # Save signal to list
    if signal:
        state.signals.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "signal": signal,
            "price": candles[-1]["close"]
        })
        if len(state.signals) > 50:  # keep only last 50
            state.signals.pop(0)

    # 3) Get balance & last price
    price = candles[-1]["close"]
    balance = get_quote_balance(client)
    state.balance = balance

    # 4) Manage open position SL/TP
    _maybe_close_position(client, price)

    # 5) Entry logic (only LONG for simplicity)
    if signal == "BUY" and not state.position.side:
        qty = _calc_order_qty(price, balance)
        if qty > 0:
            result = _place_order(client, "BUY", qty)
            if result.get("retCode") == 0:
                sl, tp = compute_sl_tp(price)
                state.position = Position(side="LONG", entry_price=price, qty=qty, sl=sl, tp=tp)
                log(f"Opened LONG: qty={qty} entry={price:.2f} SL={sl:.2f} TP={tp:.2f}")
            else:
                log(f"Open failed: {result}")


def run_bot_loop():
    client = get_exchange()
    state.running = True
    log(f"🚀 Starting Bybit bot on {config.SYMBOL} (DRY_RUN={config.DRY_RUN})…")
    while state.running:
        try:
            step_once(client)
            time.sleep(config.LOOP_SECS)
        except Exception as e:
            log(f"⚠️ Error in main loop: {e}")
            time.sleep(2)


def stop_bot():
    state.running = False
