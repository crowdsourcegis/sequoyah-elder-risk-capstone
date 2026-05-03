# ArcGIS Online Publishing Bridge

This document records the manual bridge between the local pipeline outputs and the hosted ArcGIS Online layer.

Publication is handled manually in ArcGIS Pro with **Share As Web Layer**. That is intentional. A scripted publish step would be tied to one account, one organization, and one set of credentials. For a public capstone repo, the cleaner approach is to document the exact bridge that was actually used.

## Scope

- This bridge begins **after** pipeline Step 10 completes.
- Source data is expected in the project geodatabase (`CAPSTONE-870.gdb`).
- This bridge covers publish and overwrite behavior. It does not try to document every dashboard styling decision.
- Network Analyst working layers and `ClosestFacilitySolver*` scratch datasets are temporary processing artifacts and are not publish targets.

## Pre-Publish Checklist

1. Confirm pipeline scripts in `scripts/pipeline/` have run in order.
2. Confirm required fields exist in the publish layer:
   `CompositeScore`, `RiskLevel`, `SpatialRegime`, `ACSScore`, reason-code outputs from Step 10, and any accessibility fields required by the dashboard (for example `Hospital_Minutes`, `Hosp_Over30`, `NearestHospital`, `Law_Minutes`, `Law_Over20`, `NearestLaw`).
3. Confirm final feature class used for publishing.
   Default: `scored_elder_records`.
   If the dashboard requires network-access outputs, publish the feature class that already contains those fields.
4. Confirm symbology and popup expressions are finalized locally in ArcGIS Pro.
5. Confirm the source layer schema is stable (field names and data types unchanged) relative to the currently hosted layer.
6. Confirm run currency fields or metadata (for example `AsOfDate`) match the current pipeline run.

## Manual Publish Procedure (ArcGIS Pro)

1. Open ArcGIS Pro and sign in to the target ArcGIS Online organization.
2. Add the final output layer to the map (typically `scored_elder_records`, unless a merged/accessibility-enriched layer is your publish source).
3. Right-click the layer and select **Sharing** -> **Share As Web Layer**.
4. Set:
   - **Name**: stable service name for dashboard wiring
   - **Summary**: short method-aware description
   - **Tags**: include `safety`, `sequoyah`, `elder-risk`, `triage`
5. Under **Layer Type**, choose **Feature**.
6. Under **Capabilities**, enable only what the dashboard actually needs. In most cases that means Query and nothing more.
7. Under **Location**, choose the target folder in your AGOL content.
8. Under **Configuration**:
   confirm coordinate system and rendering behavior, confirm field visibility and aliases, and disable editing if the layer is read-only for dashboard users.
9. Click **Analyze** and resolve all blocking errors.
10. Click **Publish**.

## Overwrite Procedure (Subsequent Runs)

Use overwrite to keep the dashboard item references stable. That matters more than creating a fresh hosted layer every run.

1. Open ArcGIS Pro with the updated source layer.
2. Repeat **Share As Web Layer** with the same service name.
3. Choose **Overwrite existing web layer**.
4. Re-run **Analyze**, resolve errors, and publish.
5. Verify item ID and layer URL remain unchanged.
6. Re-open the hosted item data tab and confirm key fields still exist with expected types.

## Verification Checklist

1. Open the hosted feature layer item page in AGOL.
2. Confirm record count is plausible for the current run.
3. Spot-check key fields, field types, and domains.
4. Confirm accessibility fields expected by the dashboard are populated when included in the publish source.
5. Open the dashboard and confirm:
   the layer loads, filters behave, indicator widgets resolve the expected fields, and popup expressions render correctly.

## Reproducibility Notes

- This repository intentionally keeps publication as a documented manual step.
- No AGOL credentials or org-specific IDs are embedded in executable scripts.
- If this repo is ever moved into a controlled internal environment, an optional `step_11_publish_to_agol.py` could be added later. For the public capstone version, this document is the more honest bridge.
