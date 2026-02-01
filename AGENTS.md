# AGENTS.md - Design Decisions and Module Specifications

## Design Philosophy

### Core Principles
1. **Single Responsibility**: Each fetcher handles exactly one data source
2. **Configuration-Driven**: URL, format, missing values defined in config files
3. **Graceful Degradation**: Partial failures don't break the pipeline
4. **Observability**: All operations are logged and tracked
5. **Flexibility**: Support different formats per institution and per indicator

## CLI Design

### Command Structure
```
climabc
├── index              # Data operations
│   ├── list          # List available indicators
│   ├── fetch         # Fetch specific indicator(s)
│   ├── fetch-all     # Fetch all indicators
│   └── status        # Check data source status
├── viz               # Visualization
│   ├── generate      # Generate static charts
│   └── dashboard     # Launch local server
├── data              # Data management
│   ├── ls            # List local data
│   ├── cat           # View data content
│   └── validate      # Validate data integrity
└── rss               # RSS operations
    └── generate      # Generate RSS feeds
```

### Implementation Notes
- Uses `click` for CLI framework
- Entry point: `climabc = "climabc.cli:cli"`
- Configuration directory: `~/.climabc/`
- Data directory: `~/.climabc/data/`

### Development with uv

This project uses `uv` for Python package management and running.

```bash
# Install dependencies
uv sync

# Run CLI commands during development
uv run climabc index list
uv run climabc index fetch nino34a

# Run tests
uv run pytest

# Run a specific Python script with dependencies
uv run python test_psl.py

# Add new dependencies
uv add requests pyyaml
uv add --dev pytest ruff
```

The `uv run` command automatically uses the virtual environment and ensures all dependencies are available.

## Data Source Configuration

### Configuration Structure

Configuration is stored in YAML format supporting per-source and per-indicator overrides:

```yaml
sources:
  psl:
    base_url: "https://psl.noaa.gov/data/correlation/"
    
    # Default settings for all PSL indicators
    default:
      columns: ['year', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
      missing: -99.99
      skiprows: []
      delimiter: "\s+"
      date_format: "{year}-{month}"
    
    # Per-indicator overrides
    indicators:
      nino34:
        url: "nina34.anom.data"
        name: "Niño 3.4 Anomaly"
        description: "East Central Tropical Pacific SST Anomaly"
        category: "enso"
        unit: "°C"
        # Uses default settings
      
      oni:
        url: "oni.data"
        name: "Oceanic Niño Index"
        missing: -99.9  # Override default missing value
        
      ao:
        url: "ao.data"
        name: "Arctic Oscillation"
        missing: -999   # Different missing value
  
  ncei:
    base_url: "https://www.ncei.noaa.gov/pub/data/cmb/ersst/v5/index/"
    
    default:
      missing: 99.99
      skiprows: []
    
    indicators:
      nina_all:
        url: "ersst.v5.el_nino.dat"
        columns: ['year', 'month', 'nina3a', 'nina4a', 'nina34a', 'nina12a']
        # Returns multiple indicators from single file
      
      pdo:
        url: "ersst.v5.pdo.dat"
        columns: ['year', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
      
      amon:
        url: "ersst.v5.amo.dat"
        columns: ['year', 'month', 'amo']
        skiprows: [0, 1]  # Skip header rows
  
  iri:
    indicators:
      enso_prob:
        # URL with placeholders for dynamic values
        url_template: "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/{year}-{month}-quick-look/"
        params:
          year: "{current_year}"
          month: "{current_month_eng}"
        parser: "html_table"  # Requires HTML parsing
  
  jamstec:
    indicators:
      dmi:
        url: "https://www.jamstec.go.jp/virtualearth/data/SINTEX/SINTEX_DMI.csv"
        format: "csv"
        parser: "csv"
```

### Configuration Inheritance

1. **Source-level defaults** apply to all indicators in that source
2. **Indicator-level settings** override source defaults
3. **Required fields**: `url` or `url_template`, `name`
4. **Optional fields**: `columns`, `missing`, `skiprows`, `delimiter`, `parser`, `unit`, `category`

## Fetcher Architecture

