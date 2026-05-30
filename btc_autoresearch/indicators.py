from __future__ import annotations

import pandas as pd


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def indicator_series(frame: pd.DataFrame, name: str, params: dict | None = None) -> pd.Series:
    params = params or {}
    normalized = name.lower()
    if normalized == "close":
        return frame["close"]
    if normalized == "rsi":
        return rsi(frame["close"], int(params.get("period", 14)))
    if normalized == "sma":
        return sma(frame["close"], int(params.get("period", 50)))
    raise ValueError(f"Unsupported indicator: {name}")


def compare(series: pd.Series, operator: str, value: float | pd.Series) -> pd.Series:
    if operator == "<":
        return series < value
    if operator == "<=":
        return series <= value
    if operator == ">":
        return series > value
    if operator == ">=":
        return series >= value
    if operator == "==":
        return series == value
    raise ValueError(f"Unsupported operator: {operator}")
