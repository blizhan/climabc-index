"""IRI forecast source implementation."""

from __future__ import annotations

import html
import logging
import math
import re
from datetime import datetime
from typing import Any

import pandas as pd

from .base import (
    BaseForecastFetcher,
    _SEASON_TOKEN_RE,
    _current_month_start,
    _extract_tables,
    _to_float,
    _values_to_batch,
)

_PUBLISHED_RE = re.compile(
    r"Published:\s*([A-Za-z]+)\s+\d{1,2},\s*(\d{4})",
    flags=re.IGNORECASE,
)
_QUICK_LOOK_PATH_RE = re.compile(r"/(\d{4})-([A-Za-z]+)-quick-look/", flags=re.IGNORECASE)
_CENTERED_SEASONS = (
    "DJF",
    "JFM",
    "FMA",
    "MAM",
    "AMJ",
    "MJJ",
    "JJA",
    "JAS",
    "ASO",
    "SON",
    "OND",
    "NDJ",
)
_IRI_SEARCH_MONTHS = 3
logger = logging.getLogger(__name__)


def _extract_iri_total_values(
    payload: Any,
    issue_date: pd.Timestamp,
) -> list[tuple[str, float]]:
    """Extract finite IRI averages.total values with centered season labels."""
    if not isinstance(payload, dict):
        return []

    averages = payload.get("averages")
    if not isinstance(averages, dict):
        return []

    total = averages.get("total")
    if not isinstance(total, list):
        return []

    issue_month_index = pd.Timestamp(issue_date).month - 1
    values: list[tuple[str, float]] = []
    for offset, raw_value in enumerate(total[:9]):
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            continue

        try:
            value = float(raw_value)
        except OverflowError:
            continue
        if not math.isfinite(value) or value == -999.0:
            continue

        season = _CENTERED_SEASONS[(issue_month_index + offset) % 12]
        values.append((season, value))

    return values


def _extract_iri_issue_date(raw_html: str) -> pd.Timestamp | None:
    """Extract issue month from IRI page published date."""
    normalized = re.sub(r"<[^>]+>", " ", raw_html)
    normalized = html.unescape(normalized)
    match = _PUBLISHED_RE.search(normalized)
    if not match:
        return None

    month_token = match.group(1)
    year_token = match.group(2)
    try:
        month = datetime.strptime(month_token[:3], "%b").month
        year = int(year_token)
    except ValueError:
        return None

    return pd.Timestamp(year=year, month=month, day=1)


def _extract_iri_nino34_values(raw_html: str) -> list[tuple[str, float]]:
    """Extract (season, value) pairs from IRI model table."""
    tables = _extract_tables(raw_html)
    for rows in tables:
        header_index = None
        season_col_indexes: list[int] = []
        season_labels: list[str] = []

        for idx, row in enumerate(rows):
            if not row:
                continue
            if not any(cell.strip().lower() == "model" for cell in row):
                continue
            season_indexes = []
            season_names = []
            for col_index, label in enumerate(row):
                token = label.strip().upper()
                if _SEASON_TOKEN_RE.match(token):
                    season_indexes.append(col_index)
                    season_names.append(token)
            if len(season_indexes) >= 3:
                header_index = idx
                season_col_indexes = season_indexes
                season_labels = season_names
                break

        if header_index is None:
            continue

        average_row: list[float | None] | None = None
        model_rows: list[list[float | None]] = []

        for row in rows[header_index + 1 :]:
            if len(row) <= max(season_col_indexes):
                continue

            label = row[0].strip().lower()
            row_values = [_to_float(row[col_index]) for col_index in season_col_indexes]
            if all(value is None for value in row_values):
                continue

            if "average" in label or "mean" in label:
                average_row = row_values
            else:
                model_rows.append(row_values)

        selected_values = average_row
        if selected_values is None and model_rows:
            selected_values = []
            for col_idx in range(len(season_col_indexes)):
                candidates = [values[col_idx] for values in model_rows if values[col_idx] is not None]
                selected_values.append(sum(candidates) / len(candidates) if candidates else None)

        if not selected_values:
            continue

        season_value_pairs: list[tuple[str, float]] = []
        for season, value in zip(season_labels, selected_values):
            if value is None:
                continue
            season_value_pairs.append((season, float(value)))
        return season_value_pairs

    return []


