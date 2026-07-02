"""A/B comparison harness: legacy DGL endpoints vs the migrated backend.

Sends an identical fixture sequence to both services and diffs the responses.
Deterministic endpoints (usage limiter + listing CRUD) are compared closely,
ignoring volatile fields (timestamps, version, prompt_version). Generator
endpoints are compared structurally only (status + envelope keys), since LLM
output is non-deterministic and needs real credentials.

Usage:
    LEGACY_URL=http://localhost:8001 NEW_URL=http://localhost:8002 \
        uv run python -m scripts.compare_legacy
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

LEGACY_URL = os.environ.get("LEGACY_URL", "http://localhost:8001")
NEW_URL = os.environ.get("NEW_URL", "http://localhost:8002")
PREFIX = "/api/v1"

# Fields that legitimately differ run-to-run / between apps.
VOLATILE = {"created_date", "reset_date", "version", "prompt_version"}


def _norm(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _norm(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [_norm(v) for v in value]
    return value


def _call(base: str, method: str, path: str, **kw: Any) -> tuple[int, Any]:
    url = base + PREFIX + path
    try:
        r = httpx.request(method, url, timeout=30, **kw)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"_raw": r.text[:200]}
    except Exception as exc:
        return -1, {"_error": str(exc)}


_LISTING = {
    "user_id": "cmp_u1",
    "listing_id": "cmp_l1",
    "title": "Bán nhà Q1",
    "description": "Mô tả",
    "style": "simple",
    "platform": "web",
}

_GEN_BODY = {
    "goal": "bán",
    "property_type": "nhà",
    "area": 50.0,
    "price": 2_000_000_000.0,
    "price_unit": "VND",
    "city": "HCM",
    "district": "Quận 1",
    "ward": "Phường Bến Nghé",
    "street": "Lê Lợi",
    "contact_name": "Anh A",
    "contact_phone": "0900000000",
}
_PAIR_BODY = {
    **_GEN_BODY,
    "new_city": "TP.HCM",
    "new_ward": "Phường Bến Nghé",
    "new_display_address": "123 Đường Nguyễn Huệ, TP.HCM",
    "display_address": "123 Đường Lê Lợi, Quận 1, TP.HCM",
}

# (label, method, path, kwargs, mode) — mode: "close" | "structural"
FIXTURES = [
    ("usage_limit (create)", "GET", "/usage_limit/cmp_u1", {}, "close"),
    ("usage_limit (repeat)", "GET", "/usage_limit/cmp_u1", {}, "close"),
    ("reset", "GET", "/reset/cmp_u1", {}, "close"),
    ("reset_all", "GET", "/reset_all", {}, "close"),
    ("day_limit", "PUT", "/day_limit", {"json": {"limit": 7}}, "close"),
    ("listing/submit", "POST", "/listing/submit", {"json": _LISTING}, "close"),
    (
        "listing (get)",
        "GET",
        "/listing",
        {"params": {"user_id": "cmp_u1", "listing_id": "cmp_l1"}},
        "close",
    ),
    (
        "description (gen)",
        "POST",
        "/description",
        {
            "json": _GEN_BODY,
            "params": {"user_id": "cmp_g1", "listing_id": "cmp_gl1", "style": "simple"},
        },
        "structural",
    ),
    (
        "pair_address (gen)",
        "POST",
        "/description/pair_address",
        {
            "json": _PAIR_BODY,
            "params": {"user_id": "cmp_g2", "listing_id": "cmp_gl2", "style": "simple"},
        },
        "structural",
    ),
]


def _diff(label: str, mode: str, ls: int, lb: Any, ns: int, nb: Any) -> list[str]:
    issues = []
    if ls != ns:
        issues.append(f"status {ls} vs {ns}")
    if mode == "close":
        ln, nn = _norm(lb), _norm(nb)
        if ln != nn:
            issues.append(
                f"body(normalized) differs:\n    legacy={ln}\n    new   ={nn}"
            )
        # surface extra/missing top-level keys even if normalized-equal elsewhere
        lk, nk = set(_flatten(lb)), set(_flatten(nb))
        if lk - nk:
            issues.append(f"keys only in legacy: {sorted(lk - nk)}")
        if nk - lk:
            issues.append(f"keys only in new: {sorted(nk - lk)}")
    else:  # structural: same key shape (ignore values, which are non-deterministic)
        lk, nk = set(_flatten(lb)), set(_flatten(nb))
        if lk != nk:
            issues.append(
                f"data shape differs: only-legacy={sorted(lk - nk)} only-new={sorted(nk - lk)}"
            )
    return issues


def _flatten(value: Any, prefix: str = "", depth: int = 99) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict) and depth > 0:
        for k, v in value.items():
            keys.append(f"{prefix}{k}")
            keys += _flatten(v, f"{prefix}{k}.", depth - 1)
    elif isinstance(value, list) and value and depth > 0:
        keys += _flatten(value[0], f"{prefix}[].", depth - 1)
    return keys


def main() -> int:
    print(f"LEGACY={LEGACY_URL}  NEW={NEW_URL}\n")
    total_issues = 0
    for label, method, path, kw, mode in FIXTURES:
        ls, lb = _call(LEGACY_URL, method, path, **kw)
        ns, nb = _call(NEW_URL, method, path, **kw)
        issues = _diff(label, mode, ls, lb, ns, nb)
        mark = "OK " if not issues else "DIFF"
        print(f"[{mark}] {method} {PREFIX}{path}  ({mode})  legacy={ls} new={ns}")
        for issue in issues:
            print(f"       - {issue}")
        total_issues += len(issues)
    print(f"\n{'PARITY OK' if total_issues == 0 else f'{total_issues} difference(s)'}")
    return 1 if total_issues else 0


if __name__ == "__main__":
    sys.exit(main())
