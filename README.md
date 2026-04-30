# sequoyah-elder-risk-dashboard

A reproducible GIS capstone workflow for rural elder safeguarding triage in Sequoyah County, Oklahoma.

This repository contains all scripts, documentation, validation outputs, ACS data inputs, and dashboard
configuration notes for the capstone project. It does not include the final paper, presentation slides,
the ArcGIS Pro project file (.aprx), the full geodatabase, any hosted ArcGIS Online layer, or any
real person-level records.

---

## What This Project Does

Rural oversight agencies face a structural disadvantage in elder safeguarding: distance compresses
welfare check frequency, sparse service networks leave elders without routine touchpoints, and uneven
broadband limits remote monitoring. This workflow addresses that gap by integrating five analytical
components into a single human-in-the-loop triage interface:

- **Synthetic elder population generation** calibrated to real 2024 ACS 5-Year Estimate data
- **Composite risk scoring** across eight equal-weight domains using ArcPy
- **Network accessibility analysis** measuring drive time to hospitals and law enforcement
- **Getis-Ord Gi* hotspot detection** identifying statistically significant clusters of elder risk
- **ArcGIS Online Operations Dashboard** delivering the integrated picture to caseworkers

The result is a 7,810-record synthetic elder layer for Sequoyah County with full demographic fidelity
to Census data, no real PII, and a complete audit trail from raw ACS input to dashboard display.

---

## Repository Structure
sequoyah-elder-risk-dashboard/
│
├── README.md
├── CITATION.cff
├── LICENSE
├── .gitignore
│
├── scripts/
│ ├── census_query_v5.py # ACS API acquisition for six ZCTA-level tables
│ ├── mock_address_generator_v10.py # Synthetic elder record generator (RNG seed 42)
│ ├── calculate_scores.py # Eight-domain composite risk scoring via ArcPy
│ ├── calculate_reason_codes.py # Human-readable reason code assignment
│ ├── reason_code_dictionary.py # Lookup dictionary for all reason code definitions
│ ├── gi_countywide_composite_300.py # Optimized Hot Spot Analysis (Gi*)
│ ├── hospital_drive_time.py # Closest Facility analysis, 30-min hospital threshold
│ └── law_enforcement_drive_time.py # Closest Facility analysis, 20-min LE threshold
│
├── docs/
│ ├── methodology.md # Full pipeline methodology and design decisions
│ ├── dashboard_configuration.md # ArcGIS Online dashboard setup and widget notes
│ ├── data_dictionary.md # All fields, types, sources, and scoring role
│ ├── limitations.md # Known limitations and interpretive constraints
│ └── layer_stack.md # Layer order, symbology logic, and publish sequence
│
├── data/
│ └── acs_cleaned/
│ ├── B01001_sequoyah.csv # Sex by Age — population controls
│ ├── B12002_sequoyah.csv # Sex by Marital Status by Age
│ ├── B28005_sequoyah.csv # Age by Internet Subscription
│ ├── B18101_sequoyah.csv # Sex by Age by Disability Status
│ ├── B17020_sequoyah.csv # Poverty Status by Age
│ └── B11010_sequoyah.csv # Nonfamily Households / Living Alone
│
├── validation/
│ ├── v10_generation_summary.csv # Total record counts by ZIP
│ ├── v10_zip_calibration_check.csv # ACS target vs. generated count per ZCTA
│ ├── v10_field_completeness_check.csv
│ ├── v10_household_occupancy_check.csv
│ ├── v10_generation_metadata.json # Runtime parameters and RNG seed record
│ └── reason_code_validation_tests.csv
│
├── dashboard/
│ ├── final_dashboard_screenshot.jpg
│ ├── field_keep_use.csv # Field-level keep/hide decisions for dashboard layers
│ └── dashboard_text_widgets.md
│
├── arcade/
│ ├── popup_expression.md
│ ├── label_expression.md
│ └── symbology_notes.md
│
└── notes/
├── scoring_and_field.md
├── gi_notes.md
├── network_analysis_notes.md
└── svi_fcc_overlay_notes.md

## ACS Inputs

The `data/acs_cleaned/` folder contains six cleaned aggregate CSVs acquired from the U.S. Census
Bureau API (2024 ACS 5-Year Estimates, ZCTA level). These are public aggregate inputs — not
individual records — and are included so the generator logic can be reviewed without requiring a
live API request. No individual-level or protected data is present anywhere in this repository.

---

## How to Reproduce

1. Run `census_query_v5.py` to re-acquire ACS CSVs (optional — cleaned CSVs already in `data/acs_cleaned/`)
2. Run `mock_address_generator_v10.py` to generate the synthetic elder record layer
3. Confirm calibration against `validation/` outputs before proceeding
4. Open ArcGIS Pro, run `calculate_scores.py` then `calculate_reason_codes.py`
5. Run `gi_countywide_composite_300.py` for hotspot detection
6. Run `hospital_drive_time.py` and `law_enforcement_drive_time.py` for accessibility layers
7. Publish to ArcGIS Online and configure the dashboard per `docs/dashboard_configuration.md`

The generator uses **RNG seed 42**. Any researcher with these scripts and the ACS CSVs will produce
the identical 7,810-record layer.

---

## Governance

This workflow is designed for **human-in-the-loop triage only**. No automated action is taken on
any record. All risk thresholds are set by human reviewers. Every flag produced by the scoring
pipeline carries an evidence trace to the specific rule or ACS-calibrated threshold that generated
it, consistent with established design requirements for algorithmic support in high-stakes
public-sector decisions.

---

## What Is Not in This Repository

| Item | Reason |
|---|---|
| Final capstone paper | Submitted separately per program requirements |
| ArcGIS Pro project file (.aprx) | Environment-specific, too large for version control |
| Full geodatabase (.gdb) | Too large; regenerate from scripts |
| Hosted ArcGIS Online layers | Access-controlled; see dashboard screenshot in `dashboard/` |
| Real person-level records | None exist — the layer is fully synthetic |

---

## Citation

If you use this workflow, please cite using the metadata in `CITATION.cff` or the GitHub
"Cite this repository" button.

Lynch, L. (2026). *sequoyah-elder-risk-dashboard* (v1.0.0).
https://github.com/crowdsourcegis/sequoyah-elder-risk-dashboard
https://orcid.org/0009-0005-6505-1639

---

## License

MIT License. © 2026 Luke Lynch. See `LICENSE` for full terms.
