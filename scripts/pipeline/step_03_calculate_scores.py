"""
ELDER SCORE CALCULATOR
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ArcGIS Scoring Workflow
Author: Luke A. Lynch
Date: 2026-03-14

This script calculates the scored elder record fields inside the project
geodatabase. It maps the expected input fields, adds the required score
columns, calculates the project risk model, and writes the scored output
feature class used by later analysis.

The point of this script is to materialize a working scored layer for ArcGIS
analysis. It does not generate synthetic records, compute narrative reason
codes, assign settlement regimes, or perform network accessibility workflows.
"""

import arcpy
import os
from datetime import datetime

# PARAMETERS START
arcpy.env.overwriteOutput = True

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
TARGET_FC = os.path.join(GDB, "scored_elder_records")

arcpy.env.workspace = GDB

AS_OF_DATE = datetime.strptime("03-10-2026", "%m-%d-%Y")

FIELD_MAP = {
    "age": "Age",
    "lastcontact": "LastContactDate",
    "apsreferral": "APSReferral",
    "fallhistory": "FallHistory",
    "cognitiveflag": "CognitiveFlag",
    "inactivebenefits": "InactiveBenefits",
    "serviceuse": "ServiceUse",
    "hasinternet": "HasInternet",
    "hascell": "HasCell",
    "hasdisability": "HasDisability",
    "livesalone": "LivesAlone",
    "refusesmedicalhelp": "RefusesMedicalHelp",
    "previousinvestigations": "PreviousInvestigationCount",
    "inpoverty": "InPoverty",
    "city": "City"
}

SCORE_FIELDS = [
    ("RS_Age", "SHORT", None),
    ("RS_Contact", "SHORT", None),
    ("RS_Flags", "SHORT", None),
    ("RS_Service", "SHORT", None),
    ("RS_Broadband", "SHORT", None),
    ("RS_Vuln", "SHORT", None),
    ("RS_History", "SHORT", None),
    ("RS_Poverty", "SHORT", None),
    ("CompositeScore", "SHORT", None),
    ("RiskLevel", "TEXT", 16),
]
# PARAMETERS END


def log(msg):
    arcpy.AddMessage(msg)
    print(msg)


def existing_fields(fc):
    return [f.name for f in arcpy.ListFields(fc)]


def require_fields(fc, field_names):
    fields = existing_fields(fc)
    missing = [f for f in field_names if f not in fields]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))


def ensure_field(fc, name, ftype, length=None):
    fields = existing_fields(fc)
    if name not in fields:
        if length:
            arcpy.management.AddField(fc, name, ftype, field_length=length)
        else:
            arcpy.management.AddField(fc, name, ftype)
        log(f"Added field: {name}")


def yes(value):
    if value is None:
        return False
    return str(value).strip().lower() in (
        "yes", "y", "true", "t", "1", "active", "present"
    )


def no(value):
    if value is None:
        return False
    return str(value).strip().lower() in (
        "no", "n", "false", "f", "0", "none", "not present", "inactive"
    )


def safe_int(value, default=0):
    if value in (None, "", "<Null>"):
        return default
    try:
        return int(float(value))
    except Exception:
        return default


def parse_date(value):
    if value in (None, "", "<Null>"):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y", "%Y%m%d", "%m-%d-%y"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass
    return None


def risk_level(score):
    if score <= 2:
        return "Low"
    if score <= 4:
        return "Moderate"
    if score <= 6:
        return "High"
    return "Critical"


def add_score_fields():
    for name, ftype, length in SCORE_FIELDS:
        ensure_field(TARGET_FC, name, ftype, length)


