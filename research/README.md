# VeriQKD-Net research replication materials

This directory supplements the QNet-VeriVal web prototype with the measurement-driven manuscript's reproducibility materials. The existing application remains a separate prototype. Its API results are not the archived experimental results.

## Final manuscript

Download [the final LaTeX ZIP](manuscript/VeriQKD_Net_Final_LaTeX.zip) or [the final PDF](manuscript/Final_Manuscript.pdf). The ZIP includes all LaTeX inputs, figures, compiled PDF, checksums, and verification notes. Select `main.tex` in Overleaf or compile it with pdfLaTeX at least twice. The optional `acm_main.tex` requires the official acmart class and was not compiled in the validation environment.

The experiment archive below remains unchanged at commit `0dcc7877755e62a216fffb95e6bf7abedc151a2f`. It retains the earlier manuscript for provenance. The separate manuscript downloads above contain the final revision with the verified GitHub availability statement and reproduction instructions.

## Contents and evidence

- `src/` and `tests/`: experimental models, checkers, processing, audits, and 20 tests.
- `measurement/source/`: all 39 unchanged files from IrelandQCI Zenodo record [21792844](https://doi.org/10.5281/zenodo.21792844), including the original CC BY 4.0 license, methodology, data dictionary, and attribution metadata.
- `measurement/DATA_CARD.md`: provenance, units, exclusions, and data limitations.
- `dataset/DATASET_CARD.md`: the separate synthetic benchmark.
- `package/`: the complete 34-page manuscript, editable LaTeX, source measurements, normalized data, capacity mappings, synthetic data, graphs, results, figures, tests, and audits, stored as three binary parts of one ZIP.

The source contains 54,531 measurement rows. Excluding the 6,024-row auxiliary subset leaves 48,507 primary observations across five platforms. The measurement arm contains 306 bounded resource-verification cases. The synthetic benchmark contains 522 configurations, of which 513 have complete graphs and nine are capped/unknown. All 20 tests passed in the recorded run.

Hardware measurements are real. Workloads, capacity conversion, expiry budgets, and injected faults are modeled. A model counterexample does not establish a defect or field failure rate in the measured devices.

## Reconstruct and validate the complete package

From the repository root, run:

```bash
python3 research/restore_package.py
cd research/replication/VeriQKD_Net_Measurement_Driven
python3 -m unittest discover -s tests -v
python3 src/validate_package.py
python3 src/audit_measurements.py
```

The restore script verifies SHA-256 before extraction and refuses to overwrite an existing extraction. Read the extracted `README.md` for full reproduction commands, environment, graph cross-checks, and the more expensive synthetic replay audit. Reusing the bundled measurements requires no network access. Plot regeneration needs Matplotlib and NumPy; compiling the graph checker requires a C++17 compiler.

## Attribution and licensing

The IrelandQCI source dataset is credited to its original researchers, not collected by this repository's authors. See its pinned Zenodo metadata and original `measurement/source/LICENSE.txt` (CC BY 4.0). The MIT license in this directory applies only to the newly supplied experimental code under `src/` and `tests/`. It does not relicense third-party data, manuscript text, or the pre-existing web application.
