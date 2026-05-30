from btc_autoresearch.models import BacktestMetrics, Strategy
from btc_autoresearch.scoring import score_strategy


def test_scoring_rejects_high_drawdown():
    strategy = Strategy(
        name="Risky",
        market="BTC/USD",
        timeframe="1d",
        entry={"close": {"operator": ">", "value": 1}},
        exit={"close": {"operator": "<", "value": 1}},
        risk={"stop_loss": 0.05, "take_profit": 0.10},
    )
    metrics = BacktestMetrics("Risky", 0.4, 0.1, 0.30, 1.0, 0.5, 1.5, 40)
    config = {
        "scoring": {
            "weights": {
                "profit_factor": 0.35,
                "max_drawdown": 0.25,
                "sharpe_ratio": 0.20,
                "win_rate": 0.10,
                "trade_count_stability": 0.10,
            },
            "reject": {"max_drawdown": 0.25, "profit_factor": 1.2, "trades": 30},
        }
    }
    score = score_strategy(strategy, metrics, config)
    assert score.rejected is True
    assert "max_drawdown" in score.reasons
