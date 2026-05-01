"""
ELDER SCORE AND FIELD BUILDER
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ArcGIS Scoring Workflow
Author: Luke A. Lynch
Date: 2026-03-11

This script rebuilds the scored elder feature class from the current v10
address layer. It adds the required score fields, calculates the composite
risk model, calculates the ACS-focused score, and writes the settlement regime
classification used by the downstream Gi analysis.

The point of this script is to materialize a defensible scored working layer
inside the project geodatabase. It does not generate synthetic people, build
the road network, or summarize Gi outputs.
This script is not part of the active pipeline. See scripts/pipeline/ for the canonical workflow.
"""

import arcpy
import os
from datetime import datetime

# PARAMETERS START
arcpy.env.overwriteOutput = True

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
SOURCE_FC = os.path.join(GDB, "elder_address_v10")
OUTPUT_FC = os.path.join(GDB, "scored_elder_records")

arcpy.env.workspace = GDB

AS_OF_DATE = datetime.strptime("03/10/2026", "%m/%d/%Y")

FIELD_MAP = {
    "age": "Age",
    "last_contact": "LastContactDate",
    "aps_referral": "APSReferral",
    "fall_history": "FallHistory",
    "cognitive_flag": "CognitiveFlag",
    "inactive_benefits": "InactiveBenefits",
    "service_use": "ServiceUse",
    "has_internet": "HasInternet",
    "has_cell": "HasCell",
    "has_disability": "HasDisability",
    "lives_alone": "LivesAlone",
    "refuses_medical_help": "RefusesMedicalHelp",
    "previous_investigations": "PreviousInvestigationCount",
    "in_poverty": "InPoverty",
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
    ("ACSScore", "SHORT", None),
    ("SpatialRegime", "TEXT", 32)
]

TOWN_NODES = {
    "SALLISAW": "Sallisaw_Node",
    "MULDROW": "Town_Node",
    "ROLAND": "Town_Node",
    "VIAN": "Town_Node",
    "GORE": "Town_Node",
    "GANS": "Town_Node",
    "MARBLE CITY": "Town_Node",
    "MOFFETT": "Town_Node"
}
# PARAMETERS END

def log(message):
    arcpy.AddMessage(message)
    print(message)

def field_name_set(fc):
    return {f.name for f in arcpy.ListFields(fc)}

def require_fields(fc, required_fields):
    fields = field_name_set(fc)
    missing = [f for f in required_fields if f not in fields]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))

def ensure_field(fc, name, ftype, length=None):
    fields = field_name_set(fc)
    if name not in fields:
        if length:
            arcpy.management.AddField(fc, name, ftype, field_length=length)
        else:
            arcpy.management.AddField(fc, name, ftype)
        log(f"Added field: {name}")

def is_yes(value):
    if value is None:
        return False
    return str(value).strip().lower() in {
        "yes", "y", "true", "t", "1", "active", "present"
    }

def is_no(value):
    if value is None:
        return False
    return str(value).strip().lower() in {
        "no", "n", "false", "f", "0", "none", "not present"
    }

def coerce_int(value, default=0):
    if value in (None, "", "<Null>"):
        return default
    try:
        return int(float(value))
    except:
        return default

def parse_date(value):
    if value in (None, "", "<Null>"):
        return None

    if isinstance(value, datetime):
        return value

    text = str(value).strip()

    formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%m/%d/%y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except:
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

def spatial_regime(city_value):
    city = str(city_value).strip().upper() if city_value else ""
    return TOWN_NODES.get(city, "Rural_Hinterland")

def rebuild_output():
    if arcpy.Exists(OUTPUT_FC):
        arcpy.management.Delete(OUTPUT_FC)
        log(f"Deleted existing output: {OUTPUT_FC}")

    arcpy.management.CopyFeatures(SOURCE_FC, OUTPUT_FC)
    log(f"Source copied into scored output: {OUTPUT_FC}")

def add_score_fields():
    for name, ftype, length in SCORE_FIELDS:
        ensure_field(OUTPUT_FC, name, ftype, length)

