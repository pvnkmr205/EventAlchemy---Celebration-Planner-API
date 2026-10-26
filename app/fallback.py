"""Deterministic fallback plan used when the Gemini call fails.

Guarantees the API always returns a schema-valid PlanResponse.
"""

from datetime import date

from app.schemas import (
    BudgetAllocation,
    BudgetLineItem,
    PlanRequest,
    PlanResponse,
    ThemeIdea,
    TimelinePhase,
    VendorChecklistItem,
)


def build_fallback_plan(request: PlanRequest) -> PlanResponse:
    """Build a complete, schema-valid PlanResponse from the request.

    Amounts are derived from the user's budget so the plan feels personalised,
    not obviously canned.
    """
    total = float(request.budget)
    contingency = round(total * 0.12, 2)
    spendable = total - contingency

    # Rough, widely-used event-spend weights.
    weights = {
        "Venue": 0.22,
        "Catering & Beverages": 0.30,
        "Photography & Video": 0.12,
        "Decor & Flowers": 0.10,
        "Entertainment": 0.08,
        "Attire & Beauty": 0.06,
        "Invitations & Stationery": 0.03,
        "Transportation & Logistics": 0.04,
        "Planning & Contingency Reserve": 0.05,
    }
    line_items = [
        BudgetLineItem(
            category=category,
            amount=round(spendable * weight, 2),
            percentage_of_budget=round((spendable * weight) / total * 100, 1),
            notes=f"Typical allocation for {category.lower()} at a {request.event_type} of this size.",
        )
        for category, weight in weights.items()
    ]

    return PlanResponse(
        event_summary=(
            f"A {request.vibe} {request.event_type} for {request.guest_count} guests "
            f"with a total budget of {request.currency} {total:,.0f}. "
            "The plan below prioritises venue and catering while reserving a 12% "
            "contingency for surprises."
        ),
        timeline=[
            TimelinePhase(
                phase_name="Vision & Budget Lock-In",
                timing="6–8 months before",
                tasks=[
                    "Confirm guest count and finalise the budget envelope.",
                    "Shortlist 3 venues that fit the vibe and capacity.",
                    "Book the venue and pay the deposit.",
                ],
            ),
            TimelinePhase(
                phase_name="Vendor Booking Sprint",
                timing="4–6 months before",
                tasks=[
                    "Book catering, photographer, and entertainment.",
                    "Send save-the-dates to the guest list.",
                    "Lock in the colour palette and decor direction.",
                ],
            ),
            TimelinePhase(
                phase_name="Design & Details",
                timing="2–3 months before",
                tasks=[
                    "Finalise menu tasting and dietary requirements.",
                    "Order invitations, attire, and floral mock-ups.",
                    "Build the day-of run sheet.",
                ],
            ),
            TimelinePhase(
                phase_name="Final Countdown",
                timing="2–4 weeks before",
                tasks=[
                    "Confirm all vendor arrival times and contacts.",
                    "Send final guest count to catering.",
                    "Prepare welcome bags and signage.",
                ],
            ),
            TimelinePhase(
                phase_name="Day Of",
                timing="Day of event",
                tasks=[
                    "Vendor load-in and setup (arrive 2 hours early).",
                    "Designated point-of-contact runs the timeline.",
                    "Enjoy the event — the plan is done.",
                ],
            ),
        ],
        budget_allocation=BudgetAllocation(
            currency=request.currency,
            total_budget=total,
            contingency=contingency,
            line_items=line_items,
            notes=(
                "Catering and venue together consume roughly half the budget — "
                "negotiate those two first. Keep the 12% contingency untouched "
                "until two weeks out."
            ),
        ),
        vendor_checklist=[
            VendorChecklistItem(
                category="Venue",
                description="The venue sets capacity, curfew, and what you must bring in yourself.",
                questions_to_ask=[
                    "What is the maximum capacity for a seated dinner?",
                    "What is the noise curfew and overtime fee?",
                    "What is included — tables, chairs, lighting, parking?",
                ],
                estimated_cost_range=f"{request.currency} {round(spendable * 0.18):,}–{request.currency} {round(spendable * 0.26):,}",
            ),
            VendorChecklistItem(
                category="Caterer",
                description="Food is the memory guests keep. Prioritise tasting and dietary handling.",
                questions_to_ask=[
                    "How many tastings are included?",
                    "How do you handle allergies and vegan guests?",
                    "What is the staff-to-guest ratio?",
                ],
                estimated_cost_range=f"{request.currency} {round(spendable * 0.25):,}–{request.currency} {round(spendable * 0.35):,}",
            ),
            VendorChecklistItem(
                category="Photographer",
                description="You are buying a documentary of the day, not just posed photos.",
                questions_to_ask=[
                    "Can I see a full gallery from a similar event?",
                    "How many shooters are on the day?",
                    "When do we receive the edited gallery?",
                ],
                estimated_cost_range=f"{request.currency} {round(spendable * 0.09):,}–{request.currency} {round(spendable * 0.15):,}",
            ),
            VendorChecklistItem(
                category="Entertainment",
                description="Music controls the energy. Book based on a live sample, not a playlist.",
                questions_to_ask=[
                    "Can I see a live performance or recent recording?",
                    "Do you take requests and MC the event?",
                    "What is the setup and soundcheck time?",
                ],
                estimated_cost_range=f"{request.currency} {round(spendable * 0.05):,}–{request.currency} {round(spendable * 0.10):,}",
            ),
        ],
        theme_ideas=[
            ThemeIdea(
                title=f"Refined {request.event_type.title()}",
                description=(
                    f"A polished take on the {request.vibe} brief. Neutral base tones, "
                    "warm lighting, and one bold accent colour carry the design."
                ),
                color_palette=["Ivory", "Warm Sand", "Terracotta", "Deep Olive"],
                key_elements=[
                    "Candlelit tables with low florals",
                    "Custom signage in a modern serif",
                    "Live acoustic set during arrival",
                    "Photo moment with a textured backdrop",
                ],
            ),
            ThemeIdea(
                title="Modern Celebration",
                description=(
                    "A clean, contemporary interpretation that still feels warm. "
                    "Think architectural florals, monochrome linens, and statement lighting."
                ),
                color_palette=["Charcoal", "Blush", "Champagne", "Emerald"],
                key_elements=[
                    "Suspended floral installation",
                    "Monochrome place settings",
                    "Neon sign with the event hashtag",
                    "Late-night snack station",
                ],
            ),
        ],
    )