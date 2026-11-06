# Task 3.1 — Council Checkpoint A

This is a structured simulated review, not independent human approval. Test and parity evidence remains authoritative.

## Persona reviews

### 1. Contrarian

The original serializer could validate a payload hash while missing contradictory emission/covariance/seed metadata. The Contrarian also challenged whether Student-t config/fitted dof equality would be a false invariant. The implementation now distinguishes initial from profiled-final dof and tests both a valid difference and a valid-hash metadata mismatch. Legacy compatibility was challenged rather than assumed; a v1 artifact is converted to the legacy schema in tests and checked for identical filtering.

### 2. First Principles Thinker

A hash proves byte integrity only. Semantic validation must independently establish array dimensions, probability normalization, finite values, model/spec/config agreement, convergence rules, and dof semantics. The review accepted the explicit two-stage design: canonical hash verification followed by complete semantic reconstruction and validation. Regularization is an operation count, not a latent measure of instability.

### 3. Expansionist

The Expansionist requested compatibility rather than a breaking schema-only fix, centralized version identity for future discovery, and detailed diagnostics in adapter/smoke output. The v1/v2 loader, `research/hmm/version.py`, deterministic counter derivation, and freeze manifest satisfy these without broadening model families or research scope.

### 4. Outsider

The Outsider asked whether a full covariance floor application was being mislabeled as numerical failure. The new evidence makes the distinction concrete: the Gaussian-full parity case has 14 floor applications and zero eigenvalue clips. Independent tests include both a well-conditioned matrix with zero clips and singular matrices with four clips. The Outsider also required the actual full-suite skip/warning to be documented.

### 5. Executor

The Executor checked commands, JUnit output, immutable source/data hashes, and sequencing. The gate is 94 focused, 72 Task 2, and 179 full-suite passes with one pre-existing skip/warning. Both parity scripts and canonical smoke passed. No Task 4 file existed when this gate was evaluated. The freeze manifest gives Task 4 a fixed engine boundary.

## WHERE THE COUNCIL AGREES

- Serialization must validate semantics independently of hashes on save and load.
- Initial Student-t dof and profiled final dof are not required to be equal.
- The historical regularization aggregate remains unchanged and is now fully explained.
- Original numerical parity and canonical smoke behavior are intact.
- Task 3.1 meets its acceptance gate and the engine can be frozen for Task 4.

## WHERE THE COUNCIL CLASHES

The Expansionist preferred accepting future engine versions flexibly; the Contrarian and Executor required explicit schema/engine pairs and optional exact-version assertions. The explicit approach won. The First Principles Thinker rejected deriving full v1 counters if the remainder was negative; compatibility therefore fails closed rather than guessing. The group agreed that requiring config/fitted dof equality would be simpler but wrong.

## BLIND SPOTS CAUGHT

- Valid hashes do not detect semantically contradictory artifacts.
- Gaussian dof metadata was previously accepted as harmless even when contradictory.
- Convergence flags could disagree with history/cap without hash corruption.
- Full-covariance floor additions were not equivalent to eigenvalue instability.
- A legacy schema bump without a numerical compatibility test would be insufficient.
- A new clone/environment must actually rerun baseline and final tests rather than rely on earlier reports.

## THE RECOMMENDATION

**PASS Task 3.1 and authorize Task 4 only against the frozen v1.1 engine.** Commit this hardening separately, preserve the parity/freeze artifacts, and make the Task 4 protocol reference the freeze-manifest hash. Do not modify engine equations to accommodate discovery.

## THE ONE THING TO DO FIRST

Commit and push Task 3.1 independently, verify remote/local identity and clean scope, then write the leakage-safe Task 4 protocol before executing any outer-fold experiment.
