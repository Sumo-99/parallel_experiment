import json
from pathlib import Path

import pytest

from brief.config import load_settings

FIXTURES = Path(__file__).parent / "fixtures"
ROOT = Path(__file__).resolve().parent.parent


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def settings():
    return load_settings(ROOT / "config.toml")


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    monkeypatch.setenv("EXA_API_KEY", "test-key")
