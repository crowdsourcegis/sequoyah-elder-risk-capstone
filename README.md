# sequoyah-elder-risk-dashboard

A reproducible GIS capstone workflow for rural elder safeguarding triage in Sequoyah County, Oklahoma.

This repo contains all scripts, documentation, validation outputs, ACS data inputs, and dashboard
configuration notes. It does not include the final paper, presentation slides, the ArcGIS Pro
project file (.aprx), the full geodatabase, any hosted ArcGIS Online layer, or any real
person-level records.

## What This Project Does

Rural oversight agencies face a structural disadvantage in elder safeguarding. Distance compresses
welfare check frequency, sparse service networks leave elders without routine touchpoints, and uneven
broadband limits remote monitoring. This workflow addresses that gap by integrating five components
into a single human-in-the-loop triage interface:

- **Synthetic elder population generation** calibrated to real 2024 ACS 5-Year Estimate data
- **Composite risk scoring** across eight equal-weight domains using ArcPy
- **Network accessibility analysis** measuring drive time to hospitals and law enforcement
- **Getis-Ord Gi* hotspot detection** identifying statistically significant clusters of elder risk
- **ArcGIS Online Operations Dashboard** delivering the integrated picture to caseworkers

The result is a 7,810-record synthetic elder layer for Sequoyah County with full demographic fidelity
to Census data, no real PII, and a complete audit trail from raw ACS input to dashboard display.

## Repository Structure

**scripts/** - Python and ArcPy pipeline, runs in order from census query to drive-time analysis

**docs/** - Methodology, data dictionary, dashboard setup, and limitations

**data/acs_cleaned/** - Six ACS 5-Year Estimate CSVs for Sequoyah County

**validation/** - Generator calibration outputs and audit trail

**dashboard/** - Screenshot, field configuration, and widget text

**arcade/** - Popup, label, and symbology expressions

## ACS Inputs

The `data/acs_cleaned/` folder contains six cleaned aggregate CSVs acquired from the U.S. Census
Bureau API (2024 ACS 5-Year Estimates, ZCTA level). These are public aggregate inputs, not
individual records, and are included so the generator logic can be reviewed without requiring a
live API request. No individual-level or protected data is present anywhere in this repository.

## How to Reproduce

1. Run `census_query_v5.py` to re-acquire ACS CSVs (optional, cleaned CSVs already in `data/acs_cleaned/`)
2. Run `mock_address_generator_v10.py` to generate the synthetic elder record layer
3. Confirm calibration against `validation/` outputs before proceeding
4. Open ArcGIS Pro, run `calculate_scores.py` then `calculate_reason_codes.py`
5. Run `gi_countywide_composite_300.py` for hotspot detection
6. Run `hospital_drive_time.py` and `law_enforcement_drive_time.py` for accessibility layers
7. Publish to ArcGIS Online and configure the dashboard per `docs/dashboard_configuration.md`

The generator uses **RNG seed 42**. Any researcher with these scripts and the ACS CSVs will produce
the identical 7,810-record layer.

## Governance

This workflow is designed for **human-in-the-loop triage only**. No automated action is taken on
any record. All risk thresholds are set by human reviewers. Every flag carries an evidence trace
to the specific rule or ACS-calibrated threshold that produced it, consistent with established
design requirements for algorithmic support in high-stakes public-sector decisions.

## What Is Not in This Repository

The final paper, .aprx project file, full geodatabase, and hosted ArcGIS Online layers are not
included. The synthetic elder layer is fully reproducible from the scripts and ACS CSVs in this
repo. No real person-level records exist anywhere in this project.

## Citation

Use the metadata in `CITATION.cff` or the GitHub "Cite this repository" button.

Lynch, L. (2026). *sequoyah-elder-risk-dashboard* (v1.0.0).
https://github.com/crowdsourcegis/sequoyah-elder-risk-dashboard
https://orcid.org/0009-0005-6505-1639

## License

MIT License. © 2026 Luke Lynch. See `LICENSE` for full terms.
