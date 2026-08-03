# -----------------------------
# Version bumping
# -----------------------------
# release-test/release-prod targets (PyPI publish) are deferred until
# pulseforge has publish-pypi.yml/publish-testpypi.yml workflows like
# parseforge's -- these three are all bump2version needs.
bump-patch:
	bump2version patch

bump-minor:
	bump2version minor

bump-major:
	bump2version major

.PHONY: bump-patch bump-minor bump-major
