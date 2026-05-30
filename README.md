# ₿ Bitcoin AutoResearch Strategy Lab

A local-first lab that **researches, backtests, scores, promotes, paper-trades, and retires** BTC/USD technical-analysis swing strategies — an AutoResearch-style experiment loop you run on your own machine.

> **Paper trading only.** No live execution, no leverage, no shorting. The evaluator is the source of truth: a strategy is never trusted until it passes schema validation, a realistic backtest, scoring gates, and promotion.

---

## The loop

```
research ──▶ backtest ──▶ score ──▶ promote ──▶ paper-trade ──▶ retire
   ▲                                                                │
   └────────────────────────  repeat on a timer  ──────────────────┘
```

1. **Research** — generate candidate strategies (Ollama `llama3.1`, with a deterministic fallback when it's offline) and write notes to an Obsidian vault.
2. **Backtest** — event-driven, cost-aware, position-sized simulation over historical BTC data.
3. **Score** — objective scoring with hard rejection gates (drawdown, profit factor, trade count).
4. **Promote** — the top strategies that clear every gate become active.
5. **Paper-trade** — active strategies open sized paper positions that close on stop / target / exit signal and can re-enter.
6. **Retire** — an active strategy is retired once its live paper-trading drawdown breaches the limit.

## Features

- **Strategy contract** — every strategy is a validated YAML with entry, exit, stop-loss, take-profit, and timeframe.
- **Honest backtester** — next-bar-open fills (no lookahead), **intrabar** stop-loss / take-profit against bar high/low, configurable fees + slippage, and position sizing that matches how the strategy is actually paper-traded (so backtest drawdown ≈ paper drawdown).
- **Paper-trade lifecycle** — open, mark-to-market, close on stop/target/exit, record realized PnL, re-enter.
- **Persistence** — SQLite for strategies, backtests, scores, paper trades, active/retired sets, and research history.
- **Obsidian vault** — auto-generated research notes, backtest summaries, and trade logs.
- **Streamlit dashboard** — KPI overview, per-strategy drill-down with cost-adjusted equity curves, a TradingView-style performance panel, and a **start/stop AutoResearch loop** with a live log.
- **Optional Alpaca** — submit orders to Alpaca's *paper* endpoint, off by default.

## Quickstart

```bash
git clone https://github.com/amemon12/btc-autoresearch.git
cd btc-autoresearch
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Run the pipeline step by step:

```bash
btc-lab init-db      # create the SQLite database and Obsidian vault
btc-lab research     # generate candidate strategies (Ollama or fallback)
btc-lab data         # fetch BTC price history via yfinance
btc-lab backtest     # backtest + score every candidate
btc-lab promote      # promote the top gate-passing strategies
btc-lab paper        # open/close paper trades for active strategies
```

Or run it all at once, or continuously:

```bash
btc-lab run                          # one full pass
btc-lab loop --sleep-minutes 60      # research→…→paper, sleep, repeat (Ctrl-C to stop)
btc-lab loop --offline               # same, using cached data (no network)
```

> **Note on data range:** 1d history goes back to `start_date` (default 2018). yfinance caps intraday data at ~730 days, so **4h backtests cover roughly the last 2 years**, not 2018.

## Dashboard

```bash
streamlit run dashboard/app.py
```

The sidebar provides:

- **Run Research once** — generate candidates and open the Obsidian vault.
- **AutoResearch Loop** — Start/Stop the research loop with a configurable cycle interval and a live log tail (runs on the machine hosting the dashboard).
- **Open Obsidian Vault** — open the vault folder in your file manager.

## Configuration (`config/config.yaml`)

| Key | Meaning |
|---|---|
| `backtest.fee_rate` / `backtest.slippage_rate` | Per-side trading costs applied on entry and exit. |
| `risk.account_risk_per_trade` / `risk.max_account_allocation_per_strategy` | Position sizing for both paper trading **and** the backtest: `fraction = min(account_risk / stop_loss, max_allocation)`. Idle capital sits in cash. |
| `scoring.reject.{max_drawdown, profit_factor, trades}` | Hard gates a strategy must clear to be promotable. Because the backtest is position-sized, `max_drawdown` reflects real traded drawdown. |
| `scoring.weights.*` | Weights for the composite score (profit factor, drawdown, sharpe, win rate, trade-count stability). |
| `retirement.max_paper_drawdown` / `retirement.min_closed_trades` | Retire an active strategy once realized paper drawdown exceeds the limit (after at least N closed trades). |
| `active_strategy_limit` | How many strategies can be active at once. |

## How the backtester works

For each bar:

- An entry/exit **signal is observed on the close** and **filled at the next bar's open** — no same-bar lookahead.
- While in a position, **stop-loss and take-profit are checked intrabar** against the bar's low/high. If both are touched in one bar, the **stop fills first** (pessimistic).
- Fees and slippage are charged on the traded notional at entry and exit.
- Each position is `min(account_risk / stop_loss, max_allocation)` of current equity; the rest is cash. This is the same sizing the paper layer uses, so backtested drawdown is comparable to live paper drawdown.

## Alpaca paper trading (optional)

```bash
export APCA_API_BASE_URL=https://paper-api.alpaca.markets
export APCA_API_KEY_ID=your_paper_key_id
export APCA_API_SECRET_KEY=your_paper_secret_key
```

`paper_trading.submit_orders` is `false` by default. Set it to `true` only when you want `btc-lab paper` to submit market orders to Alpaca **paper** trading. When credentials are missing or submission is disabled, orders are simulated and recorded locally.

## Testing

```bash
pytest -q
```

Covers scoring gates, risk validation, strategy validation, the backtester's execution model (next-bar fill, intrabar stop, cost impact), and the paper-trade lifecycle (exit resolution, drawdown tracking).

## Project structure

```
btc_autoresearch/      core package (cli, backtester, scoring, paper, promotion, …)
config/config.yaml     all tunable knobs
dashboard/app.py       Streamlit dashboard
strategies/            seed (yaml/) and generated (generated/) strategies
tests/                 pytest suite
obsidian_vault/        generated research notes, reports, and trade logs
```

## Disclaimer

This project is for research and education. It is **not** financial advice, and it does not place real-money trades. Backtested and paper results do not predict live performance.
