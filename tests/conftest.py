import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from priceintel import data, research  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    return research.Engine(data.records())
