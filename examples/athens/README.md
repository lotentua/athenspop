# Athens Example

This folder contains a dataset-specific reproduction example built on top of the generic `athenspop` library.

The example keeps source verification, wide-to-long conversion, travel-time resources, method-specific imputation, method-specific sequence costs, artifact writing, and example tests outside `src/athenspop`.

Run the repository-local smoke workflow without external source files:

```powershell
uv run python -m examples.athens.smoke
```

Run the full artifact workflow when the required source files and resources are present:

```powershell
uv run python -m examples.athens.reproduce
```

Expected source files at the repository root are `CSuM2026.pdf` and `CSuM2026.zip`. The source hashes and required archive members are documented in `examples/athens/docs/athens_method_contract.md`. Generated artifacts are written under `examples/athens/output`, which is ignored by Git.
