# Bitcoin AutoResearch Strategy Lab

Local-first Bitcoin strategy research and paper-trading scaffold inspired by AutoResearch-style experiment loops.

## What is included

- Strategy YAML schema and validation
- BTC historical data updater via `yfinance` (1d back to `start_date`; 4h is limited to ~730 days by yfinance's intraday cap, so 4h backtests cover roughly the last 2 years, not 2018)
- Event-driven long-only backtester: next-bar-open fills, intrabar stop-loss/take-profit (low/high), and configurable fees + slippage
- Objective scoring and rejection gates
- Top-3 promotion; retirement driven by live paper-trade drawdown
- SQLite persistence
- Obsidian vault note/report generation
- Streamlit dashboard
- CLI loop for daily/weekly/monthly workflows

## Setup

```bash
cd "/Users/azimmemon/Documents/New project/btc-autoresearch"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
btc-lab init-db
btc-lab research
btc-lab data
btc-lab backtest
btc-lab promote
btc-lab paper
streamlit run dashboard/app.py
```

The dashboard sidebar has **Run Research**, **Run Full Cycle**, and **Open Obsidian Vault** buttons (these execute on the machine hosting the dashboard).

This project is paper-trading only. Live execution is intentionally out of scope.

## Tunable knobs (`config/config.yaml`)

- `backtest.fee_rate` / `backtest.slippage_rate` — per-side trading costs applied on entry and exit.
- `scoring.reject.{max_drawdown,profit_factor,trades}` — gate a strategy must clear to be promotable. The backtest is position-sized using the same formula as paper trading (`min(risk.account_risk_per_trade / stop_loss, risk.max_account_allocation_per_strategy)`), so backtested drawdown reflects how the strategy is actually traded.
- `risk.account_risk_per_trade` / `risk.max_account_allocation_per_strategy` — drive both paper position sizing and the backtest's position size (and therefore its drawdown).
- `retirement.max_paper_drawdown` / `retirement.min_closed_trades` — an active strategy is retired once its realized paper-trading equity draws down past the limit (after at least `min_closed_trades` closed trades).

`btc-lab run` executes the local AutoResearch loop:

```bash
btc-lab run
```

The research step uses Ollama `llama3.1` at `http://localhost:11434/api/generate`. If Ollama is not running or the model is unavailable, the command falls back to deterministic local candidates so the evaluation loop still works.

## Alpaca Paper Trading

The project defaults to Alpaca's paper endpoint:

```bash
export APCA_API_BASE_URL=https://paper-api.alpaca.markets
export APCA_API_KEY_ID=your_paper_key_id
export APCA_API_SECRET_KEY=your_paper_secret_key
```

`paper_trading.submit_orders` is `false` by default for safety. Set it to `true` in `config/config.yaml` only when you want `btc-lab paper` to submit market orders to Alpaca paper trading. When credentials are missing or submission is disabled, the workflow records local simulated paper orders instead.
