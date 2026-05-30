# SMA Trend Following

- Source URL: local_seed
- Market: BTC/USD
- Timeframe: 1d

## Entry Rules
```yaml
{'close': {'operator': '>', 'other_indicator': 'sma', 'other_params': {'period': 100}}}
```

## Exit Rules
```yaml
{'close': {'operator': '<', 'other_indicator': 'sma', 'other_params': {'period': 50}}}
```

## Risk
- Stop Loss: 8.00%
- Take Profit: 20.00%

## Backtest Results
- Total Return: 29.71%
- Max Drawdown: 7.86%
- Sharpe Ratio: 0.50
- Profit Factor: 1.35
- Trades: 362