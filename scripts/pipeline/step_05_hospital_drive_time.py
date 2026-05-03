"""
HOSPITAL DRIVE-TIME ANALYSIS
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Network Accessibility Workflow
Author: Luke A. Lynch
Date: 2026-03-18

This script calculates nearest-hospital drive-time accessibility for the
scored elder records. It uses the project road network dataset, writes the
drive-time results back to the analysis layer, and creates a flagged output
for records beyond the hospital threshold.

The point of this script is healthcare accessibility measurement. It does not
build the road network, calculate risk scores, or assign reason codes.
"""

import arcpy
import os

# Define the input layers, network settings, travel mode, and threshold.

# PARAMETERS START

arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
ELDER_FC = os.path.join(GDB, "scored_elder_records")
HOSPITAL_FC = os.path.join(GDB, "Hospital")
NETWORK_DATASET = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb\Transportation\RoadNetwork_ND"

ELDER_ID_FIELD = "OBJECTID"
TRAVEL_MODE = "Driving Time"
THRESHOLD_MINUTES = 30
ASSUMED_MPH = 45
FACILITY_SEARCH_TOLERANCE = "2000 Meters"
INCIDENT_SEARCH_TOLERANCE = "500 Meters"
SNAP_OFFSET = "25 Meters"

ACCESS_FC = os.path.join(GDB, "elder_hospital_access")
FLAGGED_FC = os.path.join(GDB, "elder_hospital_over30")
ROUTES_FC = os.path.join(GDB, "hospital_cf_routes")
TEMP_ROUTES_FC = r"in_memory\hospital_cf_routes_tmp"
SAVE_ROUTE_LINES = True
ADD_POINT_OUTPUTS_TO_MAP = True

# Network Analyst creates temporary solver layers and datasets during processing.
CF_LAYER_NAME = "HospitalClosestFacility"
NA_SOLVER_DATASET_PREFIX = "ClosestFacilitySolver"
NA_TEMP_LAYER_PREFIXES = (
    "Facilities",
    "Incidents",
    "CFRoutes",
    "Barriers",
    "PolylineBarriers",
    "PolygonBarriers"
)

DRIVE_TIME_FIELD = "Hospital_Minutes"
FLAG_FIELD = "Hosp_Over30"
NEAREST_NAME_FIELD = "NearestHospital"

# PARAMETERS END

def log(msg):
    arcpy.AddMessage(msg)
    print(msg)

def delete_if_exists(path):
    if arcpy.Exists(path):
        arcpy.management.Delete(path)

def remove_layer_if_present(map_obj, layer_name):
    for layer in map_obj.listLayers():
        try:
            current_name = layer.name
        except AttributeError:
            continue
        except Exception:
            continue

        if current_name == layer_name:
            map_obj.removeLayer(layer)

def get_active_map():
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        return aprx.activeMap
    except Exception:
        return None

# Remove temporary Network Analyst layers so only final outputs remain in the map.
def remove_network_analysis_layers_from_map():
    active_map = get_active_map()
    if active_map is None:
        return

    removed = 0
    for layer in active_map.listLayers():
        try:
            current_name = layer.name
        except Exception:
            continue

        is_cf_layer = current_name == CF_LAYER_NAME
        is_na_sublayer = any(
            current_name.startswith(prefix)
            for prefix in NA_TEMP_LAYER_PREFIXES
        )

        if is_cf_layer or is_na_sublayer:
            active_map.removeLayer(layer)
            removed += 1

    if removed:
        log(f"Removed temporary Network Analyst map layers: {removed}")

# Remove temporary Closest Facility solver datasets left in the geodatabase.
def remove_network_analysis_solver_datasets():
    old_workspace = arcpy.env.workspace
    arcpy.env.workspace = GDB

    try:
        solver_datasets = arcpy.ListDatasets(
            f"{NA_SOLVER_DATASET_PREFIX}*",
            "Feature"
        ) or []

        for dataset in solver_datasets:
            dataset_path = os.path.join(GDB, dataset)
            try:
                arcpy.management.Delete(dataset_path)
                log(f"Deleted temporary Network Analyst solver dataset: {dataset}")
            except Exception as ex:
                log(f"Could not delete temporary solver dataset {dataset}: {ex}")
    finally:
        arcpy.env.workspace = old_workspace

def ensure_field(fc, name, field_type, length=None):
    existing = {f.name for f in arcpy.ListFields(fc)}
    if name not in existing:
        if length:
            arcpy.management.AddField(fc, name, field_type, field_length=length)
        else:
            arcpy.management.AddField(fc, name, field_type)
        log(f"Added field: {name}")

