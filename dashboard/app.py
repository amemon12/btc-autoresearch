from __future__ import annotations

import os
import platform
import signal
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from btc_autoresearch.backtester import backtest_equity_curve  # noqa: E402
from btc_autoresearch.config import load_config  # noqa: E402
from btc_autoresearch.data import load_price_data  # noqa: E402
from btc_autoresearch.strategy_io import load_all_strategies  # noqa: E402

st.set_page_config(page_title="BTC AutoResearch", page_icon="₿", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem;}
      [data-testid="stMetric"] {
        background: #161b22; border: 1px solid #30363d; border-radius: 12px;
        padding: 14px 16px;
      }
      [data-testid="stMetricLabel"] {opacity: 0.7;}
      h1, h2, h3 {letter-spacing: -0.01em;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_config():
    return load_config(ROOT / "config/config.yaml")


CONFIG = get_config()
DB_PATH = CONFIG.database_path
DATA_DIR = CONFIG.data_dir
MARKET = CONFIG.values["market"]
COSTS = CONFIG.values.get("backtest", {})
SIZING = CONFIG.values.get("risk", {})

st.title("₿ Bitcoin AutoResearch Strategy Lab")
st.caption("Local-first research → backtest → score → promote → paper-trade → retire. Paper trading only.")


def open_in_file_manager(path: Path) -> None:
    """Open a folder in the OS file manager. Works only when Streamlit runs on the local machine."""
    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    elif system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def run_cli_steps(steps: list[str]) -> str:
    """Run btc-lab pipeline steps in subprocesses (reusing tested code paths) and return combined output."""
    output: list[str] = []
    for step in steps:
        result = subprocess.run(
            [sys.executable, "-m", "btc_autoresearch.cli", step],
            cwd=ROOT, capture_output=True, text=True,
        )
        output.append(f"$ btc-lab {step}\n{result.stdout}{result.stderr}")
    return "\n".join(output)


LOOP_PIDFILE = ROOT / "logs" / "loop.pid"
LOOP_LOG = ROOT / "logs" / "loop.log"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def loop_pid() -> int | None:
    """PID of the running AutoResearch loop, or None. Cleans up a stale pidfile."""
    if not LOOP_PIDFILE.exists():
        return None
    try:
        pid = int(LOOP_PIDFILE.read_text().strip())
    except (ValueError, OSError):
        LOOP_PIDFILE.unlink(missing_ok=True)
        return None
    if _pid_alive(pid):
        return pid
    LOOP_PIDFILE.unlink(missing_ok=True)
    return None


def start_loop(sleep_minutes: int, refresh_data: bool) -> int:
    """Launch `btc-lab loop` detached so it survives Streamlit reruns; record its PID."""
    LOOP_LOG.parent.mkdir(parents=True, exist_ok=True)
    # -u keeps stdout unbuffered so the loop's per-cycle output reaches the log in real time.
    args = [sys.executable, "-u", "-m", "btc_autoresearch.cli", "loop", "--sleep-minutes", str(sleep_minutes)]
    if not refresh_data:
        args.append("--offline")
    log_handle = open(LOOP_LOG, "a", encoding="utf-8")
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    process = subprocess.Popen(
        args, cwd=ROOT, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True, env=env
    )
    LOOP_PIDFILE.write_text(str(process.pid))
    return process.pid


def stop_loop() -> None:
    pid = loop_pid()
    if pid is None:
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    LOOP_PIDFILE.unlink(missing_ok=True)


with st.sidebar:
    st.header("Controls")
    if st.button("▶ Run Research once", use_container_width=True, help="Generate new strategy candidates and write notes to the vault"):
        with st.spinner("Running research cycle…"):
            from btc_autoresearch.research_agent import run_research_cycle

            candidates = run_research_cycle(CONFIG)
        st.success(f"Generated {len(candidates)} candidate(s). Vault updated.")
        open_in_file_manager(CONFIG.vault_dir)
        st.cache_data.clear()
    if st.button("📂 Open Obsidian Vault", use_container_width=True):
        open_in_file_manager(CONFIG.vault_dir)
        st.toast(f"Opened {CONFIG.vault_dir}")

    st.divider()
    st.subheader("AutoResearch Loop")
    running = loop_pid()
    if running:
        st.success(f"Running — PID {running}")
    else:
        st.info("Stopped")
    sleep_minutes = st.number_input("Cycle interval (minutes)", min_value=1, max_value=1440, value=60, disabled=running is not None)
    refresh_data = st.checkbox("Refresh market data each cycle (needs internet)", value=False, disabled=running is not None)
    start_col, stop_col = st.columns(2)
    if start_col.button("▶ Start", use_container_width=True, disabled=running is not None):
        pid = start_loop(int(sleep_minutes), refresh_data)
        st.toast(f"Loop started (PID {pid})")
        st.rerun()
    if stop_col.button("■ Stop", use_container_width=True, disabled=running is None):
        stop_loop()
        st.toast("Loop stopped")
        st.rerun()
    st.caption("Each cycle: research → backtest → promote → retire → paper, then sleeps. Runs on the dashboard host.")

    if LOOP_LOG.exists():
        if st.button("🔄 Refresh view", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        with st.expander("Loop log (latest)", expanded=bool(running)):
            tail = LOOP_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()[-50:]
            st.code("\n".join(tail) or "(empty)")

if not DB_PATH.exists():
    st.warning("Database not initialized yet. Use **Run Full Cycle** in the sidebar, or run `btc-lab run` in a terminal.")
    st.stop()


@st.cache_data(ttl=30)
def read_sql(query: str) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


@st.cache_resource
def strategy_map() -> dict:
    strategies = load_all_strategies([ROOT / "strategies/generated", ROOT / "strategies/yaml"])
    return {s.name: s for s in strategies}


@st.cache_data(ttl=300)
def latest_price(timeframe: str) -> float | None:
    path = DATA_DIR / f"{MARKET.lower()}_{timeframe}.csv"
    if not path.exists():
        return None
    return float(load_price_data(path)["close"].iloc[-1])


@st.cache_data(ttl=300)
def equity_curve(strategy_name: str) -> pd.Series | None:
    strategy = strategy_map().get(strategy_name)
    if strategy is None:
        return None
    path = DATA_DIR / f"{MARKET.lower()}_{strategy.timeframe}.csv"
    if not path.exists():
        return None
    return backtest_equity_curve(strategy, load_price_data(path), COSTS, SIZING)


def paper_frame() -> pd.DataFrame:
    """Unified paper-trade view: realized PnL for closed trades, marked unrealized for open ones."""
    trades = read_sql("select * from paper_trades order by created_at, id")
    if trades.empty:
        return trades
    smap = strategy_map()

    def mark(row) -> float:
        if row["status"] == "closed" and pd.notna(row.get("realized_pnl")):
            return float(row["realized_pnl"])
        strat = smap.get(row["strategy_name"])
        price = latest_price(strat.timeframe) if strat else latest_price("4h")
        if price is None:
            return 0.0
        return (price - row["price"]) * row["quantity"]

    trades["pnl"] = trades.apply(mark, axis=1)
    trades["notional"] = trades["quantity"] * trades["price"]
    return trades


STARTING_CASH = float(CONFIG.values["paper_trading"]["starting_cash"])


def render_performance(closed: pd.DataFrame, starting_cash: float, time_col: str = "closed_at") -> None:
    """TradingView-style performance panel: key stats + cumulative PnL + per-trade run-ups/drawdowns."""
    if closed.empty:
        st.info("No closed trades yet — performance appears once trades close.")
        return
    closed = closed.sort_values([time_col, "id"]).copy()
    pnl = closed["pnl"].astype(float)
    cumulative = pnl.cumsum()
    equity = starting_cash + cumulative
    peak = equity.cummax()
    drawdown = equity - peak  # USD, <= 0

    total_pnl = float(pnl.sum())
    max_dd_usd = float(-drawdown.min())
    max_dd_pct = float(-(drawdown / peak).min()) if (peak > 0).all() else 0.0
    wins = int((pnl > 0).sum())
    n_trades = int(len(pnl))
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else (99.0 if gross_profit else 0.0)

    st.subheader("Key stats")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total PnL", f"${total_pnl:,.0f}", f"{total_pnl / starting_cash:.2%}")
    k2.metric("Max Drawdown", f"${max_dd_usd:,.0f}", f"-{max_dd_pct:.2%}", delta_color="inverse")
    k3.metric("Profitable Trades", f"{wins / n_trades:.2%}" if n_trades else "n/a", f"{wins}/{n_trades}")
    k4.metric("Profit Factor", f"{profit_factor:.3f}")

    st.markdown("**Performance — Cumulative PnL**")
    index = pd.to_datetime(closed[time_col], errors="coerce")
    st.area_chart(pd.DataFrame({"Cumulative PnL": cumulative.values}, index=index))
    st.markdown("**Run-ups & drawdowns (per trade)**")
    st.bar_chart(pd.DataFrame({"Trade PnL": pnl.values}, index=index))


scores = read_sql("select * from strategy_scores order by created_at desc")
backtests = read_sql("select * from backtests order by created_at desc")
paper = paper_frame()

tabs = st.tabs(
    ["Overview", "Strategy Explorer", "Rankings", "Backtests", "Paper Trading", "Active / Retired", "Research"]
)

# ----------------------------------------------------------------------------- Overview
with tabs[0]:
    active_count = len(read_sql("select * from active_strategies"))
    realized = float(paper.loc[paper["status"] == "closed", "pnl"].sum()) if not paper.empty else 0.0
    unrealized = float(paper.loc[paper["status"] == "open", "pnl"].sum()) if not paper.empty else 0.0
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Strategies", active_count)
    c2.metric("Strategies Scored", scores["strategy_name"].nunique() if not scores.empty else 0)
    c3.metric("Best Score", f"{scores['score'].max():.1f}" if not scores.empty else "n/a")
    c4.metric("Realized Paper PnL", f"${realized:,.0f}")
    c5.metric("Open Unrealized PnL", f"${unrealized:,.0f}")

    if not paper.empty:
        st.subheader("Paper Equity Curve")
        starting_cash = float(CONFIG.values["paper_trading"]["starting_cash"])
        closed = paper[paper["status"] == "closed"].copy()
        if not closed.empty:
            closed = closed.sort_values(["closed_at", "id"])
            closed["equity"] = starting_cash + closed["pnl"].cumsum()
            curve = closed.set_index("closed_at")["equity"]
            st.area_chart(curve)
        else:
            st.info("No closed paper trades yet — equity curve appears once trades close.")

    if not backtests.empty:
        st.subheader("Backtest Snapshot (latest per strategy)")
        snap = backtests.groupby("strategy_name", as_index=True).first()
        st.bar_chart(snap[["total_return", "max_drawdown"]])
    else:
        st.info("No backtests yet. Run `btc-lab backtest`.")

# --------------------------------------------------------------------- Strategy Explorer
with tabs[1]:
    smap = strategy_map()
    names = sorted(set(backtests["strategy_name"]) | set(smap)) if not backtests.empty else sorted(smap)
    if not names:
        st.info("No strategies found yet.")
    else:
        choice = st.selectbox("Strategy", names)
        strat = smap.get(choice)
        left, right = st.columns([1, 1])
        with left:
            st.subheader("Definition")
            if strat:
                st.write(f"**Market:** {strat.market}  |  **Timeframe:** {strat.timeframe}")
                st.write(f"**Stop loss:** {strat.risk['stop_loss']:.2%}  |  **Take profit:** {strat.risk['take_profit']:.2%}")
                st.markdown("**Entry**")
                st.json(strat.entry, expanded=False)
                st.markdown("**Exit**")
                st.json(strat.exit, expanded=False)
            else:
                st.info("No YAML on disk for this strategy (it may have been regenerated).")
        with right:
            st.subheader("Latest Backtest")
            row = backtests[backtests["strategy_name"] == choice]
            if row.empty:
                st.info("Not backtested yet.")
            else:
                r = row.iloc[0]
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Return", f"{r['total_return']:.1%}")
                m2.metric("Max Drawdown", f"{r['max_drawdown']:.1%}")
                m3.metric("Sharpe", f"{r['sharpe_ratio']:.2f}")
                m4, m5, m6 = st.columns(3)
                m4.metric("Profit Factor", f"{r['profit_factor']:.2f}")
                m5.metric("Win Rate", f"{r['win_rate']:.1%}")
                m6.metric("Trades", int(r["trades"]))

        curve = equity_curve(choice)
        if curve is not None:
            st.subheader("Backtest Equity Curve (cost-adjusted)")
            st.line_chart(curve)

        st.subheader("Paper Trades")
        if paper.empty or paper[paper["strategy_name"] == choice].empty:
            st.info("No paper trades for this strategy.")
        else:
            strat_trades = paper[paper["strategy_name"] == choice]
            render_performance(strat_trades[strat_trades["status"] == "closed"], STARTING_CASH)
            cols = ["id", "status", "quantity", "price", "exit_price", "pnl", "exit_reason", "created_at", "closed_at"]
            st.dataframe(strat_trades[cols], use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------- Rankings
with tabs[2]:
    rankings = read_sql(
        """
        select strategy_name, max(score) as best_score, min(rejected) as best_rejected, count(*) as runs
        from strategy_scores group by strategy_name order by best_score desc
        """
    )
    if rankings.empty:
        st.info("No scores yet.")
    else:
        rankings["accepted"] = rankings["best_rejected"] == 0
        if st.toggle("Show accepted (gate-passing) only", value=False):
            rankings = rankings[rankings["accepted"]]
        st.dataframe(
            rankings[["strategy_name", "best_score", "accepted", "runs"]],
            use_container_width=True,
            hide_index=True,
        )

# ------------------------------------------------------------------------------ Backtests
with tabs[3]:
    if backtests.empty:
        st.info("No backtest reports yet.")
    else:
        latest = backtests.groupby("strategy_name", as_index=False).first()
        col1, col2 = st.columns(2)
        col1.bar_chart(latest.set_index("strategy_name")["total_return"])
        col2.bar_chart(latest.set_index("strategy_name")["max_drawdown"])
        st.dataframe(latest, use_container_width=True, hide_index=True)
        st.caption(f"Markdown reports: `{ROOT / 'backtest/reports'}`")

# --------------------------------------------------------------------------- Paper Trading
with tabs[4]:
    if paper.empty:
        st.info("No paper trades yet. Promote a strategy, then run `btc-lab paper`.")
    else:
        open_trades = paper[paper["status"] == "open"]
        closed_trades = paper[paper["status"] == "closed"]

        render_performance(closed_trades, STARTING_CASH)

        st.divider()
        o1, o2 = st.columns(2)
        o1.metric("Open Trades", len(open_trades))
        o2.metric("Open Unrealized PnL", f"${open_trades['pnl'].sum():,.0f}")

        if not closed_trades.empty:
            st.subheader("Exit Reasons")
            st.bar_chart(closed_trades["exit_reason"].value_counts())

        st.subheader("All Paper Trades")
        cols = [
            "id", "strategy_name", "status", "quantity", "price", "exit_price",
            "pnl", "stop_loss", "take_profit", "exit_reason", "created_at", "closed_at",
        ]
        st.dataframe(paper.sort_values("id", ascending=False)[cols], use_container_width=True, hide_index=True)
        st.caption(f"Logs: `{ROOT / 'paper_trading'}`")

# ----------------------------------------------------------------------- Active / Retired
with tabs[5]:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Active")
        st.dataframe(
            read_sql("select * from active_strategies order by promoted_at desc"),
            use_container_width=True, hide_index=True,
        )
    with col2:
        st.subheader("Retired")
        st.dataframe(
            read_sql("select * from retired_strategies order by retired_at desc"),
            use_container_width=True, hide_index=True,
        )

# ------------------------------------------------------------------------------- Research
with tabs[6]:
    st.dataframe(
        read_sql("select * from research_history order by collected_at desc"),
        use_container_width=True, hide_index=True,
    )
