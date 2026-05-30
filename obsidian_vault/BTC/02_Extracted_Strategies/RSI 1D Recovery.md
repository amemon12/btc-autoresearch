# RSI 1D Recovery

- Source URL: local-fallback
- Market: BTC/USD
- Timeframe: 1d

## Entry Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '<', 'value': 40}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '>', 'value': 65}}
```

## Risk
- Stop Loss: 6.00%
- Take Profit: 12.00%

## Backtest Results
- Total Return: -14.25%
- Max Drawdown: 25.73%
- Sharpe Ratio: -0.21
- Profit Factor: 0.90
- Trades: 182