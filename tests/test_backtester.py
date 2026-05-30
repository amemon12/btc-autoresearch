import pandas as pd

from btc_autoresearch.backtester import run_backtest, simulate
from btc_autoresearch.models import Strategy


def _frame(rows: list[tuple]) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=len(rows), freq="D")
    return pd.DataFrame(rows, columns=["open", "high", "low", "close", "volume"], index=index)


def _always_in_strategy(stop_loss: float, take_profit: float) -> Strategy:
    # close > 0 is always true, so entry fires every bar; exit never fires on its own.
    return Strategy(
        name="T",
        market="BTC/USD",
        timeframe="1d",
        entry={"close": {"operator": ">", "value": 0}},
        exit={"close": {"operator": "<", "value": 0}},
        risk={"stop_loss": stop_loss, "take_profit": take_profit},
    )


def test_entry_fills_next_bar_not_signal_bar():
    # Signal fires on bar 0's close; fill must happen at bar 1's open, not bar 0's close.
    frame = _frame([(100, 100, 100, 100, 1), (110, 110, 110, 110, 1), (110, 110, 110, 110, 1)])
    result = simulate(_always_in_strategy(0.5, 0.5), frame, {"fee_rate": 0, "slippage_rate": 0})
    # Entered at bar 1 open (110); bar 1 close is 110 -> no gain captured from the 100->110 move.
    assert result.equity_curve.iloc[1] == 1.0


def test_intrabar_stop_caps_loss_at_stop_not_close():
    # Enter at bar 1 open=100, then bar 2 dips to low=80 (below 5% stop) but closes at 99.
    frame = _frame([(100, 100, 100, 100, 1), (100, 100, 100, 100, 1), (99, 100, 80, 99, 1)])
    result = simulate(_always_in_strategy(0.05, 1.0), frame, {"fee_rate": 0, "slippage_rate": 0})
    # Stop at 95 must trigger on the low; trade return ~ -5%, NOT the -1% close move.
    assert result.trade_returns
    assert result.trade_returns[0] == pytest_approx(-0.05)


def test_costs_reduce_returns():
    frame = _frame([(100, 100, 100, 100, 1)] * 2 + [(100, 130, 100, 130, 1), (130, 130, 130, 130, 1)])
    strat = _always_in_strategy(0.5, 0.2)  # 20% take-profit triggers on the 130 high
    free = run_backtest(strat, frame, {"fee_rate": 0, "slippage_rate": 0})
    costed = run_backtest(strat, frame, {"fee_rate": 0.01, "slippage_rate": 0.01})
    assert costed.total_return < free.total_return


def pytest_approx(value, tol=1e-9):
    class _Approx:
        def __eq__(self, other):
            return abs(other - value) <= tol

    return _Approx()