def calculate_scores():
    source_fields = list(FIELD_MAP.values())
    require_fields(OUTPUT_FC, source_fields)

    update_fields = source_fields + [f[0] for f in SCORE_FIELDS]

    with arcpy.da.UpdateCursor(OUTPUT_FC, update_fields) as cursor:
        for row in cursor:
            idx = {field: i for i, field in enumerate(update_fields)}

            age = coerce_int(row[idx[FIELD_MAP["age"]]], None)
            last_contact = parse_date(row[idx[FIELD_MAP["last_contact"]]])
            aps_referral = row[idx[FIELD_MAP["aps_referral"]]]
            fall_history = row[idx[FIELD_MAP["fall_history"]]]
            cognitive_flag = row[idx[FIELD_MAP["cognitive_flag"]]]
            inactive_benefits = row[idx[FIELD_MAP["inactive_benefits"]]]
            service_use = row[idx[FIELD_MAP["service_use"]]]
            has_internet = row[idx[FIELD_MAP["has_internet"]]]
            has_cell = row[idx[FIELD_MAP["has_cell"]]]
            has_disability = row[idx[FIELD_MAP["has_disability"]]]
            lives_alone = row[idx[FIELD_MAP["lives_alone"]]]
            refuses_medical_help = row[idx[FIELD_MAP["refuses_medical_help"]]]
            previous_investigations = coerce_int(row[idx[FIELD_MAP["previous_investigations"]]])
            in_poverty = row[idx[FIELD_MAP["in_poverty"]]]
            city = row[idx[FIELD_MAP["city"]]]

            rs_age = 1 if age is not None and age >= 80 else 0

            rs_contact = 0
            if last_contact:
                days_since_contact = (AS_OF_DATE - last_contact).days
                rs_contact = 1 if days_since_contact > 180 else 0

            risk_flag_count = sum([
                1 if is_yes(aps_referral) else 0,
                1 if is_yes(fall_history) else 0,
                1 if is_yes(cognitive_flag) else 0
            ])
            rs_flags = 1 if risk_flag_count >= 2 else 0

            service_text = str(service_use).strip().lower() if service_use is not None else ""
            rs_service = 1 if is_yes(inactive_benefits) and service_text in {
                "none", "no active service", "inactive", "no service", ""
            } else 0

            rs_broadband = 1 if is_no(has_internet) and is_no(has_cell) else 0

            vuln_count = sum([
                1 if is_yes(has_disability) else 0,
                1 if is_yes(lives_alone) else 0,
                1 if is_yes(refuses_medical_help) else 0
            ])
            rs_vuln = 1 if vuln_count >= 2 else 0

            rs_history = 1 if previous_investigations >= 1 else 0
            rs_poverty = 1 if is_yes(in_poverty) else 0

            composite = (
                rs_age +
                rs_contact +
                rs_flags +
                rs_service +
                rs_broadband +
                rs_vuln +
                rs_history +
                rs_poverty
            )

            acs_score = rs_age + rs_broadband + rs_vuln + rs_poverty

            row[idx["RS_Age"]] = rs_age
            row[idx["RS_Contact"]] = rs_contact
            row[idx["RS_Flags"]] = rs_flags
            row[idx["RS_Service"]] = rs_service
            row[idx["RS_Broadband"]] = rs_broadband
            row[idx["RS_Vuln"]] = rs_vuln
            row[idx["RS_History"]] = rs_history
            row[idx["RS_Poverty"]] = rs_poverty
            row[idx["CompositeScore"]] = composite
            row[idx["RiskLevel"]] = risk_level(composite)
            row[idx["ACSScore"]] = acs_score
            row[idx["SpatialRegime"]] = spatial_regime(city)

            cursor.updateRow(row)

    log("Composite and ACS risk scores calculated.")

def add_indexes():
    index_specs = [
        ("RiskLevel", "idx_risklevel"),
        ("CompositeScore", "idx_compositescore"),
        ("SpatialRegime", "idx_spatialregime")
    ]

    for field, index_name in index_specs:
        try:
            arcpy.management.AddIndex(OUTPUT_FC, field, index_name)
            log(f"Added index: {index_name}")
        except Exception as exc:
            log(f"Index skipped for {field}: {exc}")

def summarize():
    count = int(arcpy.management.GetCount(OUTPUT_FC)[0])
    log(f"Output records: {count}")

    risk_counts = {}
    with arcpy.da.SearchCursor(OUTPUT_FC, ["RiskLevel"]) as cursor:
        for row in cursor:
            risk_counts[row[0]] = risk_counts.get(row[0], 0) + 1

    for key in ["Low", "Moderate", "High", "Critical"]:
        log(f"{key}: {risk_counts.get(key, 0)}")

def main():
    log("Building scored_elder_records from the current source layer.")
    rebuild_output()
    add_score_fields()
    calculate_scores()
    add_indexes()
    summarize()
    log("Scoring pass complete.")

if __name__ == "__main__":
    main()
