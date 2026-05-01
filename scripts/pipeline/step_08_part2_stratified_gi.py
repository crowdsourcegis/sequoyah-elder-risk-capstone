"""
PART 2: STRATIFIED GI RUNNER
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Stratified Gi Sensitivity Workflow
Author: Luke A. Lynch
Date: 2026-04-03

This script runs the settlement-stratified Gi sensitivity tests. Each run
locks the analysis field, settlement subset, and distance band explicitly so
the resulting Gi outputs can be compared as scenarios instead of treated as a
single black-box result.

The point of this script is controlled sensitivity testing. It does not assign
settlement regimes, score records, or summarize the generated Gi feature
classes into a final comparison table.
"""

import arcpy
import os

# PARAMETERS START
arcpy.env.overwriteOutput = True

gdb = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
arcpy.env.workspace = gdb

INPUT_FC = os.path.join(gdb, "scored_elder_records")

RUN_SPECS = [
    {
        "name": "countywide_composite_300",
        "where": None,
        "field": "CompositeScore",
        "distance": "300 Meters"
    },
    {
        "name": "countywide_composite_500",
        "where": None,
        "field": "CompositeScore",
        "distance": "500 Meters"
    },
    {
        "name": "sallisaw_composite_200",
        "where": "SpatialRegime = 'Sallisaw_Node'",
        "field": "CompositeScore",
        "distance": "200 Meters"
    },
    {
        "name": "sallisaw_composite_300",
        "where": "SpatialRegime = 'Sallisaw_Node'",
        "field": "CompositeScore",
        "distance": "300 Meters"
    },
    {
        "name": "towns_composite_400",
        "where": "SpatialRegime = 'Town_Node'",
        "field": "CompositeScore",
        "distance": "400 Meters"
    },
    {
        "name": "towns_composite_600",
        "where": "SpatialRegime = 'Town_Node'",
        "field": "CompositeScore",
        "distance": "600 Meters"
    },
    {
        "name": "rural_composite_800",
        "where": "SpatialRegime = 'Rural_Hinterland'",
        "field": "CompositeScore",
        "distance": "800 Meters"
    },
    {
        "name": "rural_composite_1200",
        "where": "SpatialRegime = 'Rural_Hinterland'",
        "field": "CompositeScore",
        "distance": "1200 Meters"
    },
    {
        "name": "sallisaw_acs_300",
        "where": "SpatialRegime = 'Sallisaw_Node'",
        "field": "ACSScore",
        "distance": "300 Meters"
    },
    {
        "name": "rural_acs_1200",
        "where": "SpatialRegime = 'Rural_Hinterland'",
        "field": "ACSScore",
        "distance": "1200 Meters"
    }
]
# PARAMETERS END

def log(message):
    arcpy.AddMessage(message)
    print(message)

def require_field(fc, field_name):
    fields = [f.name for f in arcpy.ListFields(fc)]
    if field_name not in fields:
        raise ValueError(f"Missing required field: {field_name}")

def build_subset_layer(run):
    layer_name = f"lyr_{run['name']}"
    if arcpy.Exists(layer_name):
        arcpy.management.Delete(layer_name)

    if run["where"]:
        arcpy.management.MakeFeatureLayer(INPUT_FC, layer_name, run["where"])
    else:
        arcpy.management.MakeFeatureLayer(INPUT_FC, layer_name)

    count = int(arcpy.management.GetCount(layer_name)[0])
    return layer_name, count

def run_hotspot(run):
    require_field(INPUT_FC, run["field"])

    layer_name, count = build_subset_layer(run)

    if count < 30:
        log(f"Skipping {run['name']}: only {count} records, below the minimum run threshold.")
        return

    output_fc = os.path.join(gdb, f"gi_{run['name']}")

    if arcpy.Exists(output_fc):
        arcpy.management.Delete(output_fc)

    log(f"Running {run['name']} on {run['field']} with {run['distance']} and {count} records.")

    arcpy.stats.HotSpots(
        Input_Feature_Class=layer_name,
        Input_Field=run["field"],
        Output_Feature_Class=output_fc,
        Conceptualization_of_Spatial_Relationships="FIXED_DISTANCE_BAND",
        Distance_Method="EUCLIDEAN_DISTANCE",
        Standardization="NONE",
        Distance_Band_or_Threshold_Distance=run["distance"]
    )

    log(f"Output created: {output_fc}")

def main():
    require_field(INPUT_FC, "SpatialRegime")
    require_field(INPUT_FC, "CompositeScore")
    require_field(INPUT_FC, "ACSScore")

    for run in RUN_SPECS:
        run_hotspot(run)

    log("Settlement-stratified Gi sensitivity runs complete.")

if __name__ == "__main__":
    main()
