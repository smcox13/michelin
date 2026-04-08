from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from services import data_loader


def test_load_financials_returns_expected_dataset():
    dataframe = data_loader.load_financials()
    assert set(dataframe["brand"]) == {
        "Michelin",
        "Goodyear",
        "Continental",
        "Bridgestone",
    }


def test_missing_file_raises_validation_error(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(data_loader, "DATA_DIR", tmp_path)
    with pytest.raises(data_loader.DataValidationError, match="Could not find dataset"):
        data_loader.load_financials()


def test_missing_required_column_raises_validation_error(monkeypatch, tmp_path: Path):
    broken_csv = tmp_path / "financials.csv"
    pd.DataFrame(
        [
            {
                "brand": "Michelin",
                "fiscal_year": 2024,
            }
        ]
    ).to_csv(broken_csv, index=False)

    monkeypatch.setattr(data_loader, "DATA_DIR", tmp_path)
    with pytest.raises(data_loader.DataValidationError, match="missing required columns"):
        data_loader.load_financials()


def test_filter_by_brands_raises_for_empty_result():
    dataframe = pd.DataFrame([{"brand": "Michelin"}])
    with pytest.raises(data_loader.DataValidationError, match="No rows found"):
        data_loader.filter_by_brands(dataframe, ["Goodyear"])
