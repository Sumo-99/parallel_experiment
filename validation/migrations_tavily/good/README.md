# vuln-watch

Daily digest of new security advisories for the platform team's dependency
stack. Every line in `watchlist.txt` is searched with [Tavily](https://tavily.com) or [Parallel](https://parallel.ai) (`search.provider` in settings.json; Tavily stays available),
restricted to advisory sources we trust and to recent publications. The digest
is posted to #platform-security by a cron job.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # add TAVILY_API_KEY
```

## Run

```bash
python -m vulnwatch                 # writes reports/digest.json and prints a summary
python -m vulnwatch --watchlist x.txt --stdout
```

## Settings (`settings.json`)

- `search.include_domains`: only these sources are searched
- `search.start_date`: ignore anything published before this date (YYYY-MM-DD)
- `search.max_results`: results requested per watch item
- `search.min_score`: Tavily relevance score below which results are discarded
- `search.search_depth`: Tavily depth (`basic` or `advanced`)
- `report.max_per_watch`: items kept per watch item in the digest

## Tests

`pytest` runs offline against recorded Tavily responses in `tests/fixtures/`.
Refresh them with `python scripts/record_fixtures.py` (needs `TAVILY_API_KEY`).


Note: Parallel results carry no relevance score, so `search.min_score` only applies when `search.provider` is `tavily`.
