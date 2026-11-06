# Task 1 content-addressed source inventories

These inventories describe the two immutable source tips, **not** the integration workspace after Task 1 documentation was added. They were generated directly from exact Git objects without checking out or changing either source branch.

| Source | Exact commit | Tree | Tracked blobs | Inventory SHA-256 |
| --- | --- | --- | ---: | --- |
| f10 | `9bb7f92d5785462462971d0479595c1d4166868c` | `86d56f5564f51ca5e0cbd7554e6d9018baf168ff` | 107 | `263098e0f78ea4522a8ec0e9ffc6b408848e84fc96ef3b9c0ad9b6c043a2d3da` |
| 1c | `c46541e9ab8611330489a920c46cdb00342931d5` | `7150991d675831f9659138b664a2f7bd813833fe` | 278 | `0930c823258af150972d06379dc618fb3bcc4e10f81304baa47601bb29de09f1` |

## Format

Each `.jsonl` file contains one UTF-8 JSON object per tracked Git blob, sorted by raw repository-relative path bytes. Every record contains:

- `path`: repository-relative path at the exact source commit;
- `mode` and `object_type`: Git tree metadata;
- `git_blob_oid`: Git's content address (which includes Git's blob framing in its hash);
- `size_bytes`: raw blob length; and
- `sha256`: SHA-256 of the raw blob bytes alone.

The two hashes answer different questions and are intentionally both retained. Duplicate raw contents may have duplicate SHA-256 values; paths remain unique. No working-tree newline conversion, archive extraction, or normalization was used. Empty files and binary files are included.

`index.json` binds each source ref, full commit, tree, file count, total byte count, inventory filename, and inventory digest. `SHA256SUMS` authenticates the two inventory files within this documentation set; it is not a signature or a substitute for Git's immutable commit IDs.

## Verification performed

From this directory:

```bash
sha256sum -c SHA256SUMS
wc -l f10-9bb7f92-tracked-blobs.jsonl 1c-c46541e-tracked-blobs.jsonl
```

Observed on 2026-11-05:

```text
f10-9bb7f92-tracked-blobs.jsonl: OK
1c-c46541e-tracked-blobs.jsonl: OK
107 f10-9bb7f92-tracked-blobs.jsonl
278 1c-c46541e-tracked-blobs.jsonl
385 total
```

A separate standard-library verifier then reread every JSONL record, compared its path/mode/blob ID with `git ls-tree -rz --full-tree <exact-commit>`, read every blob with `git cat-file`, and recomputed its size and raw SHA-256. All 385 records and both inventory-file digests matched. This was an integrity check only; no tests, builds, model fits, or experiments were invoked by that verifier.

## Scope limitation

The inventories cover tracked blobs at the two source commits. They do not claim that ignored files, a local untracked dataset, external vendor data, GitHub releases, or files referenced only by historical documentation exist. In particular, discrepancies between 1c's older `MANIFEST.sha256` and its newer tracked tree are recorded in `../dataset_artifact_verification.json`; they were not silently repaired.
