from __future__ import annotations

import argparse
import time

from btc_autoresearch.config import load_config
from btc_autoresearch.db import connect, init_db
from btc_autoresearch.obsidian import ensure_vault, write_strategy_note
from btc_autoresearch.promotion import promote_top_strategies, retire_failing_strategies
from btc_autoresearch.reporting import (
    append_log,
    write_active_report,
    write_backlog_report,
    write_backtest_summary,
    write_paper_trade_logs,
)
from btc_autoresearch.strategy_io import load_all_strategies, load_strategies


def cmd_init_db(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    ensure_vault(config.vault_dir)
    init_db(config.database_path)
    print(f"Initialized {config.database_path}")


def cmd_data(args: argparse.Namespace) -> None:
    from btc_autoresearch.data import update_btc_data

    config = load_config(args.config)
    for timeframe in config.values["timeframes"]:
        path = update_btc_data(config.values["market"], timeframe, config.values["start_date"], config.data_dir)
        print(f"Updated {path}")


def cmd_research(args: argparse.Namespace) -> None:
    from btc_autoresearch.research_agent import run_research_cycle

    config = load_config(args.config)
    init_db(config.database_path)
    candidates = run_research_cycle(config)
    generator = config.values.get("llm", {}).get("model", "llama3.1")
    print(f"Research generated {len(candidates)} candidates via {generator} or local fallback")
    for candidate in candidates:
        print(f"- {candidate.title} ({candidate.strategy.timeframe})")


def cmd_backtest(args: argparse.Namespace) -> None:
    from btc_autoresearch.backtester import run_backtest, write_backtest_outputs
    from btc_autoresearch.data import load_price_data
    from btc_autoresearch.db import save_backtest, save_score
    from btc_autoresearch.scoring import score_strategy

    config = load_config(args.config)
    init_db(config.database_path)
    costs = config.values.get("backtest", {})
    sizing = config.values.get("risk", {})
    strategies = load_all_strategies([config.root / "strategies/generated", config.root / "strategies/yaml"])
    with connect(config.database_path) as conn:
        for strategy in strategies:
            data_path = config.data_dir / f"{config.values['market'].lower()}_{strategy.timeframe}.csv"
            frame = load_price_data(data_path)
            metrics = run_backtest(strategy, frame, costs, sizing)
            score = score_strategy(strategy, metrics, config.values)
            save_backtest(conn, metrics)
            save_score(conn, score)
            write_backtest_outputs(metrics, config.root / "backtest/reports")
            write_strategy_note(config.vault_dir, strategy, metrics)
            append_log(config.root, f"backtest {strategy.name} score={score.score} rejected={score.rejected}")
            print(f"{strategy.name}: score={score.score} rejected={score.rejected}")
        backlog = write_backlog_report(conn, config.vault_dir)
        summary = write_backtest_summary(conn, config.vault_dir, config.root / "backtest/reports")
        print(f"Wrote backlog report: {backlog}")
        print(f"Wrote backtest summary: {summary}")


def cmd_promote(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    with connect(config.database_path) as conn:
        promoted = promote_top_strategies(conn, config)
        active = write_active_report(conn, config.vault_dir)
        print("Promoted:", ", ".join(promoted) or "none")
        print(f"Wrote active report: {active}")


def cmd_retire(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    with connect(config.database_path) as conn:
        retired = retire_failing_strategies(conn, config)
        print("Retired:", ", ".join(retired) or "none")


def cmd_paper(args: argparse.Namespace) -> None:
    from btc_autoresearch.data import load_price_data
    from btc_autoresearch.paper import (
        build_paper_order,
        close_open_trades,
        has_open_paper_trade,
        maybe_submit_alpaca_order,
        save_paper_order,
    )

    config = load_config(args.config)
    all_strategies = load_all_strategies([config.root / "strategies/generated", config.root / "strategies/yaml"])
    strategies = {strategy.name: strategy for strategy in all_strategies}
    with connect(config.database_path) as conn:
        closed = close_open_trades(conn, strategies, config.values["market"], config.data_dir)
        for closure in closed:
            append_log(
                config.root,
                f"paper close {closure['strategy_name']} {closure['reason']} pnl={closure['realized_pnl']:.2f}",
            )
            print(f"{closure['strategy_name']}: closed ({closure['reason']}) realized_pnl={closure['realized_pnl']:.2f}")
        rows = conn.execute("select strategy_name from active_strategies order by promoted_at desc").fetchall()
        for (name,) in rows:
            strategy = strategies.get(name)
            if strategy is None:
                print(f"Skipping {name}: no YAML found")
                continue
            if has_open_paper_trade(conn, strategy.name):
                print(f"{strategy.name}: existing open paper trade, skipped duplicate entry")
                continue
            data_path = config.data_dir / f"{config.values['market'].lower()}_{strategy.timeframe}.csv"
            frame = load_price_data(data_path)
            price = float(frame["close"].iloc[-1])
            equity = float(config.values["paper_trading"]["starting_cash"])
            order = build_paper_order(strategy, price, equity, config.values["risk"])
            response = maybe_submit_alpaca_order(strategy, order, config.values)
            save_paper_order(conn, order)
            mode = "submitted to Alpaca paper" if response else "recorded locally"
            append_log(config.root, f"paper {strategy.name} {mode} qty={order['quantity']:.8f} price={price:.2f}")
            print(f"{strategy.name}: {mode}, qty={order['quantity']:.8f}, price={price:.2f}")
        latest_price = None
        data_path = config.data_dir / f"{config.values['market'].lower()}_4h.csv"
        if data_path.exists():
            latest_price = float(load_price_data(data_path)["close"].iloc[-1])
        vault_log, csv_log = write_paper_trade_logs(conn, config.vault_dir, config.root / "paper_trading", latest_price)
        print(f"Wrote paper trade log: {vault_log}")
        print(f"Wrote paper trade CSV: {csv_log}")


def cmd_run(args: argparse.Namespace) -> None:
    steps = [cmd_init_db, cmd_research, cmd_data, cmd_backtest, cmd_promote, cmd_retire, cmd_paper]
    for step in steps:
        print(f"\n== {step.__name__.replace('cmd_', '').replace('_', ' ')} ==")
        step(args)


def cmd_loop(args: argparse.Namespace) -> None:
    steps = [cmd_init_db, cmd_research, cmd_backtest, cmd_promote, cmd_retire, cmd_paper]
    if not args.offline:
        steps.insert(2, cmd_data)
    cycle = 1
    while True:
        print(f"\n######## AutoResearch cycle {cycle} ########")
        for step in steps:
            print(f"\n== {step.__name__.replace('cmd_', '').replace('_', ' ')} ==")
            try:
                step(args)
            except Exception as exc:
                print(f"{step.__name__.replace('cmd_', '')} failed: {exc}")
        print(f"Sleeping for {args.sleep_minutes} minute(s). Press Ctrl-C to stop.")
        time.sleep(args.sleep_minutes * 60)
        cycle += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Bitcoin AutoResearch Strategy Lab")
    parser.add_argument("--config", default="config/config.yaml")
    subparsers = parser.add_subparsers(required=True)
    commands = {
        "init-db": cmd_init_db,
        "research": cmd_research,
        "data": cmd_data,
        "backtest": cmd_backtest,
        "promote": cmd_promote,
        "retire": cmd_retire,
        "paper": cmd_paper,
        "run": cmd_run,
        "loop": cmd_loop,
    }
    for name, handler in commands.items():
        subparser = subparsers.add_parser(name)
        if name == "loop":
            subparser.add_argument("--sleep-minutes", type=int, default=60)
            subparser.add_argument("--offline", action="store_true", help="Use cached market data and skip refreshes")
        subparser.set_defaults(func=handler)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
