# Historical research archives

The current app does not use the original project implementation. To keep the
active tree navigable without discarding research, the originals were archived
before cleanup:

- `original-project-31902b7.zip` contains every tracked file from original
  commit `31902b7cdec9409f805784d9634d3bfd5f25c03f` except the separate Arena
  ZIP below. It includes notebooks, models, datasets, CSV results, old backend,
  frontend, configuration, and README with their original relative paths.
- `original-project-31902b7.sha256.json` records the SHA-256 of every file in
  that archive. The archive was checked against the original Git blobs before
  removing the duplicate files from the active tree. Original files also remain
  accessible through Git history at that commit.
- `arena-market-regime-platform.zip` is the unchanged later Arena archive,
  including its reports, experiments, research artifacts and bundled environment.
  It was previously at the repository root as `market-regime-platform.zip`.
  Its SHA-256 is `bdf7b9136f8fd9b52dc6eedd34fd916c74f8baaaccc8815b3bd170dfc948d4b1`,
  verified against the original Git blob.

To inspect the original project without overwriting the current app, extract it
into a separate, empty directory:

```bash
mkdir original-project-inspection
unzip historical/original-project-31902b7.zip -d original-project-inspection
```

The archived code is historical and should not be treated as the validated
current research platform. The new project's research engine and reproducible
experiment outputs remain under `research/` and are not part of this cleanup.
