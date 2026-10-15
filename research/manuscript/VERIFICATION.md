# Final verification, 15 October 2026

- Remote GitHub commit 0dcc7877755e62a216fffb95e6bf7abedc151a2f: all 69 text files matched the prepared upload exactly; three archive parts reconstructed the delivered ZIP byte for byte.
- All 39 deposited source files passed their pinned MD5 checksums; all 23 source CSV summary counts matched.
- All 582,084 primary capacity mappings were recomputed; all 306 resource graphs and 80 safety witnesses passed integrity and replay checks.
- All 522 synthetic outcome records and 513 complete graphs passed structural validation. Full replay checked 451 exhaustive witnesses and 120,000 sampled traces (970,037 actions), with zero false witnesses and zero random cutoffs.
- All 20 unit tests passed from the reconstructed archive.
- All 17 bibliography entries are cited; all 32 figure/table/model labels are referenced. All LaTeX inputs and figure assets are included.
- Final main.tex compiled in three pdfLaTeX passes, without undefined references or overfull boxes. The final PDF is 34 pages.
- The supplied PDF uses the portable article entry point. The optional acm_main.tex entry point requires an official acmart installation and was not compiled here.

Checks establish reproducibility and consistency within the stated models. They do not establish implementation conformance or the independence of graph labels from the Python model.