### BaseFetcher Interface (Async)

The fetcher architecture uses **async/await** with `httpx` for concurrent HTTP requests and `tenacity` for robust retry logic.

```python
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

class BaseFetcher(ABC):
    """Async base class for all data fetchers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.source_config = config.get('sources', {}).get(self.source, {})
        self.client = self._create_client()
    
    @property
    @abstractmethod
    def source(self) -> str:
        """Source identifier (e.g., 'psl', 'ncei')."""
        pass
    
    @abstractmethod
    async def fetch(self, indicator: str) -> pd.DataFrame:
        """Fetch data for a specific indicator asynchronously."""
        pass
    
    def _create_client(self) -> httpx.AsyncClient:
        """Create async HTTP client with timeout."""
        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={'User-Agent': 'ClimABC-Index/0.1.0'}
        )
    
    async def _fetch_with_retry(self, url: str) -> str:
        """Fetch URL content with exponential backoff retry."""
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10)
        )
        async def _fetch():
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        return await _fetch()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes client."""
        await self.client.aclose()
```

### BaseFetcher Utility Methods

The following static methods are provided for common data processing tasks:

```python
# Validate year format (1-2200)
BaseFetcher._is_valid_year(year_str) -> bool

# Replace missing value markers with NaN
BaseFetcher._replace_missing_with_nan(df, missing_value) -> pd.DataFrame

# Transform wide format (year x months) to long format
BaseFetcher._wide_to_long_transform(df, id_col='year') -> pd.DataFrame
```

### Usage Pattern

```python
import asyncio
from climabc.fetchers import PSLFetcher

async def main():
    config = load_config()
    
    # Method 1: Using async context manager (recommended)
    async with PSLFetcher(config) as fetcher:
        df = await fetcher.fetch('nino34a')
    
    # Method 2: Manual client management
    fetcher = PSLFetcher(config)
    try:
        df = await fetcher.fetch('nino34a')
    finally:
        await fetcher.client.aclose()

asyncio.run(main())
```

### Source-Specific Fetchers

Each data source requires specific parsing logic due to different formats:

#### PSL Fetcher
- **Format**: Space-delimited text files
- **Pattern**: Year followed by 12 monthly values
- **Missing values**: Varies by indicator (-99.99, -999, etc.)
- **Parsing**: Split by whitespace, reshape to long format

#### NCEI Fetcher
- **Format**: Space-delimited with headers
- **Pattern**: Year-Month-Value or Year + 12 monthly values
- **Special**: Some files have header rows to skip
- **Parsing**: Handle both formats, skip specified rows

#### IRI Fetcher
- **Format**: HTML tables
- **Pattern**: Dynamic URLs with year/month
- **Parsing**: BeautifulSoup or pandas read_html
- **Challenge**: URL construction requires date logic

#### JAMSTEC Fetcher
- **Format**: CSV
- **Pattern**: Standard CSV with headers
- **Parsing**: pandas read_csv

## Adding New Data Sources

### Step-by-Step Guide

To add a new data source (e.g., ECMWF, JMA, etc.), follow these steps:

#### 1. Add Configuration to `indicators.yaml`

```yaml
sources:
  your_source_id:  # e.g., ecmwf, jma, etc.
    name: "Full Institution Name"
    base_url: "https://base.url/"
    
    default:
      format: "space_delimited"  # or "csv", "json", "html_table"
      columns: ['year', '1', '2', ..., '12']
      missing: -99.99
      skiprows: []
      delimiter: '\s+'
      unit: "°C"
    
    indicators:
      your_indicator:
        name: "Indicator Name"
        description: "Description of the indicator"
        url: "/path/to/data.file"
        category: "enso"  # or "oscillation", "temperature", etc.
        # Override defaults if needed:
        missing: -999
```

#### 2. Create the Fetcher Class

Create a new file `src/climabc/fetchers/your_source.py`:

```python
"""Fetcher for Your Source data."""

import io
from typing import Any, Dict
import pandas as pd
from .base import BaseFetcher, FetchError, ParseError


class YourSourceFetcher(BaseFetcher):
    """Fetcher for Your Source climate data."""
    
    @property
    def source(self) -> str:
        return "your_source_id"  # Must match YAML config key
    
    async def fetch(self, indicator: str) -> pd.DataFrame:
        """Fetch data for the specified indicator."""
        if indicator not in self.indicators:
            raise ValueError(f"Unknown indicator: {indicator}")
        
        config = self.get_indicator_config(indicator)
        url = self._build_url(config)
        
        # Fetch data with retry
        try:
            raw_text = await self._fetch_with_retry(url)
        except Exception as e:
            raise FetchError(f"Failed to fetch {indicator}: {e}")
        
        # Parse and normalize
        try:
            df = self._parse_data(raw_text, config)
            df = self._normalize_data(df, indicator)
            self.validate_data(df, indicator)
            return df
        except Exception as e:
            raise ParseError(f"Failed to parse {indicator}: {e}")
    
    def _build_url(self, config: Dict[str, Any]) -> str:
        """Build full URL from configuration."""
        base_url = self.source_config.get('base_url', '')
        url_path = config.get('url', '')
        return f"{base_url.rstrip('/')}/{url_path.lstrip('/')}"
    
    def _parse_data(self, raw_text: str, config: Dict[str, Any]) -> pd.DataFrame:
        """Parse source-specific data format.
        
        Use base class utilities for common operations:
        - self._is_valid_year() - Filter valid years
        - self._replace_missing_with_nan() - Handle missing values
        - self._wide_to_long_transform() - Wide to long format
        """
        # Implement parsing logic
        # Example for space-delimited data:
        skiprows = config.get('skiprows', [])
        columns = config.get('columns')
        missing_value = config.get('missing')
        
        # Parse lines
        lines = []
        for i, line in enumerate(raw_text.strip().split('\n')):
            if i in skiprows or not line.strip():
                continue
            lines.append(line.strip())
        
        df = pd.read_csv(
            io.StringIO('\n'.join(lines)),
            sep=r'\s+',
            header=None,
            names=columns,
            on_bad_lines='skip'
        )
        
        # Use base class utilities
        df = self._filter_valid_years(df)
        df = self._replace_missing_with_nan(df, missing_value)
        df = df.dropna(how='any')
        df = self._wide_to_long_transform(df, id_col='year')
        
        return df
    
    def _filter_valid_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter rows with valid years using base class method."""
        if 'year' not in df.columns:
            return df
        mask = df['year'].apply(self._is_valid_year)
        return df[mask].copy()
```

#### 3. Register the Fetcher

Update `src/climabc/fetchers/__init__.py`:

```python
from .your_source import YourSourceFetcher

__all__ = [
    'BaseFetcher',
    'PSLFetcher',
    'YourSourceFetcher',  # Add here
    'FetchError',
    'ValidationError',
    'ParseError'
]
```

#### 4. Test the Fetcher

Create a test script:

```python
import asyncio
import yaml
from climabc.fetchers import YourSourceFetcher

async def test():
    with open('src/climabc/config/indicators.yaml') as f:
        config = yaml.safe_load(f)
    
    async with YourSourceFetcher(config) as fetcher:
        df = await fetcher.fetch('your_indicator')
        print(f"Fetched {len(df)} records")
        print(df.head())

asyncio.run(test())
```

### Common Patterns

#### Pattern 1: Space-Delimited (PSL-style)
```python
df = pd.read_csv(io.StringIO(text), sep=r'\s+', header=None, names=columns)
df = self._wide_to_long_transform(df, id_col='year')
```

#### Pattern 2: Year-Month-Value (NCEI-style)
```python
df = pd.read_csv(io.StringIO(text), sep=r'\s+', names=['year', 'month', 'value'])
df['timestamp'] = pd.to_datetime(df[['year', 'month']].assign(day=15))
```

#### Pattern 3: CSV Format
```python
df = pd.read_csv(io.StringIO(text), skiprows=config.get('skiprows', 0))
# Rename columns to match standard schema
df = df.rename(columns={'Date': 'timestamp', 'SST': 'value'})
```

#### Pattern 4: HTML Table
```python
from bs4 import BeautifulSoup

soup = BeautifulSoup(raw_text, 'html.parser')
table = soup.find('table')
df = pd.read_html(str(table))[0]
```

