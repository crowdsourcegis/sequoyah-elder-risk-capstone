"""
REASON CODE CALCULATOR
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Reason Code Workflow
Author: Luke A. Lynch
Date: 2026-04-20

This script calculates structured reason-code fields for the scored elder
records. It applies the project reason-code dictionary to notes and selected
status fields, then writes the primary reason code and summary text used in
the dashboard and interpretation workflow.

The point of this script is explicit, reproducible reason-code assignment. It
does not build the dictionary itself, generate synthetic records, or calculate
the base risk scores.
"""

import arcpy
import os
import sys
import re
from datetime import datetime, date

# PARAMETERS START
PROJECT = r"C:\Users\GIS\Documents\ArcGIS\Projects\Sequoyah_Elder_Risk"
GDB = r"C:\Users\GIS\Documents\ArcGIS\Projects\CAPSTONE-870.gdb"
FC = os.path.join(GDB, "scored_elder_records")
ASOFDATE = datetime.strptime("03/10/2026", "%m/%d/%Y")

if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

from reason_code_dictionary import REASON_CODES, PRIMARY_PRIORITY, LABELS

arcpy.env.workspace = GDB
arcpy.env.overwriteOutput = True

NOTE_FIELDS = list(REASON_CODES.keys())

STRUCTURED_FIELDS = [
    "RC_ActiveInvestigation",
    "RC_APSHistory",
    "RC_RefusesMedicalHelp",
    "RC_NoActiveServices",
    "RC_EconomicHardship",
    "RC_OverdueContact",
    "RC_Hospice",
    "RC_Veteran"
]

TEXT_FIELDS = [
    "PrimaryReasonCode",
    "ReasonCodeSummary"
]

SOURCE_FIELDS = [
    "Notes",
    "CurrentInvestigation",
    "APSReferral",
    "RefusesMedicalHelp",
    "ServiceUse",
    "InPoverty",
    "LastContactDate",
    "HospiceAssigned",
    "VeteranStatus"
]
# PARAMETERS END

def log(msg):
    try:
        arcpy.AddMessage(msg)
    except Exception:
        pass
    print(msg)

def existing_fields(fc):
    return {field.name: field for field in arcpy.ListFields(fc)}

def ensure_field(fc, name, field_type, length=None):
    fields = existing_fields(fc)
    if name in fields:
        return
    if length:
        arcpy.management.AddField(fc, name, field_type, field_length=length)
    else:
        arcpy.management.AddField(fc, name, field_type)
    log(f"Added field: {name}")

def require_fields(fc, names):
    fields = existing_fields(fc)
    missing = [name for name in names if name not in fields]
    if missing:
        log("Existing fields:")
        for name in sorted(fields.keys()):
            log(f"  {name}")
        raise ValueError("Missing required fields: " + ", ".join(missing))

def yes(value):
    if value is None:
        return False
    return str(value).strip().lower() in {
        "yes",
        "y",
        "true",
        "t",
        "1",
        "active",
        "present"
    }

def no_service(value):
    if value is None:
        return False
    return str(value).strip().lower() in {
        "none",
        "no active service",
        "inactive",
        "no service"
    }

def clean_text(value):
    if value in (None, "", "<Null>"):
        return ""
    return str(value).strip().lower()

