# RSI 1D Recovery

- Source URL: local-fallback
- Generator: local-fallback
- Market: BTC/USD
- Timeframe: 1d

## Summary
Fallback local strategy candidate used when Ollama Llama 3.1 is unavailable.

## Entry Rules
```json
{
  "rsi": {
    "params": {
      "period": 10
    },
    "operator": "<",
    "value": 40
  }
}
```

## Exit Rules
```json
{
  "rsi": {
    "params": {
      "period": 10
    },
    "operator": ">",
    "value": 65
  }
}
```

## Stop Loss
6.00%

## Take Profit
12.00%

## Risks
- Generated candidates must pass backtest and scoring gates before promotion.