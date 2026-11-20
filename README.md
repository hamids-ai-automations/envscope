envscope: zero-dependency CLI that audits .env files against .env.example and a JSON schema, never printing secret values.

## Features
- Drift detection (missing, extra, empty, duplicate keys)
- Type validation: string, int, float, bool, port, url, email, pattern, choices
- Duplicate detection
- Secret-aware (values flagged secret are never printed)
- CI-friendly (--json, --sarif, stable exit codes)
- SARIF 2.1.0 export for GitHub code scanning
- Zero dependencies (Python 3.9+)
- Fast (parses thousands of keys in milliseconds)

## Requirements
- Python 3.11 or newer
- macOS, Linux, or Windows

## Install
```bash
git clone https://github.com/hamids-ai-automations/envscope.git
cd envscope
python -m pip install -e .
```

## Usage
```bash
envscope check [--env .env --example .env.example --schema envscope.json --strict --json --sarif PATH --quiet --no-color]
envscope init --example .env.example --out envscope.json
envscope version
```

## Schema format
envscope.json: `{"variables": {"APP_ENV":{"type":"string","choices":["development","staging","production"]},...}}`
Flat `{"PORT":"port"}` also accepted.

## CI example
```yaml
- name: Validate environment contract
  run: |
    python -m pip install -e .
    envscope check --strict --json > envscope-report.json
  env:
    PYTHONPATH: src
```

## SARIF / code scanning
`envscope check --sarif envscope.sarif` writes a SARIF 2.1.0 log next to the normal
output. Findings map to one rule per issue code (`parse`, `duplicate`, `missing`,
`empty`, `invalid`, `extra`) with error/warning levels, so GitHub code scanning can
group and annotate them inline on the offending dotenv line.

The log only contains key names, line numbers and envscope's own messages. Secret
values are never written to it, which is what makes it safe to upload as a build
artifact.

```yaml
- name: Validate environment contract
  run: |
    python -m pip install -e .
    envscope check --strict --sarif envscope.sarif
  env:
    PYTHONPATH: src
  continue-on-error: true

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: envscope.sarif
    category: envscope
```

## Tests
42 tests, no dependencies. CI runs on Python 3.11, 3.12, 3.13.

## License
MIT
