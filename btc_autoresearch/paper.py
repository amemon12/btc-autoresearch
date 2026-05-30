from __future__ import annotations

import sqlite3
from pathlib import Path

from btc_autoresearch.alpaca import AlpacaPaperClient, load_alpaca_credentials
from btc_autoresearch.backtester import signal_from_rule
from btc_autoresearch.data import load_price_data
from btc_autoresearch.models import Strategy
from btc_autoresearch.risk import validate_order


def build_paper_order(strategy: Strategy, price: float, account_equity: float, risk_config: dict) -> dict:
    risk_budget = account_equity * risk_config["account_risk_per_trade"]
    stop_price = price * (1 - strategy.risk["stop_loss"])
    take_profit = price * (1 + strategy.risk["take_profit"])
    per_unit_risk = price - stop_price
    quantity_by_risk = risk_budget / per_unit_risk
    max_notional = account_equity * risk_config["max_account_allocation_per_strategy"]
    quantity = min(quantity_by_risk, max_notional / price) * 0.999
    order = {
        "strategy_name": strategy.name,
        "side": "buy",
        "quantity": quantity,
        "entry_price": price,
        "price": price,
        "stop_loss": stop_price,
        "take_profit": take_profit,
        "notional": quantity * price,
        "account_equity": account_equity,
        "leverage": 1,
    }
    validate_order(order, risk_config)
    return order


def save_paper_order(conn: sqlite3.Connection, order: dict) -> None:
    conn.execute(
        """
        insert into paper_trades (
          strategy_name, side, quantity, price, stop_loss, take_profit, status
        ) values (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order["strategy_name"],
            order["side"],
            order["quantity"],
            order["price"],
            order["stop_loss"],
            order["take_profit"],
            "open",
        ),
    )


def _resolve_exit(strategy: Strategy, frame, stop_loss: float, take_profit: float) -> tuple[float, str] | None:
    """Decide whether an open trade closes on the latest bar.

    Mirrors the backtester's intrabar model: stop-loss (low) is checked before
    take-profit (high); a fresh exit signal closes at the latest close. Returns
    (exit_price, reason) or None if the trade stays open.
    """
    last = frame.iloc[-1]
    if float(last["low"]) <= stop_loss:
        return min(float(last["open"]), stop_loss), "stop_loss"
    if float(last["high"]) >= take_profit:
        return max(float(last["open"]), take_profit), "take_profit"
    if bool(signal_from_rule(frame, strategy.exit).iloc[-1]):
        return float(last["close"]), "exit_signal"
    return None


def close_open_trades(conn: sqlite3.Connection, strategies: dict[str, Strategy], market: str, data_dir: Path) -> list[dict]:
    """Mark open paper trades against the latest bar and close any that hit stop, target, or exit signal."""
    rows = conn.execute(
        "select id, strategy_name, quantity, price, stop_loss, take_profit from paper_trades where status = 'open'"
    ).fetchall()
    closed: list[dict] = []
    for trade_id, name, quantity, entry_price, stop_loss, take_profit in rows:
        strategy = strategies.get(name)
        if strategy is None:
            continue
        data_path = data_dir / f"{market.lower()}_{strategy.timeframe}.csv"
        if not data_path.exists():
            continue
        outcome = _resolve_exit(strategy, load_price_data(data_path), stop_loss, take_profit)
        if outcome is None:
            continue
        exit_price, reason = outcome
        realized_pnl = (exit_price - entry_price) * quantity
        conn.execute(
            """
            update paper_trades
            set status = 'closed', exit_price = ?, realized_pnl = ?, exit_reason = ?, closed_at = current_timestamp
            where id = ?
            """,
            (exit_price, realized_pnl, reason, trade_id),
        )
        closed.append({"strategy_name": name, "exit_price": exit_price, "reason": reason, "realized_pnl": realized_pnl})
    return closed


def has_open_paper_trade(conn: sqlite3.Connection, strategy_name: str) -> bool:
    row = conn.execute(
        "select 1 from paper_trades where strategy_name = ? and status = 'open' limit 1",
        (strategy_name,),
    ).fetchone()
    return row is not None


def maybe_submit_alpaca_order(strategy: Strategy, order: dict, config: dict) -> dict | None:
    paper_config = config.get("paper_trading", {})
    if not paper_config.get("enabled", False) or not paper_config.get("submit_orders", False):
        return None
    credentials = load_alpaca_credentials(config)
    if credentials is None:
        return None
    symbol = strategy.market.replace("-", "/")
    client = AlpacaPaperClient(credentials)
    return client.submit_crypto_market_order(symbol=symbol, qty=order["quantity"], side=order["side"])
