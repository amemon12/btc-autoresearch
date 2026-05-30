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
- Total Return: 32.11%
- Max Drawdown: 11.35%
- Sharpe Ratio: 0.40
- Profit Factor: 1.74
- Trades: 40