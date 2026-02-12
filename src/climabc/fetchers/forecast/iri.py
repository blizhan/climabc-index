"""IRI forecast source implementation."""

from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Any

import pandas as pd

from .base import (
    BaseForecastFetcher,
    _SEASON_TOKEN_RE,
    _extract_tables,
    _to_float,
    _values_to_batch,
)

_PUBLISHED_RE = re.compile(
    r"Published:\s*([A-Za-z]+)\s+\d{1,2},\s*(\d{4})",
    flags=re.IGNORECASE,
)
_QUICK_LOOK_PATH_RE = re.compile(r"/(\d{4})-([A-Za-z]+)-quick-look/", flags=re.IGNORECASE)


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
        """Render one IRI quick-look URL for a specific issue month."""
        template = indicator_config.get("url_template")
        if not template:
            raise ValueError("IRI forecast indicator requires 'url_template'")

        rendered_path = template.format(
            year=issue_date.year,
            month=issue_date.strftime("%B"),
        )
        base_url = str(self.source_config.get("base_url", "")).strip()
        return f"{base_url.rstrip('/')}/{rendered_path.lstrip('/')}"

    def _build_current_url(self, indicator_config: dict[str, Any]) -> str:
        """Build URL for the latest IRI ENSO page."""
        current_path = indicator_config.get(
            "current_url",
            "/our-expertise/climate/forecasts/enso/current/?enso_tab=enso-sst_table",
        )
        current_url = str(current_path).strip()
        if current_url.startswith("http://") or current_url.startswith("https://"):
            return current_url

        base_url = str(self.source_config.get("base_url", "")).strip()
        return f"{base_url.rstrip('/')}/{current_url.lstrip('/')}"

    async def fetch_batch(self) -> dict[str, Any] | None:
        batches = await self.fetch_batches(max_batches=1)
        return batches[0] if batches else None

    async def fetch_batches(
        self,
        max_batches: int = 1,
        start_issue_date: pd.Timestamp | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch recent IRI forecast batches by walking backward month-by-month."""
        indicator_config = self.source_config.get("indicators", {}).get("enso_prob")
        if not indicator_config:
            return []

        limit = max(1, int(max_batches))
        search_window = int(self.source_config.get("search_months", max(limit * 3, limit)))
        search_window = max(search_window, limit)

        issue_start = start_issue_date or pd.Timestamp.utcnow().tz_localize(None).replace(day=1)

        batches: list[dict[str, Any]] = []
        seen_issue_dates: set[str] = set()

        def _append_batch(values: list[tuple[str, float]], issue_date: pd.Timestamp) -> bool:
            issued_key = issue_date.strftime("%Y-%m")
            if issued_key in seen_issue_dates:
                return False

            batch = _values_to_batch(
                values,
                issue_date=issue_date,
                metric_key="nino34",
                source_label=self.source,
            )
            if batch is None:
                return False

            seen_issue_dates.add(issued_key)
            batches.append(batch)
            return True

        # Fetch latest batch from IRI "current" page first.
        history_start = issue_start
        try:
            current_url = self._build_current_url(indicator_config)
            response = await self.client.get(current_url)
            if response.status_code < 400:
                current_values = _extract_iri_nino34_values(response.text)
                if current_values:
                    current_issue_date = (
                        _extract_iri_issue_date(response.text)
                        or _extract_issue_date_from_quicklook_url(str(response.url))
                        or issue_start
                    )
                    if _append_batch(current_values, current_issue_date):
                        history_start = current_issue_date - pd.DateOffset(months=1)
        except Exception:  # noqa: BLE001
            pass

        for month_offset in range(search_window):
            if len(batches) >= limit:
                break

            candidate_issue_date = history_start - pd.DateOffset(months=month_offset)
            url = self._build_issue_month_url(indicator_config, candidate_issue_date)

            try:
                response = await self.client.get(url)
            except Exception:  # noqa: BLE001
                continue

            if response.status_code >= 400:
                continue

            values = _extract_iri_nino34_values(response.text)
            if not values:
                continue

            page_issue_date = _extract_iri_issue_date(response.text) or candidate_issue_date
            _append_batch(values, page_issue_date)

        batches.sort(key=lambda item: item.get("issuedDate", ""), reverse=True)
        return batches
