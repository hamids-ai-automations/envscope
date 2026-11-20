"""SARIF 2.1.0 export so envscope findings can be uploaded to code scanning.

The exporter only ever emits key names, line numbers and envscope's own
messages. Values from the checked ``.env`` file never reach the report, so the
SARIF artifact is safe to upload to GitHub code scanning, a CI artifact store,
or any other third-party consumer.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from .checker import Issue, Report

SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
SARIF_VERSION = "2.1.0"
TOOL_URI = "https://github.com/hamids-ai-automations/envscope"

_LEVELS = {"error": "error", "warning": "warning", "info": "note"}

_RULES: List[Dict[str, object]] = [
    {
        "id": "parse",
        "name": "DotenvParseError",
        "shortDescription": {"text": "A dotenv line could not be parsed."},
        "help": {"text": "Fix the reported line so it is a valid KEY=VALUE assignment."},
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "duplicate",
        "name": "DuplicateKey",
        "shortDescription": {"text": "A key is defined more than once in a dotenv file."},
        "help": {"text": "Keep a single definition per key; later duplicates silently win at runtime."},
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "missing",
        "name": "MissingKey",
        "shortDescription": {"text": "A key required by .env.example or the schema is absent."},
        "help": {"text": "Add the key to the dotenv file or mark it as not required."},
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "empty",
        "name": "EmptyValue",
        "shortDescription": {"text": "A key is present but has an empty value."},
        "help": {"text": "Provide a value, or drop the key if it is optional."},
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "invalid",
        "name": "InvalidValue",
        "shortDescription": {"text": "A value does not satisfy the schema type or constraints."},
        "help": {"text": "Adjust the value to match the type, pattern or allowed choices."},
        "defaultConfiguration": {"level": "error"},
    },
    {
        "id": "extra",
        "name": "UnexpectedKey",
        "shortDescription": {"text": "A key is set but is not documented in .env.example or the schema."},
        "help": {"text": "Document the key in .env.example/schema, or remove it."},
        "defaultConfiguration": {"level": "warning"},
    },
]

_RULE_INDEX: Dict[str, int] = {str(rule["id"]): index for index, rule in enumerate(_RULES)}


def _artifact_uri(env_path: Optional[str]) -> str:
    """Return a repo-relative POSIX path, never a machine-specific absolute one."""
    if not env_path:
        return ".env"
    try:
        return Path(env_path).as_posix()
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return ".env"


def _result(issue: Issue, uri: str) -> Dict[str, object]:
    rule_id = issue.code if issue.code in _RULE_INDEX else "invalid"
    physical: Dict[str, object] = {"artifactLocation": {"uri": uri}}
    if issue.line:
        physical["region"] = {"startLine": int(issue.line)}
    return {
        "ruleId": rule_id,
        "ruleIndex": _RULE_INDEX[rule_id],
        "level": _LEVELS.get(issue.level, "note"),
        "message": {"text": issue.message},
        "locations": [{"physicalLocation": physical}],
        "properties": {"key": issue.key} if issue.key else {},
    }


def to_sarif(report: Report, env_path: Optional[str] = None,
             version: str = "0.0.0") -> Dict[str, object]:
    """Build a SARIF 2.1.0 document for *report*."""
    uri = _artifact_uri(env_path)
    results = [_result(issue, uri) for issue in report.issues]
    return {
        "$schema": SCHEMA_URI,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "envscope",
                        "informationUri": TOOL_URI,
                        "version": version,
                        "rules": _RULES,
                    }
                },
                "columnKind": "utf16CodeUnits",
                "results": results,
                "properties": {
                    "envFile": uri,
                    "summary": dict(report.stats),
                },
            }
        ],
    }


def dumps_sarif(report: Report, env_path: Optional[str] = None,
                version: str = "0.0.0", indent: int = 2) -> str:
    """Serialise the SARIF document to a JSON string."""
    return json.dumps(to_sarif(report, env_path, version), indent=indent,
                      ensure_ascii=False)


def write_sarif(path: Path, report: Report, env_path: Optional[str] = None,
                version: str = "0.0.0") -> Path:
    """Write the SARIF document to *path* and return the path."""
    path.write_text(dumps_sarif(report, env_path, version) + "\n", encoding="utf-8")
    return path