def _extract_issue_date_from_quicklook_url(url: str) -> pd.Timestamp | None:
    """Extract issue date from quick-look URL path when available."""
    match = _QUICK_LOOK_PATH_RE.search(str(url))
    if not match:
        return None

    year_token = match.group(1)
    month_token = match.group(2)
    try:
        month = datetime.strptime(month_token[:3], "%b").month
        year = int(year_token)
    except ValueError:
        return None

    return pd.Timestamp(year=year, month=month, day=1)


class IriForecastFetcher(BaseForecastFetcher):
    """IRI ENSO forecast fetcher."""

    @property
    def source(self) -> str:
        return "iri"

    def _build_issue_month_url(
        self,
        indicator_config: dict[str, Any],
        issue_date: pd.Timestamp,
    ) -> str:
        """Render one IRI plumes JSON URL for a specific issue month."""
        template = indicator_config.get("endpoint_template")
        if not template:
            raise ValueError("IRI forecast indicator requires 'endpoint_template'")

        rendered_path = template.format(
            year=issue_date.year,
            month=issue_date.month - 1,
        )
        base_url = str(self.source_config.get("base_url", "")).strip()
        return f"{base_url.rstrip('/')}/{rendered_path.lstrip('/')}"

    async def fetch_batch(self) -> dict[str, Any] | None:
        batches = await self.fetch_batches(max_batches=1)
        return batches[0] if batches else None

    async def fetch_batches(
        self,
        max_batches: int = 1,
        start_issue_date: pd.Timestamp | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent IRI forecast batches by walking backward month-by-month."""
        if isinstance(max_batches, bool) or not isinstance(max_batches, int):
            raise ValueError("max_batches must be an integer")
        limit = max(1, max_batches)

        indicator_config = self.source_config.get("indicators", {}).get("enso_prob")
        if not indicator_config:
            return []

        if start_issue_date is None:
            issue_start = _current_month_start().normalize().replace(day=1)
        else:
            issue_start = pd.Timestamp(start_issue_date)
            if issue_start.tz is not None:
                issue_start = issue_start.tz_localize(None)
            issue_start = issue_start.normalize().replace(day=1)

        batches: list[dict[str, Any]] = []
        for month_offset in range(_IRI_SEARCH_MONTHS):
            if len(batches) >= limit:
                break

            candidate_issue_date = issue_start - pd.DateOffset(months=month_offset)
            url = self._build_issue_month_url(indicator_config, candidate_issue_date)

            try:
                response = await self.client.get(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Skipping IRI forecast %s: request failed: %s",
                    candidate_issue_date.strftime("%Y-%m"),
                    exc,
                )
                continue

            if response.status_code >= 400:
                logger.warning(
                    "Skipping IRI forecast %s: HTTP %s",
                    candidate_issue_date.strftime("%Y-%m"),
                    response.status_code,
                )
                continue

            try:
                payload = response.json()
            except ValueError as exc:
                logger.warning(
                    "Skipping IRI forecast %s: invalid JSON: %s",
                    candidate_issue_date.strftime("%Y-%m"),
                    exc,
                )
                continue

            values = _extract_iri_total_values(payload, candidate_issue_date)
            if not values:
                logger.warning(
                    "Skipping IRI forecast %s: missing usable averages.total",
                    candidate_issue_date.strftime("%Y-%m"),
                )
                continue

            batch = _values_to_batch(
                values,
                issue_date=candidate_issue_date,
                metric_key="nino34",
                source_label=self.source,
            )
            if batch is not None:
                batches.append(batch)

        batches.sort(key=lambda item: item.get("issuedDate", ""), reverse=True)
        return batches
