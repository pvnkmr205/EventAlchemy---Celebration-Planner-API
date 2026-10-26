"""Pydantic schemas for the Celebration & Event Planner API.

These models serve TWO roles:
  1. FastAPI API contract (request validation + response serialization).
  2. Gemini structured-output schema — Phase 3 passes `PlanResponse` directly
     to the Gemini SDK as `response_schema=PlanResponse`. Gemini is forced to
     return JSON matching this exact shape, so the API never parses markdown.

Every field on `PlanResponse` MUST carry a `Field(description=...)`.
Gemini uses these descriptions as generation hints — they are not cosmetic.
"""

from datetime import date, datetime
from typing import List

from pydantic import BaseModel, Field, field_validator


# ═════════════════════════════════════════════════════════════════════════════
# REQUEST SCHEMA
# ═════════════════════════════════════════════════════════════════════════════

class PlanRequest(BaseModel):
    """Input payload for POST /api/v1/generate-plan."""

    event_type: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description=(
            "Type of event, e.g. 'wedding', 'birthday', 'anniversary', "
            "'corporate offsite', 'baby shower', 'sangeet', 'graduation party'."
        ),
        examples=["wedding", "corporate offsite", "sangeet"],
    )

    budget: float = Field(
        ...,
        gt=0,
        le=10_000_000,
        description="Total budget for the event, in the given `currency`. Must be positive.",
        examples=[25000.0],
    )

    guest_count: int = Field(
        ...,
        ge=1,
        le=100_000,
        description="Expected number of guests.",
        examples=[150],
    )

    event_date: date = Field(
        ...,
        description="Event date in ISO 8601 format (YYYY-MM-DD). Must not be in the past.",
        examples=["2027-06-15"],
    )

    vibe: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description=(
            "Free-form description of desired mood, theme, style, or constraints. "
            "E.g. 'boho rustic outdoor with string lights and neutral tones'."
        ),
        examples=["boho rustic outdoor with string lights and neutral tones"],
    )

    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO 4217 three-letter currency code, e.g. 'USD', 'INR', 'EUR'.",
        examples=["USD", "INR", "EUR"],
    )

    @field_validator("event_date")
    @classmethod
    def _reject_past_dates(cls, v: date) -> date:
        if v < date.today():
            raise ValueError(
                "event_date must be today or in the future. "
                f"Received {v.isoformat()}, today is {date.today().isoformat()}."
            )
        return v

    @field_validator("currency")
    @classmethod
    def _uppercase_currency(cls, v: str) -> str:
        return v.upper()

    model_config = {
        "extra": "forbid",  # reject unknown fields so casing bugs surface loudly
        "json_schema_extra": {
            "example": {
                "event_type": "wedding",
                "budget": 25000,
                "guest_count": 150,
                "event_date": "2027-06-15",
                "vibe": "boho rustic outdoor with string lights and neutral tones",
                "currency": "USD",
            }
        },
    }


# ═════════════════════════════════════════════════════════════════════════════
# RESPONSE SCHEMAS — these become Gemini's `response_schema` in Phase 3.
# ═════════════════════════════════════════════════════════════════════════════

class TimelinePhase(BaseModel):
    """A single phase of the planning timeline."""

    phase_name: str = Field(
        ...,
        description=(
            "Short, scannable name of the phase, e.g. 'Budget & Vision', "
            "'Venue & Vendors', 'Final Countdown', 'Day Of'."
        ),
    )
    timing: str = Field(
        ...,
        description=(
            "When to execute this phase relative to the event date. "
            "Use natural phrasing: '12 months before', '6 weeks before', 'Day of'."
        ),
    )
    tasks: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Concrete, actionable tasks for this phase, each a single imperative sentence.",
    )


class BudgetLineItem(BaseModel):
    """One category line in the budget breakdown."""

    category: str = Field(
        ...,
        description=(
            "Budget category, e.g. 'Venue', 'Catering', 'Photography', "
            "'Decor & Flowers', 'Entertainment', 'Attire', 'Invitations'."
        ),
    )
    amount: float = Field(
        ...,
        ge=0,
        description="Amount allocated to this category, in the plan's currency.",
    )
    percentage_of_budget: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percent of total budget this category represents (0–100).",
    )
    notes: str = Field(
        ...,
        description="One-sentence justification or cost-saving tip for this line item.",
    )