def get_field_names(fc):
    return [f.name for f in arcpy.ListFields(fc)]

def choose_facility_name_field(fc):
    candidates = ["Name", "NAME", "Hospital", "HOSPITAL", "Facility", "FACILITY"]
    fields = get_field_names(fc)
    field_lookup = {f.upper(): f for f in fields}

    for candidate in candidates:
        if candidate.upper() in field_lookup:
            return field_lookup[candidate.upper()]

    string_fields = [f.name for f in arcpy.ListFields(fc) if f.type == "String"]
    if string_fields:
        return string_fields[0]

    return None

def build_facility_name_map():
    facility_id_field = arcpy.Describe(HOSPITAL_FC).OIDFieldName
    facility_name_field = choose_facility_name_field(HOSPITAL_FC)

    if facility_name_field is None:
        log("No facility name field found; nearest facility names will be blank.")
        return {}

    name_map = {}
    with arcpy.da.SearchCursor(HOSPITAL_FC, [facility_id_field, facility_name_field]) as cursor:
        for facility_id, facility_name in cursor:
            name_map[int(facility_id)] = str(facility_name) if facility_name is not None else None
    return name_map

# Check that the elder records, hospital layer, and road network are available.
def validate_inputs():
    for path, label in [
        (ELDER_FC, "elder_fc"),
        (HOSPITAL_FC, "hospital_fc"),
        (NETWORK_DATASET, "network_dataset"),
    ]:
        if not arcpy.Exists(path):
            raise ValueError(f"Missing {label}: {path}")
        log(f"Verified {label}: {path}")

def log_network_dataset_sources():
    log(f"Network dataset in use: {NETWORK_DATASET}")
    try:
        nd_desc = arcpy.Describe(NETWORK_DATASET)
        sources = getattr(nd_desc, "sources", None)

        if not sources:
            log("Network source listing unavailable from Describe().")
            return

        log("Network dataset sources:")
        for source in sources:
            source_name = getattr(source, "name", "<unknown>")
            source_type = getattr(source, "sourceType", "<unknown>")
            log(f" - {source_name} ({source_type})")
    except Exception as ex:
        log(f"Could not inspect network dataset sources: {ex}")

def choose_route_cost_field(fc):
    candidates = [
        "Total_Minutes",
        "Total_TravelTime",
        "Total_DriveTime",
        "Total_Time",
        "Total_Impedance",
        "Total_Length"
    ]
    fields = set(get_field_names(fc))
    for c in candidates:
        if c in fields:
            return c
    raise ValueError(
        "Could not find a route cost field. Available fields: "
        + ", ".join(sorted(fields))
    )

def convert_route_cost_to_minutes(field_name, value):
    if value is None:
        return None

    if field_name == "Total_Length":
        return (float(value) / 1609.344) / ASSUMED_MPH * 60

    return float(value)

def choose_route_incident_field(fc):
    candidates = ["IncidentID", "IncidentName", "IncidentOID", "Name"]
    fields = set(get_field_names(fc))
    for c in candidates:
        if c in fields:
            return c
    raise ValueError(
        "Could not find a usable route incident field. Available fields: "
        + ", ".join(sorted(fields))
    )

def choose_incident_status_field(fc):
    candidates = ["Status", "SolveStatus", "LocationStatus"]
    fields = set(get_field_names(fc))
    for candidate in candidates:
        if candidate in fields:
            return candidate
    return None

def summarize_incident_location_quality(incidents_layer):
    fields = set(get_field_names(incidents_layer))
    if "SourceID" not in fields and "SourceOID" not in fields:
        log(
            "Diagnostics: incident sublayer has no SourceID/SourceOID fields; "
            "cannot compute located/unlocated counts."
        )
        return

    probe_fields = []
    if "SourceID" in fields:
        probe_fields.append("SourceID")
    if "SourceOID" in fields:
        probe_fields.append("SourceOID")

    located = 0
    unlocated = 0
    with arcpy.da.SearchCursor(incidents_layer, probe_fields) as cursor:
        for row in cursor:
            values = list(row)
            is_located = all(v not in (None, -1) for v in values)
            if is_located:
                located += 1
            else:
                unlocated += 1

    log(f"Diagnostics: incidents located on network={located}, unlocated={unlocated}")

def parse_incident_id(value):
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        text = str(value).strip()
        for separator in (" - ",):
            if separator in text:
                text = text.split(separator)[0].strip()
                break

        if text.lower().startswith("location "):
            parts = text.split()
            if parts and parts[-1].isdigit():
                return int(parts[-1])

        try:
            return int(text)
        except Exception:
            return None

def build_access_fc():

