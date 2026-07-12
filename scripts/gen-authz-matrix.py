#!/usr/bin/env python3
"""gen-authz-matrix.py — derive the authorization matrix from an OpenAPI contract.

Usage:
    python3 scripts/gen-authz-matrix.py openapi.yaml                  # matrix JSON to stdout
    python3 scripts/gen-authz-matrix.py openapi.yaml -o authz-matrix.json
    python3 scripts/gen-authz-matrix.py openapi.yaml --check authz-matrix.json
    python3 scripts/gen-authz-matrix.py --csharp-scaffold             # xUnit adapter, print once

What it does: for every operation in the contract and every derivable
identity, it emits the expected outcome a caller observes — behavior-level
by construction:

    allow      the identity may call the operation (2xx family expected)
    deny-401   unauthenticated caller on a secured operation
    deny-403   authenticated caller lacking the required scope/role

Identity axis (mechanical, documented, no judgment):
    anonymous          — no credentials
    authenticated      — valid credentials, no scopes/roles
    <one per scope>    — every scope found in security requirements
    <one per role>     — every value of an `x-roles` operation extension

Semantics honored: operation-level `security` overrides global; `security: []`
means explicitly public; a list of requirement objects is an OR (any object
satisfies); multiple schemes inside one object are an AND; oauth2/openIdConnect
scopes must all be held; scopeless schemes (bearer, apiKey) need only
authentication. `x-roles: [a, b]` on an operation requires any listed role in
addition to the declared security (refining AND).

Honest scope: the matrix covers the authorization surface THE CONTRACT
DECLARES. Object-level authorization ("only the owning merchant may capture
THIS payment") is invisible to any schema and needs hand-written behavior
tests — the matrix is the floor, not the ceiling. A new endpoint without a
matrix row is uncovered authz; the --check mode makes that a CI failure.

Output is deterministic (sorted, no timestamps), so the JSON diffs cleanly:
a new endpoint appears in review as new rows.

Exit 0 = generated / check passed.  Exit 1 = --check found drift.
Exit 2 = usage or parse error.
"""

import json
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

IDENTITY_ANON = "anonymous"
IDENTITY_AUTH = "authenticated"

CSHARP_SCAFFOLD = '''\
// AuthzMatrixTests.cs — copy ONCE into your test project and adapt the TODOs.
// This is a scaffold, not a generated file: the generated artifact is
// authz-matrix.json (regenerate + --check it in CI); this adapter only reads it.
using System.Text.Json;
public class AuthzMatrixTests
{
    public static IEnumerable<object[]> Cases() =>
        JsonDocument.Parse(File.ReadAllText("authz-matrix.json"))
            .RootElement.GetProperty("rows").EnumerateArray()
            .Select(r => new object[] {
                r.GetProperty("method").GetString()!,
                r.GetProperty("path").GetString()!,
                r.GetProperty("identity").GetString()!,
                r.GetProperty("expect").GetString()! });

    [Theory]
    [MemberData(nameof(Cases))]
    public async Task Authorization_matrix_holds(string method, string path,
                                                 string identity, string expect)
    {
        // TODO: build a client authenticated as `identity`
        //       (anonymous / token without scopes / token carrying the scope or role),
        //       substitute sample values for path parameters, send the request.
        var status = await SendAsAsync(method, path, identity);
        switch (expect)
        {
            case "allow":    Assert.NotEqual(401, status); Assert.NotEqual(403, status); break;
            case "deny-401": Assert.Equal(401, status); break;
            case "deny-403": Assert.Equal(403, status); break;
        }
    }
}'''


def _fail(msg, code=2):
    print(f"gen-authz-matrix: {msg}")
    return code


def load_spec(path):
    text = open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        return json.loads(text)
    if yaml is None:
        raise RuntimeError("PyYAML not available and input is not JSON")
    return yaml.safe_load(text)


def scheme_scopes(spec):
    """scheme name -> set of scopes it defines (oauth2/openIdConnect), else empty."""
    out = {}
    comps = (spec.get("components") or {}).get("securitySchemes") or {}
    for name, sch in comps.items():
        scopes = set()
        for flow in ((sch or {}).get("flows") or {}).values():
            scopes |= set((flow.get("scopes") or {}).keys())
        out[name] = scopes
    return out


HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


def operations(spec):
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        if "$ref" in item:
            print(f"gen-authz-matrix: WARNING — $ref path item skipped: {path}",
                  file=sys.stderr)
            continue
        for method in HTTP_METHODS:
            op = item.get(method)
            if isinstance(op, dict):
                yield path, method.upper(), op


