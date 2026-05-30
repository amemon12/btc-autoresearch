from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime, timedelta

import pandas as pd
import yfinance as yf


INTERVALS = {"1d": "1d", "4h": "1h"}


def update_btc_data(market: str, timeframe: str, start: str, data_dir: Path) -> Path:
    data_dir.mkdir(parents=True, exist_ok=True)
    interval = INTERVALS[timeframe]
    effective_start = start
    if timeframe == "4h":
        effective_start = (datetime.now(UTC) - timedelta(days=729)).date().isoformat()
    frame = yf.download(market, start=effective_start, interval=interval, auto_adjust=True, progress=False)
    if frame.empty:
        raise RuntimeError(f"No data returned for {market} {timeframe}")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.rename(columns={column: str(column).lower() for column in frame.columns})
    if timeframe == "4h":
        frame = frame.resample("4h").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
    path = data_dir / f"{market.lower()}_{timeframe}.csv"
    frame.to_csv(path)
    return path


def load_price_data(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=[0], index_col=0)
    frame.columns = [column.lower() for column in frame.columns]
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Price data missing columns: {', '.join(sorted(missing))}")
    return frame.dropna()
