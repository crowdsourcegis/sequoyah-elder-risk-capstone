"""
ELDER TRIAGE PIPELINE
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ArcGIS Scoring and Gi Workflow
Author: Luke A. Lynch
Date: 2026-03-09

This script rebuilds a scored working elder feature class, calculates the
project risk fields, and runs the fixed-band Gi passes for both CompositeScore
and ACSScore. It is the compact pipeline version of the scoring-plus-Gi
workflow used inside the project geodatabase.

The point of this script is end-to-end execution in one place. It does not
generate synthetic records, build the road network dataset, or summarize the
Gi outputs into a separate results table.
This script is not part of the active pipeline. See scripts/pipeline/ for the canonical workflow.
"""

import arcpy
import os
from datetime import datetime

# PARAMETERS START
arcpy.env.overwriteOutput = True

gdb = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
arcpy.env.workspace = gdb

INPUT_FC = os.path.join(gdb, "elder_address")
WORKING_FC = os.path.join(gdb, "scored_elder_records")

AS_OF_DATE = datetime(2026, 3, 10)

DISTANCE_BANDS = [
    ("600", "Meters"),
    ("943", "Meters"),
    ("1200", "Meters")
]

SCORE_FIELDS = [
    ("RS_Age", "SHORT"),
    ("RS_Contact", "SHORT"),
    ("RS_Flags", "SHORT"),
    ("RS_Service", "SHORT"),
    ("RS_Broadband", "SHORT"),
    ("RS_Vuln", "SHORT"),
    ("RS_History", "SHORT"),
    ("RS_Poverty", "SHORT"),
    ("CompositeScore", "SHORT"),
    ("ACSScore", "SHORT"),
    ("RiskLevel", "TEXT", 12)
]
# PARAMETERS END

def log(message):
    arcpy.AddMessage(message)
    print(message)

def ensure_field(fc, name, ftype, flen=None):
    existing = [f.name for f in arcpy.ListFields(fc)]
    if name not in existing:
        if flen:
            arcpy.management.AddField(fc, name, ftype, field_length=flen)
        else:
            arcpy.management.AddField(fc, name, ftype)

def is_yes(value):
    return str(value).strip().lower() == "yes"

def copy_input():
    if arcpy.Exists(WORKING_FC):
        arcpy.management.Delete(WORKING_FC)
    arcpy.management.CopyFeatures(INPUT_FC, WORKING_FC)

def add_score_fields():
    for fld in SCORE_FIELDS:
        if len(fld) == 2:
            ensure_field(WORKING_FC, fld[0], fld[1])
        else:
            ensure_field(WORKING_FC, fld[0], fld[1], fld[2])

def calc_scores():
    fields = [
        "Age",
        "LastContactDate",
        "APSReferral",
        "FallHistory",
        "CognitiveFlag",
        "InactiveBenefits",
        "ServiceUse",
        "HasInternet",
        "HasCell",
        "HasDisability",
        "LivesAlone",
        "RefusesMedicalHelp",
        "PreviousInvestigationCount",
        "InPoverty",
        "RS_Age",
        "RS_Contact",
        "RS_Flags",
        "RS_Service",
        "RS_Broadband",
        "RS_Vuln",
        "RS_History",
        "RS_Poverty",
        "CompositeScore",
        "ACSScore",
        "RiskLevel"
    ]

    with arcpy.da.UpdateCursor(WORKING_FC, fields) as cursor:
        for row in cursor:
            age = row[0]
            last_contact = row[1]
            aps = row[2]
            fall = row[3]
            cog = row[4]
            inactive_benefits = row[5]
            service_use = row[6]
            has_internet = row[7]
            has_cell = row[8]
            has_disability = row[9]
            lives_alone = row[10]
            refuses_help = row[11]
            prev_inv = row[12]
            poverty = row[13]

            rs_age = 1 if age is not None and age >= 80 else 0

            rs_contact = 0
            if last_contact not in (None, "", "<Null>"):
                try:
                    if hasattr(last_contact, "year"):
                        dt = last_contact
                    else:
                        dt = datetime.strptime(str(last_contact), "%m/%d/%Y")
                    rs_contact = 1 if (AS_OF_DATE - dt).days > 180 else 0
                except:
                    rs_contact = 0

            rs_flags = 1 if sum([is_yes(aps), is_yes(fall), is_yes(cog)]) >= 2 else 0
            rs_service = 1 if is_yes(inactive_benefits) and str(service_use).strip().lower() == "none" else 0
            rs_broadband = 1 if (not is_yes(has_internet)) and (not is_yes(has_cell)) else 0
            rs_vuln = 1 if sum([is_yes(has_disability), is_yes(lives_alone), is_yes(refuses_help)]) >= 2 else 0
            rs_history = 1 if prev_inv not in (None, "", "<Null>") and int(prev_inv) >= 1 else 0
            rs_poverty = 1 if is_yes(poverty) else 0

            composite = (
                rs_age + rs_contact + rs_flags + rs_service +
                rs_broadband + rs_vuln + rs_history + rs_poverty
            )

            acs_score = rs_age + rs_broadband + rs_vuln + rs_poverty

            if composite <= 2:
                level = "Low"
            elif composite <= 4:
                level = "Moderate"
            elif composite <= 6:
                level = "High"
            else:
                level = "Critical"

            row[14] = rs_age
            row[15] = rs_contact
            row[16] = rs_flags
            row[17] = rs_service
            row[18] = rs_broadband
            row[19] = rs_vuln
            row[20] = rs_history
            row[21] = rs_poverty
            row[22] = composite
            row[23] = acs_score
            row[24] = level

            cursor.updateRow(row)

def run_gi(input_features, analysis_field, suffix):
    for value, unit in DISTANCE_BANDS:
        distance_text = f"{value} {unit}"
        out_name = f"gi_{suffix}_{value}"
        out_fc = os.path.join(gdb, out_name)

        if arcpy.Exists(out_fc):
            arcpy.management.Delete(out_fc)

        log(f"Running Gi on {analysis_field} at {distance_text}.")

        arcpy.stats.HotSpots(
            Input_Feature_Class=input_features,
            Input_Field=analysis_field,
            Output_Feature_Class=out_fc,
            Conceptualization_of_Spatial_Relationships="FIXED_DISTANCE_BAND",
            Distance_Method="EUCLIDEAN_DISTANCE",
            Standardization="NONE",
            Distance_Band_or_Threshold_Distance=distance_text
        )

        log(f"Output created: {out_fc}")

def main():
    log("Running scoring and multi-band Gi pipeline.")
    copy_input()
    add_score_fields()
    calc_scores()

    run_gi(WORKING_FC, "CompositeScore", "composite")
    run_gi(WORKING_FC, "ACSScore", "acs")

    log("Scoring and multi-band Gi analysis complete.")

if __name__ == "__main__":
    main()
