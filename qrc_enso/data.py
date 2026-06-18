"""U2 -- Nino 3.4 ingestion and leakage-safe anomaly pipeline.

Sources the *raw* monthly Nino 3.4 SST series from NOAA PSL. The pre-computed
``nina34.anom.csv`` is deliberately NOT used as the modelling input: it is
already anomalized against a fixed base period, so applying a per-fold
climatology to it would double-normalize or no-op, defeating the central
leakage guard (R2). Raw SST gives each fold a real value to anomalize.
"""

from __future__ import annotations

import io
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Raw monthly Nino 3.4 SST (degrees C), one row per year, 12 columns.
RAW_SST_URL = "https://psl.noaa.gov/data/correlation/nina34.data"
# Pre-anomalized series; kept only as an optional cross-check, never the model input.
ANOM_CROSSCHECK_URL = "https://psl.noaa.gov/data/correlation/nina34.anom.csv"

# Documented NOAA missing-value sentinels. ``.data`` pads pre-record and
# not-yet-observed future months with these.
MISSING_SENTINELS = (-99.99, -9999.0, -999.0)
_SENTINEL_TOL = 1e-3

DEFAULT_CACHE = Path("data") / "nina34_raw.csv"


def parse_nino34_data(text: str) -> pd.Series:
    """Parse the NOAA PSL ``.data`` fixed format into a monthly Series.

    Format: a ``start_year end_year`` header line, then one ``year v1..v12``
    row per year, then a footer (a lone missing-value line plus provenance
    text). Missing-value sentinels are dropped, which also trims the
    not-yet-observed trailing months of the current year.

    Returns a float Series indexed by a monthly ``DatetimeIndex`` (month start),
    sorted ascending, gap-free over its covered range.
    """
    header_years: tuple[int, int] | None = None
    records: dict[pd.Timestamp, float] = {}

    for raw_line in text.splitlines():
        tokens = raw_line.split()
        if not tokens:
            continue

        # Header: exactly two integer-looking tokens (start, end year).
        if header_years is None and len(tokens) == 2:
            try:
                start, end = int(tokens[0]), int(tokens[1])
            except ValueError:
                continue
            if 1700 <= start <= end <= 2200:
                header_years = (start, end)
                continue

        # Data row: a 4-digit year followed by 12 monthly floats.
        if len(tokens) == 13:
            try:
                year = int(tokens[0])
                values = [float(t) for t in tokens[1:]]
            except ValueError:
                continue
            if header_years is not None and not (
                header_years[0] <= year <= header_years[1]
            ):
                continue
            for month, value in enumerate(values, start=1):
                records[pd.Timestamp(year=year, month=month, day=1)] = value

    if not records:
        raise ValueError("No Nino 3.4 data rows parsed from input text.")

    series = pd.Series(records, name="nino34_sst").sort_index()
    series = _drop_sentinels(series)
    return series


def _drop_sentinels(series: pd.Series) -> pd.Series:
    """Drop documented missing-value sentinels (incl. trailing future months)."""
    mask = np.ones(len(series), dtype=bool)
    for sentinel in MISSING_SENTINELS:
        mask &= ~np.isclose(series.to_numpy(), sentinel, atol=_SENTINEL_TOL)
    return series[mask]


def load_nino34(
    cache_path: Path | str = DEFAULT_CACHE,
    url: str = RAW_SST_URL,
    *,
    use_cache: bool = True,
    refresh: bool = False,
) -> pd.Series:
    """Load the raw monthly Nino 3.4 SST series, fetching and caching as needed.

    A timestamped provenance comment is written alongside the cached CSV so the
    snapshot is reproducible. A second call with ``use_cache`` reads the cache
    without re-downloading.
    """
    cache_path = Path(cache_path)
    if use_cache and not refresh and cache_path.exists():
        return _read_cache(cache_path)

    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (trusted host)
        text = resp.read().decode("utf-8")
    series = parse_nino34_data(text)

    if use_cache:
        _write_cache(series, cache_path, url)
    return series


def _write_cache(series: pd.Series, cache_path: Path, source_url: str) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# Nino 3.4 raw SST snapshot\n"
        f"# source: {source_url}\n"
        f"# fetched_utc: {datetime.now(timezone.utc).isoformat()}\n"
    )
    body = series.to_csv(index_label="date", header=["nino34_sst"])
    cache_path.write_text(header + body)


def _read_cache(cache_path: Path) -> pd.Series:
    text = cache_path.read_text()
    payload = "\n".join(
        line for line in text.splitlines() if not line.startswith("#")
    )
    frame = pd.read_csv(io.StringIO(payload), parse_dates=["date"], index_col="date")
    series = frame["nino34_sst"]
    series.name = "nino34_sst"
    return series


class MonthlyAnomalyNormalizer:
    """Leakage-safe per-calendar-month anomaly normalizer (R2).

    ``fit`` consumes *only* the training slice the caller passes; climatology
    mean and standard deviation are computed per calendar month from that slice
    alone, so test-span values can never influence normalization. ``transform``
    applies the stored statistics to any span.
    """

    def __init__(self, standardize: bool = True) -> None:
        self.standardize = standardize
        self.month_mean_: dict[int, float] = {}
        self.month_std_: dict[int, float] = {}

    def fit(self, train_series: pd.Series) -> "MonthlyAnomalyNormalizer":
        if train_series.empty:
            raise ValueError("Cannot fit anomaly normalizer on an empty series.")
        by_month = train_series.groupby(train_series.index.month)
        self.month_mean_ = by_month.mean().to_dict()
        std = by_month.std(ddof=0)
        # Guard against a zero-variance calendar month.
        self.month_std_ = {m: (s if s > 0 else 1.0) for m, s in std.to_dict().items()}
        return self

    def transform(self, series: pd.Series) -> pd.Series:
        if not self.month_mean_:
            raise RuntimeError("Normalizer must be fit before transform.")
        months = series.index.month
        missing = sorted(set(months) - set(self.month_mean_))
        if missing:
            raise ValueError(
                f"No training climatology for calendar month(s) {missing}; "
                "fit on a window covering all 12 months."
            )
        means = np.array([self.month_mean_[m] for m in months])
        anom = series.to_numpy() - means
        if self.standardize:
            stds = np.array([self.month_std_[m] for m in months])
            anom = anom / stds
        return pd.Series(anom, index=series.index, name="nino34_anom")

    def fit_transform(self, train_series: pd.Series) -> pd.Series:
        return self.fit(train_series).transform(train_series)
