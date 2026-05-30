from __future__ import annotations

import sqlite3

from btc_autoresearch.obsidian import move_strategy_note
from btc_autoresearch.config import AppConfig


def promote_top_strategies(conn: sqlite3.Connection, config: AppConfig) -> list[str]:
    limit = int(config.values["active_strategy_limit"])
    rows = conn.execute(
        """
        select strategy_name, max(score) as best_score
        from strategy_scores
        where rejected = 0
        group by strategy_name
        order by best_score desc
        limit ?
        """,
        (limit,),
    ).fetchall()
    conn.execute("delete from active_strategies")
    promoted: list[str] = []
    for name, _score in rows:
        conn.execute("insert or replace into active_strategies (strategy_name) values (?)", (name,))
        move_strategy_note(config.vault_dir, name, "active")
        promoted.append(name)
    return promoted


def paper_drawdown(conn: sqlite3.Connection, strategy_name: str, starting_cash: float) -> tuple[float, int]:
    """Peak-to-trough drawdown of a strategy's realized paper-trading equity curve.

    Returns (max_drawdown_fraction, closed_trade_count). Equity starts at the configured
    cash and accrues realized PnL in close order; open positions are excluded until they close.
    """
    rows = conn.execute(
        """
        select realized_pnl from paper_trades
        where strategy_name = ? and status = 'closed' and realized_pnl is not null
        order by closed_at, id
        """,
        (strategy_name,),
    ).fetchall()
    if not rows:
        return 0.0, 0
    equity = starting_cash
    peak = starting_cash
    max_drawdown = 0.0
    for (realized_pnl,) in rows:
        equity += float(realized_pnl)
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown, len(rows)


def retire_failing_strategies(conn: sqlite3.Connection, config: AppConfig) -> list[str]:
    retirement = config.values.get("retirement", {})
    max_drawdown_limit = float(retirement.get("max_paper_drawdown", 0.15))
    min_closed_trades = int(retirement.get("min_closed_trades", 3))
    starting_cash = float(config.values["paper_trading"]["starting_cash"])

    active = [name for (name,) in conn.execute("select strategy_name from active_strategies").fetchall()]
    retired: list[str] = []
    for name in active:
        drawdown, closed_trades = paper_drawdown(conn, name, starting_cash)
        if closed_trades < min_closed_trades or drawdown <= max_drawdown_limit:
            continue
        conn.execute("delete from active_strategies where strategy_name = ?", (name,))
        conn.execute(
            "insert or replace into retired_strategies (strategy_name, reason) values (?, ?)",
            (name, f"paper_drawdown_{drawdown:.0%}_over_limit_{max_drawdown_limit:.0%}"),
        )
        move_strategy_note(config.vault_dir, name, "retired")
        retired.append(name)
    return retired
