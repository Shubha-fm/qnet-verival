# VeriQKD-Net research and replication materials

This directory supplements the QNet-VeriVal web prototype with the manuscript's research evidence. The existing web application's API output is not the archived experimental evidence.

## Code-and-data distribution

Manuscript LaTeX, PDF, and manuscript ZIP files are excluded. Older embedded paper copies have also been removed from the replication archive. Code, datasets, graphs, logs, and experiment results are retained. Analysis scripts can still generate LaTeX tables locally.

## Reproduce the complete experiment package

From a clone of this repository:

```bash
python3 research/restore_extension.py
cd research/replication/VeriQKD_Net_Measurement_Driven
python3 -m unittest discover -s tests -v
python3 src/validate_package.py
python3 src/audit_measurements.py
python3 src/audit_extension.py
```

The restoration script verifies and restores the original three-part archive if needed, then verifies and merges the extension. Read `EXTENSION_README.md` in the restored directory. Java is needed for TLC. Regenerating figures needs Matplotlib and NumPy. Reusing bundled source measurements requires no network access.

Expected: **28 tests pass**, 522 original synthetic records and 513 complete graphs validate, 306 resource graphs and independent TLC results validate, 2,040 SQL batches validate, and all 80 witness executions are replayed across 430 matching projections.

## Evidence and provenance

- **Hardware data:** 54,531 original rows, with an exact 6,024-row auxiliary subset excluded from primary pooling, leaving 48,507 primary observations across five platforms. [Source data and original license](measurement/source/), [data card](measurement/DATA_CARD.md), and [source DOI](https://doi.org/10.5281/zenodo.21792844).
- **Original coordination benchmark:** 522 configurations, including 513 complete graphs and nine capped/unknown outcomes; 120,000 sampled traces.
- **Independent safety baseline:** a separately written TLA+ module, executed by TLC, agrees on all 306 aggregate safety verdicts and all 245 complete passing state counts. It does not reuse Python-exported graphs or labels.
- **Matched testing:** 306,000 additional executions, 3,060 seed trials, and 3,181,452 actions. The selected seeds miss one of 61 failing cases at the largest budget.
- **Executable implementation:** newly implemented SQLite lifecycle code, 2,040 controlled threaded batches, and 11,760 requests. Identifier reuse without excess capacity shows a limitation of the count abstraction.

The [replication archive](package/) is distributed in three parts. Its SHA-256 is `655c7dc71b59410acff273e093ad39175062c4384c5990068c93f3d89cb015d0`. `restore_package.py` verifies the concatenated bytes before extraction. Manuscript files have been removed; retained experiment files are unchanged except the package README and integrity manifest. The [implementation and baseline extension](extension/) is unchanged.

## Interpretation and licenses

Hardware measurements are real. Workloads, supply conversion, timing budgets, and fault schedules are assumed or controlled. The SQLite controller is research code, not an independently deployed QKD KMS. Matching selected count projections is not a complete refinement proof and does not establish key-identifier uniqueness in the count model.

TLC is compared on aggregate I1-I3 safety only. No liveness equivalence or checker speed advantage is claimed. Controlled database schedules are not a distribution of production failures.

The IrelandQCI researchers retain credit for the original hardware measurements under CC BY 4.0. Newly supplied experiment code is covered by its scoped MIT licenses. TLC retains its original license. The pre-existing web application is not relicensed by the research licenses. Generative-AI assistance in research scripting and manuscript development is disclosed in the [provenance note](extension/AI_ASSISTANCE.md).

