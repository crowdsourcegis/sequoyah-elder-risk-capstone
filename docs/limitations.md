## Synthetic Population Limits
The elder point dataset in this project is synthetic. It is calibrated to real
aggregate Census patterns, but it does not represent observed individual elder
case records. A synthetic point may resemble a plausible household location and
attribute profile without corresponding to any real person or active case.

## Aggregate ACS Limits
The workflow depends on ACS 5-Year Estimates summarized at ZCTA scale. Those
tables are suitable for calibration, but they smooth variation within ZIP-like
areas and can hide local differences at the neighborhood or road-segment level.
The workflow should therefore be interpreted as an approximation of broad
spatial conditions, not a census of true household-level vulnerability.

## Address Point Placement Limits
Synthetic elders are assigned to available residential address points by ZIP.
That improves geographic realism compared with random placement, but it is still
a modeled placement process. When synthetic demand exceeds available point
capacity, the workflow can reuse address points. Those cases are audit-labeled,
but they remain a modeling compromise rather than a confirmed housing pattern.

## Road Network and Drive-Time Limits
Accessibility results depend on the completeness and routability of the ArcGIS
road network dataset. If a road segment is missing, disconnected, restricted,
or not routable in the network build, the resulting drive times will reflect
that limitation. The snapping improvements in the routing steps help near-road
points receive valid travel times, but they do not create connectivity where
the network itself lacks it.

## Facility Layer Limits
Hospital and law-enforcement accessibility are only as accurate as the facility
layers used as Closest Facility destinations. Missing facilities, outdated
locations, or simplified point representations can affect travel-time outputs.
The workflow measures proximity to the included facility layers, not every
possible real-world response option.

## Risk Score Limits
Composite risk scores are rule-based and intentionally transparent. That is a
strength for auditability, but it also means the model reflects the chosen
rules, thresholds, and field definitions rather than a clinically validated
predictive outcome model. High scores indicate modeled triage concern under the
project rules, not proof of actual harm.

## Gi* Sensitivity Limits
Getis-Ord Gi* results are sensitive to subset choice, analysis field, and
distance band. For that reason, the workflow runs multiple stratified Gi*
scenarios instead of presenting one hotspot surface as unquestioned truth.
Even so, hotspot outputs remain analytic interpretations of spatial structure,
not direct evidence of service failure or case concentration on the ground.

## Reason Code Limits
Reason codes are deterministic summaries derived from workflow fields. They help
explain why a synthetic record or cluster may appear important in the dashboard,
but they are not diagnoses, legal findings, or investigator conclusions.

## Temporal Limits
This workflow combines ACS 2024 aggregate inputs, synthetic modeling choices,
and locally built ArcGIS assets. Over time, service locations, roads, community
conditions, and population structure can change. Outputs should therefore be
treated as time-bound to the current project build rather than permanently
stable representations of Sequoyah County conditions.

## Operational Limits
The repository does not include the full geodatabase, the ArcGIS Pro project
file, or hosted ArcGIS Online layers. That keeps the repo clean and safer to
share, but it also means a reviewer cannot reproduce every map or service
configuration from GitHub alone without the matching ArcGIS environment.

## Use Limits
This workflow is for human-in-the-loop triage support, exploratory GIS
analysis, and capstone demonstration. It is not an automated decision engine.
No output in this repository should be used on its own to trigger an action,
label a household, or replace field verification and professional judgment.
