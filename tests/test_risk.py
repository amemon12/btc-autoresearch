import pytest

from btc_autoresearch.risk import validate_order


RISK = {
    "max_account_allocation_per_strategy": 0.25,
    "account_risk_per_trade": 0.01,
}


def test_risk_rejects_missing_stop():
    with pytest.raises(ValueError, match="stop loss"):
        validate_order(
            {
                "side": "buy",
                "notional": 1000,
                "account_equity": 10000,
                "entry_price": 100,
                "quantity": 1,
                "take_profit": 110,
            },
            RISK,
        )
