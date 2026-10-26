"""Gemini-powered event plan generation with structured output + fallback.

This is the only module that talks to Gemini. The router (Phase 4) calls
`generate_event_plan()` and receives a `GeneratePlanResponse` every time,
even if the AI call fails.

Resilience layers, in order:
  1. FORCE_FALLBACK env var — bypasses Gemini entirely (hackathon kill switch).
  2. Model ladder — primary model, then fallbacks on retryable HTTP codes.
  3. Strategy ladder per model — response_json_schema → response_schema → json_only.
  4. Key-drift normalisation — renames `phase`→`phase_name`, etc. before parsing.
  5. Deterministic fallback plan — schema-valid, budget-derived, no AI needed.
"""

import json
import logging
from datetime import date, datetime
from typing import Any

from google import genai
from google.genai import errors, types

from app.config import settings
from app.fallback import build_fallback_plan
from app.schemas import GeneratePlanResponse, PlanRequest, PlanResponse

logger = logging.getLogger("celebration-api.ai_engine")

# Initialise the client once at import time.
_client: genai.Client | None = None
if settings.GEMINI_API_KEY:
    _client = genai.Client(api_key=settings.GEMINI_API_KEY)

# HTTP codes that mean "try a different model or strategy" rather than "give up".
# 400 is included because Gemini returns 400 for model-specific schema/parameter
# incompatibilities (e.g. exclusiveMinimum, deprecated sampling params on 3.6-flash).
# 404 is included because Google returns 404 when a model is deprecated.
_RETRYABLE_CODES = {400, 404, 408, 429, 500, 502, 503, 504}

# Observed field-name drift when Gemini generates without schema enforcement.
# Deterministic renames — no guessing, no LLM.
_KEY_ALIASES: dict[str, str] = {
    "event_overview": "event_summary",
    "event_info": "event_summary",
    "summary": "event_summary",
    "phase": "phase_name",
    "stage": "phase_name",
    "phase_tasks": "tasks",
    "budget": "budget_allocation",
    "budget_breakdown": "budget_allocation",
    "vendors": "vendor_checklist",
    "vendor_items": "vendor_checklist",
    "themes": "theme_ideas",
    "theme_concepts": "theme_ideas",
    "palette": "color_palette",
    "colors": "color_palette",
    "elements": "key_elements",
}


def _normalize_keys(obj: Any) -> Any:
    """Recursively rename drifted field names to the PlanResponse contract."""
    if isinstance(obj, dict):
        return {
            _KEY_ALIASES.get(k, k): _normalize_keys(v) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_normalize_keys(item) for item in obj]
    return obj


def _resolve_and_sanitize(node: Any, defs: dict[str, Any]) -> Any:
    """Inline `$ref`s against `$defs`, then strip keywords Gemini rejects.

    Gemini's responseSchema parser cannot reliably resolve `$ref`/`$defs` and
    treats a `title` keyword on a nested object as a required property. This
    flattens the schema: `$ref` → definition, `title` metadata stripped,
    `exclusiveMinimum`/`exclusiveMaximum` → `minimum`/`maximum`.

    The `properties` map is special-cased: its keys are property names
    (including one literally named `title`) and must be preserved; its values
    are schemas and get sanitised.
    """
    if isinstance(node, dict):
        # Resolve $ref by inlining the referenced definition.
        if "$ref" in node:
            ref = node["$ref"]
            def_name = ref.rsplit("/", 1)[-1]
            if def_name in defs:
                return _resolve_and_sanitize(defs[def_name], defs)
            return {}

        node_type = node.get("type")
        cleaned: dict[str, Any] = {}

        for key, value in node.items():
            # properties map: keys are property names (preserve), values are schemas.
            if key == "properties" and isinstance(value, dict):
                cleaned["properties"] = {
                    prop_name: _resolve_and_sanitize(prop_schema, defs)
                    for prop_name, prop_schema in value.items()
                }
                continue

            # Schema-level metadata Gemini rejects.
            if key in {
                "$schema",
                "$defs",
                "$ref",
                "$id",
                "title",
                "additionalProperties",
                "default",
            }:
                continue

            if key == "exclusiveMinimum":
                cleaned["minimum"] = (
                    value + 1 if node_type == "integer" else value + 0.01
                )
            elif key == "exclusiveMaximum":
                cleaned["maximum"] = (
                    value - 1 if node_type == "integer" else value - 0.01
                )
            else:
                cleaned[key] = _resolve_and_sanitize(value, defs)

        # Safety net: `required` must never reference a missing property.
        if isinstance(cleaned.get("required"), list) and isinstance(
            cleaned.get("properties"), dict
        ):
            cleaned["required"] = [
                r for r in cleaned["required"] if r in cleaned["properties"]
            ]

        return cleaned

    if isinstance(node, list):
        return [_resolve_and_sanitize(item, defs) for item in node]

    return node


