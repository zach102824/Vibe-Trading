"""Tests for the US mega-cap jump screener skill."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from src.agent.skills import SkillsLoader, _parse_frontmatter


SKILL_DIR = Path(__file__).resolve().parents[1] / "src" / "skills" / "us-mega-cap-jump-screener"
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "screen_us_mega_cap_jump.py"
LOCAL_SETUP = SKILL_DIR / "LOCAL_SETUP.md"
SETUP_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "setup-us-mega-cap-screener"


def _load_screener_module():
    spec = importlib.util.spec_from_file_location("screen_us_mega_cap_jump", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_skill_metadata_and_loader_exposure(tmp_path: Path) -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)

    assert meta["name"] == "us-mega-cap-jump-screener"
    assert meta["category"] == "analysis"
    assert "US mega-cap 30-day jump screener" in meta["description"]
    assert "not financial advice" in body
    assert "scripts/setup-us-mega-cap-screener" in body

    loader = SkillsLoader(SKILL_DIR.parent, user_skills_dir=tmp_path)
    assert '<skill name="us-mega-cap-jump-screener">' in loader.get_content("us-mega-cap-jump-screener")
    assert "us-mega-cap-jump-screener" in loader.get_descriptions()


def test_local_setup_assets_document_clone_and_run_path() -> None:
    guide = LOCAL_SETUP.read_text(encoding="utf-8")
    script = SETUP_SCRIPT.read_text(encoding="utf-8")

    assert "git clone" in guide
    assert "python3 -m venv .venv" in guide
    assert "screen_us_mega_cap_jump.py --top-n 10" in guide
    assert "Usage: scripts/setup-us-mega-cap-screener" in script
    assert "pip install -e" in script


def test_select_top_market_caps_sorts_descending() -> None:
    module = _load_screener_module()
    snapshots = {
        "AAA": module.CompanySnapshot("AAA", 100.0),
        "BBB": module.CompanySnapshot("BBB", 300.0),
        "CCC": module.CompanySnapshot("CCC", None),
        "DDD": module.CompanySnapshot("DDD", 200.0),
    }

    assert module.select_top_market_caps(snapshots, 2) == ["BBB", "DDD"]


def test_calculate_price_metrics_detects_momentum_and_volume() -> None:
    module = _load_screener_module()
    close = pd.Series([100 + i * 0.5 for i in range(100)], dtype=float)
    high = close + 1
    volume = pd.Series([1_000_000.0] * 99 + [2_000_000.0])
    frame = pd.DataFrame({"Close": close, "High": high, "Volume": volume})

    metrics = module.calculate_price_metrics(frame)

    assert metrics is not None
    assert metrics["return_20d"] > 0
    assert metrics["return_60d"] > 0
    assert metrics["volume_surge"] > 0.8
    assert -0.02 < metrics["distance_60d_high"] < 0


def test_score_candidates_prefers_stronger_setup() -> None:
    module = _load_screener_module()
    metrics = pd.DataFrame(
        [
            {
                "symbol": "STRONG",
                "company": "Strong Corp",
                "sector": "Technology",
                "market_cap": 500.0,
                "return_20d": 0.12,
                "return_60d": 0.25,
                "volume_surge": 0.8,
                "distance_60d_high": -0.01,
                "vol_compression": 0.2,
                "close_vs_sma50": 0.1,
            },
            {
                "symbol": "WEAK",
                "company": "Weak Corp",
                "sector": "Utilities",
                "market_cap": 600.0,
                "return_20d": -0.04,
                "return_60d": 0.01,
                "volume_surge": -0.2,
                "distance_60d_high": -0.2,
                "vol_compression": -0.1,
                "close_vs_sma50": -0.03,
            },
        ]
    )

    scored = module.score_candidates(metrics)

    assert list(scored["symbol"]) == ["STRONG", "WEAK"]
    assert scored.loc[0, "score"] > scored.loc[1, "score"]

