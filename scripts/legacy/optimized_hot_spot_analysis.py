"""
OPTIMIZED HOT SPOT ANALYSIS
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ArcPy Hot Spot Workflow
Author: Luke A. Lynch
Date: 2026-03-07

This script runs the original optimized hot spot workflow against the elder
layer. It copies the working feature class into a scored output slot, verifies
that CompositeScore is present, and executes Optimized Hot Spot Analysis on
that field.

The point of this script is a direct ArcPy hot spot run with minimal moving
parts. It does not calculate the full scoring model, generate synthetic data,
or perform the settlement-stratified Gi sensitivity sequence.
This script is not part of the active pipeline. See scripts/pipeline/ for the canonical workflow.
"""

import arcpy
import os

# PARAMETERS START
arcpy.env.overwriteOutput = True

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
arcpy.env.workspace = GDB

ELDER_FC = os.path.join(GDB, "elder_address")
HOTSPOT_FC = os.path.join(GDB, "elder_address_gi")
SCORED_COPY_FC = os.path.join(GDB, "scored_elder_records")
# PARAMETERS END

def log(message):
    arcpy.AddMessage(message)
    print(message)

def has_field(fc, field_name):
    fields = [f.name for f in arcpy.ListFields(fc)]
    return field_name in fields

def copy_scored_layer():
    log("Copying the working feature class into the scored output slot.")
    if arcpy.Exists(SCORED_COPY_FC):
        arcpy.management.Delete(SCORED_COPY_FC)
    arcpy.management.CopyFeatures(ELDER_FC, SCORED_COPY_FC)
    log(f"Scored working copy created: {SCORED_COPY_FC}")

def run_hotspot():
    log("Running optimized hot spot analysis on CompositeScore.")
    if not has_field(SCORED_COPY_FC, "CompositeScore"):
        raise ValueError("CompositeScore is required before the hot spot step can run.")

    if arcpy.Exists(HOTSPOT_FC):
        arcpy.management.Delete(HOTSPOT_FC)

    arcpy.stats.OptimizedHotSpotAnalysis(
        Input_Features=SCORED_COPY_FC,
        Output_Features=HOTSPOT_FC,
        Analysis_Field="CompositeScore"
    )

    log(f"Hot spot output created: {HOTSPOT_FC}")

def main():
    log("Running ArcPy elder triage pipeline.")
    copy_scored_layer()
    run_hotspot()
    log("ArcPy elder triage pipeline finished cleanly.")

if __name__ == "__main__":
    main()