class BudgetAllocation(BaseModel):
    """Full itemized budget for the event."""

    currency: str = Field(
        ...,
        description="ISO 4217 currency code the amounts are denominated in.",
    )
    total_budget: float = Field(
        ...,
        ge=0.01,
        description="Total event budget. Must equal the user's input budget.",
    )
    contingency: float = Field(
        ...,
        ge=0,
        description="Amount reserved for unexpected costs (typically 10–15% of total).",
    )
    line_items: List[BudgetLineItem] = Field(
        ...,
        min_length=3,
        max_length=15,
        description="Itemized budget categories. Amounts should sum to total_budget - contingency.",
    )
    notes: str = Field(
        ...,
        description="2–3 sentences of high-level budget strategy or trade-off guidance.",
    )


class VendorChecklistItem(BaseModel):
    """A vendor category the planner must source, with what to ask them."""

    category: str = Field(
        ...,
        description=(
            "Vendor category, e.g. 'Venue', 'Caterer', 'Photographer', "
            "'DJ / Band', 'Florist', 'Officiant', 'Transportation'."
        ),
    )
    description: str = Field(
        ...,
        description="2–3 sentences on what to look for and what 'good' looks like in this category.",
    )
    questions_to_ask: List[str] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="Sharp, high-signal questions to ask this vendor category when vetting.",
    )
    estimated_cost_range: str = Field(
        ...,
        description=(
            "Expected cost range for this category given the budget, formatted as a string, "
            "e.g. '$3,000–$5,000', or '~15–20% of total budget'."
        ),
    )


class ThemeIdea(BaseModel):
    """A distinct personalized theme concept."""

    title: str = Field(
        ...,
        description="Evocative 3–6 word theme name, e.g. 'Sunset Boho Meadow', 'Midnight Garden Party'.",
    )
    description: str = Field(
        ...,
        description="2–4 sentences painting the theme — mood, atmosphere, signature moments.",
    )
    color_palette: List[str] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="Color names or hex codes that define the palette, e.g. 'Dusty Rose', '#C9A87C'.",
    )
    key_elements: List[str] = Field(
        ...,
        min_length=3,
        max_length=10,
        description="Concrete décor/sensory elements that bring the theme to life.",
    )


class PlanResponse(BaseModel):
    """The full event plan.

    This model IS Gemini's `response_schema` in Phase 3 — do not add fields
    that Gemini cannot reasonably generate (e.g. timestamps, IDs).
    """

    event_summary: str = Field(
        ...,
        description=(
            "2–3 sentence executive summary of the event vision that ties together "
            "the theme, budget strategy, and timeline highlights."
        ),
    )
    timeline: List[TimelinePhase] = Field(
        ...,
        min_length=3,
        max_length=8,
        description="Planning timeline, ordered from earliest phase to the day of the event.",
    )
    budget_allocation: BudgetAllocation = Field(
        ...,
        description="The itemized budget breakdown for the event.",
    )
    vendor_checklist: List[VendorChecklistItem] = Field(
        ...,
        min_length=3,
        max_length=10,
        description="Vendor categories to source, with vetting questions and cost estimates.",
    )
    theme_ideas: List[ThemeIdea] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Personalized theme concepts the planner can pitch to the client.",
    )


# ═════════════════════════════════════════════════════════════════════════════
# API ENVELOPE — inherits from PlanResponse so the frontend sees `timeline`,
# `budget_allocation`, etc. at the top level, PLUS server metadata.
# ═════════════════════════════════════════════════════════════════════════════

class GeneratePlanResponse(PlanResponse):
    """Full response returned by POST /api/v1/generate-plan."""

    model_used: str = Field(
        default="",
        description="Gemini model ID used to generate this plan.",
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the plan was generated.",
    )
    fallback_used: bool = Field(
        default=False,
        description="True if the AI call failed and a canned fallback plan was returned.",
    )