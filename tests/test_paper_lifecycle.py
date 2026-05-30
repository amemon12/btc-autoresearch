import sqlite3

import pandas as pd

from btc_autoresearch.models import Strategy
from btc_autoresearch.paper import _resolve_exit
from btc_autoresearch.promotion import paper_drawdown


def _strategy() -> Strategy:
    return Strategy(
        name="T",
        market="BTC/USD",
        timeframe="1d",
        entry={"close": {"operator": ">", "value": 0}},
        exit={"close": {"operator": "<", "value": 0}},  # never fires
        risk={"stop_loss": 0.05, "take_profit": 0.10},
    )


def _last_bar(open_, high, low, close) -> pd.DataFrame:
    return pd.DataFrame(
        [(open_, high, low, close, 1)],
        columns=["open", "high", "low", "close", "volume"],
        index=pd.date_range("2020-01-01", periods=1),
    )


def test_resolve_exit_stop_before_target():
    # Bar touches both stop (90) and target (110); stop must win.
    frame = _last_bar(100, 115, 85, 100)
    exit_price, reason = _resolve_exit(_strategy(), frame, stop_loss=90, take_profit=110)
    assert reason == "stop_loss"
    assert exit_price == 90


def test_resolve_exit_none_when_untouched():
    frame = _last_bar(100, 102, 98, 100)
    assert _resolve_exit(_strategy(), frame, stop_loss=90, take_profit=110) is None


def _conn_with_trades(realized: list[float]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "create table paper_trades (id integer primary key, strategy_name text, status text, realized_pnl real, closed_at text)"
    )
    for i, pnl in enumerate(realized):
        conn.execute(
            "insert into paper_trades (id, strategy_name, status, realized_pnl, closed_at) values (?, 'T', 'closed', ?, ?)",
            (i, pnl, f"2020-01-{i + 1:02d}"),
        )
    return conn


def test_paper_drawdown_tracks_peak_to_trough():
    # Equity: 100k -> 110k (peak) -> 95k. Drawdown = (110-95)/110.
    conn = _conn_with_trades([10000, -15000])
    drawdown, closed = paper_drawdown(conn, "T", starting_cash=100000)
    assert closed == 2
    assert abs(drawdown - (15000 / 110000)) < 1e-9
