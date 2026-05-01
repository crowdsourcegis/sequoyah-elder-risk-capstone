"""
NETWORK DATASET BUILDER
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
ArcGIS Network Prep
Author: Luke A. Lynch
Date: 2026-03-16

This script prepares the road network dataset used by the CAPSTONE routing
workflow. It verifies the working geodatabase inputs, copies the project road
source into the transportation feature dataset, creates the network dataset if
it does not already exist, and builds it in place.

The point of this script is to keep network creation explicit and repeatable.
It does not score elder records, run hot spot analysis, or create any ACS-
derived outputs. It only builds the network asset the later workflow depends on.
"""

import arcpy
import os

# PARAMETERS START
arcpy.env.overwriteOutput = True

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
SOURCE_ROADS = os.path.join(GDB, "roads_mvp")
FEATURE_DATASET = os.path.join(GDB, "Transportation")

ROADS_NAME = "Roads"
ROADS_FC = os.path.join(FEATURE_DATASET, ROADS_NAME)

NETWORK_NAME = "RoadNetwork_ND"
NETWORK_PATH = os.path.join(FEATURE_DATASET, NETWORK_NAME)
# PARAMETERS END

def log(msg):
    arcpy.AddMessage(msg)
    print(msg)

def delete_if_exists(path):
    if arcpy.Exists(path):
        arcpy.management.Delete(path)
        log(f"Deleted existing: {path}")

def check_extension():
    status = arcpy.CheckExtension("network")
    if status != "Available":
        raise RuntimeError(f"Network Analyst extension not available: {status}")
    arcpy.CheckOutExtension("network")
    log("Network Analyst extension checked out.")

def validate_inputs():
    if not arcpy.Exists(GDB):
        raise RuntimeError(f"Configured geodatabase not found: {GDB}")
    if not arcpy.Exists(SOURCE_ROADS):
        raise RuntimeError(f"Source roads feature class not found: {SOURCE_ROADS}")
    if not arcpy.Exists(FEATURE_DATASET):
        raise RuntimeError(f"Transportation feature dataset not found: {FEATURE_DATASET}")
    log("Input geodatabase, roads source, and feature dataset verified.")

def copy_roads():
    delete_if_exists(ROADS_FC)
    arcpy.conversion.FeatureClassToFeatureClass(
        in_features=SOURCE_ROADS,
        out_path=FEATURE_DATASET,
        out_name=ROADS_NAME
    )
    log(f"Roads copied into transportation dataset: {ROADS_FC}")

def create_network():
    if arcpy.Exists(NETWORK_PATH):
        log(f"Network dataset already exists: {NETWORK_PATH}")
        return

    arcpy.na.CreateNetworkDataset(
        feature_dataset=FEATURE_DATASET,
        out_name=NETWORK_NAME,
        source_feature_class_names=[ROADS_NAME],
        elevation_model="NO_ELEVATION"
    )
    log(f"Network dataset created: {NETWORK_PATH}")

def build_network():
    arcpy.na.BuildNetwork(NETWORK_PATH)
    log(f"Network dataset built: {NETWORK_PATH}")

def verify_network():
    if not arcpy.Exists(NETWORK_PATH):
        raise RuntimeError(f"Network dataset missing after build step: {NETWORK_PATH}")

    d = arcpy.Describe(NETWORK_PATH)
    log(f"Exists: True")
    log(f"dataType: {d.dataType}")
    log(f"name: {d.name}")
    log(f"catalogPath: {d.catalogPath}")

    if d.dataType != "NetworkDataset":
        raise RuntimeError(
            f"Object exists but is not a NetworkDataset. Returned dataType: {d.dataType}"
        )

def list_network_datasets():
    arcpy.env.workspace = GDB
    nds = arcpy.ListDatasets("", "Network") or []
    log("Network datasets found:")
    for nd in nds:
        log(f"  {os.path.join(GDB, nd)}")

def main():
    try:
        check_extension()
        validate_inputs()
        copy_roads()
        create_network()
        build_network()
        verify_network()
        list_network_datasets()
        log("Road network workflow complete.")
    finally:
        try:
            arcpy.CheckInExtension("network")
            log("Network Analyst extension checked in.")
        except:
            pass

if __name__ == "__main__":
    main()
