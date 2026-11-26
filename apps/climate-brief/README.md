# climate-brief

Builds the weekly climate-tech market brief that goes to the investment team on
Monday mornings. Each line in `queries.txt` becomes a section; results come from
[Exa](https://exa.ai) search, restricted to the outlets the team trusts and to
news since the start of the fund quarter.

## Setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env   # then add EXA_API_KEY
```

## Usage

```bash
python -m brief                       # writes out/brief.md
python -m brief --json                # machine-readable output on stdout
python -m brief --queries my.txt      # custom query list
```

## Configuration

`config.toml` holds the search settings:

| Key | Meaning |
| --- | --- |
| `include_domains` | Only these outlets are searched |
| `start_published_date` | Ignore articles published before this date |
| `num_results` | Results requested per query |
| `max_items_per_section` | Cap on items shown per query in the brief |

## Tests

```bash
pytest
```

Tests use recorded API responses in `tests/fixtures/` and make no network calls.
`scripts/record_fixtures.py` refreshes the recordings (needs `EXA_API_KEY`).
