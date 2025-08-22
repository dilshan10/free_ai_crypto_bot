from flask import Flask, render_template_string, jsonify
from bot import start_bot, trade_log, bot_status

app = Flask(__name__)
start_bot()  # run bot in background

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Crypto Bot Dashboard</title>
  <style>
    body { font-family: Arial; margin: 20px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    th { background: #333; color: white; }
  </style>
</head>
<body>
  <h2>🤖 Crypto Bot Dashboard</h2>
  <p>Status: {{status}}</p>
  <p>Last Action: {{last_action}}</p>
  <p>Entry Price: {{entry_price}}</p>

  <h3>Trade History</h3>
  <table>
    <tr><th>Side</th><th>Price</th><th>Amount</th><th>Time</th></tr>
    {% for t in trades %}
    <tr>
      <td>{{t.side}}</td>
      <td>{{t.price}}</td>
      <td>{{t.amount}}</td>
      <td>{{t.ts}}</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, 
        status="IN Position" if bot_status["in_position"] else "OUT of Position",
        last_action=bot_status["last_action"],
        entry_price=bot_status["entry_price"],
        trades=trade_log[-20:]  # last 20 trades
    )

@app.route("/api/trades")
def api_trades():
    return jsonify(trade_log)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
