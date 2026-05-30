from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from btc_autoresearch.indicators import compare, indicator_series
from btc_autoresearch.models import BacktestMetrics, Strategy


# Defaults are intentionally conservative; override via config.yaml -> backtest.
DEFAULT_FEE_RATE = 0.001
DEFAULT_SLIPPAGE_RATE = 0.0005
TRADING_DAYS_PER_YEAR = 252
NO_LOSS_PROFIT_FACTOR = 99.0


def signal_from_rule(frame: pd.DataFrame, rule: dict) -> pd.Series:
    conditions: list[pd.Series] = []
    for indicator, spec in rule.items():
        left = indicator_series(frame, indicator, spec.get("params"))
        if "other_indicator" in spec:
            value = indicator_series(frame, spec["other_indicator"], spec.get("other_params"))
        else:
            value = float(spec["value"])
        conditions.append(compare(left, spec["operator"], value))
    if not conditions:
        raise ValueError("Rule must contain at least one condition")
    combined = conditions[0]
    for condition in conditions[1:]:
        combined = combined & condition
    return combined.fillna(False)


@dataclass(frozen=True)
class SimulationResult:
    equity_curve: pd.Series
    trade_returns: list[float]


def resolve_costs(costs: dict | None) -> tuple[float, float]:
    costs = costs or {}
    fee = float(costs.get("fee_rate", DEFAULT_FEE_RATE))
    slippage = float(costs.get("slippage_rate", DEFAULT_SLIPPAGE_RATE))
    return fee, slippage


def position_fraction(stop_loss: float, sizing: dict | None) -> float:
    """Fraction of equity allocated to a position.

    Mirrors paper.build_paper_order: min(account_risk / stop_loss, max_allocation). When
    no sizing config is supplied the position is all-in (fraction 1.0), which is used by
    the mechanics unit tests. The paper layer's 0.999 rounding buffer is intentionally
    omitted here as it is immaterial to drawdown.
    """
    if not sizing:
        return 1.0
    max_allocation = float(sizing.get("max_account_allocation_per_strategy", 1.0))
    account_risk = float(sizing.get("account_risk_per_trade", max_allocation))
    if stop_loss <= 0:
        return max_allocation
    return min(account_risk / stop_loss, max_allocation)


def simulate(
    strategy: Strategy, frame: pd.DataFrame, costs: dict | None = None, sizing: dict | None = None
) -> SimulationResult:
    """Event-driven, long-only simulation with explicit cash/units accounting.

    Execution model:
    - Entry/exit signals are observed on a bar's close and filled at the NEXT bar's open
      (no same-bar lookahead).
    - Stop-loss and take-profit are evaluated intrabar against that bar's low/high.
    - When both the stop and the target are touched in the same bar, the STOP fills first
      (pessimistic tie-break).
    - Fees and slippage are charged on the traded notional at entry and exit.
    - Position size is `position_fraction(stop_loss, sizing)` of current equity; the
      remainder stays in cash earning nothing. With no sizing config this is all-in,
      matching how the strategy is paper-traded so backtest drawdown == paper drawdown.
    """
    fee, slippage = resolve_costs(costs)
    stop_loss = float(strategy.risk["stop_loss"])
    take_profit = float(strategy.risk["take_profit"])
    fraction = position_fraction(stop_loss, sizing)

    entry_signal = signal_from_rule(frame, strategy.entry)
    exit_signal = signal_from_rule(frame, strategy.exit)
    open_ = frame["open"].to_numpy(dtype=float)
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)

    cash = 1.0
    units = 0.0
    curve = [1.0]
    in_position = False
    pending_entry = False
    entry_equity = 1.0
    stop_price = 0.0
    target_price = 0.0
    trade_returns: list[float] = []

    def close_position(fill_price: float) -> None:
        nonlocal cash, units, in_position
        proceeds = units * fill_price * (1 - slippage)
        cash += proceeds - proceeds * fee
        units = 0.0
        in_position = False
        trade_returns.append(cash / entry_equity - 1)

    for i in range(1, len(frame)):
        bar_open, bar_high, bar_low, bar_close = open_[i], high[i], low[i], close[i]

        if not in_position and pending_entry:
            entry_equity = cash
            entry_fill = bar_open * (1 + slippage)
            notional = fraction * cash
            units = notional / entry_fill
            cash -= notional + notional * fee
            stop_price = entry_fill * (1 - stop_loss)
            target_price = entry_fill * (1 + take_profit)
            in_position = True
            pending_entry = False

        if in_position:
            if bar_low <= stop_price:
                close_position(min(bar_open, stop_price))
            elif bar_high >= target_price:
                close_position(max(bar_open, target_price))
            elif bool(exit_signal.iloc[i]):
                close_position(bar_close)

        if not in_position and bool(entry_signal.iloc[i]):
            pending_entry = True

        curve.append(cash + units * bar_close)

    equity_series = pd.Series(curve, index=frame.index[: len(curve)])
    return SimulationResult(equity_curve=equity_series, trade_returns=trade_returns)


def backtest_equity_curve(
    strategy: Strategy, frame: pd.DataFrame, costs: dict | None = None, sizing: dict | None = None
) -> pd.Series:
    return simulate(strategy, frame, costs, sizing).equity_curve


def run_backtest(
    strategy: Strategy, frame: pd.DataFrame, costs: dict | None = None, sizing: dict | None = None
) -> BacktestMetrics:
    result = simulate(strategy, frame, costs, sizing)
    equity_series = result.equity_curve
    trade_returns = result.trade_returns

    returns = equity_series.pct_change().dropna()
    total_return = float(equity_series.iloc[-1] - 1)
    years = max((equity_series.index[-1] - equity_series.index[0]).days / 365.25, 1 / 365.25)
    annualized_return = float(equity_series.iloc[-1] ** (1 / years) - 1)
    drawdown = equity_series / equity_series.cummax() - 1
    sharpe = float(np.sqrt(TRADING_DAYS_PER_YEAR) * returns.mean() / returns.std()) if returns.std() else 0.0
    wins = [ret for ret in trade_returns if ret > 0]
    losses = [ret for ret in trade_returns if ret < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = float(gross_profit / gross_loss) if gross_loss else (NO_LOSS_PROFIT_FACTOR if wins else 0.0)
    win_rate = float(len(wins) / len(trade_returns)) if trade_returns else 0.0
    return BacktestMetrics(
        strategy_name=strategy.name,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=float(abs(drawdown.min())),
        sharpe_ratio=sharpe,
        win_rate=win_rate,
        profit_factor=profit_factor,
        trades=len(trade_returns),
    )


def write_backtest_outputs(metrics: BacktestMetrics, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = metrics.strategy_name.lower().replace(" ", "-")
    json_path = output_dir / f"{slug}.json"
    md_path = output_dir / f"{slug}.md"
    json_path.write_text(json.dumps(metrics.__dict__, indent=2), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# {metrics.strategy_name} Backtest",
                "",
                f"- Total Return: {metrics.total_return:.2%}",
                f"- Annualized Return: {metrics.annualized_return:.2%}",
                f"- Max Drawdown: {metrics.max_drawdown:.2%}",
                f"- Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
                f"- Win Rate: {metrics.win_rate:.2%}",
                f"- Profit Factor: {metrics.profit_factor:.2f}",
                f"- Trades: {metrics.trades}",
            ]
        ),
        encoding="utf-8",
    )
    return json_path, md_path
