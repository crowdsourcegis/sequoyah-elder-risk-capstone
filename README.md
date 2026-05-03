# sequoyah-elder-risk-dashboard

A GIS capstone workflow for rural elder safeguarding triage in Sequoyah County, Oklahoma.

This repository holds the working pipeline, the legacy scripts kept for audit, the cleaned ACS inputs, the generator validation outputs, and the notes needed to understand how the dashboard layer was built. It does not include the final paper, the presentation slides, the ArcGIS Pro project file (`.aprx`), the full geodatabase, any hosted ArcGIS Online layer, or any real person-level records.

## What This Project Is

This project treats rural elder-risk triage as a spatial access problem, not just a case-management problem. The working idea is straightforward: if vulnerability, distance, weak service coverage, and isolation stack in the same places, then triage should surface those places explicitly instead of making staff infer them one case at a time.

The workflow combines five pieces:

- Synthetic elder population generation calibrated to real 2024 ACS 5-Year Estimate data
- Composite risk scoring across eight equal-weight domains using ArcPy
- Network accessibility analysis measuring drive time to hospitals and law enforcement
- Getis-Ord Gi* hotspot detection identifying statistically significant clusters of elder risk
- Rule-based reason-code extraction supporting dashboard interpretation

The result is a synthetic elder workflow for Sequoyah County with a visible audit trail from raw ACS input to scored, accessibility-aware, spatially stratified outputs.

## Repository Structure

`scripts/pipeline/` - Canonical workflow scripts in execution order

`scripts/legacy/` - Earlier, superseded, or exploratory scripts retained for reproducibility audit

`docs/` - Methodology and limitations

`data/acs_cleaned/` - Six ACS 5-Year Estimate CSVs for Sequoyah County

`validation/` - Generator calibration outputs and audit trail

`PUBLISHING.md` - Manual ArcGIS Pro -> ArcGIS Online publication bridge

## Core Pipeline

1. `scripts/pipeline/step_01_census_query_v5.py`
   ACS data acquisition
2. `scripts/pipeline/step_02_mock_address_generator_v10.py`
   Synthetic population generation
3. `scripts/pipeline/step_03_calculate_scores.py`
   Composite risk scoring and field schema
4. `scripts/pipeline/step_04_network_dataset.py`
   Network dataset build
5. `scripts/pipeline/step_05_hospital_drive_time.py`
   Hospital Closest Facility, 30-minute threshold
6. `scripts/pipeline/step_06_law_enforcement_drive_time.py`
   Law enforcement Closest Facility, 20-minute threshold
7. `scripts/pipeline/step_07_part1_create_settlement_regimes.py`
   `SpatialRegime` field assignment
8. `scripts/pipeline/step_08_part2_stratified_gi.py`
   Stratified Gi* analysis
9. `scripts/pipeline/step_09_part3_summarize_results.py`
   Gi* classification count summaries
10. `scripts/pipeline/step_10_calculate_reason_codes.py`
   Rule-based reason-code extraction

`scripts/pipeline/reason_code_dictionary.py` is the rule library used by Step 10. It belongs to the active pipeline, but it is a dependency module rather than its own run step.

Important routing note:
Steps 5 and 6 explicitly locate address points and facilities onto the road network before solving. The current pipeline scripts use larger search tolerances, `MATCH_TO_CLOSEST`, and `SNAP` against the `Roads` network source so near-road points are more likely to receive valid drive times without manual cleanup.

## Legacy Scripts

Scripts in `scripts/legacy/` stay in the repo on purpose. They show earlier or exploratory versions of logic that were later consolidated into the active pipeline. I kept them for audit, comparison, and method transparency, not as parallel official workflows.

- `composite_risk.py`
- `scoring_and_field.py`
- `optimized_hot_spot_analysis.py`
- `elder_triage_pipeline.py`

## ACS Inputs

The `data/acs_cleaned/` folder contains six cleaned aggregate CSVs acquired from the U.S. Census Bureau API (2024 ACS 5-Year Estimates, ZCTA level). These are public aggregate inputs, not individual records. They are included so the generator logic can be inspected without requiring a live API pull. No individual-level or protected data is present anywhere in this repository.

## Run Order

1. Run `scripts/pipeline/step_01_census_query_v5.py` to acquire or refresh ACS source tables.
2. Run `scripts/pipeline/step_02_mock_address_generator_v10.py` to generate the synthetic elder record layer.
3. Confirm generator calibration against the files in `validation/`.
4. Run `scripts/pipeline/step_03_calculate_scores.py` to create the scored elder layer.
5. Run `scripts/pipeline/step_04_network_dataset.py` to build the network dataset required for accessibility analysis.
6. Run `scripts/pipeline/step_05_hospital_drive_time.py` and `scripts/pipeline/step_06_law_enforcement_drive_time.py` to calculate accessibility outputs.
7. Run `scripts/pipeline/step_07_part1_create_settlement_regimes.py` to assign settlement regimes and ACS score values.
8. Run `scripts/pipeline/step_08_part2_stratified_gi.py` to generate the stratified Gi* outputs.
9. Run `scripts/pipeline/step_09_part3_summarize_results.py` to summarize Gi* classifications.
10. Run `scripts/pipeline/step_10_calculate_reason_codes.py` to write structured reason-code outputs.
11. Publish or overwrite the hosted ArcGIS Online feature layer using the documented manual bridge in `PUBLISHING.md`.

`scripts/pipeline/step_10_calculate_reason_codes.py` uses `scripts/pipeline/reason_code_dictionary.py` as its rule library.
ArcGIS Online publication is documented as a manual bridge in `PUBLISHING.md`. That choice is deliberate. It keeps the public repo reproducible without pretending everyone reviewing it shares the same AGOL environment, credentials, or org settings.

The generator uses RNG seed `42`. Anyone with these scripts, the same cleaned ACS inputs, and the same ArcGIS environment should be able to reproduce the same synthetic output.

## Governance

This workflow is for human-in-the-loop triage only. It does not make decisions on its own. Every risk flag comes from an explicit rule, threshold, or ACS-calibrated input that can be traced back through the code and outputs.

## What Is Not in This Repository

The final paper, `.aprx` project file, full geodatabase, hosted ArcGIS Online layers, and any publication push script are not included. Publication is documented in `PUBLISHING.md` as a controlled manual ArcGIS Pro step. The workflow itself is documented here in executable and reviewable form. No real person-level records exist anywhere in this project.

## Citation

Use the metadata in `CITATION.cff` or the GitHub "Cite this repository" button.

Lynch, L. A. (2026). Sequoyah elder risk dashboard (Version 1.0.0) [Computer software]. GitHub. 
https://github.com/crowdsourcegis/sequoyah-elder-risk-dashboard

Lynch, L. (2026). *sequoyah-elder-risk-dashboard* (v1.0.0).
[https://github.com/crowdsourcegis/sequoyah-elder-risk-dashboard](https://github.com/crowdsourcegis/sequoyah-elder-risk-capstone/tree/main)

https://orcid.org/0009-0005-6505-1639

## License

MIT License. Copyright 2026 Luke Lynch. See `LICENSE.md` for full terms.
