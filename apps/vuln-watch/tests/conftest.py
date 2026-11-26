import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def tavily_key(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
