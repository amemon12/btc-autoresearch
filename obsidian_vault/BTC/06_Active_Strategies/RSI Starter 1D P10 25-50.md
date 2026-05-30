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
- Total Return: 122.40%
- Max Drawdown: 20.87%
- Sharpe Ratio: 0.51
- Profit Factor: 1.89
- Trades: 45