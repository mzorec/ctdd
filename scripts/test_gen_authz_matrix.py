#!/usr/bin/env python3
"""Tests for gen-authz-matrix.py — the executable spec of the matrix semantics.

Run:  python3 scripts/test_gen_authz_matrix.py   (or via pytest)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent / "gen-authz-matrix.py")

SPEC = """\
openapi: 3.0.3
info: {title: payments, version: "1"}
security:
  - bearer: []
components:
  securitySchemes:
    bearer: {type: http, scheme: bearer}
    oauth:
      type: oauth2
      flows:
        clientCredentials:
          tokenUrl: https://sso.example/token
          scopes:
            payments.capture: capture a payment
            payments.read: read payments
paths:
  /public/health:
    get:
      security: []
      responses: {"200": {description: ok}}
  /payments/{id}/capture:
    post:
      operationId: capturePayment
      security:
        - oauth: [payments.capture]
      responses: {"200": {description: ok}}
  /payments/{id}:
    get:
      security:
        - oauth: [payments.read]
        - bearer: []
      responses: {"200": {description: ok}}
  /admin/replay:
    post:
      x-roles: [ops.admin]
      responses: {"200": {description: ok}}
"""


def write(text, suffix=".yaml"):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    f.write(text); f.close()
    return f.name


def run(*args, stdin=None):
    return subprocess.run([sys.executable, SCRIPT, *args],
                          input=stdin, capture_output=True, text=True, timeout=20)


def matrix_of(path):
    r = run(path)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout)


def cell(m, path, method, identity):
    for row in m["rows"]:
        if (row["path"], row["method"], row["identity"]) == (path, method, identity):
            return row["expect"]
    raise AssertionError(f"no row for {method} {path} as {identity}")


class GenAuthzMatrixTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.spec = write(SPEC)
        cls.m = matrix_of(cls.spec)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.spec)

    def test_identity_axis_is_mechanical(self):
        self.assertEqual(self.m["identities"],
                         ["anonymous", "authenticated",
                          "ops.admin", "payments.capture", "payments.read"])

    def test_every_operation_gets_a_full_row_set(self):
        self.assertEqual(self.m["operations"], 4)
        self.assertEqual(len(self.m["rows"]), 4 * 5)

    def test_explicitly_public_allows_anonymous(self):
        self.assertEqual(cell(self.m, "/public/health", "GET", "anonymous"), "allow")

    def test_secured_op_anonymous_is_401(self):
        self.assertEqual(cell(self.m, "/payments/{id}/capture", "POST", "anonymous"),
                         "deny-401")

    def test_authenticated_without_scope_is_403(self):
        self.assertEqual(cell(self.m, "/payments/{id}/capture", "POST", "authenticated"),
                         "deny-403")

    def test_wrong_scope_is_403_right_scope_allows(self):
        self.assertEqual(cell(self.m, "/payments/{id}/capture", "POST", "payments.read"),
                         "deny-403")
        self.assertEqual(cell(self.m, "/payments/{id}/capture", "POST", "payments.capture"),
                         "allow")

    def test_or_alternative_scopeless_bearer_allows_any_authenticated(self):
        self.assertEqual(cell(self.m, "/payments/{id}", "GET", "authenticated"), "allow")
        self.assertEqual(cell(self.m, "/payments/{id}", "GET", "anonymous"), "deny-401")

    def test_x_roles_refines_global_security(self):
        # /admin/replay inherits global bearer AND requires x-role ops.admin
        self.assertEqual(cell(self.m, "/admin/replay", "POST", "authenticated"), "deny-403")
        self.assertEqual(cell(self.m, "/admin/replay", "POST", "ops.admin"), "allow")
        self.assertEqual(cell(self.m, "/admin/replay", "POST", "anonymous"), "deny-401")

    def test_output_is_deterministic(self):
        a, b = run(self.spec).stdout, run(self.spec).stdout
        self.assertEqual(a, b)

    def test_check_passes_when_current_and_fails_on_drift(self):
        out = write("", suffix=".json")
        try:
            r = run(self.spec, "-o", out)
            self.assertEqual(r.returncode, 0)
            self.assertEqual(run(self.spec, "--check", out).returncode, 0)
            # drift: retire an endpoint from the spec, keep the old matrix
            drifted = write(SPEC.replace("/admin/replay", "/admin/replay-v2"))
            try:
                r = run(drifted, "--check", out)
                self.assertEqual(r.returncode, 1)
                self.assertIn("DRIFT", r.stdout)
                self.assertIn("uncovered authz", r.stdout)
            finally:
                os.unlink(drifted)
        finally:
            os.unlink(out)

    def test_not_an_openapi_doc_is_usage_error(self):
        f = write("just: some yaml\n")
        try:
            self.assertEqual(run(f).returncode, 2)
        finally:
            os.unlink(f)

    def test_csharp_scaffold_prints_adapter(self):
        r = run("--csharp-scaffold")
        self.assertEqual(r.returncode, 0)
        self.assertIn("MemberData", r.stdout)
        self.assertIn("scaffold, not a generated file", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
