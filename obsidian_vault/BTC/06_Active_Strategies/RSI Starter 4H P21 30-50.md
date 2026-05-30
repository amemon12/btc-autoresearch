# RSI Starter 4H P21 30-50

- Source URL: local-grid-search
- Market: BTC/USD
- Timeframe: 4h

## Entry Rules
```yaml
{'rsi': {'params': {'period': 21}, 'operator': '<', 'value': 30}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 21}, 'operator': '>', 'value': 50}}
```

## Risk
- Stop Loss: 1.00%
- Take Profit: 2.00%

## Backtest Results
- Total Return: -2.42%
- Max Drawdown: 4.85%
- Sharpe Ratio: -0.19
- Profit Factor: 0.80
- Trades: 66