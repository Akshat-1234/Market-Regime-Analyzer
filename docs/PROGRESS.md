# Progress record

## Phase 0 — audit
Completed: source and historical experiment inventory, dataset hash comparison, risks, unresolved provenance. See RESEARCH_DECISIONS.md. Archive remains intact.

## Phase 1 — reproduction
Executed the archived `run.py` from the extracted ZIP on the supplied CSV with `--start 2012-01-01 --execution-delay 1 --bootstrap-samples 1000`. Produced `research/experiments/baseline_20261104`; configuration, fit metadata, inputs and source snapshots, daily outcomes and signals are retained. This new directory is separate from the original archive. All headline metrics reproduce at displayed precision; CSV signal bytes differ (`92b569...` vs archived `e3e17a...`); observed metric differences were floating point at ~1e-14. Do not claim byte-for-byte reproduction. The version manifest accompanies the run. The previous full main attribution run is incomplete in the archive, so this reproduction is of the original delayed baseline, not that missing main run.

Source copied without modification to `research/legacy` to facilitate independent reproduction. This is a historical four-model 2/3-state ensemble, not proof that it is the optimal specification. Future research and product surface must clearly name the run and keep retrospective vs prospective distinct.
