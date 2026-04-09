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


def test_invalid_report_page_raises_validation_error(monkeypatch, tmp_path: Path):
    broken_csv = tmp_path / "financials.csv"
    pd.DataFrame(
        [
            {
                "brand": "Michelin",
                "fiscal_year": 2024,
                "revenue_usd_bn": 30.0,
                "prior_revenue_usd_bn": 27.0,
                "net_income_usd_bn": 2.5,
                "operating_margin_pct": 12.0,
                "market_cap_usd_bn": 28.0,
                "report_year": 2025,
                "report_summary": "Summary",
                "evidence_1": "Driver",
                "evidence_1_page": "ten",
                "evidence_2": "Capital",
                "evidence_2_page": 11,
                "evidence_3": "Risk",
                "evidence_3_page": 12,
            }
        ]
    ).to_csv(broken_csv, index=False)

    monkeypatch.setattr(data_loader, "DATA_DIR", tmp_path)
    with pytest.raises(data_loader.DataValidationError, match="evidence_1_page"):
        data_loader.load_financials()
