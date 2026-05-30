# RSI Mean Reversion

- Source URL: local_seed
- Market: BTC/USD
- Timeframe: 1d

## Entry Rules
```yaml
{'rsi': {'params': {'period': 14}, 'operator': '<', 'value': 30}}
```

## Exit Rules
```yaml
{'rsi': {'params': {'period': 14}, 'operator': '>', 'value': 55}}
```

## Risk
- Stop Loss: 4.00%
- Take Profit: 8.00%

## Backtest Results
- Total Return: -16.65%
- Max Drawdown: 17.84%
- Sharpe Ratio: -0.37
- Profit Factor: 0.69
- Trades: 73