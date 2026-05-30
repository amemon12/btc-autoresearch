# RSI Starter 4H P10 20-50

- Source URL: local-grid-search
- Market: BTC/USD
- Timeframe: 4h

## Entry Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '<', 'value': 20}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '>', 'value': 50}}
```

## Risk
- Stop Loss: 1.00%
- Take Profit: 2.00%

## Backtest Results
- Total Return: 17.16%
- Max Drawdown: 9.54%
- Sharpe Ratio: 0.26
- Profit Factor: 1.47
- Trades: 35