### Base Class Utilities Reference

| Method | Purpose | Example |
|--------|---------|---------|
| `_is_valid_year()` | Validate year values | `df[df['year'].apply(self._is_valid_year)]` |
| `_replace_missing_with_nan()` | Convert missing markers to NaN | `df = self._replace_missing_with_nan(df, -99.99)` |
| `_wide_to_long_transform()` | Transform year×months → timestamp×value | `df = self._wide_to_long_transform(df, 'year')` |
| `_normalize_data()` | Add metadata columns | `df = self._normalize_data(df, indicator)` |
| `_fetch_with_retry()` | HTTP GET with retry | `text = await self._fetch_with_retry(url)` |

## Testing Architecture

### Test Organization

```
tests/
├── conftest.py              # Shared pytest fixtures
├── utils.py                 # Test utilities and base classes
├── unit/
│   ├── test_base_fetcher.py # BaseFetcher utility tests
│   └── test_psl_fetcher.py  # PSL fetcher tests
└── integration/             # Integration tests (optional)
```

### Testing Dependencies

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "respx>=0.21.0",  # For mocking HTTP requests
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### Key Testing Principles

1. **Mock External HTTP Calls**: Never hit real APIs in tests (use `respx`)
2. **Test Base Class Utilities**: Shared logic tested once in `test_base_fetcher.py`
3. **Test Fetcher-Specific Logic**: Each fetcher tests its own parsing logic
4. **Async Test Support**: All fetcher tests use `pytest-asyncio`

### Shared Fixtures (conftest.py)

```python
@pytest.fixture(scope="session")
def config():
    """Load indicators configuration."""
    with open("src/climabc/config/indicators.yaml") as f:
        return yaml.safe_load(f)

@pytest.fixture
def sample_psl_data():
    """Sample PSL format data for testing."""
    return """1950   -1.99   -1.69   -1.42...
1951   -1.21   -0.76   -0.50..."""

@pytest.fixture
def mock_respx():
    """Provide respx mock router for HTTP mocking."""
    with respx.mock:
        yield respx
```

### BaseFetcher Utility Tests

Located in `tests/unit/test_base_fetcher.py`:

```python
class TestIsValidYear:
    @pytest.mark.parametrize("year_str,expected", [
        ("1950", True),
        ("0", False),
        ("abc", False),
    ])
    def test_year_validation(self, year_str, expected):
        assert BaseFetcher._is_valid_year(year_str) == expected

class TestWideToLongTransform:
    def test_basic_transform(self):
        df = pd.DataFrame({
            'year': [1950, 1951],
            '1': [1.0, 2.0],
            '2': [3.0, 4.0]
        })
        result = BaseFetcher._wide_to_long_transform(df)
        assert 'timestamp' in result.columns
        assert len(result) == 4
```

### Adding Tests for New Data Sources (Template Method Pattern)

With the template method pattern, you only need to test:
1. **Parsing logic** (required) - How raw text becomes DataFrame
2. **Preprocessing** (optional) - Any special filtering/transformations

#### Option 1: Parsing-Only Tests (Fastest, No HTTP)

For pure parsing logic testing (no network calls):

```python
# tests/unit/test_new_source.py
from tests.utils import create_parsing_tests
from climabc.fetchers import NewSourceFetcher

TestNewSourceParsing = create_parsing_tests(
    fetcher_class=NewSourceFetcher,
    test_cases=[
        ('indicator1', 'raw data string', 12),  # (indicator, data, expected_records)
        ('indicator2', 'more raw data', 24),
    ]
)
```

#### Option 2: Integration Tests (With HTTP Mock)

For end-to-end workflow testing:

```python
from tests.utils import create_fetcher_tests
from climabc.fetchers import NewSourceFetcher

TestNewSourceIntegration = create_fetcher_tests(
    fetcher_class=NewSourceFetcher,
    source_name='new_source',
    sample_indicators=['indicator1'],
    sample_data={'indicator1': '1950 1.0 2.0...'}
)
```

#### Option 3: Custom Test Class (Full Control)

