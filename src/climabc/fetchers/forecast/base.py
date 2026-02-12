"""Shared forecast fetching primitives and utilities."""

from __future__ import annotations

import html
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx
import pandas as pd

# Seasonal 3-month rolling windows used by IRI ENSO tables.
_SEASON_TOKEN_RE = re.compile(
    r"^(JFM|FMA|MAM|AMJ|MJJ|JJA|JAS|ASO|SON|OND|NDJ|DJF)$",
    flags=re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_SEASON_TO_MONTH = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}


def _current_month_start() -> pd.Timestamp:
    """Return current month start timestamp without timezone."""
    return pd.Timestamp.utcnow().tz_localize(None).replace(day=1)


def _to_float(raw_value: str) -> float | None:
    """Extract first numeric token from a table cell."""
    if raw_value is None:
        return None
    match = _NUMBER_RE.search(str(raw_value))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _extract_tables(raw_html: str) -> list[list[list[str]]]:
    """Parse HTML table structures using lightweight regex extraction."""
    tables: list[list[list[str]]] = []
    table_matches = re.findall(r"<table[^>]*>(.*?)</table>", raw_html, flags=re.IGNORECASE | re.DOTALL)

    for table_html in table_matches:
        rows: list[list[str]] = []
        row_matches = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.IGNORECASE | re.DOTALL)
        for row_html in row_matches:
            cell_matches = re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", row_html, flags=re.IGNORECASE | re.DOTALL)
            cells: list[str] = []
            for cell_html in cell_matches:
                text = re.sub(r"<[^>]+>", "", cell_html)
                text = html.unescape(text)
                text = re.sub(r"\s+", " ", text).strip()
                cells.append(text)
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)

    return tables


def _resolve_template_params(raw_params: dict[str, Any] | None) -> dict[str, str]:
    """Resolve dynamic params used by forecast URL templates."""
    params = raw_params or {}
    now = datetime.now(timezone.utc)
    resolved: dict[str, str] = {}
    for key, value in params.items():
        if value == "{current_year}":
            resolved[key] = str(now.year)
        elif value == "{current_month_eng}":
            # IRI quick-look URL expects title case month, e.g. "May".
            resolved[key] = now.strftime("%B")
        else:
            resolved[key] = str(value)
    return resolved

def _build_static_url(source_config: dict[str, Any], indicator_config: dict[str, Any]) -> str:
    """Build URL for forecast indicators with static `url` config."""
    raw_url = str(indicator_config.get("url", "")).strip()
    if not raw_url:
        raise ValueError("Forecast indicator requires 'url'")
    if raw_url.startswith("http://") or raw_url.startswith("https://"):
        return raw_url

    base_url = str(source_config.get("base_url", "")).strip()
    return f"{base_url.rstrip('/')}/{raw_url.lstrip('/')}"


def _values_to_batch(
    values: list[tuple[str, float]],
    issue_date: pd.Timestamp,
    metric_key: str = "nino34",
    source_label: str = "iri",
) -> dict[str, Any] | None:
    """Convert (season, value) tuples into frontend forecast batch schema."""
    if not values:
        return None

    target_dates: list[str] = []
    forecast_points: list[dict[str, float]] = []

    for season, value in values:
        month = _SEASON_TO_MONTH.get(str(season).upper())
        if month is None:
            continue

        target_year = issue_date.year + (1 if month - issue_date.month < 0 else 0)
        target_date = pd.Timestamp(year=target_year, month=month, day=1)
        target_dates.append(target_date.strftime("%Y-%m"))
        forecast_points.append({metric_key: float(value)})

    if not target_dates:
        return None

    return {
        "id": f"forecast-{source_label}-{issue_date.strftime('%Y-%m')}",
        "source": source_label,
        "issuedDate": issue_date.strftime("%Y-%m"),
        "targetDates": target_dates,
        "data": forecast_points,
        "isHistorical": issue_date < _current_month_start(),
    }


class BaseForecastFetcher(ABC):
    """Base class for forecast sources, aligned with fetcher-style lifecycle."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.source_config = config.get("sources", {}).get(self.source, {})
        self.client = self._create_client()

    @property
    @abstractmethod
    def source(self) -> str:
        """Return source identifier."""

    def _create_client(self) -> httpx.AsyncClient:
        """Create HTTP client for forecast endpoints."""
        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": "ClimABC-Index/0.1.0 (Forecast Integration)"},
        )

    @abstractmethod
    async def fetch_batch(self) -> dict[str, Any] | None:
        """Fetch latest forecast batch from this source."""

    async def fetch_batches(self, max_batches: int = 1) -> list[dict[str, Any]]:
        """Fetch multiple batches; default implementation returns latest batch only."""
        if max_batches <= 0:
            return []
        batch = await self.fetch_batch()
        return [batch] if batch else []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
