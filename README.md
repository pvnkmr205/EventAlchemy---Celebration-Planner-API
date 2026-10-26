# Celebration & Event Planner API

GenAI backend that turns event inputs into a **structured plan**: timeline,
itemized budget, vendor checklist with vetting questions, and theme concepts.

**The API never returns a 500 because the AI failed.** If Gemini is down,
a deterministic fallback plan is returned with HTTP 200 and `fallback_used: true`.

## Live Demo

- **Base URL**: `https://YOUR-SERVICE.onrender.com`  (replace after deploy)
- **Interactive Docs**: `https://YOUR-SERVICE.onrender.com/docs`

## Endpoint

`POST /api/v1/generate-plan`

```json
{
  "event_type": "wedding",
  "budget": 25000,
  "guest_count": 150,
  "event_date": "2027-06-15",
  "vibe": "boho rustic outdoor",
  "currency": "USD"
}