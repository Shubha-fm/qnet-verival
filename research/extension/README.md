# Implementation and independent-baseline extension

This archive supplements the original VeriQKD-Net experiment archive pinned to Git commit 0dcc7877755e62a216fffb95e6bf7abedc151a2f. It does not change the original source measurements or synthetic results.

Restore the base archive first. Copy this archive's src/, tests/, implementation/, baseline/, tools/, figures/, and AI_ASSISTANCE.md into the extracted base package root, merging directories. Then run:

```bash
python3 -m unittest discover -s tests -v
python3 src/fetch_tlc.py
python3 src/audit_extension.py
```

Expected: 28 tests pass, 306 TLC logs verify, 2,040 SQL batches validate, 80 witness executions are replayed, and 3,060 random seed trials validate. To regenerate the new runs, execute run_tlc_baseline.py, run_pool_testing.py, run_implementation.py, and analyze_extension.py in that order. The complete independent baseline may take several minutes; each Java process uses a private temporary directory. The official TLC JAR is included with its original MIT license and a pinned checksum. Java is required. Plot generation needs Matplotlib and NumPy.

The baseline compares aggregate I1-I3 safety, not liveness or performance superiority. The SQLite controller is newly implemented research code, not an external deployed KMS. Clock values and barrier schedules are controlled test inputs. Model witness projection omits key identity; the identity-level tests demonstrate that duplicate allocation can occur without exceeding capacity.

Results: 306/306 TLC safety verdicts agree, and all 245 complete passing state counts agree. Additional random testing runs 306,000 executions. SQLite tests cover 2,040 batches and 11,760 requests; all 80 witness replays agree across 430 count projections. Atomic and reserved modes avoid the selected findings; split mode exposes duplicate identifiers, excessive delivery, and expiry violations under the chosen schedules.

The final paper and its LaTeX sources are distributed separately from this experiment extension. See implementation/summary.json, baseline/summary.json, baseline/random_summary.json, implementation/audit.json, and AI_ASSISTANCE.md for exact evidence and scope.
