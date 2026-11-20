"""Tests for the SARIF 2.1.0 exporter."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from envscope.checker import Issue, Report, check  # noqa: E402
from envscope.parser import parse_env  # noqa: E402
from envscope.sarif import dumps_sarif, to_sarif  # noqa: E402

EXAMPLE = """APP_NAME=envscope
DEBUG=false
PORT=8080
API_TOKEN=replace-me
"""

CLEAN = """APP_NAME=envscope
DEBUG=false
PORT=8080
API_TOKEN=super-secret-value-123
"""

BROKEN = """APP_NAME=envscope
DEBUG=maybe
PORT=70000
API_TOKEN=
EXTRA_FLAG=1
"""


class SarifDocumentTests(unittest.TestCase):
    def _report(self, env_text: str) -> Report:
        example = parse_env(EXAMPLE, "<example>")
        env = parse_env(env_text, "<env>")
        return check(example, env, {})

    def test_document_shape(self) -> None:
        payload = to_sarif(self._report(CLEAN), ".env", "0.1.0")
        self.assertEqual(payload["version"], "2.1.0")
        self.assertEqual(len(payload["runs"]), 1)
        run = payload["runs"][0]
        driver = run["tool"]["driver"]
        self.assertEqual(driver["name"], "envscope")
        self.assertEqual(driver["version"], "0.1.0")
        rule_ids = [rule["id"] for rule in driver["rules"]]
        self.assertIn("missing", rule_ids)
        self.assertIn("extra", rule_ids)
        self.assertEqual(run["results"], [])

    def test_levels_and_rule_indexes_are_consistent(self) -> None:
        payload = to_sarif(self._report(BROKEN), ".env", "0.1.0")
        run = payload["runs"][0]
        rules = run["tool"]["driver"]["rules"]
        self.assertTrue(run["results"])
        for result in run["results"]:
            self.assertEqual(rules[result["ruleIndex"]]["id"], result["ruleId"])
            self.assertIn(result["level"], {"error", "warning", "note"})

    def test_lines_and_uri_are_reported(self) -> None:
        payload = to_sarif(self._report(BROKEN), "config/.env", "0.1.0")
        results = payload["runs"][0]["results"]
        located = [r for r in results if r["locations"][0]["physicalLocation"].get("region")]
        self.assertTrue(located, "expected at least one finding with a line number")
        for result in located:
            physical = result["locations"][0]["physicalLocation"]
            self.assertEqual(physical["artifactLocation"]["uri"], "config/.env")
            self.assertGreaterEqual(physical["region"]["startLine"], 1)

    def test_empty_value_never_leaks_the_secret(self) -> None:
        text = dumps_sarif(self._report(CLEAN + "EXTRA_FLAG=1\n"), ".env", "0.1.0")
        self.assertNotIn("super-secret-value-123", text)
        # extra-key finding is a warning, so it must not carry a value either
        self.assertIn("EXTRA_FLAG", text)

    def test_unknown_code_falls_back_to_invalid_rule(self) -> None:
        report = Report(issues=[Issue(level="error", code="something-new",
                                      message="hypothetical finding")],
                        stats={})
        payload = to_sarif(report, ".env", "0.1.0")
        result = payload["runs"][0]["results"][0]
        self.assertEqual(result["ruleId"], "invalid")
        self.assertEqual(result["level"], "error")

    def test_missing_uri_defaults_to_dot_env(self) -> None:
        payload = to_sarif(self._report(CLEAN), None, "0.1.0")
        self.assertEqual(payload["runs"][0]["properties"]["envFile"], ".env")


class SarifCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / ".env.example").write_text(EXAMPLE, encoding="utf-8")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "envscope", *args],
            cwd=self.dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_cli_writes_sarif_file(self) -> None:
        (self.dir / ".env").write_text(BROKEN, encoding="utf-8")
        result = self.run_cli("check", "--sarif", "envscope.sarif")
        self.assertEqual(result.returncode, 1)
        out = self.dir / "envscope.sarif"
        self.assertTrue(out.exists())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], "2.1.0")
        self.assertGreater(len(payload["runs"][0]["results"]), 0)
        self.assertIn("wrote SARIF report", result.stdout)

    def test_cli_sarif_on_clean_run_is_empty_but_valid(self) -> None:
        (self.dir / ".env").write_text(CLEAN, encoding="utf-8")
        result = self.run_cli("check", "--sarif", "clean.sarif")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads((self.dir / "clean.sarif").read_text(encoding="utf-8"))
        self.assertEqual(payload["runs"][0]["results"], [])
        self.assertEqual(payload["runs"][0]["properties"]["envFile"], ".env")


if __name__ == "__main__":
    unittest.main()
