#!/usr/bin/env python3
"""
Paper Trader - fake $5 ledger so you can see buys/sells + PnL with 0 real money.
Called by automaton via: exec python paper_trade.py BUY WETH 0.001 2500
"""
import json, sys, os, datetime

BALANCE_FILE = os.path.expanduser("~/.automaton/paper_pnl.json")
START_BALANCE = 5.0

if len(sys.argv) < 2:
    print("Usage: paper_trade.py BALANCE")
    print("       paper_trade.py BUY|SELL <token> <amount> <price>")
    print("Example: paper_trade.py BUY WETH 0.001 2500")
    sys.exit(1)

action = sys.argv[1].upper()

# load ledger
try:
    with open(BALANCE_FILE) as f:
        data = json.load(f)
except:
    data = {"balance": START_BALANCE, "start_balance": START_BALANCE, "trades": [], "positions": {}}
data.setdefault("positions", {})


def show_state() -> None:
    """Print balance, P&L, and open positions."""
    pnl = data["balance"] - data["start_balance"]
    pnl_pct = (pnl / data["start_balance"] * 100) if data["start_balance"] else 0
    print(f"Balance: ${data['balance']:.2f} (start ${data['start_balance']:.2f}) | "
          f"PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%)")
    pos = {k: v for k, v in data["positions"].items() if abs(v) > 1e-9}
    if pos:
        print("Positions: " + ", ".join(f"{k}={v:g}" for k, v in sorted(pos.items())))
    else:
        print("Positions: none")


if action == "BALANCE":
    show_state()
    sys.exit(0)

if len(sys.argv) < 5:
    print("Usage: paper_trade.py BALANCE")
    print("       paper_trade.py BUY|SELL <token> <amount> <price>")
    sys.exit(1)

token = sys.argv[2]
try:
    amount = float(sys.argv[3])
    price = float(sys.argv[4])
except:
    print("amount and price must be numbers")
    sys.exit(1)

if action not in ("BUY","SELL"):
    print("action must be BUY, SELL, or BALANCE")
    sys.exit(1)

# ensure start_balance
if "start_balance" not in data:
    data["start_balance"] = START_BALANCE

cost = amount * price

# ENFORCEMENT: reject trades the account cannot afford, rather than warning
# after the fact. A warning still logged a $300 position against a $5 balance,
# which made the ledger meaningless as a test of spending discipline.
if action == "BUY":
    if cost > data["balance"] + 1e-9:
        print(f"REJECTED: buy of {amount} {token} @ ${price} costs ${cost:.2f} "
              f"but balance is only ${data['balance']:.2f}. "
              f"Check balance first with: paper_trade.py BALANCE")
        sys.exit(1)
    data["balance"] -= cost
    data["positions"][token] = data["positions"].get(token, 0.0) + amount
else:  # SELL
    held = data["positions"].get(token, 0.0)
    if amount > held + 1e-9:
        print(f"REJECTED: sell of {amount} {token} exceeds held position of {held:g}. "
              f"Check balance first with: paper_trade.py BALANCE")
        sys.exit(1)
    data["balance"] += cost
    data["positions"][token] = held - amount
    if abs(data["positions"][token]) <= 1e-9:
        del data["positions"][token]

trade = {
    "time": datetime.datetime.now().isoformat(),
    "action": action,
    "token": token,
    "amount": amount,
    "price": price,
    "cost": round(cost, 2),
    "balance": round(data["balance"], 2)
}
data["trades"].append(trade)

pnl = data["balance"] - data["start_balance"]
pnl_pct = (pnl / data["start_balance"] * 100) if data["start_balance"] else 0

print(f"{action} {amount} {token} @ ${price} | Cost: ${cost:.2f} | Balance: ${data['balance']:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.1f}%)")

os.makedirs(os.path.dirname(BALANCE_FILE), exist_ok=True)
with open(BALANCE_FILE, "w") as f:
    json.dump(data, f, indent=2)

# also append to csv for easy chart
csv_file = os.path.expanduser("~/.automaton/paper_pnl.csv")
is_new = not os.path.exists(csv_file)
with open(csv_file, "a") as cf:
    if is_new:
        cf.write("time,action,token,amount,price,cost,balance,pnl\n")
    cf.write(f"{trade['time']},{action},{token},{amount},{price},{cost:.2f},{data['balance']:.2f},{pnl:.2f}\n")
