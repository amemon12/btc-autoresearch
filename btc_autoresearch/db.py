from __future__ import annotations

import sqlite3
from pathlib import Path

from btc_autoresearch.models import BacktestMetrics, StrategyScore


SCHEMA = """
create table if not exists strategies (
  name text primary key,
  market text not null,
  timeframe text not null,
  source text
);
create table if not exists backtests (
  strategy_name text not null,
  total_return real not null,
  annualized_return real not null,
  max_drawdown real not null,
  sharpe_ratio real not null,
  win_rate real not null,
  profit_factor real not null,
  trades integer not null,
  created_at text default current_timestamp
);
create table if not exists strategy_scores (
  strategy_name text not null,
  score real not null,
  rejected integer not null,
  reasons text not null,
  created_at text default current_timestamp
);
create table if not exists paper_trades (
  id integer primary key autoincrement,
  strategy_name text not null,
  side text not null,
  quantity real not null,
  price real not null,
  stop_loss real not null,
  take_profit real not null,
  status text not null,
  created_at text default current_timestamp,
  exit_price real,
  realized_pnl real,
  exit_reason text,
  closed_at text
);
create table if not exists active_strategies (
  strategy_name text primary key,
  promoted_at text default current_timestamp
);
create table if not exists retired_strategies (
  strategy_name text primary key,
  reason text not null,
  retired_at text default current_timestamp
);
create table if not exists daily_metrics (
  day text primary key,
  portfolio_pnl real not null,
  drawdown real not null
);
create table if not exists research_history (
  source_url text primary key,
  title text,
  collected_at text default current_timestamp
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


# Columns added after the initial release; applied to pre-existing databases.
PAPER_TRADE_MIGRATIONS = {
    "exit_price": "real",
    "realized_pnl": "real",
    "exit_reason": "text",
    "closed_at": "text",
}


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        _migrate_paper_trades(conn)


def _migrate_paper_trades(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("pragma table_info(paper_trades)")}
    for column, column_type in PAPER_TRADE_MIGRATIONS.items():
        if column not in existing:
            conn.execute(f"alter table paper_trades add column {column} {column_type}")


def save_backtest(conn: sqlite3.Connection, metrics: BacktestMetrics) -> None:
    conn.execute(
        """
        insert into backtests (
          strategy_name, total_return, annualized_return, max_drawdown,
          sharpe_ratio, win_rate, profit_factor, trades
        ) values (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            metrics.strategy_name,
            metrics.total_return,
            metrics.annualized_return,
            metrics.max_drawdown,
            metrics.sharpe_ratio,
            metrics.win_rate,
            metrics.profit_factor,
            metrics.trades,
        ),
    )


def save_score(conn: sqlite3.Connection, score: StrategyScore) -> None:
    conn.execute(
        "insert into strategy_scores (strategy_name, score, rejected, reasons) values (?, ?, ?, ?)",
        (score.strategy_name, score.score, int(score.rejected), ",".join(score.reasons)),
    )
