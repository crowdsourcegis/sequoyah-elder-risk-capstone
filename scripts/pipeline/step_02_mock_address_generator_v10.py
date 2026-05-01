"""
MOCK ADDRESS GENERATOR v10
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ACS 5-Year 2024
Author: Luke A. Lynch
Date: 2026-02-28

v10 uses the clean 2024 ACS-derived schemas produced by step_01_census_query_v5.py.
It reads named columns from cleaned CSVs instead of raw Census API variable IDs.
B01001 remains the population control for total synthetic elder counts by ZIP,
sex, and age band. B11010 is used only to shape LivesAlone among already
created non-married elders and never creates or removes synthetic people.

The generator preserves address-point geocoding, deterministic RNG, married
couple address sharing, and ArcGIS-friendly schema.ini output. It adds auditable
household placement fields and writes validation CSVs for methodology support.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from itertools import count
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd

# PARAMETERS START
GENERATOR_VERSION = "V10"
RNG_SEED = 42
AS_OF_DATE = date(2026, 3, 10)
STATE = "OK"

OUTPUT_DIR = Path(r"G:\03_Projects\PSU_Stuff\CAPSTONE\Data\census_project\output")
OUTPUT_CSV_PATH = OUTPUT_DIR / "mock_address_generator_v10.csv"
ADDRESS_POINTS_SHP = Path(r"G:\03_Projects\PSU_Stuff\CAPSTONE\Data\census_project\docs\residential_points")

B01001CSV = OUTPUT_DIR / "B01001_sequoyah.csv"
B12002CSV = OUTPUT_DIR / "B12002_sequoyah.csv"
B28005CSV = OUTPUT_DIR / "B28005_sequoyah.csv"
B18101CSV = OUTPUT_DIR / "B18101_sequoyah.csv"
B17020CSV = OUTPUT_DIR / "B17020_sequoyah.csv"
B11010CSV = OUTPUT_DIR / "B11010_sequoyah.csv"

AGEBANDS = ((65, 69), (70, 74), (75, 79), (80, 84))
AGEBAND_LABELS = ["65-69", "70-74", "75-79", "80-84", "85+"]
AGE_SCORE = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4}
AGE85PLUS = np.arange(85, 105)
AGE85PLUS_WEIGHTS = np.exp(-0.15 * (AGE85PLUS - 85))
AGE85PLUS_PROBS = AGE85PLUS_WEIGHTS / AGE85PLUS_WEIGHTS.sum()

MARITAL_CATEGORIES = ["Married", "Widowed", "Divorced", "Separated", "Never Married"]
NON_MARRIED = {"Widowed", "Divorced", "Separated", "Never Married"}
SERVICES = ["Meals on Wheels", "Home Care", "Medical Checkup", "None"]
YESNO = ["Yes", "No"]
NOTES = [
    "Family support", "Health concerns", "Socially active", "Mobility issues",
    "No issues", "Limited income", "Regular calls", "Volunteers",
    "Needs assistance", "Recently hospitalized", "Isolated", "Church group",
]
FAKE_STREET_NAMES = [
    "Cedar Hollow Rd", "Prairie View Ln", "Redbird Loop", "Mockingbird Dr",
    "Oak Ridge Rd", "Maple Crossing", "Pine Valley Rd", "River Bend Ln",
    "Sequoyah View Dr", "Dogwood Creek Rd", "Hilltop Loop", "Meadow Branch Rd",
    "Walnut Grove Ln", "Cottonwood Trail", "Bluebird Way", "Rural Route",
]

MULTI_ELDER_RATE = 0.05
MULTI_ELDER_TRIPLE_PROB = 0.20

CSVHEADER = [
    "ID", "MockAddress", "Age", "AgeBand", "AgeScore", "Gender", "MaritalStatus",
    "City", "State", "Zip", "HasInternet", "HasCell", "HasEmail", "HasDisability",
    "LivesAlone", "InPoverty", "LastContactDate", "APSReferral", "FallHistory",
    "CognitiveFlag", "ServiceUse", "InactiveBenefits", "Notes", "RefusesMedicalHelp",
    "POAActive", "UnusualWealth", "HospiceAssigned", "HospiceDurationMonths",
    "PreviousInvestigationCount", "CurrentInvestigation", "InvestigationStartDate",
    "VeteranStatus", "Longitude", "Latitude", "HouseholdID", "AddressPointID",
    "HouseholdSize", "HouseholdType", "PlacementRule", "GeneratorVersion", "AsOfDate",
    "AddressIsSynthetic",
]

REQUIRED_COLUMNS = {
    "B01001": [
        "Zip", "City", "TotalPopulation", "Male65_69", "Male70_74", "Male75_79",
        "Male80_84", "Male85Plus", "Female65_69", "Female70_74", "Female75_79",
        "Female80_84", "Female85Plus", "Male65Plus", "Female65Plus", "Total65Plus",
    ],
    "B12002": [
        "Zip", "MaleNeverMarriedRate65", "MaleMarriedRate65", "MaleSeparatedRate65",
        "MaleWidowedRate65", "MaleDivorcedRate65", "FemaleNeverMarriedRate65",
        "FemaleMarriedRate65", "FemaleSeparatedRate65", "FemaleWidowedRate65",
        "FemaleDivorcedRate65",
    ],
    "B28005": ["Zip", "HasInternetRate65", "NoComputerRate65", "Total65Plus"],
    "B18101": [
        "Zip", "Male65_74DisabilityRate", "Male75PlusDisabilityRate",
        "Female65_74DisabilityRate", "Female75PlusDisabilityRate", "DisabilityRate65Plus",
    ],
    "B17020": ["Zip", "PovertyRate60_74", "PovertyRate75Plus", "PovertyRate60Plus"],
    "B11010": [
        "Zip", "MaleLivingAloneRate65", "FemaleLivingAloneRate65", "LivingAloneRate65",
        "MaleHouseholder65Total", "FemaleHouseholder65Total", "Householder65Total",
    ],
}
# PARAMETERS END

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(funcName)s: %(message)s")
rng = np.random.default_rng(RNG_SEED)


def safe_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def safe_float(value: Any, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clean_zip(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(5)[-5:]


def validate_rate(value: float, table: str, column: str, zipcode: str) -> float:
    if not 0 <= value <= 1:
        raise ValueError(f"{table} {column} for ZIP {zipcode} is outside 0-1: {value}")
    return value


def read_clean_csv(path: Path, table_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing ACS input: {path}")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS[table_name] if c not in df.columns]
    if missing:
        raise ValueError(f"{table_name} is missing required clean columns: {missing}")
    df["Zip"] = df["Zip"].map(clean_zip)
    if df["Zip"].duplicated().any():
        duplicated = df.loc[df["Zip"].duplicated(), "Zip"].tolist()
        raise ValueError(f"{table_name} contains duplicate ZIP rows: {duplicated}")
    return df


def assert_zip_coverage(zips: set[str], tables: dict[str, pd.DataFrame]) -> None:
    for table_name, df in tables.items():
        missing = sorted(zips - set(df["Zip"]))
        if missing:
            raise ValueError(f"{table_name} is missing ZIPs required by B01001: {missing}")


def rows_by_zip(df: pd.DataFrame) -> dict[str, pd.Series]:
    return {row["Zip"]: row for _, row in df.iterrows()}


def load_acs_inputs() -> dict[str, dict[str, pd.Series]]:
    frames = {
        "B01001": read_clean_csv(B01001CSV, "B01001"),
        "B12002": read_clean_csv(B12002CSV, "B12002"),
        "B28005": read_clean_csv(B28005CSV, "B28005"),
        "B18101": read_clean_csv(B18101CSV, "B18101"),
        "B17020": read_clean_csv(B17020CSV, "B17020"),
        "B11010": read_clean_csv(B11010CSV, "B11010"),
    }
    zips = set(frames["B01001"]["Zip"])
    assert_zip_coverage(zips, frames)
    return {name: rows_by_zip(df) for name, df in frames.items()}


def resolve_shapefile(path: Path) -> Path:
    if path.is_file() and path.suffix.lower() == ".shp":
        return path
    if path.is_dir():
        shp_files = sorted(path.glob("*.shp"))
        if len(shp_files) == 1:
            return shp_files[0]
        if len(shp_files) > 1:
            raise ValueError(f"Multiple shapefiles found in {path}; set ADDRESS_POINTS_SHP to one .shp")
    raise FileNotFoundError(f"Address point shapefile not found: {path}")


def find_zip_column(gdf: gpd.GeoDataFrame) -> str:
    candidates = ["zipcode", "ZIPCODE", "Zip", "ZIP", "zip", "ZCTA", "ZCTA5CE20", "POSTAL", "POSTCODE"]
    for col in candidates:
        if col in gdf.columns:
            return col
    lower = {col.lower(): col for col in gdf.columns}
    for key in ("zipcode", "zip", "zcta"):
        if key in lower:
            return lower[key]
    raise ValueError("Address points need a ZIP-like column such as zipcode or ZIP")


def find_id_column(gdf: gpd.GeoDataFrame) -> str | None:
    candidates = ["AddressPointID", "ADDRESSID", "ADDR_ID", "POINTID", "OBJECTID", "FID"]
    for col in candidates:
        if col in gdf.columns:
            return col
    return None


def load_address_points(required_zips: set[str]) -> gpd.GeoDataFrame:
    shp = resolve_shapefile(ADDRESS_POINTS_SHP)
    gdf = gpd.read_file(shp)
    if gdf.empty:
        raise ValueError(f"Address point layer is empty: {shp}")
    zip_col = find_zip_column(gdf)
    gdf["Zip"] = gdf[zip_col].map(clean_zip)
    gdf = gdf[gdf["Zip"].isin(required_zips)].copy()
    if gdf.empty:
        raise ValueError("No address points match the ACS ZIP list")
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    id_col = find_id_column(gdf)
    if id_col:
        gdf["AddressPointID"] = gdf.apply(lambda r: f"AP_{r['Zip']}_{r[id_col]}", axis=1)
    else:
        gdf["AddressPointID"] = [f"AP_{z}_{i:06d}" for i, z in zip(gdf.index, gdf["Zip"])]
    missing_zips = sorted(required_zips - set(gdf["Zip"]))
    if missing_zips:
        raise ValueError(f"No residential address points found for ZIPs: {missing_zips}")
    return gdf[["Zip", "AddressPointID", "geometry"]].copy()


class AddressPointAllocator:
    def __init__(self, gdf: gpd.GeoDataFrame) -> None:
        self.points: dict[str, pd.DataFrame] = {}
        self.cursor: dict[str, int] = {}
        self.overflow_counts: Counter[str] = Counter()
        for zipcode, group in gdf.groupby("Zip"):
            order = rng.permutation(len(group))
            shuffled = group.iloc[order].reset_index(drop=True)
            self.points[zipcode] = shuffled
            self.cursor[zipcode] = 0

    def assign(self, zipcode: str) -> dict[str, Any]:
        if zipcode not in self.points or self.points[zipcode].empty:
            raise ValueError(f"No address points available for ZIP {zipcode}")
        group = self.points[zipcode]
        idx = self.cursor[zipcode]
        overflow = idx >= len(group)
        if overflow:
            idx = int(rng.integers(0, len(group)))
            self.overflow_counts[zipcode] += 1
        else:
            self.cursor[zipcode] += 1
        row = group.iloc[idx]
        pt = row.geometry
        return {
            "AddressPointID": row["AddressPointID"],
            "Longitude": float(pt.x),
            "Latitude": float(pt.y),
            "Overflow": overflow,
        }

    def available_count(self, zipcode: str) -> int:
        return len(self.points.get(zipcode, []))

    def used_unique_count(self, zipcode: str) -> int:
        return min(self.cursor.get(zipcode, 0), self.available_count(zipcode))


def format_date(d: date | datetime) -> str:
    return d.strftime("%m/%d/%Y")


def random_date(start: datetime, end: datetime) -> str:
    delta_days = (end - start).days
    return (start + timedelta(days=int(rng.integers(0, delta_days + 1)))).strftime("%m/%d/%Y")


def age_for_band(band_idx: int) -> int:
    if band_idx <= 3:
        lo, hi = AGEBANDS[band_idx]
        return int(rng.integers(lo, hi + 1))
    return int(rng.choice(AGE85PLUS, p=AGE85PLUS_PROBS))


def allocate_counts(total: int, rates: list[float]) -> list[int]:
    rates_arr = np.array(rates, dtype=float)
    if np.any(rates_arr < 0):
        raise ValueError(f"Negative allocation rate: {rates}")
    if rates_arr.sum() <= 0:
        rates_arr = np.ones_like(rates_arr) / len(rates_arr)
    else:
        rates_arr = rates_arr / rates_arr.sum()
    raw = rates_arr * total
    floors = np.floor(raw).astype(int)
    shortfall = total - int(floors.sum())
    remainders = raw - floors
    for idx in np.argsort(remainders)[::-1][:shortfall]:
        floors[idx] += 1
    return floors.astype(int).tolist()


def marital_rates(row: pd.Series, sex: str, zipcode: str) -> list[float]:
    prefix = "Male" if sex == "Male" else "Female"
    mapping = [
        f"{prefix}MarriedRate65",
        f"{prefix}WidowedRate65",
        f"{prefix}DivorcedRate65",
        f"{prefix}SeparatedRate65",
        f"{prefix}NeverMarriedRate65",
    ]
    return [validate_rate(safe_float(row[col]), "B12002", col, zipcode) for col in mapping]


def make_person(zipcode: str, city: str, sex: str, band_idx: int, marital: str, acs: dict[str, dict[str, pd.Series]]) -> dict[str, Any]:
    age = age_for_band(band_idx)
    b28005 = acs["B28005"][zipcode]
    b18101 = acs["B18101"][zipcode]
    b17020 = acs["B17020"][zipcode]

    internet_prob = validate_rate(safe_float(b28005["HasInternetRate65"]), "B28005", "HasInternetRate65", zipcode)
    disability_col = f"{sex}65_74DisabilityRate" if band_idx <= 1 else f"{sex}75PlusDisabilityRate"
    disability_prob = validate_rate(safe_float(b18101[disability_col]), "B18101", disability_col, zipcode)
    poverty_col = "PovertyRate60_74" if band_idx <= 1 else "PovertyRate75Plus"
    poverty_prob = validate_rate(safe_float(b17020[poverty_col]), "B17020", poverty_col, zipcode)

    has_internet = "Yes" if rng.random() < internet_prob else "No"
    has_disability = "Yes" if rng.random() < disability_prob else "No"
    in_poverty = "Yes" if rng.random() < poverty_prob else "No"

    cell_prob = 0.88 - (band_idx * 0.06) if has_internet == "Yes" else 0.45 - (band_idx * 0.06)
    cell_prob = min(0.95, max(0.12, cell_prob))
    email_prob = 0.78 - (band_idx * 0.08) if has_internet == "Yes" else 0.05
    email_prob = min(0.90, max(0.02, email_prob))

    recent_pct = max(0.30, 0.70 - band_idx * 0.08)
    mid_pct = 0.20 + band_idx * 0.03
    stale_pct = max(0.01, 1.0 - recent_pct - mid_pct)
    probs = np.array([recent_pct, mid_pct, stale_pct], dtype=float)
    probs = probs / probs.sum()
    contact_bucket = rng.choice(["recent", "mid", "stale"], p=probs)
    if contact_bucket == "recent":
        days_ago = int(rng.integers(0, 91))
    elif contact_bucket == "mid":
        days_ago = int(rng.integers(91, 181))
    else:
        days_ago = int(rng.integers(181, 366))

    aps_prob = min(0.40, 0.10 + band_idx * 0.05)
    fall_prob = min(0.50, 0.12 + band_idx * 0.08)
    cog_prob = min(0.45, 0.05 + band_idx * 0.08)
    hospice_assigned = "Yes" if rng.random() < 0.08 else "No"
    current_investigation = "Yes" if rng.random() < 0.12 else "No"

    return {
        "Age": age,
        "AgeBand": AGEBAND_LABELS[band_idx],
        "AgeScore": AGE_SCORE[band_idx],
        "Gender": sex,
        "MaritalStatus": marital,
        "City": city,
        "State": STATE,
        "Zip": zipcode,
        "HasInternet": has_internet,
        "HasCell": "Yes" if rng.random() < cell_prob else "No",
        "HasEmail": "Yes" if rng.random() < email_prob else "No",
        "HasDisability": has_disability,
        "LivesAlone": "No",
        "InPoverty": in_poverty,
        "LastContactDate": format_date(AS_OF_DATE - timedelta(days=days_ago)),
        "APSReferral": "Yes" if rng.random() < aps_prob else "No",
        "FallHistory": "Yes" if rng.random() < fall_prob else "No",
        "CognitiveFlag": "Yes" if rng.random() < cog_prob else "No",
        "ServiceUse": rng.choice(SERVICES),
        "InactiveBenefits": "Yes" if rng.random() < 0.20 else "No",
        "Notes": rng.choice(NOTES),
        "RefusesMedicalHelp": rng.choice(YESNO),
        "POAActive": rng.choice(YESNO),
        "UnusualWealth": rng.choice(YESNO),
        "HospiceAssigned": hospice_assigned,
        "HospiceDurationMonths": int(rng.integers(0, 25)) if hospice_assigned == "Yes" else 0,
        "PreviousInvestigationCount": int(rng.integers(0, 5)),
        "CurrentInvestigation": current_investigation,
        "InvestigationStartDate": random_date(datetime(2022, 1, 1), datetime(2024, 3, 1)) if current_investigation == "Yes" else "",
        "VeteranStatus": rng.choice(YESNO),
    }


def build_people_for_zip(zipcode: str, acs: dict[str, dict[str, pd.Series]]) -> list[dict[str, Any]]:
    b01001 = acs["B01001"][zipcode]
    b12002 = acs["B12002"][zipcode]
    city = str(b01001["City"])
    people: list[dict[str, Any]] = []
    for sex in ("Male", "Female"):
        band_counts = [
            safe_int(b01001[f"{sex}65_69"]),
            safe_int(b01001[f"{sex}70_74"]),
            safe_int(b01001[f"{sex}75_79"]),
            safe_int(b01001[f"{sex}80_84"]),
            safe_int(b01001[f"{sex}85Plus"]),
        ]
        shell: list[dict[str, Any]] = []
        for band_idx, band_count in enumerate(band_counts):
            for _ in range(band_count):
                shell.append({"band_idx": band_idx})
        rng.shuffle(shell)
        counts = allocate_counts(len(shell), marital_rates(b12002, sex, zipcode))
        pos = 0
        for marital, n in zip(MARITAL_CATEGORIES, counts):
            for item in shell[pos:pos + n]:
                people.append(make_person(zipcode, city, sex, item["band_idx"], marital, acs))
            pos += n
    expected = safe_int(b01001["Total65Plus"])
    if len(people) != expected:
        raise ValueError(f"ZIP {zipcode} generated {len(people)} people, expected B01001 Total65Plus {expected}")
    return people


def assign_lives_alone(people: list[dict[str, Any]], acs: dict[str, dict[str, pd.Series]]) -> None:
    for person in people:
        if person["MaritalStatus"] == "Married":
            person["LivesAlone"] = "No"
    zips = sorted({p["Zip"] for p in people})
    for zipcode in zips:
        b11010 = acs["B11010"][zipcode]
        for sex in ("Male", "Female"):
            eligible = [p for p in people if p["Zip"] == zipcode and p["Gender"] == sex and p["MaritalStatus"] in NON_MARRIED]
            rate_col = f"{sex}LivingAloneRate65"
            rate = validate_rate(safe_float(b11010[rate_col]), "B11010", rate_col, zipcode)
            target = int(round(len(eligible) * rate))
            order = rng.permutation(len(eligible)) if eligible else []
            for i, idx in enumerate(order):
                eligible[int(idx)]["LivesAlone"] = "Yes" if i < target else "No"


def make_mock_address() -> str:
    house_number = int(rng.integers(10, 9999))
    street = str(rng.choice(FAKE_STREET_NAMES))
    return f"{house_number} {street}"


def id_generator(start: int = 10000000) -> Iterator[int]:
    yield from count(start=start, step=1)


def household_id_generator(start: int = 1) -> Iterator[int]:
    yield from count(start=start, step=1)


def create_household_rows(
    members: list[dict[str, Any]],
    household_type: str,
    placement_rule: str,
    id_iter: Iterator[int],
    household_iter: Iterator[int],
    allocator: AddressPointAllocator,
) -> list[dict[str, Any]]:
    if not members:
        return []
    zipcode = members[0]["Zip"]
    ap = allocator.assign(zipcode)
    hid = f"HH_{zipcode}_{next(household_iter):07d}"
    hsize = len(members)
    mock_address = make_mock_address()
    final_type = "CapacityOverflow" if ap["Overflow"] else household_type
    final_rule = f"{placement_rule}_CapacityOverflow" if ap["Overflow"] else placement_rule
    rows = []
    for member in members:
        row = dict(member)
        row.update({
            "ID": str(next(id_iter)),
            "MockAddress": mock_address,
            "Longitude": ap["Longitude"],
            "Latitude": ap["Latitude"],
            "HouseholdID": hid,
            "AddressPointID": ap["AddressPointID"],
            "HouseholdSize": hsize,
            "HouseholdType": final_type,
            "PlacementRule": final_rule,
            "GeneratorVersion": GENERATOR_VERSION,
            "AsOfDate": format_date(AS_OF_DATE),
            "AddressIsSynthetic": "Yes",
        })
        rows.append(row)
    return rows


def split_multi_elder_groups(candidates: list[dict[str, Any]]) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    if len(candidates) < 2:
        return [], candidates
    shuffled = list(candidates)
    rng.shuffle(shuffled)
    target_people = int(np.floor(len(shuffled) * MULTI_ELDER_RATE))
    target_people = min(target_people, len(shuffled))
    groups: list[list[dict[str, Any]]] = []
    used = 0
    while used + 1 < target_people:
        group_size = 3 if used + 2 < target_people and rng.random() < MULTI_ELDER_TRIPLE_PROB else 2
        groups.append(shuffled[used:used + group_size])
        used += group_size
    return groups, shuffled[used:]


def build_rows(acs: dict[str, dict[str, pd.Series]], allocator: AddressPointAllocator) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    id_iter = id_generator()
    household_iter = household_id_generator()
    rows: list[dict[str, Any]] = []
    generation_log: list[dict[str, Any]] = []
    all_people: list[dict[str, Any]] = []

    for zipcode in sorted(acs["B01001"]):
        all_people.extend(build_people_for_zip(zipcode, acs))
    assign_lives_alone(all_people, acs)

    for zipcode in sorted(acs["B01001"]):
        zip_people = [p for p in all_people if p["Zip"] == zipcode]
        males_married = [p for p in zip_people if p["Gender"] == "Male" and p["MaritalStatus"] == "Married"]
        females_married = [p for p in zip_people if p["Gender"] == "Female" and p["MaritalStatus"] == "Married"]
        rng.shuffle(males_married)
        rng.shuffle(females_married)
        n_couples = min(len(males_married), len(females_married))
        for i in range(n_couples):
            rows.extend(create_household_rows(
                [males_married[i], females_married[i]], "MarriedPair", "MarriedCoupleSharedPoint",
                id_iter, household_iter, allocator,
            ))

        paired_ids = {id(p) for p in males_married[:n_couples] + females_married[:n_couples]}
        leftovers = [p for p in zip_people if id(p) not in paired_ids]
        married_leftovers = [p for p in leftovers if p["MaritalStatus"] == "Married"]
        nonmarried = [p for p in leftovers if p["MaritalStatus"] in NON_MARRIED]
        nonmarried_alone = [p for p in nonmarried if p["LivesAlone"] == "Yes"]
        nonmarried_not_alone = [p for p in nonmarried if p["LivesAlone"] == "No"]
        multi_groups, remaining_not_alone = split_multi_elder_groups(nonmarried_not_alone)

        for person in married_leftovers:
            person["LivesAlone"] = "No"
            rows.extend(create_household_rows([person], "MarriedLeftover", "MarriedLeftoverSolo", id_iter, household_iter, allocator))
        for group in multi_groups:
            rows.extend(create_household_rows(group, "MultiElder", "IntentionalMultiElder", id_iter, household_iter, allocator))
        for person in nonmarried_alone:
            rows.extend(create_household_rows([person], "Solo", "SoloLivesAlone", id_iter, household_iter, allocator))
        for person in remaining_not_alone:
            rows.extend(create_household_rows([person], "NonMarriedNotAlone", "SingleElderWithUnmodeledCoResident", id_iter, household_iter, allocator))

        generation_log.append({
            "Zip": zipcode,
            "City": str(acs["B01001"][zipcode]["City"]),
            "B01001_Total65Plus": safe_int(acs["B01001"][zipcode]["Total65Plus"]),
            "GeneratedRecords": len(zip_people),
            "MarriedPairs": n_couples,
            "MarriedLeftovers": len(married_leftovers),
            "MultiElderHouseholds": len(multi_groups),
            "AddressPointsAvailable": allocator.available_count(zipcode),
        })

    df = pd.DataFrame(rows, columns=CSVHEADER)
    return df, generation_log


def write_generation_summary(df: pd.DataFrame, generation_log: list[dict[str, Any]], allocator: AddressPointAllocator, outdir: Path) -> None:
    rows = []
    for item in generation_log:
        zipcode = item["Zip"]
        subset = df[df["Zip"] == zipcode]
        households = subset.drop_duplicates("HouseholdID")
        item = dict(item)
        item.update({
            "HouseholdsGenerated": int(households.shape[0]),
            "AddressPointsUsedUnique": int(subset["AddressPointID"].nunique()),
            "OverflowAssignments": int(allocator.overflow_counts[zipcode]),
            "GeneratorVersion": GENERATOR_VERSION,
            "RNGSeed": RNG_SEED,
            "AsOfDate": format_date(AS_OF_DATE),
        })
        rows.append(item)
    pd.DataFrame(rows).to_csv(outdir / "v10_generation_summary.csv", index=False)


def write_zip_calibration_check(df: pd.DataFrame, acs: dict[str, dict[str, pd.Series]], outdir: Path) -> None:
    rows = []
    for zipcode in sorted(acs["B01001"]):
        subset = df[df["Zip"] == zipcode]
        b01001 = acs["B01001"][zipcode]
        for sex in ("Male", "Female"):
            sex_subset = subset[subset["Gender"] == sex]
            rows.append({"Zip": zipcode, "Metric": f"{sex}65Plus", "Target": safe_int(b01001[f"{sex}65Plus"]), "Generated": len(sex_subset), "Difference": len(sex_subset) - safe_int(b01001[f"{sex}65Plus"])})
            for label, col in zip(AGEBAND_LABELS, [f"{sex}65_69", f"{sex}70_74", f"{sex}75_79", f"{sex}80_84", f"{sex}85Plus"]):
                generated = int((sex_subset["AgeBand"] == label).sum())
                target = safe_int(b01001[col])
                rows.append({"Zip": zipcode, "Metric": f"{sex}_{label}", "Target": target, "Generated": generated, "Difference": generated - target})
        total_target = safe_int(b01001["Total65Plus"])
        rows.append({"Zip": zipcode, "Metric": "Total65Plus", "Target": total_target, "Generated": len(subset), "Difference": len(subset) - total_target})

        target_internet = safe_float(acs["B28005"][zipcode]["HasInternetRate65"])
        generated_internet = (subset["HasInternet"] == "Yes").mean() if len(subset) else 0
        rows.append({"Zip": zipcode, "Metric": "HasInternetRate65", "Target": target_internet, "Generated": generated_internet, "Difference": generated_internet - target_internet})

        target_disability = safe_float(acs["B18101"][zipcode]["DisabilityRate65Plus"])
        generated_disability = (subset["HasDisability"] == "Yes").mean() if len(subset) else 0
        rows.append({"Zip": zipcode, "Metric": "DisabilityRate65Plus", "Target": target_disability, "Generated": generated_disability, "Difference": generated_disability - target_disability})

        for sex in ("Male", "Female"):
            elig = subset[(subset["Gender"] == sex) & (subset["MaritalStatus"] != "Married")]
            rate_col = f"{sex}LivingAloneRate65"
            target = safe_float(acs["B11010"][zipcode][rate_col])
            generated = (elig["LivesAlone"] == "Yes").mean() if len(elig) else 0
            rows.append({"Zip": zipcode, "Metric": rate_col, "Target": target, "Generated": generated, "Difference": generated - target})

        for label, target_col, mask in [
            ("PovertyRate60_74", "PovertyRate60_74", subset["Age"].between(65, 74)),
            ("PovertyRate75Plus", "PovertyRate75Plus", subset["Age"] >= 75),
        ]:
            group = subset[mask]
            target = safe_float(acs["B17020"][zipcode][target_col])
            generated = (group["InPoverty"] == "Yes").mean() if len(group) else 0
            rows.append({"Zip": zipcode, "Metric": label, "Target": target, "Generated": generated, "Difference": generated - target})
    pd.DataFrame(rows).to_csv(outdir / "v10_zip_calibration_check.csv", index=False)


def write_household_occupancy_check(df: pd.DataFrame, outdir: Path) -> None:
    households = df.drop_duplicates("HouseholdID")
    rows = []
    grouped = households.groupby(["Zip", "HouseholdType", "HouseholdSize"], dropna=False).size().reset_index(name="HouseholdCount")
    for _, row in grouped.iterrows():
        rows.append(row.to_dict())
    pd.DataFrame(rows).to_csv(outdir / "v10_household_occupancy_check.csv", index=False)


def write_duplicate_point_audit(df: pd.DataFrame, outdir: Path) -> None:
    rows = []
    for (zipcode, apid), group in df.groupby(["Zip", "AddressPointID"]):
        person_count = len(group)
        household_ids = sorted(group["HouseholdID"].unique())
        household_count = len(household_ids)
        if person_count > 1 or household_count > 1:
            rows.append({
                "Zip": zipcode,
                "AddressPointID": apid,
                "PersonCount": person_count,
                "HouseholdCount": household_count,
                "HouseholdIDs": ";".join(household_ids),
                "HouseholdTypes": ";".join(sorted(group["HouseholdType"].unique())),
                "PlacementRules": ";".join(sorted(group["PlacementRule"].unique())),
                "Longitude": group["Longitude"].iloc[0],
                "Latitude": group["Latitude"].iloc[0],
                "AuditClass": "IntentionalHousehold" if household_count == 1 else "CapacityOverflowOrDuplicateHouseholds",
            })
    pd.DataFrame(rows).to_csv(outdir / "v10_duplicate_point_audit.csv", index=False)


def write_field_completeness_check(df: pd.DataFrame, outdir: Path) -> None:
    rows = []
    for col in CSVHEADER:
        series = df[col]
        missing = int(series.isna().sum() + (series.astype(str).str.strip() == "").sum())
        row = {
            "Field": col,
            "Records": len(df),
            "MissingCount": missing,
            "MissingPercent": missing / len(df) if len(df) else 0,
        }
        if set(series.dropna().astype(str).unique()).issubset({"Yes", "No"}):
            row["YesCount"] = int((series == "Yes").sum())
            row["NoCount"] = int((series == "No").sum())
        rows.append(row)
    pd.DataFrame(rows).to_csv(outdir / "v10_field_completeness_check.csv", index=False)


def write_metadata(outdir: Path, df: pd.DataFrame, acs_paths: dict[str, Path]) -> None:
    metadata = {
        "generator_version": GENERATOR_VERSION,
        "rng_seed": RNG_SEED,
        "as_of_date": format_date(AS_OF_DATE),
        "output_csv": str(OUTPUT_CSV_PATH),
        "record_count": int(len(df)),
        "household_count": int(df["HouseholdID"].nunique()),
        "acs_inputs": {name: str(path) for name, path in acs_paths.items()},
        "address_points_source": str(ADDRESS_POINTS_SHP),
        "notes": [
            "B01001 controls population totals by ZIP, sex, and age band.",
            "B11010 shapes LivesAlone only among eligible non-married elders.",
            "MockAddress is synthetic and does not expose source address text.",
            "Repeated coordinates are audited by household and address point.",
        ],
    }
    with open(outdir / "v10_generation_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)


def write_validation_outputs(df: pd.DataFrame, generation_log: list[dict[str, Any]], allocator: AddressPointAllocator, acs: dict[str, dict[str, pd.Series]], outdir: Path) -> None:
    write_generation_summary(df, generation_log, allocator, outdir)
    write_zip_calibration_check(df, acs, outdir)
    write_household_occupancy_check(df, outdir)
    write_duplicate_point_audit(df, outdir)
    write_field_completeness_check(df, outdir)
    write_metadata(outdir, df, {
        "B01001": B01001CSV,
        "B12002": B12002CSV,
        "B28005": B28005CSV,
        "B18101": B18101CSV,
        "B17020": B17020CSV,
        "B11010": B11010CSV,
    })


def generate_schema_ini(csv_filename: str) -> str:
    return f"""[{csv_filename}]
