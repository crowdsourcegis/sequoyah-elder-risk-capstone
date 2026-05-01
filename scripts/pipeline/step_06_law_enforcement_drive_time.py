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

gdb = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"

elder_fc = os.path.join(gdb, "scored_elder_records")
facility_fc = os.path.join(gdb, "Law_enforcement")
network_dataset = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb\Transportation\RoadNetwork_ND"

elder_id_field = "OBJECTID"
travel_mode = "Driving Time"

threshold_minutes = 20
assumed_mph = 55

access_fc = os.path.join(gdb, "elder_law_access")
flagged_fc = os.path.join(gdb, "elder_law_over20")
routes_fc = os.path.join(gdb, "law_cf_routes")

cf_layer_name = "LawEnforcementClosestFacility"

drive_time_field = "Law_Minutes"
flag_field = "Law_Over20"
nearest_name_field = "NearestLaw"
# PARAMETERS END

def log(msg):
    arcpy.AddMessage(msg)
    print(msg)

def delete_if_exists(path):
    if arcpy.Exists(path):
        arcpy.management.Delete(path)

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

def validate_inputs():
    for path, label in [
        (elder_fc, "elder_fc"),
        (facility_fc, "facility_fc"),
        (network_dataset, "network_dataset"),
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
        return (float(value) / 1609.344) / assumed_mph * 60

    return float(value)

def choose_route_name_field(fc):
    candidates = ["Name", "IncidentName", "IncidentID"]
    fields = set(get_field_names(fc))
    for c in candidates:
        if c in fields:
            return c
    raise ValueError(
        "Could not find a usable route name field. Available fields: "
        + ", ".join(sorted(fields))
    )

def parse_route_name(route_name):
    if route_name is None:
        return None, None

    text = str(route_name).strip()

    if " - " in text:
        parts = text.split(" - ")
        incident_part = parts[0].strip()
        facility_part = parts[-1].strip()
    else:
        incident_part = text
        facility_part = None

    try:
        incident_id = int(incident_part)
    except:
        incident_id = None

    return incident_id, facility_part

# =========================
# STEP 1: BUILD OUTPUT FC
# =========================
def build_access_fc():
    delete_if_exists(access_fc)
    arcpy.management.CopyFeatures(elder_fc, access_fc)
    log(f"Copied elder layer to {access_fc}")

    ensure_field(access_fc, drive_time_field, "DOUBLE")
    ensure_field(access_fc, flag_field, "SHORT")
    ensure_field(access_fc, nearest_name_field, "TEXT", length=100)

# =========================
# STEP 2: SOLVE CLOSEST FACILITY
# =========================
def solve_closest_facility():
    result = arcpy.na.MakeClosestFacilityAnalysisLayer(
        network_data_source=network_dataset,
        layer_name=cf_layer_name,
        travel_mode=travel_mode,
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
        in_table=facility_fc,
        search_tolerance="5000 Meters",
        append="CLEAR"
    )
    log("Added law enforcement facilities.")

    field_mappings = arcpy.na.NAClassFieldMappings(cf_layer, incidents_sub)
    if "Name" in field_mappings:
        field_mappings["Name"].mappedFieldName = elder_id_field

    arcpy.na.AddLocations(
        in_network_analysis_layer=cf_layer,
        sub_layer=incidents_sub,
        in_table=access_fc,
        field_mappings=field_mappings,
        search_tolerance="5000 Meters",
        append="CLEAR"
    )
    log("Added elder incidents.")

    arcpy.na.Solve(
        in_network_analysis_layer=cf_layer,
        ignore_invalids="SKIP",
        terminate_on_solve_error="TERMINATE"
    )
    log("Solved closest law enforcement analysis.")

    routes_layer = arcpy.na.GetNASublayer(cf_layer, "CFRoutes")

    delete_if_exists(routes_fc)
    arcpy.management.CopyFeatures(routes_layer, routes_fc)
    log(f"Saved routes to {routes_fc}")

# =========================
# STEP 3: OPTIONAL DIAGNOSTICS
# =========================
def print_route_fields():
    log("Route fields:")
    for f in arcpy.ListFields(routes_fc):
        log(f" - {f.name}")

# =========================
# STEP 4: WRITE RESULTS BACK
# =========================
def write_results_back():
    route_name_field = choose_route_name_field(routes_fc)
    cost_field = choose_route_cost_field(routes_fc)

    log(f"Using route name field: {route_name_field}")
    log(f"Using route cost field: {cost_field}")

    if cost_field == "Total_Length":
        log(f"Converting Total_Length to minutes using assumed speed: {assumed_mph} mph")

    route_map = {}

    with arcpy.da.SearchCursor(routes_fc, [route_name_field, cost_field]) as cursor:
        for route_name, route_cost in cursor:
            incident_id, facility_name = parse_route_name(route_name)
            if incident_id is None:
                continue

            minutes = convert_route_cost_to_minutes(cost_field, route_cost)
            route_map[incident_id] = (minutes, facility_name)

    updated = 0
    matched = 0
    flagged = 0

    with arcpy.da.UpdateCursor(
        access_fc,
        [elder_id_field, drive_time_field, flag_field, nearest_name_field]
    ) as cursor:
        for row in cursor:
            oid = row[0]
            minutes, facility_name = route_map.get(oid, (None, None))

            if minutes is not None:
                matched += 1

            row[1] = minutes
            row[2] = 1 if minutes is not None and minutes > threshold_minutes else 0
            row[3] = facility_name

            if row[2] == 1:
                flagged += 1

            cursor.updateRow(row)
            updated += 1

    log(f"Updated records: {updated}")
    log(f"Matched routes: {matched}")
    log(f"Flagged > {threshold_minutes} minutes: {flagged}")

# =========================
# STEP 5: EXPORT FLAGGED SUBSET
# =========================
def export_flagged_subset():
    delete_if_exists(flagged_fc)
    arcpy.analysis.Select(access_fc, flagged_fc, f"{flag_field} = 1")

    total = int(arcpy.management.GetCount(access_fc)[0])
    flagged = int(arcpy.management.GetCount(flagged_fc)[0])

    log(f"Created flagged subset: {flagged_fc}")
    log(f"Total records: {total}")
    log(f"Flagged records: {flagged}")

# =========================
# MAIN
# =========================
def main():
    log("Starting law enforcement drive-time analysis...")
    validate_inputs()
    build_access_fc()
    solve_closest_facility()
    print_route_fields()
    write_results_back()
    export_flagged_subset()
    log("Law enforcement drive-time workflow complete.")

if __name__ == "__main__":
    main()
