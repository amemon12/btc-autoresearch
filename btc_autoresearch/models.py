from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Strategy:
    name: str
    market: str
    timeframe: str
    entry: dict[str, Any]
    exit: dict[str, Any]
    risk: dict[str, float]
    source: str | None = None

    @property
    def slug(self) -> str:
        return self.name.lower().replace("/", "-").replace(" ", "-")


@dataclass(frozen=True)
class BacktestMetrics:
    strategy_name: str
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    trades: int


@dataclass(frozen=True)
class StrategyScore:
    strategy_name: str
    score: float
    rejected: bool
    reasons: list[str]
