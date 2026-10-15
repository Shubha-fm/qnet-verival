# Verification of strengthened manuscript and artifact

- 39-page ACM review manuscript, compiled with the official acmart class and its Libertine, Inconsolata, and newtx math fonts. Public-link variant also compiled.
- 30 cited references; 35 referenced figure/table/model labels; 12 figures and 23 tables. All figures have accessibility descriptions.
- 306/306 separately encoded TLC aggregate-safety verdicts agree. All 245 complete passing state counts agree. Liveness is deliberately outside the TLC comparison.
- New matched testing: 306,000 executions, 3,181,452 actions, 3,060 seed trials; no false positives.
- SQLite: 2,040 batches and 11,760 requests. All 80 witness replays agree across 430 projected snapshots. Key-identity reuse is separately observed and is not guaranteed by the count projection.
- All 28 unit tests pass. All 39 original deposited file checksums, 582,084 capacity mappings, 306 resource graphs, and stored resource witnesses were previously audited and retained unchanged.
- Original synthetic evidence remains 522 cases, 513 complete graphs, 451 exhaustive witnesses, and 120,000 earlier sampled traces. Original archive is preserved; this revision does not relabel those traces as new runs.

No production-controller assurance, full refinement proof, independent-team replication, or tool speed advantage is claimed. Venue-specific TOSEM guidelines were inaccessible beyond search results, so no journal-specific anonymity or page-limit compliance claim is made.
