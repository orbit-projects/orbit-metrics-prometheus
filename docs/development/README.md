# Orbit Metrics Prometheus: development

This package declares support for `>=3.11,<3.15` in `pyproject.toml`. That declaration is distinct from evidence that hosted CI ran.

Use the checks for each language manifest present in this repository:

### Python package

```bash
python -m pip install -e '.[dev]' build
pytest
ruff check src tests
ruff format --check src tests
mypy
```

Optional SDKs and live-service tests are described by the package README. Do not run an opt-in live test against a shared or production service unless its own documentation explicitly supports that use.

## Contribution expectations

Add focused regression coverage for behavior changes. Update the README and relevant guide when a contract, configuration option, security property, lifecycle rule, or operational assumption changes. Report the exact versions and services exercised; local checks do not imply hosted CI or release validation.

## Latest local checkpoint (2026-10-10)

The current exporter and route tests passed on CPython **3.11.14, 3.12.14, 3.13.15, and 3.14.7**:
8 tests per interpreter. Ruff lint and formatting, strict mypy, and wheel/sdist builds also passed on
each interpreter. The tests use Orbit's local Core, Metrics, Auth, and Testing checkouts. No live
Prometheus scrape, hosted CI, publication, provenance, or deployment was exercised.
