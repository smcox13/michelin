"""One-time helper to enrich demo CSVs with report-backed evidence.

This script is intentionally separate from the runtime application. It uses
PyMuPDF to validate cited report pages and then writes curated evidence fields
into the demo datasets in ``data/``.

Usage:
    python scripts/curate_report_evidence.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import fitz
except ImportError as exc:  # pragma: no cover - local helper
    raise SystemExit(
        "PyMuPDF is required for this one-time curation helper. "
        "Install it locally with: python -m pip install pymupdf"
    ) from exc


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "assets" / "reports"

COMMON_COLUMNS = [
    "report_year",
    "report_summary",
    "evidence_1",
    "evidence_1_page",
    "evidence_2",
    "evidence_2_page",
    "evidence_3",
    "evidence_3_page",
]

REPORT_FILES = {
    "Michelin": "michelin-2025.pdf",
    "Goodyear": "goodyear-2024.pdf",
    "Continental": "continental-2025.pdf",
    "Bridgestone": "bridgestone-2025.pdf",
}

CURATED_REPORT_DATA = {
    "financials.csv": {
        "Michelin": {
            "report_year": 2025,
            "report_summary": (
                "Michelin's 2025 report shows a business defending margins through "
                "premium mix and value-based pricing even as consolidated sales fell "
                "in softer OE and specialty markets. Cash generation stayed strong "
                "enough to fund dividends, buybacks, and debt reduction."
            ),
            "evidence_1": (
                "Positive price-mix came from disciplined pricing and a bigger share "
                "of MICHELIN-brand and 18-inch-plus tires."
            ),
            "evidence_1_page": 13,
            "evidence_2": (
                "Free cash flow of EUR 2.181 billion supported dividends, debt "
                "reduction, and a EUR 668 million share buyback."
            ),
            "evidence_2_page": 31,
            "evidence_3": (
                "Operating income still absorbed lower OE volumes, under-utilized "
                "capacity, higher raw-material costs, and manufacturing inflation."
            ),
            "evidence_3_page": 21,
        },
        "Goodyear": {
            "report_year": 2024,
            "report_summary": (
                "Goodyear's 2024 filing highlights an earnings recovery powered by "
                "Goodyear Forward savings and lower raw-material costs, even as net "
                "sales fell on lower volume and weaker mix. Liquidity remained "
                "usable, but the model is still exposed to leverage and execution "
                "risk."
            ),
            "evidence_1": (
                "Goodyear Forward contributed USD 480 million and lower raw-material "
                "costs added USD 289 million to segment operating income."
            ),
            "evidence_1_page": 32,
            "evidence_2": (
                "Goodyear Forward prioritizes portfolio optimization, lower exposure "
                "to lower-tier products, and a path toward a roughly 10% segment "
                "operating margin."
            ),
            "evidence_2_page": 31,
            "evidence_3": (
                "Management warns that failure to execute Goodyear Forward could "
                "delay margin improvement, cash-flow gains, and leverage reduction."
            ),
            "evidence_3_page": 15,
        },
        "Continental": {
            "report_year": 2025,
            "report_summary": (
                "Continental's 2025 report shows resilient profitability and cash "
                "generation in continuing operations, with Tires holding up on "
                "replacement demand and mix despite weaker OE markets. Management "
                "still frames tariffs, FX, and soft industrial demand as ongoing "
                "earnings pressure."
            ),
            "evidence_1": (
                "Replacement growth and positive mix in Tires partly offset weak OE "
                "and truck demand, supporting the group's profitability."
            ),
            "evidence_1_page": 48,
            "evidence_2": (
                "Adjusted free cash flow reached EUR 959 million and backed a "
                "proposed dividend of EUR 2.70 per share."
            ),
            "evidence_2_page": 8,
            "evidence_3": (
                "Management expects exchange-rate and tariff pressure to persist, "
                "even if lower raw-material costs provide some relief."
            ),
            "evidence_3_page": 8,
        },
        "Bridgestone": {
            "report_year": 2025,
            "report_summary": (
                "Bridgestone's 2025 integrated report shows revenue and profit "
                "growth, but management says returns and margins still trail target "
                "levels as the industry shifts under pressure from Chinese EV "
                "entrants, low-end imports, and tariffs. Capital allocation remains "
                "concentrated on premium tires and disciplined shareholder returns."
            ),
            "evidence_1": (
                "Revenue and profits increased as Bridgestone improved sales mix by "
                "focusing more tightly on premium tires and cost reduction."
            ),
            "evidence_1_page": 14,
            "evidence_2": (
                "2025 resource allocation keeps roughly JPY 400 billion of capital "
                "expenditure focused on the premium tire business."
            ),
            "evidence_2_page": 14,
            "evidence_3": (
                "Bridgestone estimated about JPY 45 billion of direct tariff impact "
                "on adjusted operating profit as of May 2025."
            ),
            "evidence_3_page": 9,
        },
    },
    "sustainability.csv": {
        "Michelin": {
            "report_year": 2025,
            "report_summary": (
                "Michelin's 2025 report frames sustainability around operational "
                "decarbonization, lower-abrasion products, tire recycling, and "
                "deforestation-free sourcing. The plan is investment-backed, but "
                "part of the footprint remains tied to ETS-regulated emissions."
            ),
            "evidence_1": (
                "Michelin invested EUR 86 million in 2025 on Scope 1 and 2 "
                "decarbonization levers including energy efficiency, electrification, "
                "boiler decarbonization, and renewable energy."
            ),
            "evidence_1_page": 57,
            "evidence_2": (
                "At its Chile site, Michelin started mining-tire recycling that "
                "turns end-of-life tires into raw material for new tires and other "
                "products."
            ),
            "evidence_2_page": 39,
            "evidence_3": (
                "About one-fifth of Michelin's Scope 1 and 2 emissions are covered "
                "by the EU ETS, leaving part of the decarbonization path exposed to "
                "emissions-trading compliance."
            ),
            "evidence_3_page": 58,
        },
        "Goodyear": {
            "report_year": 2024,
            "report_summary": (
                "Goodyear's 2024 filing sets science-based net-zero and near-term "
                "GHG targets and ties product development to lower-emission tires, "
                "renewable power, and sustainable materials. Management also warns "
                "that future climate regulation could demand more capital and "
                "operational change."
            ),
            "evidence_1": (
                "Goodyear targets net-zero GHG emissions across its value chain by "
                "2050 and a 46% cut in absolute Scope 1 and 2 emissions by 2030 "
                "from a 2019 base year."
            ),
            "evidence_1_page": 12,
            "evidence_2": (
                "Goodyear's commercial model already includes retreading centers, "
                "retread materials, and retread services for truck, aviation, and "
                "OTR tires."
            ),
            "evidence_2_page": 7,
            "evidence_3": (
                "Goodyear warns that tighter greenhouse-gas regulation or cap-and-"
                "trade rules could force higher capex, emissions-credit purchases, "
                "or manufacturing restructuring."
            ),
            "evidence_3_page": 21,
        },
        "Continental": {
            "report_year": 2025,
            "report_summary": (
                "Continental's 2025 report shows clear operational decarbonization "
                "progress, zero market-based Scope 2 electricity emissions, and hard "
                "materials targets for the tire business. The sustainability story "
                "is strong, but comparability is affected by the post-spin-off "
                "reporting reset."
            ),
            "evidence_1": (
                "Combined own Scope 1 and market-based Scope 2 emissions fell to "
                "0.707 million tCO2e in 2025, and market-based Scope 2 emissions "
                "from purchased electricity were zero."
            ),
            "evidence_1_page": 40,
            "evidence_2": (
                "Continental is developing tires with renewable and recycled "
                "materials and kept its tire-material target aligned to circularity "
                "and lower-impact production."
            ),
            "evidence_2_page": 41,
            "evidence_3": (
                "Continental says the Aumovio spin-off materially affects "
                "sustainability metrics and comparability, so 2025 progress needs to "
                "be read in the context of the transformation."
            ),
            "evidence_3_page": 96,
        },
        "Bridgestone": {
            "report_year": 2025,
            "report_summary": (
                "Bridgestone's 2025 report presents sustainability as core strategy, "
                "with Scope 1 and 2 emissions already down beyond its mid-term "
                "target and circularity moving into industrial recycling programs. "
                "Execution risk now sits in scaling circular systems and managing "
                "emerging environmental requirements."
            ),
            "evidence_1": (
                "Bridgestone says its 2024 Scope 1 and 2 CO2 emissions were down "
                "62% versus 2011, beating its mid-term target for the second year in "
                "a row."
            ),
            "evidence_1_page": 38,
            "evidence_2": (
                "Its precise-pyrolysis work is designed to turn end-of-life tires "
                "into tire-derived oil and recovered carbon black for reuse."
            ),
            "evidence_2_page": 32,
            "evidence_3": (
                "Bridgestone flags tire-particle regulation, EUDR compliance, and "
                "cyber risk as priority global management risks."
            ),
            "evidence_3_page": 7,
        },
    },
    "products.csv": {
        "Michelin": {
            "report_year": 2025,
            "report_summary": (
                "Michelin's 2025 report shows a clearly premium-skewed portfolio "
                "with continued growth in 18-inch-plus passenger tires, strong "
                "OEM positions in China, and deliberate pruning of lower-tier "
                "volume. The portfolio is increasingly value-driven and EV-relevant, "
                "but also more selective."
            ),
            "evidence_1": (
                "Eighteen-inch and larger tires now represent 68% of Michelin's "
                "Automotive tire sales, reinforcing the group's premium positioning."
            ),
            "evidence_1_page": 15,
            "evidence_2": (
                "Michelin says Chinese OEMs now account for the majority of its OE "
                "volumes sold in China, with strong growth in electric powertrains."
            ),
            "evidence_2_page": 16,
            "evidence_3": (
                "Michelin is actively reducing Tier 2 and Tier 3 exposure where "
                "budget imports pressure the market, making the portfolio more "
                "selective by design."
            ),
            "evidence_3_page": 15,
        },
        "Goodyear": {
            "report_year": 2024,
            "report_summary": (
                "Goodyear's 2024 report describes a broad branded portfolio across "
                "consumer, commercial, and specialty tires, with retreads and "
                "services still important to the mix. Product momentum is strongest "
                "in EV-related OE fitments and newer premium and sustainable-material "
                "launches."
            ),
            "evidence_1": (
                "Goodyear's Americas lineup spans Assurance, Eagle, Wrangler, "
                "WinterCommand, Cooper, and Mickey Thompson lines plus commercial "
                "tires, retreads, and service solutions."
            ),
            "evidence_1_page": 7,
            "evidence_2": (
                "Asia Pacific OE volume rose on consumer EV fitments in China, "
                "showing where Goodyear's EV-related product strategy is gaining "
                "traction."
            ),
            "evidence_2_page": 40,
            "evidence_3": (
                "Goodyear says it must keep modernizing plants to grow premium "
                "large-rim tire capacity, but those projects and closures can "
                "temporarily disrupt operations."
            ),
            "evidence_3_page": 15,
        },
        "Continental": {
            "report_year": 2025,
            "report_summary": (
                "Continental's 2025 report positions Tires as a premium portfolio "
                "spanning passenger, truck, bus, two-wheeler, and specialty "
                "segments, increasingly paired with digital services. Growth is tied "
                "to UHP, EV, and replacement demand, while weaker OE and truck "
                "markets remain the main drag."
            ),
            "evidence_1": (
                "Tires is described as a premium portfolio across passenger car, "
                "truck, bus, two-wheeler, and specialty segments, plus digital tire "
                "services for fleets and dealers."
            ),
            "evidence_1_page": 33,
            "evidence_2": (
                "Seventeen of the world's 20 highest-volume EV manufacturers use "
                "Continental tires, and growth is being driven by UHP tires and "
                "data-based tire services."
            ),
            "evidence_2_page": 35,
            "evidence_3": (
                "Weak original-equipment demand for passenger cars and softer truck "
                "markets offset replacement growth and positive mix in 2025."
            ),
            "evidence_3_page": 48,
        },
        "Bridgestone": {
            "report_year": 2025,
            "report_summary": (
                "Bridgestone's 2025 report centers the portfolio on premium tires as "
                "the core business, supported by solutions and selected exploratory "
                "bets like recycling. OEM strategy is increasingly concentrated on "
                "premium vehicles, prestige OEMs, and ENLITEN-equipped EV programs."
            ),
            "evidence_1": (
                "Bridgestone defines the premium tire business as its core across "
                "passenger, truck and bus, and specialty tires."
            ),
            "evidence_1_page": 3,
            "evidence_2": (
                "Bridgestone is expanding ENLITEN in premium vehicles, prestige "
                "OEMs, and premium EVs, reaching 124 vehicle programs by the end of "
                "Q1 2025."
            ),
            "evidence_2_page": 22,
            "evidence_3": (
                "Management says Chinese EV growth and low-end imports are reshaping "
                "competition and forcing tighter premium-focused portfolio actions."
            ),
            "evidence_3_page": 14,
        },
    },
}


def validate_report_pages(brand: str, curated_fields: dict[str, object]) -> None:
    report_file = REPORT_FILES[brand]
    report_path = REPORT_DIR / report_file
    if not report_path.exists():
        raise FileNotFoundError(f"Missing report for {brand}: {report_path}")

    document = fitz.open(report_path)
    try:
        for field_name in ("evidence_1_page", "evidence_2_page", "evidence_3_page"):
            page_number = int(curated_fields[field_name])
            if page_number < 1 or page_number > document.page_count:
                raise ValueError(
                    f"{brand} cites page {page_number}, but {report_file} only has "
                    f"{document.page_count} pages."
                )
            page_text = document[page_number - 1].get_text("text").strip()
            if not page_text:
                raise ValueError(
                    f"{brand} cites page {page_number} in {report_file}, but "
                    "PyMuPDF did not extract any text from that page."
                )
    finally:
        document.close()


def enrich_dataset(dataset_name: str, curated_rows: dict[str, dict[str, object]]) -> None:
    dataset_path = DATA_DIR / dataset_name
    dataframe = pd.read_csv(dataset_path)

    for brand, fields in curated_rows.items():
        validate_report_pages(brand, fields)

    curated_frame = (
        pd.DataFrame.from_dict(curated_rows, orient="index")
        .reset_index()
        .rename(columns={"index": "brand"})
    )

    merged = dataframe.drop(columns=COMMON_COLUMNS, errors="ignore").merge(
        curated_frame,
        on="brand",
        how="left",
        validate="one_to_one",
    )

    missing = merged[COMMON_COLUMNS].isna().any(axis=1)
    if missing.any():
        brands = ", ".join(merged.loc[missing, "brand"].astype(str).tolist())
        raise ValueError(f"Missing curated report evidence for: {brands}")

    ordered_columns = [
        column for column in dataframe.columns if column not in COMMON_COLUMNS
    ] + COMMON_COLUMNS
    merged[ordered_columns].to_csv(dataset_path, index=False)


def main() -> None:
    for dataset_name, curated_rows in CURATED_REPORT_DATA.items():
        enrich_dataset(dataset_name, curated_rows)
        print(f"Updated {dataset_name}")


if __name__ == "__main__":
    main()