Format=CSVDelimited
ColNameHeader=True
MaxScanRows=0
CharacterSet=65001

Col1=ID Text Width 12
Col2=MockAddress Text Width 80
Col3=Age Long
Col4=AgeBand Text Width 8
Col5=AgeScore Long
Col6=Gender Text Width 10
Col7=MaritalStatus Text Width 20
Col8=City Text Width 40
Col9=State Text Width 2
Col10=Zip Text Width 5
Col11=HasInternet Text Width 3
Col12=HasCell Text Width 3
Col13=HasEmail Text Width 3
Col14=HasDisability Text Width 3
Col15=LivesAlone Text Width 3
Col16=InPoverty Text Width 3
Col17=LastContactDate Date
Col18=APSReferral Text Width 3
Col19=FallHistory Text Width 3
Col20=CognitiveFlag Text Width 3
Col21=ServiceUse Text Width 30
Col22=InactiveBenefits Text Width 3
Col23=Notes Text Width 80
Col24=RefusesMedicalHelp Text Width 3
Col25=POAActive Text Width 3
Col26=UnusualWealth Text Width 3
Col27=HospiceAssigned Text Width 3
Col28=HospiceDurationMonths Long
Col29=PreviousInvestigationCount Long
Col30=CurrentInvestigation Text Width 3
Col31=InvestigationStartDate Date
Col32=VeteranStatus Text Width 3
Col33=Longitude Double
Col34=Latitude Double
Col35=HouseholdID Text Width 24
Col36=AddressPointID Text Width 40
Col37=HouseholdSize Long
Col38=HouseholdType Text Width 30
Col39=PlacementRule Text Width 40
Col40=GeneratorVersion Text Width 10
Col41=AsOfDate Date
Col42=AddressIsSynthetic Text Width 3
"""


def main() -> None:
    logging.info("Starting mock address generator %s", GENERATOR_VERSION)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    acs = load_acs_inputs()
    required_zips = set(acs["B01001"].keys())
    address_points = load_address_points(required_zips)
    allocator = AddressPointAllocator(address_points)
    dfout, generation_log = build_rows(acs, allocator)

    dfout = dfout[CSVHEADER]
    dfout.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8")
    schema_path = OUTPUT_CSV_PATH.parent / "schema.ini"
    schema_path.write_text(generate_schema_ini(OUTPUT_CSV_PATH.name), encoding="utf-8")
    write_validation_outputs(dfout, generation_log, allocator, acs, OUTPUT_DIR)

    logging.info("Wrote %d records to %s", len(dfout), OUTPUT_CSV_PATH)
    logging.info("Wrote schema.ini to %s", schema_path)
    logging.info("Wrote v10 validation outputs to %s", OUTPUT_DIR)


if __name__ == "__main__":
    main()