def _prepare_gemini_schema(model_cls: type) -> dict[str, Any]:
    """Turn a Pydantic model into a flat JSON Schema Gemini accepts."""
    raw = model_cls.model_json_schema()
    defs = raw.get("$defs", {})
    top_level = {k: v for k, v in raw.items() if k != "$defs"}
    return _resolve_and_sanitize(top_level, defs)


def _build_prompt(request: PlanRequest) -> str:
    """Build a date-anchored prompt that forces concrete, budget-aware output."""
    today = date.today().isoformat()
    return f"""You are an expert event planner and budget strategist.

TODAY'S DATE: {today}
EVENT DATE: {request.event_date.isoformat()}
EVENT TYPE: {request.event_type}
GUEST COUNT: {request.guest_count}
TOTAL BUDGET: {request.currency} {request.budget:,.2f}
VIBE / STYLE BRIEF: {request.vibe}

Produce a complete, realistic event plan that a professional planner could hand
to a client today. Follow these rules:

1. TIMELINE: Every phase must be dated relative to the event date. If the event
   is fewer than 6 months away, compress the early phases instead of inventing
   past deadlines. Use natural phrasing such as "10 months before", "6 weeks
   before", "Day of".
2. BUDGET: The `total_budget` in your response must exactly equal the user's
   budget. The sum of `line_items[].amount` plus `contingency` must equal
   `total_budget`. All amounts are in {request.currency}.
3. VENDORS: Provide at least 4 vendor categories relevant to a
   {request.event_type} for {request.guest_count} guests. Cost ranges must be
   realistic for the budget — do not quote luxury prices for a modest budget.
4. THEMES: Provide 2–3 distinct theme concepts that interpret the vibe brief.
   Each theme needs a specific colour palette and concrete decor elements.
5. Be specific. Avoid generic filler like "choose a venue" without explaining
   what to look for.
"""


_JSON_SKELETON_PROMPT = """

Return ONLY a JSON object matching this exact skeleton. Do not rename keys.
Do not nest the plan inside another object.

{
  "event_summary": "string",
  "timeline": [
    {"phase_name": "string", "timing": "string", "tasks": ["string"]}
  ],
  "budget_allocation": {
    "currency": "USD",
    "total_budget": 25000,
    "contingency": 3000,
    "line_items": [
      {"category": "string", "amount": 0, "percentage_of_budget": 0, "notes": "string"}
    ],
    "notes": "string"
  },
  "vendor_checklist": [
    {"category": "string", "description": "string", "questions_to_ask": ["string"], "estimated_cost_range": "string"}
  ],
  "theme_ideas": [
    {"title": "string", "description": "string", "color_palette": ["string"], "key_elements": ["string"]}
  ]
}
"""


