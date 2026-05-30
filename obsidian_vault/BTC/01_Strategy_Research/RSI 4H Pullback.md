# RSI 4H Pullback

- Source URL: local-fallback
- Generator: local-fallback
- Market: BTC/USD
- Timeframe: 4h

## Summary
Fallback local strategy candidate used when Ollama Llama 3.1 is unavailable.

## Entry Rules
```json
{
  "rsi": {
    "params": {
      "period": 14
    },
    "operator": "<",
    "value": 35
  }
}
```

## Exit Rules
```json
{
  "rsi": {
    "params": {
      "period": 14
    },
    "operator": ">",
    "value": 60
  }
}
```

## Stop Loss
3.50%

## Take Profit
7.00%

## Risks
- Generated candidates must pass backtest and scoring gates before promotion.