# v0.1.0 — Initial Scaffold & Release Pipeline

## 🏗️ Project Scaffold
Full package layout in place — `envelope`, `naming`, `forge`, `parsing`,
`health`, `ingestion`, `cli`. Every pipeline stage is currently a stub
(`NotImplementedError`): directory layout and module boundaries are
settled, nothing is wired end to end yet.

## 🤝 Delegates to ParseForge, Doesn't Reimplement It
`forge/adapter.py` is the only module that imports `parseforge` — template
forging (trial → integration → promotion) is called straight from
`parseforge.api`, with a PulseForge *category* passed in wherever
ParseForge expects a *cli-name*. The parts unique to log messages —
envelope splitting, category naming, and pulse (health) scoring — are
what's actually new here.

## 📚 Docs Site
Live versioned documentation via mkdocs (Material theme) + mike:
https://geeks-trident-llc.github.io/pulseforge/

## 🔧 Full Dev/Release Pipeline
- `Tests` workflow (pytest on push/PR to `main`/`develop`)
- Branch protection on `main`: required review + required status checks
- `Deploy Docs` workflow (lint/format/typecheck gate → mike deploy)
- `bump2version`, `Makefile` / `scripts/release.ps1`: bump-patch/minor/major,
  release-test, release-prod
- CI: Tests, Deploy Docs, Publish to TestPyPI — all wired and verified
  end-to-end. Publish to PyPI is wired but not yet exercised (no release
  has been promoted to production PyPI).

## 📦 Version
Initial release: `0.1.0`
