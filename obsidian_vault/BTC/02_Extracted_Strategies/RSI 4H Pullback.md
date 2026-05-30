# RSI 4H Pullback

- Source URL: local-fallback
- Market: BTC/USD
- Timeframe: 4h

## Entry Rules
```yaml
{'rsi': {'params': {'period': 14}, 'operator': '<', 'value': 35}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 14}, 'operator': '>', 'value': 60}}
```

## Risk
- Stop Loss: 3.50%
- Take Profit: 7.00%

## Backtest Results
- Total Return: -8.43%
- Max Drawdown: 13.54%
- Sharpe Ratio: -0.18
- Profit Factor: 0.86
- Trades: 101