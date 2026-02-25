"""
Shared I/O helpers for generator outputs.
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd


def normalize_output_format(output_format: Optional[str]) -> str:
    """Validate and normalize output format."""
    fmt = (output_format or "csv").lower()
    if fmt not in {"csv", "parquet"}:
        raise ValueError(
            f"Unsupported OUTPUT_FORMAT '{output_format}'. Use 'csv' or 'parquet'."
        )
    return fmt


def build_output_path(out_dir: str, base_name: str, output_format: str) -> str:
    """Build file path with extension from output format."""
    ext = "csv" if output_format == "csv" else "parquet"
    return os.path.join(out_dir, f"{base_name}.{ext}")


def save_dataframe(
    df: pd.DataFrame,
    out_dir: str,
    base_name: str,
    output_format: str,
    csv_mode: str = "w",
    csv_header: bool = True,
) -> str:
    """
    Persist dataframe using configured output format.

    For CSV, append mode is supported via csv_mode/csv_header.
    For Parquet, each call writes a standalone file.
    """
    os.makedirs(out_dir, exist_ok=True)
    fmt = normalize_output_format(output_format)
    filepath = build_output_path(out_dir, base_name, fmt)

    if fmt == "csv":
        df.to_csv(filepath, mode=csv_mode, header=csv_header, index=False)
    else:
        try:
            df.to_parquet(filepath, index=False)
        except ImportError as exc:
            raise ImportError(
                "Parquet output requires 'pyarrow' or 'fastparquet'. "
                "Install dependencies with: pip install -r data-generator/requirements.txt"
            ) from exc

    return filepath
