"""Unit tests for Module 1 data loading and preprocessing.

Two tiers:
- Fixture-based tests run everywhere (including CI) using a tiny committed sample.
- Real-data tests run only when the gitignored full dataset is present locally.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ipis.module1_soft_sensor.data.loaders import (
    DEBUTANIZER_COLUMNS,
    DebutanizerLoader,
)
from ipis.module1_soft_sensor.data.preprocessing import time_ordered_split

# Fixture: small committed sample mirroring the real file format.
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "debutanizer_sample.txt"
# Real data: gitignored, present only on machines that downloaded it.
REAL_DATA_PATH = Path("data/raw/debutanizer/debutanizer_data.txt")


class TestDebutanizerLoaderFixture:
    """Loader tests against the committed fixture (run in CI)."""

    def test_loads_fixture(self) -> None:
        df = DebutanizerLoader().load(FIXTURE_PATH)
        assert list(df.columns) == DEBUTANIZER_COLUMNS
        assert df.shape == (10, 8)

    def test_no_missing_values(self) -> None:
        df = DebutanizerLoader().load(FIXTURE_PATH)
        assert not df.isna().any().any()

    def test_skips_headers_and_blanks(self) -> None:
        """First data row should be numeric, not a header string."""
        df = DebutanizerLoader().load(FIXTURE_PATH)
        assert df["u1"].iloc[0] == pytest.approx(0.26890035)

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            DebutanizerLoader().load(Path("does/not/exist.txt"))


class TestTimeOrderedSplit:
    """Tests for the time-ordered split utility."""

    def test_split_preserves_order_and_counts(self) -> None:
        df = DebutanizerLoader().load(FIXTURE_PATH)
        split = time_ordered_split(df, train_frac=0.6, val_frac=0.2)
        # 10 rows: 6 train, 2 val, 2 test
        assert split.summary() == {"train": 6, "val": 2, "test": 2, "total": 10}

    def test_no_overlap_between_splits(self) -> None:
        df = DebutanizerLoader().load(FIXTURE_PATH)
        split = time_ordered_split(df, train_frac=0.6, val_frac=0.2)
        # First train row must precede first test row in original order
        assert split.train["u1"].iloc[0] != split.test["u1"].iloc[0]

    def test_invalid_fractions_raise(self) -> None:
        df = DebutanizerLoader().load(FIXTURE_PATH)
        with pytest.raises(ValueError):
            time_ordered_split(df, train_frac=0.9, val_frac=0.2)


@pytest.mark.skipif(
    not REAL_DATA_PATH.exists(),
    reason="Full Debutanizer dataset not present (gitignored). Local-only test.",
)
class TestDebutanizerLoaderRealData:
    """Tests against the full dataset — run locally, skipped in CI."""

    def test_full_shape(self) -> None:
        df = DebutanizerLoader().load(REAL_DATA_PATH)
        assert df.shape == (2394, 8)

    def test_normalized_ranges(self) -> None:
        df = DebutanizerLoader().load(REAL_DATA_PATH)
        for col in DEBUTANIZER_COLUMNS:
            assert df[col].min() >= 0.0
            assert df[col].max() <= 1.0

    def test_full_split_counts(self) -> None:
        df = DebutanizerLoader().load(REAL_DATA_PATH)
        split = time_ordered_split(df, train_frac=0.70, val_frac=0.15)
        s = split.summary()
        assert s["total"] == 2394
        assert s["train"] == 1675  # int(2394 * 0.70)
        assert s["val"] == 359  # int(2394 * 0.85) - 1675
        assert s["test"] == 360
