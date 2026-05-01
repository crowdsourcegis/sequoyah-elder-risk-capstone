"""
CENSUS DATA ACQUISITION ENGINE v5
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ACS 5-Year 2024
Author: Luke A. Lynch
Date: 2026-03-02

This script acquires the ACS inputs used by the Sequoyah County elder-risk
workflow. It pulls the required ACS 5-year 2024 tables, writes raw extracts,
builds clean generator-ready CSVs, and prepares table-specific references for
paper documentation.

The point of this script is controlled ACS acquisition and transformation. It
does not generate synthetic people, score elder records, calculate reason
codes, or run ArcGIS accessibility analysis.

Reviewer setup note:
- No secrets are committed in this repository.
- Provide your own U.S. Census API key before running this script.
- Preferred: set env var `CENSUS_API_KEY` (or add it to a local `.env` file).
- Fallback: directly set `API_KEY = "your_key_here"` below for local-only testing.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

import pandas as pd
import requests
from dotenv import load_dotenv

# PARAMETERS START
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

API_KEY = os.getenv("CENSUS_API_KEY")
API_BASE = "https://api.census.gov/data/2024/acs/acs5"
DATA_CENSUS_BASE = "https://data.census.gov/table"

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
RAW_DIR = OUTPUT_DIR / "raw_acs"

STATE = "40"
COUNTY = "135"
ZCTAS = "74948,74435,74931,74954,74936,74955,74962"
COUNTY_NAME = "Sequoyah"
STATE_NAME = "Oklahoma"

CITY_LOOKUP = {
    "74435": "Gore",
    "74931": "Bunch",
    "74936": "Gans",
    "74948": "Muldrow",
    "74954": "Roland",
    "74955": "Sallisaw",
    "74962": "Vian",
}

TABLE_TITLES = {
    "B01001": "Sex by Age",
    "B12002": "Sex by Marital Status by Age for the Population 15 Years and Over",
    "B28005": "Age by Presence of a Computer and Types of Internet Subscription",
    "B18101": "Sex by Age by Disability Status",
    "B17020": "Poverty Status in the Past 12 Months by Age",
    "B11010": "Nonfamily Households by Sex of Householder by Living Alone by Age of Householder",
}

TARGETS = [
    ("B01001", "zcta", TABLE_TITLES["B01001"]),
    ("B12002", "zcta", TABLE_TITLES["B12002"]),
    ("B28005", "zcta", TABLE_TITLES["B28005"]),
    ("B18101", "zcta", TABLE_TITLES["B18101"]),
    ("B17020", "zcta", TABLE_TITLES["B17020"]),
    ("B11010", "zcta", TABLE_TITLES["B11010"]),
]

GEO_MAP = {
    "zcta": {
        "for": f"zip code tabulation area:{ZCTAS}",
    },
    "tract": {
        "for": "tract:*",
        "in": f"state:{STATE} county:{COUNTY}",
    },
}
# PARAMETERS END


def safe_int(row: pd.Series, col: str) -> int:
    val = row.get(col, 0)
    try:
        if pd.isna(val):
            return 0
        return int(float(val))
    except (TypeError, ValueError):
        return 0


def safe_rate(num: int | float, den: int | float) -> float:
    if den in (0, None) or pd.isna(den):
        return 0.0
    return round(float(num) / float(den), 4)


def zcta_from_row(row: pd.Series) -> str:
    return str(row["zip code tabulation area"]).zfill(5)


def base_record(row: pd.Series) -> dict:
    z = zcta_from_row(row)
    return {
        "Zip": z,
        "City": CITY_LOOKUP.get(z, ""),
    }


def safe_write_csv(df: pd.DataFrame, path: Path) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        df.to_csv(temp_path, index=False)
        temp_path.replace(path)
    except PermissionError:
        raise PermissionError(
            f"Could not write {path}. The file is probably open in Excel, ArcGIS, or another program."
        )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def safe_write_text(text: str, path: Path) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        temp_path.write_text(text, encoding="utf-8")
        temp_path.replace(path)
    except PermissionError:
        raise PermissionError(
            f"Could not write {path}. The file is probably open in another program."
        )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def acquire(table: str, geo: str) -> pd.DataFrame | None:
    params = {
        "get": f"NAME,group({table})",
        "key": API_KEY,
    }
    params.update(GEO_MAP[geo])

    try:
        response = requests.get(API_BASE, params=params, timeout=60)
    except requests.RequestException as exc:
        print(f"REQUEST ERROR {table}: {exc}")
        return None

    if response.status_code != 200:
        print(f"HTTP {response.status_code} {table}: {response.text[:300]}")
        return None

    data = response.json()
    if not data or len(data) < 2:
        print(f"EMPTY RESPONSE {table}")
        return None

    header, *rows = data
    df = pd.DataFrame(rows, columns=header)

    prefix = table.split()[0]
    estimate_cols = [
        col for col in header
        if col.startswith(prefix)
        and col.endswith("E")
        and not col.endswith("EA")
        and not col.endswith("MA")
    ]
    id_cols = [col for col in header if not col.startswith(prefix)]

    df = df[id_cols + estimate_cols]
    df[estimate_cols] = df[estimate_cols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)
    return df


def transform_b01001(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)

        male_65_69 = safe_int(row, "B01001_020E") + safe_int(row, "B01001_021E")
        female_65_69 = safe_int(row, "B01001_044E") + safe_int(row, "B01001_045E")

        rec.update({
            "TotalPopulation": safe_int(row, "B01001_001E"),
            "Male65_69": male_65_69,
            "Male70_74": safe_int(row, "B01001_022E"),
            "Male75_79": safe_int(row, "B01001_023E"),
            "Male80_84": safe_int(row, "B01001_024E"),
            "Male85Plus": safe_int(row, "B01001_025E"),
            "Female65_69": female_65_69,
            "Female70_74": safe_int(row, "B01001_046E"),
            "Female75_79": safe_int(row, "B01001_047E"),
            "Female80_84": safe_int(row, "B01001_048E"),
            "Female85Plus": safe_int(row, "B01001_049E"),
        })

        rec["Male65Plus"] = rec["Male65_69"] + rec["Male70_74"] + rec["Male75_79"] + rec["Male80_84"] + rec["Male85Plus"]
        rec["Female65Plus"] = rec["Female65_69"] + rec["Female70_74"] + rec["Female75_79"] + rec["Female80_84"] + rec["Female85Plus"]
        rec["Total65Plus"] = rec["Male65Plus"] + rec["Female65Plus"]
        rec["SourceTable"] = "ACS B01001 Sex by Age"
        records.append(rec)

    return pd.DataFrame(records)


def transform_b12002(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)

        male_never = safe_int(row, "B12002_015E") + safe_int(row, "B12002_016E") + safe_int(row, "B12002_017E")
        male_married = (
            safe_int(row, "B12002_031E") + safe_int(row, "B12002_032E") + safe_int(row, "B12002_033E") +
            safe_int(row, "B12002_062E") + safe_int(row, "B12002_063E") + safe_int(row, "B12002_064E")
        )
        male_separated = safe_int(row, "B12002_047E") + safe_int(row, "B12002_048E") + safe_int(row, "B12002_049E")
        male_widowed = safe_int(row, "B12002_077E") + safe_int(row, "B12002_078E") + safe_int(row, "B12002_079E")
        male_divorced = safe_int(row, "B12002_092E") + safe_int(row, "B12002_093E") + safe_int(row, "B12002_094E")

        female_never = safe_int(row, "B12002_108E") + safe_int(row, "B12002_109E") + safe_int(row, "B12002_110E")
        female_married = (
            safe_int(row, "B12002_124E") + safe_int(row, "B12002_125E") + safe_int(row, "B12002_126E") +
            safe_int(row, "B12002_155E") + safe_int(row, "B12002_156E") + safe_int(row, "B12002_157E")
        )
        female_separated = safe_int(row, "B12002_140E") + safe_int(row, "B12002_141E") + safe_int(row, "B12002_142E")
        female_widowed = safe_int(row, "B12002_170E") + safe_int(row, "B12002_171E") + safe_int(row, "B12002_172E")
        female_divorced = safe_int(row, "B12002_185E") + safe_int(row, "B12002_186E") + safe_int(row, "B12002_187E")

        male_total = male_never + male_married + male_separated + male_widowed + male_divorced
        female_total = female_never + female_married + female_separated + female_widowed + female_divorced

        rec.update({
            "MaleNeverMarried65": male_never,
            "MaleMarried65": male_married,
            "MaleSeparated65": male_separated,
            "MaleWidowed65": male_widowed,
            "MaleDivorced65": male_divorced,
            "MaleMaritalTotal65": male_total,
            "FemaleNeverMarried65": female_never,
            "FemaleMarried65": female_married,
            "FemaleSeparated65": female_separated,
            "FemaleWidowed65": female_widowed,
            "FemaleDivorced65": female_divorced,
            "FemaleMaritalTotal65": female_total,
            "MaleNeverMarriedRate65": safe_rate(male_never, male_total),
            "MaleMarriedRate65": safe_rate(male_married, male_total),
            "MaleSeparatedRate65": safe_rate(male_separated, male_total),
            "MaleWidowedRate65": safe_rate(male_widowed, male_total),
            "MaleDivorcedRate65": safe_rate(male_divorced, male_total),
            "FemaleNeverMarriedRate65": safe_rate(female_never, female_total),
            "FemaleMarriedRate65": safe_rate(female_married, female_total),
            "FemaleSeparatedRate65": safe_rate(female_separated, female_total),
            "FemaleWidowedRate65": safe_rate(female_widowed, female_total),
            "FemaleDivorcedRate65": safe_rate(female_divorced, female_total),
            "SourceTable": "ACS B12002 Sex by Marital Status by Age",
        })
        records.append(rec)

    return pd.DataFrame(records)


def transform_b28005(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)
        total_65 = safe_int(row, "B28005_014E")
        has_computer_65 = safe_int(row, "B28005_015E")
        broadband_65 = safe_int(row, "B28005_016E")
        cellular_only_65 = safe_int(row, "B28005_017E")
        no_computer_65 = safe_int(row, "B28005_018E")
        has_internet_65 = broadband_65 + cellular_only_65

        rec.update({
            "Total65Plus": total_65,
            "HasComputer65": has_computer_65,
            "BroadbandSubscription65": broadband_65,
            "CellularOnly65": cellular_only_65,
            "NoComputer65": no_computer_65,
            "HasInternet65": has_internet_65,
            "HasInternetRate65": safe_rate(has_internet_65, total_65),
            "NoComputerRate65": safe_rate(no_computer_65, total_65),
            "SourceTable": "ACS B28005 Age by Presence of a Computer and Types of Internet Subscription",
        })
        records.append(rec)

    return pd.DataFrame(records)


def transform_b18101(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)

        male_65_74_total = safe_int(row, "B18101_012E")
        male_65_74_disabled = safe_int(row, "B18101_013E")
        male_75_total = safe_int(row, "B18101_015E")
        male_75_disabled = safe_int(row, "B18101_016E")
        female_65_74_total = safe_int(row, "B18101_031E")
        female_65_74_disabled = safe_int(row, "B18101_032E")
        female_75_total = safe_int(row, "B18101_034E")
        female_75_disabled = safe_int(row, "B18101_035E")

        total_65 = male_65_74_total + male_75_total + female_65_74_total + female_75_total
        disabled_65 = male_65_74_disabled + male_75_disabled + female_65_74_disabled + female_75_disabled

        rec.update({
            "Male65_74Total": male_65_74_total,
            "Male65_74Disabled": male_65_74_disabled,
            "Male65_74DisabilityRate": safe_rate(male_65_74_disabled, male_65_74_total),
            "Male75PlusTotal": male_75_total,
            "Male75PlusDisabled": male_75_disabled,
            "Male75PlusDisabilityRate": safe_rate(male_75_disabled, male_75_total),
            "Female65_74Total": female_65_74_total,
            "Female65_74Disabled": female_65_74_disabled,
            "Female65_74DisabilityRate": safe_rate(female_65_74_disabled, female_65_74_total),
            "Female75PlusTotal": female_75_total,
            "Female75PlusDisabled": female_75_disabled,
            "Female75PlusDisabilityRate": safe_rate(female_75_disabled, female_75_total),
            "Total65Plus": total_65,
            "Disabled65Plus": disabled_65,
            "DisabilityRate65Plus": safe_rate(disabled_65, total_65),
            "SourceTable": "ACS B18101 Sex by Age by Disability Status",
        })
        records.append(rec)

    return pd.DataFrame(records)


def transform_b17020(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)

        below_60_74 = safe_int(row, "B17020_007E")
        below_75 = safe_int(row, "B17020_008E")
        above_60_74 = safe_int(row, "B17020_016E")
        above_75 = safe_int(row, "B17020_017E")
        total_60_74 = below_60_74 + above_60_74
        total_75 = below_75 + above_75

        rec.update({
            "BelowPoverty60_74": below_60_74,
            "AbovePoverty60_74": above_60_74,
            "PovertyUniverse60_74": total_60_74,
            "PovertyRate60_74": safe_rate(below_60_74, total_60_74),
            "BelowPoverty75Plus": below_75,
            "AbovePoverty75Plus": above_75,
            "PovertyUniverse75Plus": total_75,
            "PovertyRate75Plus": safe_rate(below_75, total_75),
            "BelowPoverty60Plus": below_60_74 + below_75,
            "PovertyUniverse60Plus": total_60_74 + total_75,
            "PovertyRate60Plus": safe_rate(below_60_74 + below_75, total_60_74 + total_75),
            "GeneratorNote": "Use 60-74 rate for synthetic ages 65-74; use 75+ rate for synthetic ages 75+",
            "SourceTable": "ACS B17020 Poverty Status in the Past 12 Months by Age",
        })
        records.append(rec)

    return pd.DataFrame(records)


def transform_b11010(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, row in df.iterrows():
        rec = base_record(row)

        male_living_alone = safe_int(row, "B11010_005E")
        male_not_living_alone = safe_int(row, "B11010_008E")
        female_living_alone = safe_int(row, "B11010_012E")
        female_not_living_alone = safe_int(row, "B11010_015E")

        male_total = male_living_alone + male_not_living_alone
        female_total = female_living_alone + female_not_living_alone
        living_alone_total = male_living_alone + female_living_alone
        not_living_alone_total = male_not_living_alone + female_not_living_alone
        household_total = male_total + female_total

        rec.update({
            "MaleLivingAlone65": male_living_alone,
            "MaleNotLivingAlone65": male_not_living_alone,
            "MaleHouseholder65Total": male_total,
            "FemaleLivingAlone65": female_living_alone,
            "FemaleNotLivingAlone65": female_not_living_alone,
            "FemaleHouseholder65Total": female_total,
            "LivingAlone65Total": living_alone_total,
            "NotLivingAlone65Total": not_living_alone_total,
            "Householder65Total": household_total,
            "MaleLivingAloneRate65": safe_rate(male_living_alone, male_total),
            "FemaleLivingAloneRate65": safe_rate(female_living_alone, female_total),
            "LivingAloneRate65": safe_rate(living_alone_total, household_total),
            "GeneratorUse": "Calibrate LivesAlone among eligible non-married synthetic elders; do not alter B01001 population counts",
            "SourceTable": "ACS B11010 Nonfamily Households by Sex of Householder by Living Alone by Age of Householder",
        })
        records.append(rec)

    out = pd.DataFrame(records)
    if out["FemaleHouseholder65Total"].sum() == 0:
        raise ValueError("B11010 validation failed: female 65+ totals summed to zero")
    return out


TRANSFORMS: dict[str, Callable[[pd.DataFrame], pd.DataFrame]] = {
    "B01001": transform_b01001,
    "B12002": transform_b12002,
    "B28005": transform_b28005,
    "B18101": transform_b18101,
    "B17020": transform_b17020,
    "B11010": transform_b11010,
}


def build_table_url(table: str, title: str) -> str:
    query = quote_plus(f"{table}: {title}")
    return f"{DATA_CENSUS_BASE}/ACSDT5Y2024.{table}?q={query}"


def write_apa_citations() -> None:
    access_date = datetime.now().strftime("%B %d, %Y")
    lines = ["Data References:", ""]

    for table, _, _ in TARGETS:
        title = TABLE_TITLES[table]
        url = build_table_url(table, title)
        citation = (
            f"U.S. Census Bureau. (n.d.). {title}. American Community Survey, "
            f"ACS 5-Year Estimates Detailed Tables, Table {table}. "
            f"Retrieved {access_date}, from {url}"
        )
        lines.append(citation)
        lines.append("")

    safe_write_text("\n".join(lines), OUTPUT_DIR / "acs_apa_citation.txt")


def write_methods_note() -> None:
    access_date = datetime.now().strftime("%B %d, %Y")
    text = f"""ACS source note

