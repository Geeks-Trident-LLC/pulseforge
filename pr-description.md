## Summary
This establishes the initial PulseForge project scaffold and full
development/release tooling, delegating template forging to ParseForge
rather than reimplementing it, culminating in v0.1.0.

## What's Included

### Project Scaffold
- Package layout: `envelope`, `naming`, `forge`, `parsing`, `health`,
  `ingestion`, `cli` — every pipeline stage a stub (`NotImplementedError`)
- `forge/adapter.py` — the only module that imports `parseforge`; delegates
  trial → integration → promotion straight to `parseforge.api`, treating a
  PulseForge category the way ParseForge treats a cli-name
- `pulseforge` CLI (`run`, `pulse`, both stubs)

### Dev Tooling
- ruff + black + mypy configured and clean across the codebase
  (`mypy.ini`: `ignore_missing_imports`, matching ParseForge's own)
- `bump2version` (`.bumpversion.cfg`)

### Documentation
- `docs/index.md` + mkdocs (Material theme); changelog page via
  `pymdownx.snippets`
- Versioned docs deployment via `mike`, live at
  https://geeks-trident-llc.github.io/pulseforge/

### CI/CD
- `Tests` workflow (pytest on push/PR to `main`/`develop`)
- Branch protection on `main` (1 required review, required status checks,
  no force-push/deletion)
- `Deploy Docs` workflow (lint/format/typecheck gate → mike deploy)
- `publish-testpypi.yml` / `publish-pypi.yml` (build + publish, gated on
  full suite)
- `Makefile`, `scripts/release.ps1` (bump-patch/minor/major, release-test,
  release-prod)

## Release Artifacts
- CHANGELOG updated for v0.1.0
- Release notes generated
- Version: `0.1.0` (initial release)

## Testing
- Smoke test suite passing (3 tests) — every pipeline stage is a stub, so
  these confirm imports/wiring, not real behavior
- ruff / black / mypy all clean
- TestPyPI release validated (`v0.1.0-test` →
  https://test.pypi.org/project/pulseforge/0.1.0/)
