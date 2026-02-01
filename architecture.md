# System Architecture

## Overview

ClimABC Index is a data pipeline system with three main components:
1. **Data Acquisition Layer** - Python package fetching climate data
2. **Automation Layer** - GitHub Actions CI/CD
3. **Presentation Layer** - GitHub Pages + RSS

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  main       │    │ data-update │    │  gh-pages       │  │
│  │  (code)     │◄───│  (data)     │───►│  (visualization)│  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         ▲                                              │
         │                    GitHub Actions             │
         │         ┌──────────────────────────┐         │
         └─────────┤  Scheduled Trigger       │◄────────┘
                   │  (Every 3 days)          │
                   └──────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  IRI/CPC     │   │  NOAA PSL    │   │  NCEI        │
│  (Forecast)  │   │  (Historical)│   │  (Historical)│
└──────────────┘   └──────────────┘   └──────────────┘
```

## Component Details

### 1. Data Acquisition Layer

#### Package Structure

```
src/climabc/
├── __init__.py
├── config.py           # Configuration management
├── exceptions.py       # Custom exceptions
├── fetchers/
│   ├── __init__.py
│   ├── base.py         # BaseFetcher abstract class
│   ├── iri.py          # IRI/CPC fetchers
│   ├── psl.py          # NOAA PSL fetchers
│   ├── ncei.py         # NCEI fetchers
│   └── jamstec.py      # JAMSTEC fetchers
├── normalizer.py       # Data standardization
├── storage/
│   ├── __init__.py
│   ├── local.py        # File system storage
│   └── git.py          # Git operations
├── validator.py        # Data quality checks
└── rss/
    ├── __init__.py
    └── generator.py    # RSS feed generation
```

#### Data Schema

All indicators normalized to:

```python
{
    "timestamp": datetime,      # ISO 8601
    "value": float,             # Primary metric
    "anomaly": float,           # Deviation from baseline (optional)
    "forecast": bool,           # True if prediction
    "lead_time": int,           # Months ahead (for forecasts)
    "source": str,              # Institution code
    "indicator": str,           # Standardized name
    "unit": str,                # Unit of measurement
    "metadata": dict            # Source-specific info
}
```

### 2. Automation Layer (GitHub Actions)

#### Workflow: update-data.yml

```yaml
name: Update Climate Data

on:
  schedule:
    - cron: '0 0 */3 * *'  # Every 3 days at midnight UTC
  workflow_dispatch:

jobs:
  fetch-and-update:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        source: [iri, psl, ncei, jamstec]
    
    steps:
      - uses: actions/checkout@v4
        with:
          ref: data-update
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install package
        run: pip install -e .
      
      - name: Fetch data
        run: python -m climabc fetch ${{ matrix.source }}
      
      - name: Validate data
        run: python -m climabc validate
      
      - name: Commit changes
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/
          git diff --staged --quiet || git commit -m "Update ${{ matrix.source }} data - $(date +%Y-%m-%d)"
          git push origin data-update
```

#### Branch Strategy

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Source code | PR required |
| `data-update` | Auto-updated data | Direct push (CI only) |
| `gh-pages` | Generated site | Force push (CI only) |

### 3. Presentation Layer

#### GitHub Pages Setup

- **Source**: `gh-pages` branch or `/docs` folder on `main`
- **Generator**: Jekyll (GitHub native) or custom Python script
- **URL**: `https://{user}.github.io/climabc-index/`

#### Dashboard Structure

```
docs/
├── index.html              # Main dashboard
├── indicators/
│   ├── enso.html          # ENSO section
│   ├── nino-indices.html  # Niño 3, 3.4, 4
│   ├── oscillations.html  # AO, NAO, SOI
│   └── iod.html           # Indian Ocean Dipole
├── assets/
│   ├── css/
│   ├── js/
│   └── data/              # Symlink to latest data
└── feed.xml               # RSS feed
```

#### RSS Feed Specification

```xml
<rss version="2.0">
  <channel>
    <title>ClimABC Index Updates</title>
    <description>Climate indicator updates</description>
    <item>
      <title>Niño 3.4 Anomaly: +1.2°C (El Niño conditions)</title>
      <pubDate>...</pubDate>
      <description>Latest value indicates weak El Niño...</description>
      <enclosure url="..." type="image/png"/>
    </item>
  </channel>
</rss>
```

## Data Flow

```
[IRI/PSL/NCEI/JAMSTEC] 
        ↓
[Institution Fetcher] → Error handling & retry
        ↓
[Data Normalizer] → Standard format
        ↓
[Validator] → Quality checks
        ↓
[Storage] → Local + Git branch
        ↓
[RSS Generator] + [GH Pages Rebuild]
```

## Data Retention & Storage

### Local Storage

```
data/
├── indicators/
│   ├── nino34/
│   │   ├── 2024-01.parquet
│   │   └── 2024-02.parquet
│   ├── soi/
│   └── ...
├── archive/
│   └── 2023/              # Compressed yearly archives
├── latest/                # Symlinks to most recent
└── metadata.json          # Index of all data
```

### Git Storage Limits

- **Warning**: GitHub has 1GB soft limit per repo
- **Strategy**: 
  - Store last 90 days in main repo
  - Archive older data to GitHub Releases or external storage
  - Use Git LFS for binary data if needed

## Security Considerations

1. **No secrets in code**: All fetchers use public APIs
2. **CI permissions**: Minimal `contents: write` for data branch only
3. **Input validation**: All fetched data validated before storage
4. **Rate limiting**: Respect source APIs (PSL: 100 req/min, etc.)

## Scalability

### Current Scale

- ~30 indicators
- Updates every 3 days
- ~10 KB per update
- Monthly volume: ~100 KB

### Future Scaling

- Sharding by indicator category
- Database backend (SQLite → PostgreSQL)
- CDN for GH Pages assets
- Webhook notifications beyond RSS

## Deployment Checklist

- [ ] Create `data-update` branch
- [ ] Enable GitHub Pages (source: gh-pages branch)
- [ ] Configure repository secrets (if needed)
- [ ] Set workflow permissions (Settings → Actions)
- [ ] Test manual trigger
- [ ] Verify RSS feed validation
- [ ] Add branch protection rules
