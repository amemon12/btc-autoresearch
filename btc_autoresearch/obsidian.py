from __future__ import annotations

from pathlib import Path

from btc_autoresearch.models import BacktestMetrics, Strategy


FOLDERS = {
    "research": "01_Strategy_Research",
    "extracted": "02_Extracted_Strategies",
    "reports": "03_Backtest_Reports",
    "paper": "04_Paper_Trading_Logs",
    "retired": "05_Retired_Strategies",
    "active": "06_Active_Strategies",
}


def ensure_vault(vault_dir: Path) -> None:
    for folder in FOLDERS.values():
        (vault_dir / folder).mkdir(parents=True, exist_ok=True)


def write_strategy_note(vault_dir: Path, strategy: Strategy, metrics: BacktestMetrics | None = None) -> Path:
    ensure_vault(vault_dir)
    path = vault_dir / FOLDERS["extracted"] / f"{strategy.name}.md"
    lines = [
        f"# {strategy.name}",
        "",
        f"- Source URL: {strategy.source or 'local'}",
        f"- Market: {strategy.market}",
        f"- Timeframe: {strategy.timeframe}",
        "",
        "## Entry Rules",
        f"```yaml\n{strategy.entry}\n```",
        "",
        "## Exit Rules",
        f"```yaml\n{strategy.exit}\n```",
        "",
        "## Risk",
        f"- Stop Loss: {strategy.risk['stop_loss']:.2%}",
        f"- Take Profit: {strategy.risk['take_profit']:.2%}",
        "",
        "## Backtest Results",
    ]
    if metrics:
        lines.extend(
            [
                f"- Total Return: {metrics.total_return:.2%}",
                f"- Max Drawdown: {metrics.max_drawdown:.2%}",
                f"- Sharpe Ratio: {metrics.sharpe_ratio:.2f}",
                f"- Profit Factor: {metrics.profit_factor:.2f}",
                f"- Trades: {metrics.trades}",
            ]
        )
    else:
        lines.append("- Pending")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def move_strategy_note(vault_dir: Path, strategy_name: str, destination_key: str) -> Path:
    ensure_vault(vault_dir)
    destination = vault_dir / FOLDERS[destination_key] / f"{strategy_name}.md"
    source_candidates = [vault_dir / folder / f"{strategy_name}.md" for folder in FOLDERS.values()]
    for source in source_candidates:
        if source.exists():
            destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            if source != destination:
                source.unlink()
            return destination
    destination.write_text(f"# {strategy_name}\n\nMoved to {destination_key}.", encoding="utf-8")
    return destination
