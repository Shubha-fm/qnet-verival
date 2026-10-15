# IrelandQCI measurement arm: source data and derived verification scenarios

## Origin, attribution, and license

Source: Horgan et al., **QKD Network Characterisation and Coexistence Datasets with Standardised Performance Metrics and Experimental Methods**, v2, Zenodo record 21792844, DOI https://doi.org/10.5281/zenodo.21792844. Credit the IrelandQCI Project / CONNECT Centre, Trinity College Dublin, and the original creators recorded in `source/zenodo_record.json`.

The original `source/LICENSE.txt` grants CC BY 4.0 reuse. All 39 deposited files are redistributed unchanged with their original names and license. The source researchers collected the measurements. This artifact reuses them; it does not claim a new hardware experiment or affiliation with their laboratory. Code, synthetic benchmark records, and source-measurement files have distinct provenance. The source license is not presented as a blanket license assignment for every item in this package.

## Acquisition and integrity

`src/acquire_measurements.py` retrieves the pinned record and checks every source file against the record's MD5. `source/acquisition_manifest.json` adds per-file SHA-256, byte count, source URL, and acquisition time. Original source rows and documentation remain unchanged. Here source files mean the unchanged deposited, already curated files, not unfiltered hardware acquisition logs. The API record and acquisition manifest are generated sidecars in addition to the 39 deposited files.

## Primary analysis set

- 23 original CSV files contain 54,531 rows.
- All 6,024 rows of `characterisation_toshiba_production_25samples.csv` occur, with multiplicities, in the full production sweep. It is preserved but excluded from primary pooling.
- The primary set has **48,507 rows from 22 CSV files**, covering five platforms and 1,331 grouped operating points.
- No numeric row is rejected by the finite/nonnegative-rate and QBER-in-[0,1] checks.
- Repeated rows within an original file are retained. Quantized repeated readings are not automatically treated as duplicated acquisitions.
- 533 primary rows have zero secure key rate. These are not an estimate of field outage frequency.
- 26 published QBER fractions exceed 0.1, with maximum 0.841. All are in the 12 dBm / 50 km coexistence file with zero SKR. They are retained, flagged, and never silently rescaled.
- Two source summary minima describe positive-rate minima although the corresponding CSVs include zeros. Our metrics use CSV values and document this convention.

The source methodology says zero-rate communication-timeout rows were removed in characterisation cleaning. Do not infer an outage process from retained zeros or from their absence.

## Units and absence of time traces

- `SecureKeyRate_bps`: bits per second.
- `QBER`: fraction, not percent. Plotted percentages multiply it by 100 explicitly.
- `VOA_dB`: added attenuation in dB.
- Fibre, injection, run, and perturbation-condition fields retain the source meaning.

No source CSV has a timestamp column. Rows are not converted into a continuous time series. Perturbation labels such as `1s_settling` are experimental conditions, not reconstructed controller-event timestamps. No packet arrivals, acknowledgement timing, inventory history, or controller failures were observed here.

## Derived observation files

`normalized/observations.csv` includes source file, source line, primary/auxiliary flag, campaign, platform, condition, run, fibre setting, noise, attenuation, QBER, and SKR. Observation IDs bind source-file SHA-256 and row number. `normalized/operating_points.csv` groups within source file and declared experimental conditions, avoiding an unsupported common-platform ranking.

## Measurement-to-model mapping

For measured rate r, assumed accumulation window W, and assumed unit length B:

`C = floor(r * W / B)` and `capacity_class = min(C, N)`.

Primary assumptions: 256-bit units, W in {0.001, 0.01, 0.1, 1} seconds, and N in {2, 4, 8} identical requests. The assumed rate is sustained over that hypothetical window, with no pre-existing inventory and no refill during the later batch. Window seconds are **not** equated with controller-event budgets.

- `normalized/capacity_crosswalk.csv.gz` contains **582,084** exact primary mappings.
- `results/capacity_counts.csv` additionally summarizes 128- and 512-bit unit sensitivity, totaling 1,746,252 transformations. These are repeated derivations, not additional measurements.
- Seventeen saturated (N, capacity) profiles are observed across primary mappings.
- `results/measurement_profile_associations.csv` joins profile outcomes to measured sampling counts. These are associations with unsafe reference-model profiles, not probabilities of device defects or network failure.

## Resource-model experiments

`src/measurement_pool.py` defines a bounded count-based key-pool model with waiting, prepared, delivered, aborted, free supply, controller-event counter, and a stale-commit flag. Requests are identical; the model is a symmetry quotient and has no per-session identity behavior.

The seventeen capacity profiles are crossed with atomic/split/reserved delivery, expiry budgets {3,6,12}, and deadline budgets {6,12}, giving **306 complete cases**. The budgets count model events and were selected for sensitivity analysis. They are not estimated from hardware timing.

Contracts check nonnegative/capacity-bounded supply, freshness at actual commit, request/reservation accounting, and eventual batch termination. There are 102 cases per delivery mode. Atomic and reserved modes have no failed contract; split mode has 61 failing cases. These are deliberate software-policy controls, not findings about faults in the source devices.

All graphs and witnesses are retained. A C++ graph checker agrees with Python on every resource graph. It consumes Python-exported graphs and labels, so it is an independent graph-algorithm check, not an independently derived hardware or controller model.

## Validation

The measurement audit checks 39 source files, all 23 source CSV row counts, every primary mapping, every resource graph checksum, and all 80 resource counterexample prefixes. Twenty targeted tests pass across the combined study. The original synthetic benchmark has its own separately retained graph and trace audits.

## Interpretation and exclusions

These records add genuine measured operating conditions to a bounded model study. They do not provide operational controller logs, real coordination-defect labels, physical-network outage statistics, cryptographic security proofs, or implementation-conformance evidence. The synthetic 522-case benchmark and its injected faults remain explicitly synthetic. The measured and generated layers are not merged into a fictitious field-trial dataset.