def parse_date(value):
    if value in (None, "", "<Null>"):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)

    text = str(value).strip()
    formats = [
        "%m/%d/%Y",
        "%Y-%m-%d",
        "%m-%d-%Y",
        "%Y%m%d",
        "%m%d%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass

    return None

def match_any(text, patterns):
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False

def add_reason_fields():
    for name in NOTE_FIELDS:
        ensure_field(FC, name, "SHORT")

    for name in STRUCTURED_FIELDS:
        ensure_field(FC, name, "SHORT")

    ensure_field(FC, "PrimaryReasonCode", "TEXT", 64)
    ensure_field(FC, "ReasonCodeSummary", "TEXT", 255)

def primary_code(flags):
    for field in PRIMARY_PRIORITY:
        if flags.get(field) == 1:
            return LABELS.get(field, field)
    return "No Issues"

def calculate_reason_codes():
    require_fields(FC, SOURCE_FIELDS)

    update_fields = SOURCE_FIELDS + NOTE_FIELDS + STRUCTURED_FIELDS + TEXT_FIELDS

    with arcpy.da.UpdateCursor(FC, update_fields) as cursor:
        idx = {field: i for i, field in enumerate(update_fields)}

        for row in cursor:
            note = clean_text(row[idx["Notes"]])
            flags = {}

            for field, patterns in REASON_CODES.items():
                flags[field] = 1 if match_any(note, patterns) else 0

            flags["RC_ActiveInvestigation"] = 1 if yes(row[idx["CurrentInvestigation"]]) else 0
            flags["RC_APSHistory"] = 1 if yes(row[idx["APSReferral"]]) else 0
            flags["RC_RefusesMedicalHelp"] = 1 if yes(row[idx["RefusesMedicalHelp"]]) else 0
            flags["RC_NoActiveServices"] = 1 if no_service(row[idx["ServiceUse"]]) else 0
            flags["RC_EconomicHardship"] = 1 if yes(row[idx["InPoverty"]]) else 0
            flags["RC_Hospice"] = 1 if yes(row[idx["HospiceAssigned"]]) else 0
            flags["RC_Veteran"] = 1 if yes(row[idx["VeteranStatus"]]) else 0

            last_contact = parse_date(row[idx["LastContactDate"]])
            if last_contact:
                days_since_contact = (ASOFDATE - last_contact).days
                flags["RC_OverdueContact"] = 1 if days_since_contact > 180 else 0
            else:
                flags["RC_OverdueContact"] = 0

            for field in NOTE_FIELDS + STRUCTURED_FIELDS:
                row[idx[field]] = flags.get(field, 0)

            matched_labels = []

            for field in NOTE_FIELDS:
                if flags.get(field) == 1:
                    matched_labels.append(LABELS.get(field, field))

            structured_labels = {
                "RC_ActiveInvestigation": "Active Investigation",
                "RC_APSHistory": "APS History",
                "RC_RefusesMedicalHelp": "Refuses Medical Help",
                "RC_NoActiveServices": "No Active Services",
                "RC_EconomicHardship": "Economic Hardship",
                "RC_OverdueContact": "Overdue Contact",
                "RC_Hospice": "Hospice",
                "RC_Veteran": "Veteran"
            }

            for field, label in structured_labels.items():
                if flags.get(field) == 1:
                    matched_labels.append(label)

            row[idx["PrimaryReasonCode"]] = primary_code(flags)
            row[idx["ReasonCodeSummary"]] = "; ".join(matched_labels) if matched_labels else "No Issues"

            cursor.updateRow(row)

def summarize():
    total = int(arcpy.management.GetCount(FC)[0])
    log(f"Total records: {total}")

    counts = {}
    with arcpy.da.SearchCursor(FC, ["PrimaryReasonCode"]) as cursor:
        for row in cursor:
            key = row[0] or "Null"
            counts[key] = counts.get(key, 0) + 1

    log("PrimaryReasonCode counts:")
    for key, value in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        log(f"{key}: {value}")

    log("Added or updated fields:")
    for field in NOTE_FIELDS + STRUCTURED_FIELDS + TEXT_FIELDS:
        log(f"  {field}")

def main():
    log("Starting reason-code calculation")
    log(f"Dictionary folder: {PROJECT}")
    log(f"Target feature class: {FC}")

    if not arcpy.Exists(FC):
        raise ValueError(f"Feature class not found: {FC}")

    add_reason_fields()
    calculate_reason_codes()
    summarize()

    log("Done")

if __name__ == "__main__":
    main()
