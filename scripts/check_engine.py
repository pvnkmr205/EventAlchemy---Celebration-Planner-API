"""Live-test the Gemini engine. Run with: python scripts/check_engine.py"""

import asyncio
from datetime import date, timedelta

from app.schemas import PlanRequest
from app.ai_engine import generate_event_plan


async def main() -> int:
    req = PlanRequest(
        event_type="wedding",
        budget=25000,
        guest_count=150,
        event_date=date.today() + timedelta(days=180),
        vibe="boho rustic outdoor with string lights and neutral tones",
    )
    result = await generate_event_plan(req)

    print("fallback_used:", result.fallback_used)
    print("model_used   :", result.model_used)
    print("timeline     :", len(result.timeline), "phases")
    print("line items   :", len(result.budget_allocation.line_items))
    print("vendors      :", len(result.vendor_checklist))
    print("themes       :", len(result.theme_ideas))
    if result.theme_ideas:
        print("first theme  :", result.theme_ideas[0].title)

    return 0 if not result.fallback_used else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))