# RSI Starter 1D P10 25-50

- Source URL: local-grid-search
- Market: BTC/USD
- Timeframe: 1d

## Entry Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '<', 'value': 25}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 10}, 'operator': '>', 'value': 50}}
```

## Risk
- Stop Loss: 2.00%
- Take Profit: 4.00%

## Backtest Results
- Total Return: -8.60%
- Max Drawdown: 11.89%
- Sharpe Ratio: -0.39
- Profit Factor: 0.71
- Trades: 77