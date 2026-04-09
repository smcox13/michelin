"""Utilities for loading and validating curated TireLens datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

REPORT_EVIDENCE_COLUMNS = [
    "report_year",
    "report_summary",
    "evidence_1",
    "evidence_1_page",
    "evidence_2",
    "evidence_2_page",
    "evidence_3",
    "evidence_3_page",
]


class DataValidationError(ValueError):
    """Raised when a dataset cannot be loaded or validated."""


DATASET_SCHEMAS = {
    "financials.csv": {
        "required_columns": [
            "brand",
            "fiscal_year",
            "revenue_usd_bn",
            "prior_revenue_usd_bn",
            "net_income_usd_bn",
            "operating_margin_pct",
            "market_cap_usd_bn",
            *REPORT_EVIDENCE_COLUMNS,
        ],
        "numeric_columns": [
            "fiscal_year",
            "revenue_usd_bn",
            "prior_revenue_usd_bn",
            "net_income_usd_bn",
            "operating_margin_pct",
            "market_cap_usd_bn",
            "report_year",
            "evidence_1_page",
            "evidence_2_page",
            "evidence_3_page",
        ],
    },
    "sustainability.csv": {
        "required_columns": [
            "brand",
            "co2_emissions_scope12_mt",
            "sustainability_commitment",
            "circular_economy_initiatives",
            "sustainability_score",
            *REPORT_EVIDENCE_COLUMNS,
        ],
        "numeric_columns": [
            "co2_emissions_scope12_mt",
            "sustainability_score",
            "report_year",
            "evidence_1_page",
            "evidence_2_page",
            "evidence_3_page",
        ],
    },
    "products.csv": {
        "required_columns": [
            "brand",
            "product_categories_count",
            "market_position",
            "ev_tire_presence",
            "product_portfolio_score",
            *REPORT_EVIDENCE_COLUMNS,
        ],
        "numeric_columns": [
            "product_categories_count",
            "product_portfolio_score",
            "report_year",
            "evidence_1_page",
            "evidence_2_page",
            "evidence_3_page",
        ],
    },
}


def _load_dataset(filename: str) -> pd.DataFrame:
    schema = DATASET_SCHEMAS[filename]
    path = DATA_DIR / filename
    if not path.exists():
        raise DataValidationError(f"Could not find dataset: {path}")

    try:
        dataframe = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - pandas error surface
        raise DataValidationError(f"Could not read dataset {filename}: {exc}") from exc

    missing_columns = [
        column
        for column in schema["required_columns"]
        if column not in dataframe.columns
    ]
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise DataValidationError(
            f"Dataset {filename} is missing required columns: {missing_list}"
        )

    for column in schema["numeric_columns"]:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
        invalid_rows = dataframe[dataframe[column].isna()]
        if not invalid_rows.empty:
            brands = ", ".join(invalid_rows["brand"].astype(str).tolist())
            raise DataValidationError(
                f"Dataset {filename} contains invalid numeric values in "
                f"'{column}' for brands: {brands}"
            )

    if dataframe.empty:
        raise DataValidationError(f"Dataset {filename} is empty.")

    return dataframe


def load_financials() -> pd.DataFrame:
    return _load_dataset("financials.csv")


def load_sustainability() -> pd.DataFrame:
    return _load_dataset("sustainability.csv")


def load_products() -> pd.DataFrame:
    return _load_dataset("products.csv")


def filter_by_brands(dataframe: pd.DataFrame, brands: list[str]) -> pd.DataFrame:
    if not brands:
        raise DataValidationError("Select at least one brand to compare.")

    filtered = dataframe[dataframe["brand"].isin(brands)].copy()
    if filtered.empty:
        requested = ", ".join(brands)
        raise DataValidationError(f"No rows found for the selected brands: {requested}")

    return filtered