# Copy elder records to a working analysis layer.
    delete_if_exists(ACCESS_FC)
    arcpy.management.CopyFeatures(ELDER_FC, ACCESS_FC)
    log(f"Copied elder layer to {ACCESS_FC}")

# Add fields for hospital drive time, threshold status, and nearest hospital.
    ensure_field(ACCESS_FC, DRIVE_TIME_FIELD, "DOUBLE")
    ensure_field(ACCESS_FC, FLAG_FIELD, "SHORT")
    ensure_field(ACCESS_FC, NEAREST_NAME_FIELD, "TEXT", length=100)

def summarize_solve_diagnostics(incidents_layer, routes_fc):
    incident_count = int(arcpy.management.GetCount(incidents_layer)[0])
    route_count = int(arcpy.management.GetCount(routes_fc)[0])
    log(f"Diagnostics: incidents loaded={incident_count}, routes solved={route_count}")
    summarize_incident_location_quality(incidents_layer)

    status_field = choose_incident_status_field(incidents_layer)
    if status_field:
        status_counts = {}
        with arcpy.da.SearchCursor(incidents_layer, [status_field]) as cursor:
            for row in cursor:
                status = row[0]
                status_counts[status] = status_counts.get(status, 0) + 1
        log(f"Incident status counts by {status_field}:")
        for status in sorted(status_counts):
            log(f" - {status}: {status_counts[status]}")
    else:
        log("Diagnostics: no incident status field found on incidents sublayer.")
        log("Incident sublayer fields:")
        for field_name in get_field_names(incidents_layer):
            log(f" - {field_name}")

def solve_closest_facility():

# Create the Closest Facility analysis layer.
    result = arcpy.na.MakeClosestFacilityAnalysisLayer(
        network_data_source=NETWORK_DATASET,
        layer_name=CF_LAYER_NAME,
        travel_mode=TRAVEL_MODE,
        travel_direction="TO_FACILITIES",
        number_of_facilities_to_find=1
    )

    cf_layer = result.getOutput(0)
    remove_network_analysis_layers_from_map()
    sublayers = arcpy.na.GetNAClassNames(cf_layer)

    facilities_sub = sublayers["Facilities"]
    incidents_sub = sublayers["Incidents"]

# Load hospitals and elder locations, then solve nearest hospital drive time.
    facilities_field_mappings = arcpy.na.NAClassFieldMappings(cf_layer, facilities_sub)
    if "ID" in facilities_field_mappings:
        facilities_field_mappings["ID"].mappedFieldName = arcpy.Describe(HOSPITAL_FC).OIDFieldName

    arcpy.na.AddLocations(
        in_network_analysis_layer=cf_layer,
        sub_layer=facilities_sub,
        in_table=HOSPITAL_FC,
        field_mappings=facilities_field_mappings,
        search_tolerance=FACILITY_SEARCH_TOLERANCE,
        match_type="MATCH_TO_CLOSEST",
        append="CLEAR",
        snap_to_position_along_network="SNAP",
        snap_offset=SNAP_OFFSET,
        exclude_restricted_elements="EXCLUDE"
    )
    log("Added hospital facilities.")

    field_mappings = arcpy.na.NAClassFieldMappings(cf_layer, incidents_sub)
    if "Name" in field_mappings:
        field_mappings["Name"].mappedFieldName = ELDER_ID_FIELD
    if "ID" in field_mappings:
        field_mappings["ID"].mappedFieldName = ELDER_ID_FIELD

    arcpy.na.AddLocations(
        in_network_analysis_layer=cf_layer,
        sub_layer=incidents_sub,
        in_table=ACCESS_FC,
        field_mappings=field_mappings,
        search_tolerance=INCIDENT_SEARCH_TOLERANCE,
        match_type="MATCH_TO_CLOSEST",
        append="CLEAR",
        snap_to_position_along_network="SNAP",
        snap_offset=SNAP_OFFSET,
        exclude_restricted_elements="EXCLUDE"
    )
    log("Added elder incidents.")

    arcpy.na.Solve(
        in_network_analysis_layer=cf_layer,
        ignore_invalids="SKIP",
        terminate_on_solve_error="TERMINATE"
    )
    log("Solved closest facility analysis.")

    routes_layer = arcpy.na.GetNASublayer(cf_layer, "CFRoutes")

# Copy solved route results for writing drive times back to elder records.
    delete_if_exists(TEMP_ROUTES_FC)
    arcpy.management.CopyFeatures(routes_layer, TEMP_ROUTES_FC)
    log("Prepared route results in memory.")
    incidents_layer = arcpy.na.GetNASublayer(cf_layer, "Incidents")
    summarize_solve_diagnostics(incidents_layer, TEMP_ROUTES_FC)

