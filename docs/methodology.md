## Project Scope
This project models rural elder-risk triage in Sequoyah County, Oklahoma as a spatial access and vulnerability workflow. The repository does not contain real person-level elder case records. It builds a synthetic elder point dataset calibrated to public aggregate Census inputs, scores those records with explicit rules, measures drive-time accessibility to key response services, and tests spatial clustering with stratified Getis-Ord Gi* analysis. Every component is auditable. Every flag traces to a rule.

## Primary Question
Do elevated vulnerability, weaker service access, and spatial isolation cluster in identifiable places that could support human-led triage and outreach planning? That is the question. The workflow answers it at the county level with reproducible inputs.

## Data Sources
ACS 5-Year Estimates, 2024. Public aggregate Census tables at ZCTA scale calibrate the synthetic elder population. The inputs describe age structure, marital status, internet access, disability, poverty, and living-alone patterns.

Residential address points. Address point geometry is the placement surface for synthetic elders. The workflow assigns synthetic households to available residential points by ZIP and preserves an audit trail for repeated or overflow placements.

ArcGIS road network inputs. A project road feature class is copied into the transportation feature dataset and used to build the network dataset required for accessibility analysis.

Service facility layers. Hospital and law-enforcement point layers serve as Closest Facility destinations during drive-time analysis.

## Data Included in the Repository
Cleaned ACS input tables

Synthetic workflow scripts

Documentation and audit notes

Validation outputs generated from the synthetic population process

## Data Not Included in the Repository
Real elder case records

The full ArcGIS Pro geodatabase

The ArcGIS Pro project file (.aprx)

Hosted ArcGIS Online layers

Credentials, publication scripts, or protected operational data

## Workflow Summary
ACS acquisition and cleaning. Census tables are queried and reshaped into cleaned, named-column CSVs used by the downstream generator.

Synthetic elder generation. A synthetic elder population is generated from ACS-calibrated ZIP-level counts. Records are assigned demographic and social attributes using explicit probability rules tied to the ACS tables. Residential coordinates come from address points, not made-up map locations.

Composite risk scoring. Synthetic records are scored with a rule-based ArcPy workflow across several vulnerability and service domains. The scoring model is explicit and auditable. No black-box classifier is involved.

Network dataset preparation. The road source is copied into the transportation feature dataset, the network dataset is created if needed, and the network is rebuilt so routing is reproducible.

Accessibility analysis. Closest Facility analysis is run for hospitals and law enforcement. Elder points and facilities are explicitly located onto the road network using larger search tolerances, MATCH_TO_CLOSEST, and SNAP against the Roads source. This improves the share of near-road points that receive valid drive times without manual cleanup.

Settlement regime assignment. Records are labeled by settlement context so later hotspot analysis can be compared across rural and node-based geographies.

Stratified Gi* sensitivity testing. Multiple Getis-Ord Gi* runs are executed across subsets, fields, and distance bands. These are scenario tests, not a single unquestioned hotspot result.

Gi* summary and reason codes. Later steps summarize Gi* outputs and calculate rule-based reason codes to support interpretation in the dashboard environment.

## Modeling Assumptions
Synthetic elder counts are controlled by ACS aggregate totals, not sampled from observed case files.

Address placement uses residential point availability within ZIP codes and may reuse points when demand exceeds available locations. Every reuse is audit-labeled.

Drive-time outputs depend on the quality and routability of the road network dataset present in ArcGIS Pro.

Risk scores and reason codes are deterministic functions of the fields created by the workflow. They do not represent clinician judgment.

## Reproducibility
The workflow is designed to reproduce within a matching ArcGIS environment. The synthetic population generator uses RNG seed 42. With the same cleaned ACS inputs, the same address point source, and the same ArcGIS network environment, the scripts produce the same synthetic outputs and the same derived accessibility fields. That is the baseline a peer-reviewed GIS workflow requires.

## Intended Use
This workflow is for human-in-the-loop triage support, exploratory analysis, and capstone research demonstration. It is not an automated decision system. It is not a substitute for field verification, agency policy, or professional judgment. Human reviewers set every threshold. No automated action touches any elder record.
