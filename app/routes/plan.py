"""Plan generation router: wires PlanRequest → ai_engine → GeneratePlanResponse."""

import logging

from fastapi import APIRouter, HTTPException, Response, status

from app.ai_engine import generate_event_plan
from app.schemas import GeneratePlanResponse, PlanRequest

logger = logging.getLogger("celebration-api.routes.plan")

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.post(
    "/generate-plan",
    response_model=GeneratePlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a full event plan",
    description=(
        "Accepts event parameters and returns a structured plan with a timeline, "
        "budget allocation, vendor checklist, and theme ideas. If the AI call "
        "fails or times out, a deterministic fallback plan is returned with "
        "`fallback_used: true` and HTTP 200 — the frontend always receives a "
        "usable response."
    ),
    responses={
        200: {
            "description": (
                "Plan generated (AI or fallback). Check `fallback_used` in the body."
            ),
            "content": {"application/json": {}},
        },
        422: {
            "description": (
                "Invalid request. Common causes: past `event_date`, "
                "non-positive `budget`, unknown field, or wrong type."
            ),
        },
        500: {
            "description": (
                "Unexpected server error. Unlike a Gemini failure, this indicates "
                "a bug in the fallback path. The frontend should retry."
            ),
        },
    },
)
async def generate_plan(
    request: PlanRequest,
    response: Response,
) -> GeneratePlanResponse:
    """Generate an event plan. Never returns an error page due to AI failures."""
    try:
        result = await generate_event_plan(request)
    except Exception as exc:
        # The engine catches all Gemini errors internally and returns a fallback.
        # Reaching here means the fallback itself raised — a bug, not an outage.
        logger.exception("Unhandled error in /generate-plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to generate the event plan due to an internal error. "
                "Please try again."
            ),
        ) from exc

    # Expose fallback status as a header for easy DevTools debugging.
    response.headers["X-Fallback-Used"] = "true" if result.fallback_used else "false"
    return result