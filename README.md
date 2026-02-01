# ClimABC Index

[![CI Update](https://github.com/{user}/{repo}/actions/workflows/update-data.yml/badge.svg)](https://github.com/{user}/{repo}/actions)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

> Automated climate data aggregation platform - Tracking ENSO, PDO, AMO, IOD and more from major climate institutions (IRI, PSL, NCEI, JAMSTEC)

## Supported Data Sources

| Institution | Type | Indicators | Status |
|-------------|------|------------|--------|
| IRI | Forecast | ENSO Probability | ✅ |
| JAMSTEC | Forecast | Dipole Mode Index | ✅ |
| NOAA PSL | Historical | Niño indices, SOI, AO, NAO, PDO, AMO, IOD | ✅ |
| NCEI | Historical | Sea surface temperature, PDO, AMO, IOD | ✅ |

## Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install climabc-index

# Or using pip
pip install climabc-index
```

### CLI Usage

```bash
# List all available indicators
climabc index list

# Fetch specific indicator
climabc index fetch nino34

# Fetch all indicators
climabc index fetch-all

# Check data source status
climabc index status
```

### Python API

```python
from climabc import fetch_indicator

# Fetch Niño 3.4 anomaly
df = fetch_indicator("nino34")
print(df.tail())
```

## Live Dashboard

🔗 **[View Dashboard](https://yourusername.github.io/climabc-index/)**

Features:
- Real-time ENSO monitoring
- Historical trend analysis
- Multi-source data comparison
- Interactive time series charts

## RSS Feeds

- **Data Updates**: `https://yourusername.github.io/climabc-index/feed.xml`
- **ENSO Alerts**: `https://yourusername.github.io/climabc-index/alerts.xml`

## Data Update Schedule

- **Frequency**: Every 3 days (UTC 00:00)
- **Manual Trigger**: Available via GitHub Actions
- **History**: Retained for 365 days
- **Storage**: Data stored in `data-update` branch

## Repository Structure

```
climabc-index/
├── src/climabc/          # Core Python package
│   ├── fetchers/         # Data fetchers for each source
│   ├── cli/              # Command-line interface
│   └── storage/          # Data storage utilities
├── docs/                 # GitHub Pages source
│   ├── _layouts/         # Jekyll layouts
│   ├── _includes/        # Reusable components
│   ├── assets/           # CSS, JS, data files
│   └── indicators/       # Indicator detail pages
├── data/                 # Auto-updated data (data-update branch)
├── .github/workflows/    # CI/CD configurations
└── tests/                # Test suite
```

## Configuration

Data sources are configured in `src/climabc/config/indicators.yaml`:

```yaml
sources:
  psl:
    base_url: "https://psl.noaa.gov/data/correlation/"
    default:
      columns: ['year', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
      missing: -99.99
    indicators:
      nino34:
        url: "nina34.anom.data"
        name: "Niño 3.4 Anomaly"
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Data provided by [NOAA PSL](https://psl.noaa.gov), [NCEI](https://www.ncei.noaa.gov), [IRI](https://iri.columbia.edu), and [JAMSTEC](https://www.jamstec.go.jp)
- Built with Python, Jekyll, and Plotly.js
