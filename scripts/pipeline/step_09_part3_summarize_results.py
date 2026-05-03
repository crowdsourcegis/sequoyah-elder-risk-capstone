"""
PART 3: GI SENSITIVITY SUMMARIZER
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Stratified Gi Sensitivity Workflow
Author: Luke A. Lynch
Date: 2026-04-08

This script summarizes the generated Gi sensitivity outputs into a single CSV.
It scans the `gi_*` feature classes, resolves the key Gi fields present in
each output, and writes a compact comparison table for review.

The point of this script is audit and comparison. It does not run the Gi
analysis itself, assign regimes, or modify the scored elder feature class.
"""

import arcpy
import os
import csv
from collections import Counter

# Define workspace and summary CSV destination.
# PARAMETERS START
gdb = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
arcpy.env.workspace = gdb

OUTPUT_CSV = r"C:\Users\GIS\Documents\ArcGIS\Projects\gi_sensitivity_summary.csv"
# PARAMETERS END

def resolve_field(fc, options):
    names = [f.name for f in arcpy.ListFields(fc)]
    for opt in options:
        if opt in names:
            return opt
    for name in names:
        for opt in options:
            if opt.lower() in name.lower():
                return name
    return None

def summarize_feature_class(fc):
    gi_bin = resolve_field(fc, ["Gi_Bin"])
    n_neighbors = resolve_field(fc, ["NNeighbors"])
    z_field = resolve_field(fc, ["GiZScore"])
    p_field = resolve_field(fc, ["GiPValue"])

    if not gi_bin:
        return None

    fields = [gi_bin]
    if n_neighbors:
        fields.append(n_neighbors)
    if z_field:
        fields.append(z_field)
    if p_field:
        fields.append(p_field)

    counts = Counter()
    neighbor_values = []
    z_values = []
    p_values = []

    with arcpy.da.SearchCursor(fc, fields) as cursor:
        for row in cursor:
            counts[row[0]] += 1

            idx = 1
            if n_neighbors:
                if row[idx] is not None:
                    neighbor_values.append(row[idx])
                idx += 1

            if z_field:
                if row[idx] is not None:
                    z_values.append(row[idx])
                idx += 1

            if p_field:
                if row[idx] is not None:
                    p_values.append(row[idx])

    total = sum(counts.values())
    hot_99 = counts.get(3, 0)
    hot_95 = counts.get(2, 0)
    hot_90 = counts.get(1, 0)
    neutral = counts.get(0, 0)
    cold_90 = counts.get(-1, 0)
    cold_95 = counts.get(-2, 0)
    cold_99 = counts.get(-3, 0)

    avg_neighbors = round(sum(neighbor_values) / len(neighbor_values), 2) if neighbor_values else None
    max_z = round(max(z_values), 4) if z_values else None
    min_p = round(min(p_values), 8) if p_values else None

    return {
        "feature_class": os.path.basename(fc),
        "total": total,
        "hot_99": hot_99,
        "hot_95": hot_95,
        "hot_90": hot_90,
        "neutral": neutral,
        "cold_90": cold_90,
        "cold_95": cold_95,
        "cold_99": cold_99,
        "avg_neighbors": avg_neighbors,
        "max_z": max_z,
        "min_p": min_p
    }

# Aggregate all Gi outputs into a single comparison table.
def main():
    rows = []

    for fc_name in arcpy.ListFeatureClasses("gi_*"):
        fc = os.path.join(gdb, fc_name)
        result = summarize_feature_class(fc)
        if result:
            rows.append(result)

    fieldnames = [
        "feature_class",
        "total",
        "hot_99",
        "hot_95",
        "hot_90",
        "neutral",
        "cold_90",
        "cold_95",
        "cold_99",
        "avg_neighbors",
        "max_z",
        "min_p"
    ]

    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Gi sensitivity summary written: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
