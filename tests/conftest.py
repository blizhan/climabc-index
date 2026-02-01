"""Pytest configuration and shared fixtures."""

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="session")
def project_root():
    """Return project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def config_path(project_root):
    """Return path to indicators config file."""
    return project_root / "src" / "climabc" / "config" / "indicators.yaml"


@pytest.fixture(scope="session")
def config(config_path):
    """Load and return indicators configuration."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def psl_config(config):
    """Return PSL source configuration."""
    return config.get("sources", {}).get("psl", {})


@pytest.fixture
def ncei_config(config):
    """Return NCEI source configuration."""
    return config.get("sources", {}).get("ncei", {})


@pytest.fixture
def sample_psl_data():
    """Return sample PSL format data for testing."""
    return """1950   -1.99   -1.69   -1.42   -1.54   -1.75   -1.50   -1.08   -0.65   -0.53   -0.82   -1.21   -1.38
1951   -1.21   -0.76   -0.50   -0.33   -0.21   -0.06    0.20    0.34    0.38    0.44    0.40    0.28
1952    0.14    0.03   -0.08   -0.11   -0.11   -0.10   -0.07   -0.06   -0.05   -0.05   -0.06   -0.07
1953   -0.09   -0.11   -0.12   -0.13   -0.14   -0.15   -0.16   -0.17   -0.18   -0.19   -0.20   -0.21
1954   -0.22   -0.23   -0.24   -0.25   -0.26   -0.27   -0.28   -0.29   -0.30   -0.31   -0.32   -0.33"""


@pytest.fixture
def sample_psl_data_with_missing():
    """Return sample PSL data with missing values."""
    return """1950   -1.99   -1.69   -99.99   -1.54   -1.75   -1.50   -1.08   -0.65   -0.53   -0.82   -1.21   -1.38
1951   -1.21   -0.76   -0.50   -0.33   -0.21   -0.06    0.20    0.34    0.38    0.44    0.40    0.28"""


@pytest.fixture
def sample_ncei_data():
    """Return sample NCEI format data."""
    return """1950 1 23.5 -0.5
1950 2 23.6 -0.4
1950 3 23.7 -0.3
1950 4 23.8 -0.2
1950 5 23.9 -0.1"""


@pytest.fixture
def mock_respx():
    """Provide respx mock router for HTTP mocking."""
    import respx

    with respx.mock:
        yield respx
