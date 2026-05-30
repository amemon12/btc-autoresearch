# BTC 1D Momentum Filter

- Source URL: local-fallback
- Market: BTC/USD
- Timeframe: 1d

## Entry Rules
```yaml
{'close': {'operator': '>', 'other_indicator': 'sma', 'other_params': {'period': 200}}}
```

## Exit Rules
```yaml
{'close': {'operator': '<', 'other_indicator': 'sma', 'other_params': {'period': 100}}}
```

## Risk
- Stop Loss: 10.00%
- Take Profit: 24.00%

## Backtest Results
- Total Return: 28.83%
- Max Drawdown: 8.67%
- Sharpe Ratio: 0.59
- Profit Factor: 1.54
- Trades: 242