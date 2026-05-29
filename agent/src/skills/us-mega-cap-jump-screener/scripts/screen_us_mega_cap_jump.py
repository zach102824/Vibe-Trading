"""Screen US mega-cap stocks for constructive 30-day jump setups.

The output is a research watchlist, not a prediction or trading instruction.
It intentionally uses free yfinance data so the workflow works without paid
market-data credentials.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Any, Iterable

import pandas as pd


DEFAULT_CANDIDATES: tuple[str, ...] = (
    "NVDA",
    "MSFT",
    "AAPL",
    "AMZN",
    "GOOGL",
    "GOOG",
    "META",
    "AVGO",
    "BRK-B",
    "LLY",
    "TSLA",
    "JPM",
    "V",
    "WMT",
    "MA",
    "XOM",
    "ORCL",
    "UNH",
    "COST",
    "HD",
    "NFLX",
    "PG",
    "JNJ",
    "ABBV",
    "BAC",
    "KO",
    "PLTR",
    "CRM",
    "CVX",
    "CSCO",
    "GE",
    "MRK",
    "WFC",
    "IBM",
    "AMD",
    "ACN",
    "MCD",
    "LIN",
    "DIS",
    "ABT",
    "NOW",
    "PM",
    "ISRG",
    "T",
    "TMO",
    "INTU",
    "GS",
    "TXN",
    "CAT",
    "VZ",
    "QCOM",
    "UBER",
    "RTX",
    "BKNG",
    "MS",
    "AMGN",
    "NEE",
    "AXP",
    "PEP",
    "LOW",
    "SPGI",
    "HON",
    "PGR",
    "ETN",
    "BLK",
    "C",
    "AMAT",
    "BA",
    "SCHW",
    "DE",
    "SYK",
    "LMT",
    "ADP",
    "TJX",
    "GILD",
    "MDT",
    "ADI",
    "COP",
    "PANW",
    "CB",
    "BSX",
    "MMC",
    "UPS",
    "ANET",
    "ELV",
    "SO",
    "MU",
    "FI",
    "BMY",
    "REGN",
    "KLAC",
    "LRCX",
)


@dataclass(frozen=True)
class CompanySnapshot:
    """Lightweight yfinance metadata used by the screener."""

    symbol: str
    market_cap: float | None
    name: str = ""
    sector: str = ""
    beta: float | None = None
    recommendation: float | None = None
    target_mean_price: float | None = None


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _info_value(info: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = info.get(key)
        if value is not None:
            return value
    return None


def fetch_company_snapshots(symbols: Iterable[str]) -> dict[str, CompanySnapshot]:
    """Fetch market caps and metadata from yfinance."""

    import yfinance as yf

    snapshots: dict[str, CompanySnapshot] = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        info: dict[str, Any] = {}
        fast_info: dict[str, Any] = {}
        try:
            fast_info = dict(ticker.fast_info or {})
        except Exception:
            fast_info = {}
        try:
            info = dict(ticker.info or {})
        except Exception:
            info = {}

        market_cap = _finite_float(
            _info_value(fast_info, "marketCap", "market_cap")
            or _info_value(info, "marketCap", "market_cap")
        )
        snapshots[symbol] = CompanySnapshot(
            symbol=symbol,
            market_cap=market_cap,
            name=str(_info_value(info, "shortName", "longName") or symbol),
            sector=str(info.get("sector") or ""),
            beta=_finite_float(info.get("beta")),
            recommendation=_finite_float(info.get("recommendationMean")),
            target_mean_price=_finite_float(info.get("targetMeanPrice")),
        )
    return snapshots


def select_top_market_caps(
    snapshots: dict[str, CompanySnapshot],
    universe_size: int,
) -> list[str]:
    """Return symbols sorted by descending market cap."""

    ranked = sorted(
        (snapshot for snapshot in snapshots.values() if snapshot.market_cap is not None),
        key=lambda item: item.market_cap or 0.0,
        reverse=True,
    )
    return [snapshot.symbol for snapshot in ranked[:universe_size]]


def download_price_history(symbols: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Download adjusted daily OHLCV bars from yfinance."""

    import yfinance as yf

    raw = yf.download(
        symbols,
        period=period,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    if raw.empty:
        return {}

    if isinstance(raw.columns, pd.MultiIndex):
        return {
            symbol: raw[symbol].dropna(how="all")
            for symbol in symbols
            if symbol in raw.columns.get_level_values(0)
        }
    if len(symbols) == 1:
        return {symbols[0]: raw.dropna(how="all")}
    return {}


def calculate_price_metrics(frame: pd.DataFrame) -> dict[str, float] | None:
    """Calculate price/volume features for one symbol."""

    if len(frame) < 80:
        return None

    normalized = {str(column).lower(): column for column in frame.columns}
    close_col = normalized.get("close")
    high_col = normalized.get("high")
    volume_col = normalized.get("volume")
    if close_col is None or high_col is None or volume_col is None:
        return None

    close = pd.to_numeric(frame[close_col], errors="coerce").dropna()
    high = pd.to_numeric(frame[high_col], errors="coerce").reindex(close.index)
    volume = pd.to_numeric(frame[volume_col], errors="coerce").reindex(close.index)
    if len(close) < 80 or close.iloc[-1] <= 0:
        return None

    returns = close.pct_change()
    latest_close = float(close.iloc[-1])
    latest_volume = _finite_float(volume.iloc[-1])
    avg_volume_20 = _finite_float(volume.tail(20).mean())
    high_60 = _finite_float(high.tail(60).max())
    sma_20 = _finite_float(close.tail(20).mean())
    sma_50 = _finite_float(close.tail(50).mean())
    vol_20 = _finite_float(returns.tail(20).std() * math.sqrt(252))
    vol_60 = _finite_float(returns.tail(60).std() * math.sqrt(252))

    if latest_volume is None or avg_volume_20 in (None, 0.0) or high_60 in (None, 0.0):
        return None

    return {
        "close": latest_close,
        "return_5d": float(close.iloc[-1] / close.iloc[-6] - 1) if len(close) >= 6 else 0.0,
        "return_20d": float(close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else 0.0,
        "return_60d": float(close.iloc[-1] / close.iloc[-61] - 1) if len(close) >= 61 else 0.0,
        "distance_60d_high": latest_close / high_60 - 1,
        "close_vs_sma20": latest_close / sma_20 - 1 if sma_20 else 0.0,
        "close_vs_sma50": latest_close / sma_50 - 1 if sma_50 else 0.0,
        "volume_surge": latest_volume / avg_volume_20 - 1,
        "volatility_20": vol_20 or 0.0,
        "volatility_60": vol_60 or 0.0,
        "vol_compression": 1 - (vol_20 / vol_60) if vol_20 is not None and vol_60 not in (None, 0.0) else 0.0,
    }


def build_metrics_table(
    price_history: dict[str, pd.DataFrame],
    snapshots: dict[str, CompanySnapshot],
) -> pd.DataFrame:
    """Build one row per symbol from prices plus company metadata."""

    rows: list[dict[str, Any]] = []
    for symbol, frame in price_history.items():
        metrics = calculate_price_metrics(frame)
        snapshot = snapshots.get(symbol)
        if metrics is None or snapshot is None:
            continue
        rows.append(
            {
                "symbol": symbol,
                "company": snapshot.name or symbol,
                "sector": snapshot.sector,
                "market_cap": snapshot.market_cap,
                "beta": snapshot.beta,
                "recommendation": snapshot.recommendation,
                "target_mean_price": snapshot.target_mean_price,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def score_candidates(metrics: pd.DataFrame) -> pd.DataFrame:
    """Score each symbol cross-sectionally and return highest-ranked rows."""

    if metrics.empty:
        return metrics

    scored = metrics.copy()
    weights = {
        "return_20d": 0.30,
        "return_60d": 0.20,
        "volume_surge": 0.15,
        "distance_60d_high": 0.15,
        "vol_compression": 0.10,
        "close_vs_sma50": 0.10,
    }

    score = pd.Series(0.0, index=scored.index)
    for column, weight in weights.items():
        series = pd.to_numeric(scored[column], errors="coerce")
        filled = series.fillna(series.median())
        score += filled.rank(pct=True) * weight
    scored["score"] = (score * 100).round(1)

    penalty = (
        (pd.to_numeric(scored["return_20d"], errors="coerce") < 0).astype(float) * 5
        + (pd.to_numeric(scored["distance_60d_high"], errors="coerce") < -0.15).astype(float) * 5
    )
    scored["score"] = (scored["score"] - penalty).clip(lower=0).round(1)
    return scored.sort_values(["score", "market_cap"], ascending=[False, False]).reset_index(drop=True)


def format_market_cap(value: Any) -> str:
    """Format market capitalization for table output."""

    number = _finite_float(value)
    if number is None:
        return "n/a"
    if number >= 1_000_000_000_000:
        return f"${number / 1_000_000_000_000:.2f}T"
    if number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.1f}B"
    return f"${number:,.0f}"


def _pct(value: Any) -> str:
    number = _finite_float(value)
    return "n/a" if number is None else f"{number * 100:.1f}%"


def render_markdown(scored: pd.DataFrame, top_n: int, universe_size: int) -> str:
    """Render the ranked watchlist as Markdown."""

    if scored.empty:
        return "No symbols had enough yfinance data to score."

    rows = [
        "## US Mega-Cap 30-Day Jump Watchlist",
        "",
        (
            f"Universe: live top {universe_size} by market cap from a large US-listed candidate set. "
            "Score combines 20D/60D momentum, volume surge, breakout proximity, volatility compression, "
            "and close vs. 50D average. Research only; not financial advice."
        ),
        "",
        "| Rank | Symbol | Company | Score | Market Cap | 20D Ret | 60D Ret | Vol Surge | Dist. 60D High |",
        "|------|--------|---------|-------|------------|---------|---------|-----------|----------------|",
    ]
    for rank, row in enumerate(scored.head(top_n).itertuples(index=False), start=1):
        rows.append(
            "| {rank} | {symbol} | {company} | {score:.1f} | {market_cap} | {ret20} | {ret60} | "
            "{volume} | {dist_high} |".format(
                rank=rank,
                symbol=row.symbol,
                company=str(row.company).replace("|", "/"),
                score=float(row.score),
                market_cap=format_market_cap(row.market_cap),
                ret20=_pct(row.return_20d),
                ret60=_pct(row.return_60d),
                volume=_pct(row.volume_surge),
                dist_high=_pct(row.distance_60d_high),
            )
        )

    leader = scored.iloc[0]
    rows.extend(
        [
            "",
            f"Preferred watchlist candidate by score: **{leader['symbol']}** ({leader['company']}).",
            "",
            "Before acting, check upcoming earnings, fresh news/catalysts, sector ETF trend, and an invalidation level.",
        ]
    )
    return "\n".join(rows)


def run_screen(
    *,
    universe_size: int,
    top_n: int,
    period: str,
    candidates: tuple[str, ...] = DEFAULT_CANDIDATES,
) -> pd.DataFrame:
    """Fetch data, select the top market-cap universe, and score candidates."""

    snapshots = fetch_company_snapshots(candidates)
    top_symbols = select_top_market_caps(snapshots, universe_size)
    history = download_price_history(top_symbols, period)
    metrics = build_metrics_table(history, snapshots)
    return score_candidates(metrics).head(top_n)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe-size", type=int, default=50, help="Live market-cap universe size to score.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of ranked rows to print.")
    parser.add_argument("--period", default="9mo", help="yfinance daily history window, e.g. 6mo, 9mo, 1y.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scored = run_screen(universe_size=args.universe_size, top_n=args.top_n, period=args.period)
    print(render_markdown(scored, top_n=args.top_n, universe_size=args.universe_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

