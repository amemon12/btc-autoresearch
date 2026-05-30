from __future__ import annotations


def validate_order(order: dict, risk_config: dict) -> None:
    if order.get("side") != "buy":
        raise ValueError("Shorting is disabled")
    if order.get("leverage", 1) != 1:
        raise ValueError("Leverage is disabled")
    if not order.get("stop_loss"):
        raise ValueError("Every position requires a stop loss")
    if not order.get("take_profit"):
        raise ValueError("Every position requires a take profit")
    allocation = float(order["notional"]) / float(order["account_equity"])
    if allocation > risk_config["max_account_allocation_per_strategy"] + 1e-9:
        raise ValueError("Strategy allocation exceeds configured maximum")
    risk_per_trade = abs(float(order["entry_price"]) - float(order["stop_loss"])) * float(order["quantity"])
    if risk_per_trade / float(order["account_equity"]) > risk_config["account_risk_per_trade"]:
        raise ValueError("Trade risk exceeds configured maximum")
