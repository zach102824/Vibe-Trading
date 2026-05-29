---
name: us-mega-cap-jump-screener
description: US mega-cap 30-day jump screener — rank the top 50 US-listed stocks by live market cap using yfinance price momentum, breakout proximity, volume surge, and volatility-compression signals.
category: analysis
---
# US Mega-Cap 30-Day Jump Screener

## Purpose

Use this skill when the user asks for "the stock most likely to jump in the next 30 days" among the largest US stocks.

The workflow produces a ranked research watchlist, not a guaranteed forecast or live trading instruction. It is designed to answer:

> Among the top 50 US-listed stocks by current market value, which names have the strongest short-term setup for a possible 30-day upside jump?

## Quick Start

From the repository root:

```bash
python agent/src/skills/us-mega-cap-jump-screener/scripts/screen_us_mega_cap_jump.py --top-n 10
```

Suggested agent prompt:

```text
Load the us-mega-cap-jump-screener skill. Rank the top 50 US-listed stocks by market cap for the strongest probability of a 30-day upside jump. Use yfinance data, show the top 10, explain the score drivers, and include risk/catalyst checks before naming a preferred watchlist candidate.
```

## Data Sources

| Need | Source | Notes |
|------|--------|-------|
| Market cap ranking | `yfinance.Ticker(...).fast_info` with `Ticker.info` fallback | Used to select the live top 50 from a larger mega-cap candidate list. |
| Daily OHLCV | `yfinance.download` | Uses adjusted daily bars where available. |
| Company metadata | `Ticker.info` | Company name, sector, beta, recommendation, and target price when Yahoo exposes them. |
| Optional catalysts | `web_search`, SEC/earnings sources | Use after the quantitative rank, especially for top 3 names. |

No paid market-data key is required for this workflow.

## Ranking Logic

The script ranks only names that pass these gates:

1. It is inside the live top 50 by available market cap.
2. At least 80 daily bars are available.
3. Latest close and volume are valid.

Then it computes cross-sectional percentiles:

| Signal | Weight | Reason |
|--------|--------|--------|
| 20-day return | 30% | Recent strength can identify institutional accumulation. |
| 60-day return | 20% | Medium-term trend confirmation. |
| Volume surge | 15% | Breakouts are more credible when current volume is above the recent average. |
| 60-day high proximity | 15% | Stocks close to recent highs need less resistance clearance. |
| Volatility compression | 10% | Lower current volatility vs. prior volatility can precede expansion. |
| Close vs. 50-day average | 10% | Keeps the rank biased toward constructive trend structure. |

Interpretation:

- `score` is a 0-100 relative setup score within the screened universe.
- `distance_60d_high_pct` near `0` means the stock is close to a breakout level.
- `volume_surge_pct` above `0` means latest volume is above its 20-day average.
- `vol_compression` above `0` means 20-day volatility is below 60-day volatility.

## Output Template

Use this answer shape:

```markdown
## US Mega-Cap 30-Day Jump Watchlist

Method: live top 50 by market cap, then momentum/breakout/volume/compression scoring via yfinance. This is research, not financial advice.

| Rank | Symbol | Company | Score | Market Cap | 20D Ret | 60D Ret | Vol Surge | Dist. 60D High | Why it screened well |
|------|--------|---------|-------|------------|---------|---------|-----------|----------------|----------------------|
| 1 | ... | ... | ... | ... | ... | ... | ... | ... | ... |

### Preferred watchlist candidate
...

### Checks before acting
- Upcoming earnings date and guidance risk.
- News/catalyst confirmation from web/SEC sources.
- Sector and index beta exposure.
- Stop/invalidation level near the 20-day or 50-day moving average.
- Position sizing and portfolio concentration risk.
```

## Follow-Up Research Checklist

For the top 3 names, verify:

1. Earnings date within the next 30 days.
2. Recent news, product, regulatory, or analyst catalysts.
3. Sector ETF trend confirmation.
4. Whether the stock is extended more than 10-15% above its 50-day average.
5. Liquidity is normal; avoid one-day volume spikes caused by index rebalances or one-off events.

## Common Pitfalls

- Do not call the result a certainty. Say "highest-ranked setup" or "watchlist candidate".
- Do not rank all S&P 500 names unless the user changes the universe; this skill is specifically top 50 by market cap.
- Do not use raw market cap from a stale static list as the final universe. Always sort the candidate list by current yfinance market cap first.
- Do not ignore binary event risk. A high score before earnings can mean upside potential and downside gap risk.
- If yfinance misses data for a symbol, disclose it instead of filling silently.

