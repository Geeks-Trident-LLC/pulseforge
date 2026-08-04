## v0.1.0 — 2026-08-04

### Added
- Initial project scaffold per SPEC.md: `envelope`, `naming`, `forge`, `parsing`,
  `health`, `ingestion`, `cli` packages, packaged as `pulseforge`. Every pipeline
  stage is currently a stub (`NotImplementedError`) — directory layout and module
  boundaries are in place, nothing is wired end to end yet
- `forge/adapter.py` — the only module that imports `parseforge`; delegates
  template forging (trial → integration → promotion) straight to
  `parseforge.api` instead of reimplementing it, treating a PulseForge category
  the way ParseForge treats a cli-name
- `pulseforge` CLI (`run`, `pulse` subcommands, both stubs)
- `Tests` workflow (GitHub Actions) running pytest on push/PR to `main` and
  `develop`
- Branch protection on `main`: 1 required approving review, required status
  checks (`Test (Python 3.9)`, `Test (Python 3.12)`), no force-push/deletion
- `bump2version` setup (`.bumpversion.cfg`) tracking version across
  `pulseforge/__init__.py` and `pyproject.toml`
- `Makefile` and `scripts/release.ps1`: `bump-patch`/`bump-minor`/`bump-major`,
  `release-test` (tags `v$(VERSION)-test`, triggers TestPyPI), `release-prod`
  (tags `v$(VERSION)`, creates a GitHub Release, requires `main`)
- `docs/index.md` and mkdocs (Material theme) with `mike`-based versioned docs
  deployment (`Deploy Docs` workflow, gated on lint/format/typecheck), published
  to GitHub Pages at https://geeks-trident-llc.github.io/pulseforge/
- `publish-testpypi.yml` / `publish-pypi.yml` workflows — build + publish gated
  on the full test/lint/format/typecheck suite. Not yet exercised end-to-end:
  the `pypi-release`/`testpypi-release` GitHub Environments and
  `TEST_PYPI_API_TOKEN` secret they reference still need to be configured
- `mypy.ini` (`ignore_missing_imports = True`, matching ParseForge's own) —
  without it, the `typecheck` job fails on a clean CI runner that hasn't
  separately installed `click`/`PyYAML`
