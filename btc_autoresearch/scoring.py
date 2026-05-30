from __future__ import annotations

from btc_autoresearch.models import BacktestMetrics, Strategy, StrategyScore


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_strategy(strategy: Strategy, metrics: BacktestMetrics, config: dict) -> StrategyScore:
    reject = config["scoring"]["reject"]
    reasons: list[str] = []
    if metrics.max_drawdown > reject["max_drawdown"]:
        reasons.append("max_drawdown")
    if metrics.profit_factor < reject["profit_factor"]:
        reasons.append("profit_factor")
    if metrics.trades < reject["trades"]:
        reasons.append("trades")
    if not strategy.risk.get("stop_loss"):
        reasons.append("missing_stop_loss")
    if not strategy.exit:
        reasons.append("missing_exit_logic")

    weights = config["scoring"]["weights"]
    components = {
        "profit_factor": clamp((metrics.profit_factor - 1.0) / 2.0),
        "max_drawdown": clamp(1 - metrics.max_drawdown / 0.25),
        "sharpe_ratio": clamp(metrics.sharpe_ratio / 2.0),
        "win_rate": clamp(metrics.win_rate),
        "trade_count_stability": clamp(metrics.trades / 100),
    }
    score = sum(components[key] * weights[key] for key in weights) * 100
    return StrategyScore(strategy.name, round(score, 2), bool(reasons), reasons)
