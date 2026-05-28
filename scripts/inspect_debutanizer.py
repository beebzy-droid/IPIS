"""Quick profile of the raw Debutanizer dataset.

Run: python scripts/inspect_debutanizer.py
"""

from pathlib import Path

import pandas as pd

RAW = Path("data/raw/debutanizer/debutanizer_data.txt")
COLUMNS = ["u1", "u2", "u3", "u4", "u5", "u6", "u7", "y"]


def main() -> None:
    # 2 header lines + blank lines; whitespace-delimited; no header row in pandas terms
    df = pd.read_csv(
        RAW,
        sep=r"\s+",
        skiprows=5,
        names=COLUMNS,
        engine="python",
    )

    print("=" * 60)
    print(f"Shape: {df.shape}")
    print("=" * 60)
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
    print("\nLast 3 rows:")
    print(df.tail(3).to_string())
    print("\nSummary statistics:")
    print(df.describe().to_string())
    print("\nMissing values per column:")
    print(df.isna().sum().to_string())
    print("\nValue ranges (confirms normalization):")
    for col in COLUMNS:
        print(f"  {col}: [{df[col].min():.4f}, {df[col].max():.4f}]")


if __name__ == "__main__":
    main()
