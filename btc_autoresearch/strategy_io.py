from __future__ import annotations

from pathlib import Path
from typing import Any

from btc_autoresearch.models import Strategy
from btc_autoresearch.simple_yaml import dump_yaml, load_yaml

REQUIRED_FIELDS = ("name", "market", "timeframe", "entry", "exit", "risk")
VALID_OPERATORS = {"<", "<=", ">", ">=", "=="}


def load_strategy(path: str | Path) -> Strategy:
    raw = load_yaml(path)
    validate_strategy_dict(raw)
    risk = raw["risk"]
    return Strategy(
        name=raw["name"],
        market=raw["market"],
        timeframe=str(raw["timeframe"]).lower(),
        entry=raw["entry"],
        exit=raw["exit"],
        risk={
            "stop_loss": float(risk["stop_loss"]),
            "take_profit": float(risk["take_profit"]),
        },
        source=raw.get("source"),
    )


def load_strategies(directory: str | Path) -> list[Strategy]:
    return [load_strategy(path) for path in sorted(Path(directory).glob("*.yaml"))]


def load_all_strategies(directories: list[str | Path]) -> list[Strategy]:
    seen: set[str] = set()
    strategies: list[Strategy] = []
    for directory in directories:
        for strategy in load_strategies(directory):
            if strategy.name not in seen:
                strategies.append(strategy)
                seen.add(strategy.name)
    return strategies


def validate_strategy_dict(raw: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        raise ValueError(f"Strategy missing required fields: {', '.join(missing)}")
    if raw["timeframe"] not in ("1d", "4h"):
        raise ValueError("Strategy timeframe must be 1d or 4h")
    risk = raw.get("risk") or {}
    for key in ("stop_loss", "take_profit"):
        if key not in risk:
            raise ValueError(f"Strategy risk missing {key}")
        if float(risk[key]) <= 0:
            raise ValueError(f"Strategy {key} must be positive")
    if not raw["entry"]:
        raise ValueError("Strategy entry logic is required")
    if not raw["exit"]:
        raise ValueError("Strategy exit logic is required")
    validate_rule_operators(raw["entry"])
    validate_rule_operators(raw["exit"])


def validate_rule_operators(rule: dict[str, Any]) -> None:
    for indicator, spec in rule.items():
        operator = spec.get("operator")
        if operator not in VALID_OPERATORS:
            raise ValueError(
                f"Strategy indicator {indicator} has invalid operator {operator!r}; quote YAML operators like \">\""
            )


def write_strategy(path: str | Path, strategy: Strategy) -> None:
    payload = {
        "name": strategy.name,
        "market": strategy.market,
        "timeframe": strategy.timeframe,
        "source": strategy.source,
        "entry": strategy.entry,
        "exit": strategy.exit,
        "risk": strategy.risk,
    }
    Path(path).write_text(dump_yaml(payload), encoding="utf-8")
