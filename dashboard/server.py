from threading import Thread
from flask import Flask, render_template
from flask_socketio import SocketIO
import time
import datetime

import config
from bot.trader import run_bot_loop, stop_bot, state


# --------------------------
# Flask + SocketIO Setup
# --------------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


# --------------------------
# Routes
# --------------------------
@app.route("/")
def index():
    print("Serving dashboard index.html")  # Debug log
    return render_template("index.html")


# --------------------------
# Background Publisher
# --------------------------
def _publisher():
    """Continuously publish bot state + server status to dashboard."""
    print("✅ Publisher thread started")
    last_status = time.time()

    while True:
        try:
            payload = {
                "serverStatus": {
                    "running": state.running,
                    "lastUpdate": datetime.datetime.utcnow().isoformat() + "Z"
                },
                "symbol": config.SYMBOL,
                "dryRun": config.DRY_RUN,
                "candles": state.candles[-200:],
                "fast": state.fast,
                "slow": state.slow,
                "lastSignal": state.last_signal,
                "balance": state.balance,
                "position": {
                    "side": state.position.side,
                    "entry_price": state.position.entry_price,
                    "qty": state.position.qty,
                    "sl": state.position.sl,
                    "tp": state.position.tp,
                },
                "pnl": state.pnl_realized,
                "logs": state.logs[-50:],
            }
            socketio.emit("update", payload)

            # Print heartbeat every 30 seconds
            if time.time() - last_status >= 30:
                print(f"💓 Server alive at {datetime.datetime.now().strftime('%H:%M:%S')}")
                last_status = time.time()

            time.sleep(1)
        except Exception as e:
            print(f"Publisher error: {e}")  # log errors for debugging
            time.sleep(1)


# --------------------------
# SocketIO Events
# --------------------------
@socketio.on("start")
def on_start():
    if not state.running:
        Thread(target=run_bot_loop, daemon=True).start()
        socketio.emit("toast", {"type": "info", "msg": "Bot started"})


@socketio.on("stop")
def on_stop():
    if state.running:
        stop_bot()
        socketio.emit("toast", {"type": "warning", "msg": "Bot stopped"})


# --------------------------
# Main Entry
# --------------------------
def run_all():
    # Start publisher thread for dashboard updates
    Thread(target=_publisher, daemon=True).start()
    socketio.run(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    run_all()
