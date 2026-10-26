"""Verify the model ladder falls through on a forced 503.

Simulates an overloaded primary model by pointing GEMINI_MODEL at a bogus
model ID. The ladder must skip it and succeed on a real fallback model.
"""

import asyncio
import os
from datetime import date, timedelta

# Force the primary to fail BEFORE importing config-dependent modules.
os.environ["GEMINI_MODEL"] = "gemini-9.9-does-not-exist"

from app.ai_engine import generate_event_plan  # noqa: E402
from app.schemas import PlanRequest  # noqa: E402


async def main() -> int:
    req = PlanRequest(
        event_type="wedding",
        budget=25000,
        guest_count=150,
        event_date=date.today() + timedelta(days=180),
        vibe="boho rustic outdoor with string lights and neutral tones",
    )
    result = await generate_event_plan(req)

    print("fallback_used :", result.fallback_used)
    print("model_used    :", result.model_used)
    print("themes        :", len(result.theme_ideas))

    ok = (not result.fallback_used) and result.model_used != "gemini-9.9-does-not-exist"
    print("RESULT:", "PASS — ladder skipped the broken model" if ok else "FAIL — ladder did not recover")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))