For testing specific preprocessing logic:

```python
class TestNewSourceSpecific:
    @pytest.fixture
    def fetcher(self, config):
        return NewSourceFetcher(config)
    
    def test_parse_custom_format(self, fetcher):
        raw = "custom format data"
        config = fetcher.get_indicator_config('ind1')
        
        df = fetcher._parse_data(raw, config)
        
        assert len(df) == 12
        assert df['value'].iloc[0] == expected_value
    
    def test_preprocess_filters(self, fetcher):
        # Test custom preprocessing if needed
        pass
```

### Test Utilities (tests/utils.py)

Two factory functions for easy test creation:

```python
# 1. Integration tests (with HTTP mock)
from tests.utils import create_fetcher_tests

TestPSL = create_fetcher_tests(
    fetcher_class=PSLFetcher,
    source_name='psl',
    sample_indicators=['nino34a', 'soi'],
    sample_data={
        'nino34a': '1950 -1.99 -1.69...',
        'soi': '1950 1.0 1.5...'
    }
)

# 2. Parsing-only tests (no HTTP, fastest)
from tests.utils import create_parsing_tests

TestPSLParsing = create_parsing_tests(
    fetcher_class=PSLFetcher,
    test_cases=[
        ('nino34a', 'raw data', 12),
        ('soi', 'raw data', 12),
    ]
)
```

### Testing Philosophy (Template Method Pattern)

With the template method pattern:
- **Don't test the workflow** - it's controlled by `BaseFetcher.fetch()`
- **Only test the differences** - `_parse_data()` and `_preprocess_data()`

#### What NOT to test:
- HTTP retry logic (tested in base class)
- Data normalization (tested in base class)
- URL building (unless custom implementation)

#### What TO test:
- Parsing logic: Does `_parse_data()` produce correct DataFrame?
- Preprocessing: Does `_preprocess_data()` handle missing values?
- Source-specific edge cases

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/test_psl_fetcher.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=climabc

# Run only failed tests
uv run pytest --lf
```

### HTTP Mocking with respx

```python
@pytest.mark.asyncio
async def test_fetch_with_mock(fetcher, mock_respx):
    # Mock specific URL
    route = mock_respx.get("https://psl.noaa.gov/data/correlation/nina34.anom.data")
    route.respond(text="1950 -1.99 -1.69...")
    
    # Fetch uses mocked data
    df = await fetcher.fetch('nino34a')
    assert len(df) > 0
```

## Data Normalization

### Standard Schema

All data is normalized to the following schema:

```python
{
    "timestamp": datetime,      # ISO 8601 format
    "value": float,             # Primary metric
    "anomaly": Optional[float], # Anomaly value if available
    "forecast": bool,           # True if this is a forecast
    "lead_time": Optional[int], # Months ahead (for forecasts)
    "source": str,              # Source identifier
    "indicator": str,           # Indicator identifier
    "unit": str,                # Unit of measurement
    "metadata": Dict            # Source-specific metadata
}
```

### Normalization Pipeline

1. **Fetch**: Retrieve raw data from source
2. **Parse**: Convert to DataFrame using source-specific parser
3. **Clean**: Handle missing values, convert types
4. **Reshape**: Transform to long format (timestamp, value)
5. **Enrich**: Add metadata (source, indicator, unit)
6. **Validate**: Check data quality

## Storage Strategy

### Local Storage

```
~/.climabc/data/
├── psl/
│   ├── nino34/
│   │   ├── 2024-01-15.parquet
│   │   └── latest.parquet -> 2024-01-15.parquet
│   └── soi/
├── ncei/
└── iri/
```

### Git Storage

- **Branch**: `data-update`
- **Format**: Parquet (efficient, typed)
- **Structure**: `data/{source}/{indicator}/{date}.parquet`
- **Symlinks**: `latest.parquet` points to most recent

### Retention Policy

| Age | Location | Action |
|-----|----------|--------|
| 0-90 days | Main repo | Keep all versions |
| 90-365 days | Main repo | Keep monthly snapshots |
| >365 days | Archive | Compress and move to releases |

## CI/CD Design

### Workflow: update-data.yml

```yaml
name: Update Climate Data