def calculate_scores():
    source_fields = list(FIELD_MAP.values())
    score_field_names = [f[0] for f in SCORE_FIELDS]

    require_fields(TARGET_FC, source_fields)
    update_fields = source_fields + score_field_names

    idx = {field: i for i, field in enumerate(update_fields)}
    count = 0

    with arcpy.da.UpdateCursor(TARGET_FC, update_fields) as cursor:
        for row in cursor:
            age = safe_int(row[idx[FIELD_MAP["age"]]], None)
            lastcontact = parse_date(row[idx[FIELD_MAP["lastcontact"]]])
            apsreferral = row[idx[FIELD_MAP["apsreferral"]]]
            fallhistory = row[idx[FIELD_MAP["fallhistory"]]]
            cognitiveflag = row[idx[FIELD_MAP["cognitiveflag"]]]
            inactivebenefits = row[idx[FIELD_MAP["inactivebenefits"]]]
            serviceuse = row[idx[FIELD_MAP["serviceuse"]]]
            hasinternet = row[idx[FIELD_MAP["hasinternet"]]]
            hascell = row[idx[FIELD_MAP["hascell"]]]
            hasdisability = row[idx[FIELD_MAP["hasdisability"]]]
            livesalone = row[idx[FIELD_MAP["livesalone"]]]
            refusesmedicalhelp = row[idx[FIELD_MAP["refusesmedicalhelp"]]]
            previousinvestigations = safe_int(row[idx[FIELD_MAP["previousinvestigations"]]], 0)
            inpoverty = row[idx[FIELD_MAP["inpoverty"]]]
            rsage = 1 if age is not None and age >= 80 else 0

            if lastcontact:
                days_since_contact = (AS_OF_DATE - lastcontact).days
                rscontact = 1 if days_since_contact > 180 else 0
            else:
                rscontact = 0

            risk_flag_count = sum([
                1 if yes(apsreferral) else 0,
                1 if yes(fallhistory) else 0,
                1 if yes(cognitiveflag) else 0
            ])
            rsflags = 1 if risk_flag_count >= 2 else 0

            service_text = str(serviceuse).strip().lower() if serviceuse is not None else ""
            no_active_service_values = (
                "none",
                "no active service",
                "no active services",
                "inactive",
                "no service",
                "no services"
            )
            rsservice = 1 if yes(inactivebenefits) and service_text in no_active_service_values else 0

            rsbroadband = 1 if no(hasinternet) and no(hascell) else 0

            vulnerability_count = sum([
                1 if yes(hasdisability) else 0,
                1 if yes(livesalone) else 0,
                1 if yes(refusesmedicalhelp) else 0
            ])
            rsvuln = 1 if vulnerability_count >= 2 else 0

            rshistory = 1 if previousinvestigations >= 1 else 0
            rspoverty = 1 if yes(inpoverty) else 0

            composite = (
                rsage +
                rscontact +
                rsflags +
                rsservice +
                rsbroadband +
                rsvuln +
                rshistory +
                rspoverty
            )

            row[idx["RS_Age"]] = rsage
            row[idx["RS_Contact"]] = rscontact
            row[idx["RS_Flags"]] = rsflags
            row[idx["RS_Service"]] = rsservice
            row[idx["RS_Broadband"]] = rsbroadband
            row[idx["RS_Vuln"]] = rsvuln
            row[idx["RS_History"]] = rshistory
            row[idx["RS_Poverty"]] = rspoverty
            row[idx["CompositeScore"]] = composite
            row[idx["RiskLevel"]] = risk_level(composite)

            cursor.updateRow(row)
            count += 1

    log(f"Composite risk scores calculated for {count:,} records.")


def add_indexes():
    index_specs = [
        ("RiskLevel", "idx_risk_level"),
        ("CompositeScore", "idx_composite_score"),
    ]

    for field, index_name in index_specs:
        try:
            arcpy.management.AddIndex(TARGET_FC, field, index_name)
            log(f"Added index: {index_name}")
        except Exception as exc:
            log(f"Index skipped for {field}: {exc}")


def summarize():
    count = int(arcpy.management.GetCount(TARGET_FC)[0])
    log(f"Target records: {count:,}")

    risk_counts = {}
    with arcpy.da.SearchCursor(TARGET_FC, ["RiskLevel"]) as cursor:
        for row in cursor:
            risk_counts[row[0]] = risk_counts.get(row[0], 0) + 1

    for key in ["Low", "Moderate", "High", "Critical"]:
        log(f"{key}: {risk_counts.get(key, 0):,}")


def main():
    log(f"Scoring target feature class: {TARGET_FC}")

    if not arcpy.Exists(TARGET_FC):
        raise ValueError(f"Target feature class not found: {TARGET_FC}")

    add_score_fields()
    calculate_scores()
    add_indexes()
    summarize()
    log("Composite scoring step complete.")


if __name__ == "__main__":
    main()