# Optional: save route line geometry if routes need to be mapped or reviewed.
    if SAVE_ROUTE_LINES:
        delete_if_exists(ROUTES_FC)
        arcpy.management.CopyFeatures(routes_layer, ROUTES_FC)
        log(f"Saved routes to {ROUTES_FC}")

    arcpy.management.Delete(cf_layer)
    remove_network_analysis_layers_from_map()
    remove_network_analysis_solver_datasets()

# List route fields created by ArcGIS Network Analyst.
def print_route_fields():
    log("Route fields:")
    for f in arcpy.ListFields(TEMP_ROUTES_FC):
        log(f" - {f.name}")

# Match solved route records back to the correct elder records.
def write_results_back():
# Find the route ID, travel-time, and hospital-name fields.
    route_incident_field = choose_route_incident_field(TEMP_ROUTES_FC)
    cost_field = choose_route_cost_field(TEMP_ROUTES_FC)
    facility_name_map = build_facility_name_map()
    facility_id_field = "FacilityID" if "FacilityID" in get_field_names(TEMP_ROUTES_FC) else None

    log(f"Using route incident field: {route_incident_field}")
    log(f"Using route cost field: {cost_field}")

    if cost_field == "Total_Length":
        log(f"Converting Total_Length to minutes using assumed speed: {ASSUMED_MPH} mph")

    route_map = {}
    route_fields = [route_incident_field, cost_field]
    if facility_id_field:
        route_fields.append(facility_id_field)

    with arcpy.da.SearchCursor(TEMP_ROUTES_FC, route_fields) as cursor:
        for row in cursor:
            incident_id = parse_incident_id(row[0])
            route_cost = row[1]
            facility_name = None

            if facility_id_field and len(row) > 2 and row[2] is not None:
                facility_name = facility_name_map.get(int(row[2]))

            if incident_id is None:
                continue

            minutes = convert_route_cost_to_minutes(cost_field, route_cost)
            route_map[incident_id] = (minutes, facility_name)

    write_access_updates(route_map)

# Write hospital drive time, over-threshold flag, and hospital name.
def write_access_updates(route_map):
    updated = 0
    flagged = 0
    matched = 0

    with arcpy.da.UpdateCursor(
        ACCESS_FC,
        [ELDER_ID_FIELD, DRIVE_TIME_FIELD, FLAG_FIELD, NEAREST_NAME_FIELD]
    ) as cursor:
        for row in cursor:
            oid = row[0]
            minutes, facility_name = route_map.get(oid, (None, None))

            if minutes is not None:
                matched += 1

            row[1] = minutes
            row[2] = 1 if minutes is not None and minutes > THRESHOLD_MINUTES else 0
            row[3] = facility_name

            if row[2] == 1:
                flagged += 1

            cursor.updateRow(row)
            updated += 1

    log(f"Updated records: {updated}")
    log(f"Matched routes: {matched}")
    log(f"Flagged > {THRESHOLD_MINUTES} minutes: {flagged}")

# Export elders over the hospital drive-time threshold.
def export_flagged_subset():
    delete_if_exists(FLAGGED_FC)
    arcpy.analysis.Select(ACCESS_FC, FLAGGED_FC, f"{FLAG_FIELD} = 1")

    total = int(arcpy.management.GetCount(ACCESS_FC)[0])
    flagged = int(arcpy.management.GetCount(FLAGGED_FC)[0])

    log(f"Created flagged subset: {FLAGGED_FC}")
    log(f"Total records: {total}")
    log(f"Flagged records: {flagged}")

# Add only the flagged hospital access layer to the ArcGIS Pro map.
def add_final_point_outputs_to_map():
    if not ADD_POINT_OUTPUTS_TO_MAP:
        return

    active_map = get_active_map()
    if active_map is None:
        log("No active ArcGIS Pro map found; skipping map add.")
        return

    remove_network_analysis_layers_from_map()
    remove_layer_if_present(active_map, os.path.basename(ACCESS_FC))
    remove_layer_if_present(active_map, os.path.basename(FLAGGED_FC))

    active_map.addDataFromPath(FLAGGED_FC)
    log("Added flagged hospital access output to the active map.")

def main():
    log("Starting hospital drive-time analysis...")
    remove_network_analysis_layers_from_map()
    remove_network_analysis_solver_datasets()
    validate_inputs()
    log_network_dataset_sources()
    build_access_fc()
    solve_closest_facility()
    print_route_fields()
    write_results_back()
    export_flagged_subset()
    add_final_point_outputs_to_map()
    log("Hospital drive-time workflow complete.")

if __name__ == "__main__":
    main()
