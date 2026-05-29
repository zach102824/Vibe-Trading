# Local Setup: US Mega-Cap Jump Screener

This guide is for running the 30-day jump screener on your own computer instead of a Cursor cloud workspace.

## 1. Install prerequisites

- Git
- Python 3.11 or newer
- Internet access for yfinance/Yahoo Finance data

No paid market-data key is needed for US stocks.

## 2. Clone the repository

```bash
git clone https://github.com/HKUDS/Vibe-Trading.git
cd Vibe-Trading
```

If you are testing this pull request before it is merged, check out the feature branch after cloning:

```bash
git fetch origin cursor/us-mega-cap-jump-screener-8365
git checkout cursor/us-mega-cap-jump-screener-8365
```

## 3. Set up Python and run the screener

Recommended one-command path:

```bash
scripts/setup-us-mega-cap-screener --top-n 10
```

That command creates `.venv`, installs the project in editable mode, and runs a live yfinance smoke test.

Manual path:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python agent/src/skills/us-mega-cap-jump-screener/scripts/screen_us_mega_cap_jump.py --top-n 10
```

Windows PowerShell equivalent:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python agent/src/skills/us-mega-cap-jump-screener/scripts/screen_us_mega_cap_jump.py --top-n 10
```

## 4. What to expect

The command prints a Markdown table like:

```markdown
## US Mega-Cap 30-Day Jump Watchlist

| Rank | Symbol | Company | Score | Market Cap | 20D Ret | 60D Ret | Vol Surge | Dist. 60D High |
|------|--------|---------|-------|------------|---------|---------|-----------|----------------|
| 1 | ORCL | Oracle Corporation | ... | ... | ... | ... | ... | ... |
```

The top row is the highest-ranked watchlist setup from the current live data pull. It is research output, not a guaranteed prediction or financial advice.

## 5. Faster future runs

After the first setup, you do not need to reinstall dependencies every time:

```bash
source .venv/bin/activate
python agent/src/skills/us-mega-cap-jump-screener/scripts/screen_us_mega_cap_jump.py --top-n 10
```

Use `git pull` occasionally to pick up updates:

```bash
git pull origin main
```

## Troubleshooting

- `python3: command not found`: install Python 3.11+ or use `python`/`py` depending on your OS.
- `externally-managed-environment`: use the `.venv` commands above instead of global `pip install`.
- Empty or stale-looking results: Yahoo/yfinance may be temporarily rate-limited; retry later.
- Corporate/firewall network: make sure Python can reach Yahoo Finance endpoints.