def _strip_markdown_fence(text: str) -> str:
    """Strip ```json ... ``` fences if the model ignored the JSON mime type."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            return inner.strip()
    return text


async def generate_event_plan(request: PlanRequest) -> GeneratePlanResponse:
    """Generate a structured event plan, falling back to a local plan on failure."""
    # Kill switch for the hackathon: if Gemini is down, serve a clean plan.
    if getattr(settings, "FORCE_FALLBACK", False):
        logger.warning("FORCE_FALLBACK=true — bypassing Gemini, returning canned plan.")
        return _fallback_response(request)

    if _client is None:
        logger.error("Gemini client is not configured; returning fallback plan.")
        return _fallback_response(request)

    prompt = _build_prompt(request)
    gemini_schema = _prepare_gemini_schema(PlanResponse)

    # Build the ladder: primary model first, then configured fallbacks.
    model_ladder = [settings.GEMINI_MODEL] + [
        m for m in settings.GEMINI_FALLBACK_MODELS if m != settings.GEMINI_MODEL
    ]

    # Strategy ladder, tried in order per model:
    #   A. response_json_schema — modern API, bypasses SDK client-side validation.
    #      Primary for 3.7+/3.8. Rejected by 3.6-flash with 400.
    #   B. response_schema (dict) — older API, works on 3.6-flash. Passing the
    #      sanitised dict (not the Pydantic class) avoids exclusiveMinimum rejection.
    #   C. json_only — no schema constraint, uses a literal skeleton in the
    #      prompt. Last resort; the normaliser handles any remaining drift.
    strategies: list[dict[str, Any]] = [
        {
            "name": "response_json_schema",
            "kwargs": {
                "response_mime_type": "application/json",
                "response_json_schema": gemini_schema,
            },
        },
        {
            "name": "response_schema_dict",
            "kwargs": {
                "response_mime_type": "application/json",
                "response_schema": gemini_schema,
            },
        },
        {
            "name": "json_only",
            "kwargs": {
                "response_mime_type": "application/json",
            },
        },
    ]

    last_error: Exception | None = None
    fatal_error = False

    for model_name in model_ladder:
        if fatal_error:
            break

        for strategy in strategies:
            strategy_name = strategy["name"]

            # json_only has no schema constraint, so append a literal skeleton.
            # Examples anchor field names far more reliably than prose checklists.
            effective_prompt = (
                prompt + _JSON_SKELETON_PROMPT
                if strategy_name == "json_only"
                else prompt
            )

            # NOTE: do NOT pass temperature, top_p, or top_k. gemini-3.6-flash
            # deprecated them and returns 400 INVALID_ARGUMENT if present.
            config = types.GenerateContentConfig(
                max_output_tokens=16384,
                http_options=types.HttpOptions(
                    timeout=45000,
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
                **strategy["kwargs"],
            )

            try:
                response = await _client.aio.models.generate_content(
                    model=model_name,
                    contents=effective_prompt,
                    config=config,
                )

                if not response.text:
                    raise ValueError(
                        f"{model_name} ({strategy_name}) returned an empty response."
                    )

                # Strip markdown fences, parse JSON, normalise key drift,
                # then validate against the strict Pydantic model.
                raw_text = _strip_markdown_fence(response.text)
                raw_dict = json.loads(raw_text)
                plan = PlanResponse.model_validate(_normalize_keys(raw_dict))

                logger.info(
                    "Plan generated successfully with %s using %s.",
                    model_name,
                    strategy_name,
                )
                return GeneratePlanResponse(
                    **plan.model_dump(),
                    model_used=f"{model_name} ({strategy_name})",
                    generated_at=datetime.utcnow(),
                    fallback_used=False,
                )

            except errors.APIError as exc:
                last_error = exc
                code = getattr(exc, "code", None)

                if code in _RETRYABLE_CODES:
                    logger.warning(
                        "Model %s strategy %s failed (HTTP %s). Trying next option.",
                        model_name,
                        strategy_name,
                        code,
                    )
                    continue

                logger.error(
                    "Non-retryable Gemini error (HTTP %s) on %s/%s: %s. Stopping.",
                    code,
                    model_name,
                    strategy_name,
                    getattr(exc, "message", str(exc)),
                )
                fatal_error = True
                break

            except Exception as exc:  # noqa: BLE001 — parse errors, timeouts, etc.
                last_error = exc
                logger.warning(
                    "Model %s strategy %s failed (%s). Trying next option.",
                    model_name,
                    strategy_name,
                    exc,
                )
                continue

    logger.error(
        "All Gemini models and strategies failed. Last error: %s. Returning fallback plan.",
        last_error,
    )
    return _fallback_response(request)


def _fallback_response(request: PlanRequest) -> GeneratePlanResponse:
    """Wrap the deterministic fallback plan in the API envelope."""
    fallback = build_fallback_plan(request)
    return GeneratePlanResponse(
        **fallback.model_dump(),
        model_used="fallback",
        generated_at=datetime.utcnow(),
        fallback_used=True,
    )