"""
LAW ENFORCEMENT DRIVE-TIME ANALYSIS
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Network Accessibility Workflow
Author: Luke A. Lynch
Date: 2026-03-22

This script calculates nearest-law-enforcement drive-time accessibility for
the scored elder records. It uses the project road network dataset, writes the
drive-time results back to the analysis layer, and creates flagged outputs for
records beyond the law-enforcement threshold.

The point of this script is public-safety accessibility measurement. It does
not build the road network, calculate risk scores, or assign reason codes.
"""

import arcpy
import os

# PARAMETERS START
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False

GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"

ELDER_FC = os.path.join(GDB, "scored_elder_records")
FACILITY_FC = os.path.join(GDB, "Law_enforcement")
NETWORK_DATASET = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb\Transportation\RoadNetwork_ND"

ELDER_ID_FIELD = "OBJECTID"
TRAVEL_MODE = "Driving Time"

THRESHOLD_MINUTES = 20
ASSUMED_MPH = 55
FACILITY_SEARCH_TOLERANCE = "10000 Meters"
INCIDENT_SEARCH_TOLERANCE = "20000 Meters"
SNAP_OFFSET = "25 Meters"

ACCESS_FC = os.path.join(GDB, "elder_law_access")
FLAGGED_FC = os.path.join(GDB, "elder_law_over20")
ROUTES_FC = os.path.join(GDB, "law_cf_routes")
TEMP_ROUTES_FC = r"in_memory\law_cf_routes_tmp"
SAVE_ROUTE_LINES = False
ADD_POINT_OUTPUTS_TO_MAP = True

CF_LAYER_NAME = "LawEnforcementClosestFacility"

DRIVE_TIME_FIELD = "Law_Minutes"
FLAG_FIELD = "Law_Over20"
NEAREST_NAME_FIELD = "NearestLaw"
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

def add_final_point_outputs_to_map():
    if not ADD_POINT_OUTPUTS_TO_MAP:
        return

    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        active_map = aprx.activeMap
    except Exception:
        log("No active ArcGIS Pro map found; skipping map add.")
        return

    if active_map is None:
        log("No active ArcGIS Pro map found; skipping map add.")
        return

    remove_layer_if_present(active_map, CF_LAYER_NAME)
    remove_layer_if_present(active_map, os.path.basename(ACCESS_FC))
    remove_layer_if_present(active_map, os.path.basename(FLAGGED_FC))

    active_map.addDataFromPath(ACCESS_FC)
    active_map.addDataFromPath(FLAGGED_FC)
    log("Added final point outputs to the active map.")

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
    candidates = ["Name", "NAME", "Agency", "AGENCY", "Facility", "FACILITY"]
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
    facility_id_field = arcpy.Describe(FACILITY_FC).OIDFieldName
    facility_name_field = choose_facility_name_field(FACILITY_FC)

    if facility_name_field is None:
        log("No facility name field found; nearest facility names will be blank.")
        return {}

    name_map = {}
    with arcpy.da.SearchCursor(FACILITY_FC, [facility_id_field, facility_name_field]) as cursor:
        for facility_id, facility_name in cursor:
            name_map[int(facility_id)] = str(facility_name) if facility_name is not None else None
    return name_map

def validate_inputs():
    for path, label in [
        (ELDER_FC, "elder_fc"),
        (FACILITY_FC, "facility_fc"),
        (NETWORK_DATASET, "network_dataset"),
    ]:
        if not arcpy.Exists(path):
            raise ValueError(f"Missing {label}: {path}")
        log(f"Verified {label}: {path}")

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
    candidates = ["IncidentID", "IncidentOID", "IncidentName", "Name"]
    fields = set(get_field_names(fc))
    for c in candidates:
        if c in fields:
            return c
    raise ValueError(
        "Could not find a usable route incident field. Available fields: "
        + ", ".join(sorted(fields))
    )

