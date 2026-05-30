from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from btc_autoresearch.db import connect
from btc_autoresearch.models import Strategy
from btc_autoresearch.obsidian import FOLDERS, ensure_vault
from btc_autoresearch.strategy_io import write_strategy


OLLAMA_URL = "http://localhost:11434/api/generate"


@dataclass(frozen=True)
class ResearchCandidate:
    title: str
    source_url: str
    summary: str
    strategy: Strategy


def run_research_cycle(config) -> list[ResearchCandidate]:
    candidates = generate_candidates_with_llama31(config.values)
    if not candidates:
        candidates = deterministic_seed_candidates()
    write_research_outputs(config, candidates)
    return candidates


def generate_candidates_with_llama31(config_values: dict) -> list[ResearchCandidate]:
    prompt = build_llama_prompt(config_values)
    payload = {
        "model": config_values.get("llm", {}).get("model", "llama3.1"),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.35},
    }
    request = Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
        return []

    try:
        parsed = json.loads(result["response"])
        raw_candidates = parsed["strategies"]
    except (KeyError, TypeError, json.JSONDecodeError):
        return []

    candidates: list[ResearchCandidate] = []
    for raw in raw_candidates:
        try:
            strategy = Strategy(
                name=raw["name"],
                market="BTC/USD",
                timeframe=raw["timeframe"].lower(),
                entry=raw["entry"],
                exit=raw["exit"],
                risk={
                    "stop_loss": float(raw["risk"]["stop_loss"]),
                    "take_profit": float(raw["risk"]["take_profit"]),
                },
                source=raw.get("source_url", "llama3.1-local"),
            )
            candidates.append(
                ResearchCandidate(
                    title=raw["name"],
                    source_url=strategy.source or "llama3.1-local",
                    summary=raw.get("summary", "Generated locally by Llama 3.1."),
                    strategy=strategy,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return candidates[:5]


def build_llama_prompt(config_values: dict) -> str:
    return f"""
You are a local Bitcoin technical-analysis research agent.
Return JSON only, with this schema:
{{
  "strategies": [
    {{
      "name": "Strategy Name",
      "timeframe": "1d or 4h",
      "source_url": "llama3.1-local",
      "summary": "short research note",
      "entry": {{"rsi": {{"params": {{"period": 14}}, "operator": "<", "value": 30}}}},
      "exit": {{"rsi": {{"params": {{"period": 14}}, "operator": ">", "value": 55}}}},
      "risk": {{"stop_loss": 0.04, "take_profit": 0.08}}
    }}
  ]
}}

Constraints:
- Market: BTC/USD only.
- Timeframes allowed: {", ".join(config_values["timeframes"])}.
- Technical analysis only.
- Long-only, no leverage, no shorts, no averaging down.
- Every strategy must include entry, exit, stop_loss, take_profit.
- Use only supported indicators: rsi, sma, close.
- Operators must be one of <, <=, >, >=, ==.
- Prefer swing-trading strategies that may beat buy-and-hold with max drawdown below 20%.
Generate 3 distinct candidates.
""".strip()


def deterministic_seed_candidates() -> list[ResearchCandidate]:
    strategies = [
        Strategy(
            name="RSI 4H Pullback",
            market="BTC/USD",
            timeframe="4h",
            source="local-fallback",
            entry={"rsi": {"params": {"period": 14}, "operator": "<", "value": 35}},
            exit={"rsi": {"params": {"period": 14}, "operator": ">", "value": 60}},
            risk={"stop_loss": 0.035, "take_profit": 0.07},
        ),
        Strategy(
            name="BTC 1D Momentum Filter",
            market="BTC/USD",
            timeframe="1d",
            source="local-fallback",
            entry={"close": {"operator": ">", "other_indicator": "sma", "other_params": {"period": 200}}},
            exit={"close": {"operator": "<", "other_indicator": "sma", "other_params": {"period": 100}}},
            risk={"stop_loss": 0.10, "take_profit": 0.24},
        ),
        Strategy(
            name="RSI 1D Recovery",
            market="BTC/USD",
            timeframe="1d",
            source="local-fallback",
            entry={"rsi": {"params": {"period": 10}, "operator": "<", "value": 40}},
            exit={"rsi": {"params": {"period": 10}, "operator": ">", "value": 65}},
            risk={"stop_loss": 0.06, "take_profit": 0.12},
        ),
    ]
    return [
        ResearchCandidate(
            title=strategy.name,
            source_url=strategy.source or "local-fallback",
            summary="Fallback local strategy candidate used when Ollama Llama 3.1 is unavailable.",
            strategy=strategy,
        )
        for strategy in strategies
    ]


def write_research_outputs(config, candidates: list[ResearchCandidate]) -> None:
    ensure_vault(config.vault_dir)
    yaml_dir = config.root / "strategies/generated"
    yaml_dir.mkdir(parents=True, exist_ok=True)
    with connect(config.database_path) as conn:
        for candidate in candidates:
            note_path = config.vault_dir / FOLDERS["research"] / f"{candidate.title}.md"
            note_path.write_text(render_research_note(candidate), encoding="utf-8")
            yaml_path = yaml_dir / f"{candidate.strategy.slug}.yaml"
            write_strategy(yaml_path, candidate.strategy)
            conn.execute(
                "insert or ignore into research_history (source_url, title) values (?, ?)",
                (candidate.source_url, candidate.title),
            )


def render_research_note(candidate: ResearchCandidate) -> str:
    strategy = candidate.strategy
    return "\n".join(
        [
            f"# {candidate.title}",
            "",
            f"- Source URL: {candidate.source_url}",
            f"- Generator: {strategy.source or 'local'}",
            f"- Market: {strategy.market}",
            f"- Timeframe: {strategy.timeframe}",
            "",
            "## Summary",
            candidate.summary,
            "",
            "## Entry Rules",
            f"```json\n{json.dumps(strategy.entry, indent=2)}\n```",
            "",
            "## Exit Rules",
            f"```json\n{json.dumps(strategy.exit, indent=2)}\n```",
            "",
            "## Stop Loss",
            f"{strategy.risk['stop_loss']:.2%}",
            "",
            "## Take Profit",
            f"{strategy.risk['take_profit']:.2%}",
            "",
            "## Risks",
            "- Generated candidates must pass backtest and scoring gates before promotion.",
        ]
    )
