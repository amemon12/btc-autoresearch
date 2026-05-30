import pytest

from btc_autoresearch.strategy_io import validate_strategy_dict


def test_valid_strategy_passes():
    validate_strategy_dict(
        {
            "name": "RSI",
            "market": "BTC/USD",
            "timeframe": "1d",
            "entry": {"rsi": {"operator": "<", "value": 30}},
            "exit": {"rsi": {"operator": ">", "value": 55}},
            "risk": {"stop_loss": 0.04, "take_profit": 0.08},
        }
    )


def test_strategy_requires_stop_loss():
    with pytest.raises(ValueError, match="stop_loss"):
        validate_strategy_dict(
            {
                "name": "No Stop",
                "market": "BTC/USD",
                "timeframe": "1d",
                "entry": {"rsi": {"operator": "<", "value": 30}},
                "exit": {"rsi": {"operator": ">", "value": 55}},
                "risk": {"take_profit": 0.08},
            }
        )
