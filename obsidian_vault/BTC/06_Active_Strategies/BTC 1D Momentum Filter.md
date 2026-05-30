# BTC 1D Momentum Filter

- Source URL: local-fallback
- Generator: local-fallback
- Market: BTC/USD
- Timeframe: 1d

## Summary
Fallback local strategy candidate used when Ollama Llama 3.1 is unavailable.

## Entry Rules
```json
{
  "close": {
    "operator": ">",
    "other_indicator": "sma",
    "other_params": {
      "period": 200
    }
  }
}
```

## Exit Rules
```json
{
  "close": {
    "operator": "<",
    "other_indicator": "sma",
    "other_params": {
      "period": 100
    }
  }
}
```

## Stop Loss
10.00%

## Take Profit
24.00%

## Risks
- Generated candidates must pass backtest and scoring gates before promotion.