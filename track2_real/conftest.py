import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "src"))


def pytest_addoption(parser):
    parser.addoption("--run-data", action="store_true", default=False, help="run tests that need data/processed")


def pytest_configure(config):
    config.addinivalue_line("markers", "data: needs processed data on disk (skipped unless --run-data)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-data"):
        return
    skip = pytest.mark.skip(reason="data test: pass --run-data to run")
    for item in items:
        if "data" in item.keywords:
            item.add_marker(skip)
