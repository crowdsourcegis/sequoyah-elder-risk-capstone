"""
PART 1: SETTLEMENT REGIME CLASSIFIER
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Stratified Gi Sensitivity Workflow
Author: Luke A. Lynch
Date: 2026-03-28

This script is the first step in the settlement-stratified Gi workflow. It
classifies each scored elder record into the project settlement regimes and
materializes the ACS-only score used in the later sensitivity runs.

The point of this script is separation of concerns. It assigns regime labels
and ACS score values only. It does not run Gi statistics, summarize outputs,
or rebuild the full scored feature class.
"""

import arcpy
import os

# Define feature-class inputs and settlement regime mapping rules.
# PARAMETERS START
arcpy.env.overwriteOutput = True

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
arcpy.env.workspace = GDB

FC = os.path.join(GDB, "scored_elder_records")

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

def ensure_field(fc, name, ftype, length=None):
    existing = [f.name for f in arcpy.ListFields(fc)]
    if name not in existing:
        if length:
            arcpy.management.AddField(fc, name, ftype, field_length=length)
        else:
            arcpy.management.AddField(fc, name, ftype)

def coerce_int(value):
    if value in (None, "", "<Null>"):
        return 0
    return int(value)

# Populate settlement regime labels and ACS-only score values.
def main():
    ensure_field(FC, "SpatialRegime", "TEXT", 32)
    ensure_field(FC, "ACSScore", "SHORT")

    fields = [
        "City",
        "RS_Age",
        "RS_Broadband",
        "RS_Vuln",
        "RS_Poverty",
        "SpatialRegime",
        "ACSScore"
    ]

    with arcpy.da.UpdateCursor(FC, fields) as cursor:
        for row in cursor:
            city = str(row[0]).strip().upper() if row[0] else ""

            if city in TOWN_NODES:
                regime = TOWN_NODES[city]
            else:
                regime = "Rural_Hinterland"

            acs_score = (
                coerce_int(row[1]) +
                coerce_int(row[2]) +
                coerce_int(row[3]) +
                coerce_int(row[4])
            )

            row[5] = regime
            row[6] = acs_score
            cursor.updateRow(row)

    log("SpatialRegime and ACSScore populated.")

if __name__ == "__main__":
    main()
