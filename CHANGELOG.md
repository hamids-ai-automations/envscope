CHANGELOG

v0.1.1 (2026-11-20)
- Added SARIF 2.1.0 export: `envscope check --sarif PATH`.
  Findings map to one rule per issue code with error/warning levels and dotenv
  line numbers, so GitHub code scanning can annotate them inline.
- Added `src/envscope/sarif.py` plus 8 tests covering document shape, rule indexes,
  line/uri attribution and the guarantee that secret values never reach the log.
- CI now produces `envscope.sarif` and asserts it is valid JSON with a `runs` array.
- Docs: corrected the install URL (the repo lives at hamids-ai-automations/envscope),
  documented the SARIF workflow, updated the test count to 42.

v0.1.0 (2026-10-30)
- Added envscope check, drift detection, type validation, pattern/choices constraints,
  --strict/--json/--quiet/--no-color, envscope init, envscope version, unit/end-to-end
  tests (34 tests), GitHub Actions CI on Python 3.11/3.12/3.13.
