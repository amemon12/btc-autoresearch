from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from btc_autoresearch.obsidian import FOLDERS, ensure_vault


def append_log(root: Path, message: str) -> None:
    log_dir = root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "autoresearch.log").open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")


def write_backlog_report(conn: sqlite3.Connection, vault_dir: Path) -> Path:
    ensure_vault(vault_dir)
    rows = conn.execute(
        """
        select strategy_name, max(score) as best_score, min(rejected) as accepted, group_concat(distinct reasons)
        from strategy_scores
        group by strategy_name
        order by accepted desc, best_score desc
        """
    ).fetchall()
    lines = [
        "# Strategy Backlog",
        "",
        "| Strategy | Best Score | Accepted | Reasons |",
        "|---|---:|---|---|",
    ]
    for name, score, accepted, reasons in rows:
        lines.append(f"| {name} | {score:.2f} | {'yes' if accepted == 0 else 'no'} | {reasons or ''} |")
    path = vault_dir / "Strategy Backlog.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_active_report(conn: sqlite3.Connection, vault_dir: Path) -> Path:
    ensure_vault(vault_dir)
    rows = conn.execute("select strategy_name, promoted_at from active_strategies order by promoted_at desc").fetchall()
    lines = ["# Active Strategies", ""]
    if rows:
        for name, promoted_at in rows:
            lines.append(f"- {name} (promoted {promoted_at})")
    else:
        lines.append("No active strategies. Candidates must pass the score gates before promotion.")
    path = vault_dir / "Active Strategies.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_backtest_summary(conn: sqlite3.Connection, vault_dir: Path, reports_dir: Path) -> Path:
    ensure_vault(vault_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        """
        select b.strategy_name, b.total_return, b.annualized_return, b.max_drawdown,
               b.sharpe_ratio, b.win_rate, b.profit_factor, b.trades,
               s.score, s.rejected, s.reasons
        from backtests b
        join (
          select strategy_name, max(created_at) as created_at
          from backtests
          group by strategy_name
        ) latest on latest.strategy_name = b.strategy_name and latest.created_at = b.created_at
        left join (
          select strategy_name, score, rejected, reasons, max(created_at)
          from strategy_scores
          group by strategy_name
        ) s on s.strategy_name = b.strategy_name
        order by coalesce(s.rejected, 1), coalesce(s.score, 0) desc
        """
    ).fetchall()
    lines = [
        "# Backtest Reports",
        "",
        "| Strategy | Score | Accepted | Return | Max DD | Sharpe | Win Rate | PF | Trades | Reasons |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        name, total_return, _annual, drawdown, sharpe, win_rate, profit_factor, trades, score, rejected, reasons = row
        lines.append(
            f"| {name} | {(score or 0):.2f} | {'yes' if rejected == 0 else 'no'} | "
            f"{total_return:.2%} | {drawdown:.2%} | {sharpe:.2f} | {win_rate:.2%} | "
            f"{profit_factor:.2f} | {trades} | {reasons or ''} |"
        )
    text = "\n".join(lines)
    vault_path = vault_dir / FOLDERS["reports"] / "Backtest Summary.md"
    local_path = reports_dir / "summary.md"
    vault_path.write_text(text, encoding="utf-8")
    local_path.write_text(text, encoding="utf-8")
    return vault_path


def write_paper_trade_logs(conn: sqlite3.Connection, vault_dir: Path, paper_dir: Path, latest_price: float | None) -> tuple[Path, Path]:
    ensure_vault(vault_dir)
    paper_dir.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        """
        select id, strategy_name, side, quantity, price, stop_loss, take_profit, status,
               created_at, realized_pnl, exit_price, exit_reason
        from paper_trades
        order by created_at desc, id desc
        """
    ).fetchall()

    def pnl_for(side, status, entry, quantity, realized_pnl) -> tuple[float, float]:
        """Realized PnL for closed trades, unrealized (marked to latest price) for open ones."""
        if status == "closed" and realized_pnl is not None:
            return float(realized_pnl), float(realized_pnl) / (entry * quantity) if entry and quantity else 0.0
        if latest_price is not None and status == "open":
            direction = 1 if side == "buy" else -1
            return (latest_price - entry) * quantity * direction, (latest_price - entry) / entry * direction
        return 0.0, 0.0

    csv_path = paper_dir / "paper_trades.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "id",
                "strategy_name",
                "side",
                "quantity",
                "entry_price",
                "latest_price",
                "pnl",
                "pnl_pct",
                "stop_loss",
                "take_profit",
                "status",
                "exit_reason",
                "created_at",
            ]
        )
        for row in rows:
            trade_id, name, side, quantity, entry, stop_loss, take_profit, status, created_at, realized_pnl, _exit_price, exit_reason = row
            pnl, pnl_pct = pnl_for(side, status, entry, quantity, realized_pnl)
            writer.writerow(
                [trade_id, name, side, quantity, entry, latest_price or "", pnl, pnl_pct, stop_loss, take_profit, status, exit_reason or "", created_at]
            )

    lines = [
        "# Paper Trading Logs",
        "",
        f"Latest BTC price used for open PnL: {latest_price:.2f}" if latest_price is not None else "Latest BTC price unavailable.",
        "",
        "| ID | Strategy | Side | Qty | Entry | PnL | PnL % | Stop | Target | Status | Exit | Created |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        trade_id, name, side, quantity, entry, stop_loss, take_profit, status, created_at, realized_pnl, _exit_price, exit_reason = row
        pnl, pnl_pct = pnl_for(side, status, entry, quantity, realized_pnl)
        lines.append(
            f"| {trade_id} | {name} | {side} | {quantity:.8f} | {entry:.2f} | "
            f"{pnl:.2f} | {pnl_pct:.2%} | {stop_loss:.2f} | {take_profit:.2f} | {status} | {exit_reason or ''} | {created_at} |"
        )
    md_text = "\n".join(lines)
    vault_path = vault_dir / FOLDERS["paper"] / "Paper Trade Log.md"
    local_path = paper_dir / "paper_trade_log.md"
    vault_path.write_text(md_text, encoding="utf-8")
    local_path.write_text(md_text, encoding="utf-8")
    return vault_path, csv_path