def collect_identities(spec):
    """anonymous + authenticated + one identity per scope and per x-role."""
    names = set()
    def scopes_of(seclist):
        for req in seclist or []:
            for _, scopes in (req or {}).items():
                names.update(scopes or [])
    scopes_of(spec.get("security"))
    for _, _, op in operations(spec):
        scopes_of(op.get("security"))
        names.update(op.get("x-roles") or [])
    return [IDENTITY_ANON, IDENTITY_AUTH] + sorted(names)


def satisfies(identity_scopes, requirement, known_schemes):
    """One requirement object: AND across its schemes. identity_scopes=None => anonymous."""
    if identity_scopes is None:
        return False
    for scheme, scopes in (requirement or {}).items():
        if scheme not in known_schemes:
            print(f"gen-authz-matrix: WARNING — unknown security scheme "
                  f"'{scheme}' treated as authenticate-only", file=sys.stderr)
        needed = set(scopes or [])
        if needed and not needed <= identity_scopes:
            return False
    return True


def expected(identity, op_security, x_roles, known_schemes):
    scopes = None if identity == IDENTITY_ANON else \
        (set() if identity == IDENTITY_AUTH else {identity})

    if op_security is not None and len(op_security) == 0:
        sec_ok, why = True, "explicitly public (security: [])"
    elif not op_security:
        sec_ok, why = True, "no security declared — public by contract"
    else:
        sec_ok = any(satisfies(scopes, req, known_schemes) for req in op_security)
        why = "satisfies a security requirement" if sec_ok else \
              "requires " + " OR ".join(
                  "+".join(f"{k}[{','.join(v) or 'auth'}]" for k, v in (r or {}).items())
                  for r in op_security)

    if sec_ok and x_roles:
        if scopes is None or not (scopes & set(x_roles)):
            sec_ok, why = False, f"x-roles requires any of {sorted(x_roles)}"
        else:
            why += f"; holds x-role"

    if sec_ok:
        return "allow", why
    if identity == IDENTITY_ANON:
        return "deny-401", why
    return "deny-403", why


def build_matrix(spec):
    identities = collect_identities(spec)
    known = scheme_scopes(spec)
    global_sec = spec.get("security")
    rows = []
    ops = 0
    for path, method, op in operations(spec):
        ops += 1
        op_sec = op.get("security", global_sec)
        for identity in identities:
            expect, why = expected(identity, op_sec, op.get("x-roles"), known)
            rows.append({"method": method, "path": path,
                         "operationId": op.get("operationId"),
                         "identity": identity, "expect": expect, "why": why})
    rows.sort(key=lambda r: (r["path"], r["method"], r["identity"]))
    return {"identities": identities, "operations": ops, "rows": rows}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if args[0] == "--csharp-scaffold":
        print(CSHARP_SCAFFOLD)
        return 0

    spec_path, out_path, check_path = args[0], None, None
    rest = args[1:]
    while rest:
        flag = rest.pop(0)
        if flag == "-o" and rest:
            out_path = rest.pop(0)
        elif flag == "--check" and rest:
            check_path = rest.pop(0)
        else:
            return _fail(f"unknown or incomplete argument: {flag}")

    try:
        spec = load_spec(spec_path)
    except Exception as exc:
        return _fail(f"cannot parse {spec_path}: {exc}")
    if not isinstance(spec, dict) or "paths" not in spec:
        return _fail(f"{spec_path} does not look like an OpenAPI document (no paths)")

    matrix = build_matrix(spec)
    rendered = json.dumps(matrix, indent=2, ensure_ascii=False, sort_keys=True)

    if check_path:
        try:
            existing = json.dumps(json.load(open(check_path, encoding="utf-8")),
                                  indent=2, ensure_ascii=False, sort_keys=True)
        except Exception as exc:
            return _fail(f"cannot read --check file {check_path}: {exc}")
        if existing == rendered:
            print(f"gen-authz-matrix: {check_path} is current "
                  f"({matrix['operations']} operations x "
                  f"{len(matrix['identities'])} identities).")
            return 0
        key = lambda m: {(r["path"], r["method"], r["identity"]): r["expect"]
                         for r in m["rows"]}
        old = key(json.loads(existing)); new = key(json.loads(rendered))
        added = len(new.keys() - old.keys()); removed = len(old.keys() - new.keys())
        changed = sum(1 for k in new.keys() & old.keys() if new[k] != old[k])
        print(f"gen-authz-matrix: DRIFT — {check_path} is stale against {spec_path}: "
              f"{added} row(s) added, {removed} removed, {changed} changed. "
              f"A new endpoint without a matrix row is uncovered authz; regenerate "
              f"and review the diff as a spec change.")
        return 1

    if out_path:
        open(out_path, "w", encoding="utf-8").write(rendered + "\n")
        print(f"gen-authz-matrix: wrote {out_path} "
              f"({matrix['operations']} operations x "
              f"{len(matrix['identities'])} identities = {len(matrix['rows'])} rows).")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