def parse_incident_id(value):
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        text = str(value).strip()
        if " - " in text:
            text = text.split(" - ")[0].strip()
        try:
            return int(text)
        except Exception:
            return None

def build_access_fc():
    delete_if_exists(ACCESS_FC)
    arcpy.management.CopyFeatures(ELDER_FC, ACCESS_FC)
    log(f"Copied elder layer to {ACCESS_FC}")

    ensure_field(ACCESS_FC, DRIVE_TIME_FIELD, "DOUBLE")
    ensure_field(ACCESS_FC, FLAG_FIELD, "SHORT")
    ensure_field(ACCESS_FC, NEAREST_NAME_FIELD, "TEXT", length=100)

def solve_closest_facility():
    result = arcpy.na.MakeClosestFacilityAnalysisLayer(
        network_data_source=NETWORK_DATASET,
        layer_name=CF_LAYER_NAME,
        travel_mode=TRAVEL_MODE,
        travel_direction="TO_FACILITIES",
        number_of_facilities_to_find=1
    )

    cf_layer = result.getOutput(0)
    sublayers = arcpy.na.GetNAClassNames(cf_layer)

    facilities_sub = sublayers["Facilities"]
    incidents_sub = sublayers["Incidents"]

    arcpy.na.AddLocations(
        in_network_analysis_layer=cf_layer,
        sub_layer=facilities_sub,
        in_table=FACILITY_FC,
        search_tolerance=FACILITY_SEARCH_TOLERANCE,
        search_criteria="Roads SHAPE",
        match_type="MATCH_TO_CLOSEST",
        append="CLEAR",
        snap_to_position_along_network="SNAP",
        snap_offset=SNAP_OFFSET,
        exclude_restricted_elements="EXCLUDE"
    )
    log("Added law enforcement facilities.")

    field_mappings = arcpy.na.NAClassFieldMappings(cf_layer, incidents_sub)
    if "Name" in field_mappings:
        field_mappings["Name"].mappedFieldName = ELDER_ID_FIELD

    arcpy.na.AddLocations(
        in_network_analysis_layer=cf_layer,
        sub_layer=incidents_sub,
        in_table=ACCESS_FC,
        field_mappings=field_mappings,
        search_tolerance=INCIDENT_SEARCH_TOLERANCE,
        search_criteria="Roads SHAPE",
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
    log("Solved closest law enforcement analysis.")

    routes_layer = arcpy.na.GetNASublayer(cf_layer, "CFRoutes")

    delete_if_exists(TEMP_ROUTES_FC)
    arcpy.management.CopyFeatures(routes_layer, TEMP_ROUTES_FC)
    log("Prepared route results in memory.")

    if SAVE_ROUTE_LINES:
        delete_if_exists(ROUTES_FC)
        arcpy.management.CopyFeatures(routes_layer, ROUTES_FC)
        log(f"Saved routes to {ROUTES_FC}")

    arcpy.management.Delete(cf_layer)

def print_route_fields():
    log("Route fields:")
    for f in arcpy.ListFields(TEMP_ROUTES_FC):
        log(f" - {f.name}")

def write_results_back():
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

    updated = 0
    matched = 0
    flagged = 0

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

def export_flagged_subset():
    delete_if_exists(FLAGGED_FC)
    arcpy.analysis.Select(ACCESS_FC, FLAGGED_FC, f"{FLAG_FIELD} = 1")

    total = int(arcpy.management.GetCount(ACCESS_FC)[0])
    flagged = int(arcpy.management.GetCount(FLAGGED_FC)[0])

    log(f"Created flagged subset: {FLAGGED_FC}")
    log(f"Total records: {total}")
    log(f"Flagged records: {flagged}")
def main():
    log("Starting law enforcement drive-time analysis...")
    validate_inputs()
    build_access_fc()
    solve_closest_facility()
    print_route_fields()
    write_results_back()
    export_flagged_subset()
    add_final_point_outputs_to_map()
    log("Law enforcement drive-time workflow complete.")

if __name__ == "__main__":
    main()
