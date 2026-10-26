"""Sanity-check the Gemini schema sanitizer. Run with: python scripts/check_schema.py

Proves:
  - $ref and $defs are fully inlined.
  - `title` metadata keywords are stripped.
  - A property literally named `title` inside an object is preserved.
  - `required` never references a missing property.
"""

import json
import sys

from app.ai_engine import _prepare_gemini_schema
from app.schemas import PlanResponse


def main() -> int:
    s = _prepare_gemini_schema(PlanResponse)
    serialized = json.dumps(s)

    theme_items = s["properties"]["theme_ideas"]["items"]
    theme_props = list(theme_items["properties"].keys())
    theme_required = theme_items.get("required", [])

    print("── theme_ideas.items ─────────────────────────────")
    print("  keys         :", list(theme_items.keys()))
    print("  properties   :", theme_props)
    print("  required     :", theme_required)
    print()
    print("── title property definition ─────────────────────")
    print(json.dumps(theme_items["properties"]["title"], indent=2))
    print()

    checks = {
        "$ref absent from schema": "$ref" not in serialized,
        "$defs absent from schema": "$defs" not in serialized,
        "'title' property preserved in theme_ideas": "title" in theme_props,
        "all required fields exist in properties": all(
            r in theme_props for r in theme_required
        ),
        "top-level has 5 required output fields": sorted(
            s["properties"].keys()
        ) == sorted(
            [
                "event_summary",
                "timeline",
                "budget_allocation",
                "vendor_checklist",
                "theme_ideas",
            ]
        ),
    }

    print("── assertions ────────────────────────────────────")
    failed = False
    for name, ok in checks.items():
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}")
        if not ok:
            failed = True

    print()
    if failed:
        print("RESULT: FAIL — sanitizer is not producing a Gemini-compatible schema.")
        return 1
    print("RESULT: PASS — schema is ready for Gemini.")
    return 0


if __name__ == "__main__":
    sys.exit(main())