Data for this project were retrieved from the U.S. Census Bureau American Community Survey 5-year estimates detailed tables for 2024.
Geography queried: ZIP Code Tabulation Areas in {COUNTY_NAME} County, {STATE_NAME}.
FIPS: state {STATE}, county {COUNTY}.
ZCTAs queried: {ZCTAS}.
Tables queried: {', '.join(t[0] for t in TARGETS)}.
Access date: {access_date}.
API endpoint: {API_BASE}

Suggested paper-ready references are written separately to acs_apa_citation.txt.
"""
    safe_write_text(text, OUTPUT_DIR / "acs_sources.md")


def execute() -> None:
    if not API_KEY:
        sys.exit(
            "FATAL: CENSUS_API_KEY is not set. Add it to your environment or local .env, "
            "or temporarily set API_KEY directly in this script for local review."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    acquired: dict[str, int] = {}
    failed: list[str] = []

    for table, geo, label in TARGETS:
        print(f"  {table:8} {label:60}", end="  ")
        raw_df = acquire(table, geo)
        if raw_df is None:
            failed.append(table)
            print("FAILED")
            continue

        raw_path = RAW_DIR / f"{table}_{COUNTY_NAME.lower()}_raw.csv"
        safe_write_csv(raw_df, raw_path)

        try:
            clean_df = TRANSFORMS[table](raw_df)
        except Exception as exc:
            failed.append(table)
            print(f"FAILED TRANSFORM: {exc}")
            continue

        clean_path = OUTPUT_DIR / f"{table}_{COUNTY_NAME.lower()}.csv"
        try:
            safe_write_csv(clean_df, clean_path)
        except PermissionError as exc:
            failed.append(table)
            print(f"FAILED WRITE: {exc}")
            continue

        acquired[table] = len(clean_df)
        print(f"{len(clean_df)} rows -> {clean_path.name}")

    write_apa_citations()
    write_methods_note()

    print("=" * 72)
    print(f"  ACQUIRED: {len(acquired)}/{len(TARGETS)}")
    if failed:
        print(f"  FAILED:   {', '.join(failed)}")
    print(f"  CLEAN:    {OUTPUT_DIR}")
    print(f"  RAW:      {RAW_DIR}")
    print(f"  APA:      {OUTPUT_DIR / 'acs_apa_citation.txt'}")
    print(f"  METHODS:  {OUTPUT_DIR / 'acs_sources.md'}")


if __name__ == "__main__":
    print("=" * 72)
    print("  CENSUS ACQUISITION ENGINE v5")
    print("=" * 72)
    print(f"  Target: {COUNTY_NAME} County, OK")
    print(f"  FIPS:   {STATE}{COUNTY}")
    print(f"  ACS:    2024 5-year")
    print(f"  ZCTAs:  {ZCTAS}")
    print(f"  Tables: {len(TARGETS)} ({', '.join(t[0] for t in TARGETS)})")
    print("=" * 72)
    execute()