on:
  schedule:
    - cron: '0 0 */3 * *'  # Every 3 days
  workflow_dispatch:

jobs:
  fetch:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        source: [psl, ncei, iri, jamstec]
    
    steps:
      - uses: actions/checkout@v4
        with:
          ref: data-update
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install package
        run: pip install -e .
      
      - name: Fetch data
        run: climabc index fetch-all --source ${{ matrix.source }}
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: data-${{ matrix.source }}
          path: data/${{ matrix.source }}/

  commit:
    needs: fetch
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
        with:
          ref: data-update
      
      - name: Download artifacts
        uses: actions/download-artifact@v4
      
      - name: Commit changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git commit -m "data: update $(date +%Y-%m-%d)" || exit 0
          git push origin data-update
```

## Visualization Architecture

### GitHub Pages Setup

- **Framework**: Jekyll (GitHub native)
- **Location**: `docs/` directory
- **Charts**: Plotly.js for interactive time series
- **Styling**: Custom CSS with CSS variables

### Data Flow to Frontend

```
CI Pipeline
    ↓
Generate JSON files
    ↓
Commit to data-update branch
    ↓
Trigger Pages rebuild
    ↓
Jekyll builds site with data
    ↓
Deploy to gh-pages
```

### Frontend Data Format

```json
{
  "indicator": "nino34",
  "source": "psl",
  "last_updated": "2024-01-15T00:00:00Z",
  "data": [
    {"timestamp": "2024-01-01", "value": 1.2, "anomaly": 1.2},
    {"timestamp": "2024-01-02", "value": 1.3, "anomaly": 1.3}
  ],
  "statistics": {
    "mean": 0.8,
    "std": 0.5,
    "min": -1.2,
    "max": 2.1
  }
}
```

## RSS Generation

### Feed Types

1. **Full Update Feed** (`feed.xml`): All data updates
2. **Alert Feed** (`alerts.xml`): Significant changes only

### Alert Conditions

- Niño 3.4 anomaly crosses ±0.5°C (El Niño/La Niña threshold)
- SOI exceeds ±7 (significant oscillation)
- New forecast data available

### Implementation

```python
from feedgen.feed import FeedGenerator

def generate_rss(indicators: List[str], output_path: str):
    fg = FeedGenerator()
    fg.title('ClimABC Index Updates')
    fg.link(href='https://user.github.io/climabc-index/')
    fg.description('Climate indicators data updates')
    
    for indicator in indicators:
        entry = fg.add_entry()
        entry.title(f'{indicator.name} updated')
        entry.description(f'Latest value: {indicator.latest_value}')
        entry.pubDate(indicator.last_updated)
    
    fg.rss_file(output_path)
```

## Error Handling

### Fetcher Errors

| Error Type | Handling |
|------------|----------|
| HTTP 404/500 | Retry 3x with backoff, then skip |
| Timeout | Mark as failed, continue with others |
| Parse Error | Log error, skip indicator |
| Validation Fail | Alert maintainer, keep previous data |

### Recovery Strategy

1. **Partial Failure**: Continue with available sources
2. **Total Failure**: Send notification, preserve last known good data
3. **Data Gap**: Interpolate or mark as missing in visualization

## Security Considerations

### CI/CD Security

- Use `GITHUB_TOKEN` with minimal permissions
- Separate branch for data (`data-update`)
- No secrets in code (all data sources are public)
- Rate limiting: Respect source API limits

### Data Validation

- Check value ranges (e.g., SST -2°C to 35°C)
- Validate timestamps are reasonable
- Detect sudden jumps (possible data error)
- Cross-validate with multiple sources where possible

## Future Extensions

### Planned Features

1. **API Server**: REST API for programmatic access
2. **WebSocket**: Real-time updates
3. **Machine Learning**: ENSO prediction models
4. **Mobile App**: React Native or PWA
5. **Data Export**: NetCDF, GRIB formats

### Extension Points

- **New Sources**: Add configuration + fetcher class
- **New Formats**: Extend parser registry
- **New Visualizations**: Add Plotly.js charts
- **New Outputs**: Implement output plugin interface
