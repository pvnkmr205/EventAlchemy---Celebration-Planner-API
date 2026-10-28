# 🎉 EventAlchemy: GenAI Celebration & Event Planner
[![Live Demo](https://img.shields.io/badge/Live_Demo-EventAlchemy-success?style=for-the-badge)](https://eventalchemy.netlify.app/) [![**API** Swagger](https://img.shields.io/badge/API_Docs-Swagger-blue?style=for-the-badge)](https://eventalchemy-celebration-planner-api.onrender.com/docs) [![Python](https://img.shields.io/badge/Python-3.12+-yellow?style=for-the-badge&logo=python)](https://python.org) [![FastAPI](https://img.shields.io/badge/FastAPI-0.**115**+-green?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com) [![Google Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-purple?style=for-the-badge&logo=google)](https://deepmind.google/technologies/gemini/)
**EventAlchemy** is a full-stack, GenAI-powered engine that transforms a few simple event inputs into a comprehensive, structured event plan. It generates a planning timeline, itemized budgets, vendor vetting checklists, and personalized theme concepts.
Built with a **bulletproof backend architecture**, the **API** enforces strict **JSON** schemas on Google Gemini and features a 5-layer resilience fallback. It **never returns a **500** error** due to AI failure—if the AI is overloaded, it generates a deterministic, budget-derived template plan instead.
---
## 🚀 Live Links
- **Frontend UI:** [https://eventalchemy.netlify.app/](https://eventalchemy.netlify.app/)
- **Backend **API**:** [https://eventalchemy-celebration-planner-api.onrender.com](https://eventalchemy-celebration-planner-api.onrender.com)
- **Interactive **API** Docs (Swagger):** [https://eventalchemy-celebration-planner-api.onrender.com/docs](https://eventalchemy-celebration-planner-api.onrender.com/docs)
---

### The 5 Resilience Layers (Why this Backend is Demo-Proof)
Most AI apps crash when the API rate-limits or hallucinates markdown. EventAlchemy solves this with 5 layers:
1. **Schema Sanitizer:** Flattens Pydantic `$ref`/`$defs` and strips `exclusiveMinimum` so Gemini accepts the schema.
2. **Strategy Ladder:** Attempts `response_json_schema` → `response_schema` → `json_only` to bypass model-specific API limits.
3. **Model Ladder:** If `gemini-2.5-flash` is down (503), automatically retries with `gemini-3.6-flash` and `gemini-3.5-flash-lite`.
4. **Key-Drift Normalizer:** If the AI outputs `phase` instead of `phase_name`, a deterministic Python dictionary renames it before Pydantic validation.
5. **Deterministic Fallback:** If all AI calls fail, the backend mathematically generates a plan based on the user's budget and guest count. The frontend shows a subtle grey badge and keeps working.
---
## 💻 Local Setup & Installation
### Prerequisites
- Python 3.12+
- A Google Gemini API Key ([Get one free here](https://aistudio.google.com/app/apikey))
### 1. Clone the Repository
bash
```
git clone https://github.com/pvnkmr205/EventAlchemy---Celebration-Planner-API.git
cd EventAlchemy---Celebration-Planner-API
```
### 2. Backend Setup
Create your virtual environment and install dependencies:
bash
```
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# Mac/Linux
source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in the root directory and add your key:
env
```
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_FALLBACK_MODELS=gemini-3.6-flash,gemini-3.5-flash-lite
FORCE_FALLBACK=false
```
Start the FastAPI server:
bash
```
uvicorn app.main:app --reload --port 8000
```
- *Backend running at:* `http://localhost:8000`
- *Swagger docs at:* `http://localhost:8000/docs`
### 3. Frontend Setup
The frontend is a standalone `index.html` file using Tailwind CSS.
1. Open `index.html` in your code editor.
2. By default, it points to the live Render backend. If you want to test your local backend, find the `fetch()` call and change the URL to `http://localhost:8000/api/v1/generate-plan`.
3. Double-click `index.html` to open it in your browser, or use the VS Code **Live Server** extension.
---
## 📡 API Contract
### `POST /api/v1/generate-plan`
**Request Body:**
json
```
{
  "event_type": "wedding",
  "budget": 25000,
  "guest_count": 150,
  "event_date": "2027-06-15",
  "vibe": "boho rustic outdoor with string lights",
  "currency": "USD"
}
```
**Response (200 OK):** Always returns 200 for valid inputs.
json
```
{
  "event_summary": "A boho rustic outdoor wedding for 150 guests...",
  "timeline": [
    {
      "phase_name": "Vision & Budget Lock-In",
      "timing": "10 months before",
      "tasks": ["Confirm guest count", "Shortlist 3 venues"]
    }
  ],
  "budget_allocation": {
    "currency": "USD",
    "total_budget": 25000,
    "contingency": 3000,
    "line_items": [
      {
        "category": "Venue",
        "amount": 4840,
        "percentage_of_budget": 22.0,
        "notes": "Negotiate off-peak dates to save."
      }
    ],
    "notes": "Prioritize venue and catering."
  },
  "vendor_checklist": [
    {
      "category": "Caterer",
      "description": "Food is the memory guests keep.",
      "questions_to_ask": ["Do you handle vegan guests?", "What is the staff ratio?"],
      "estimated_cost_range": "$5,000 - $7,500"
    }
  ],
  "theme_ideas": [
    {
      "title": "Earthy Elegance",
      "description": "Neutral base tones with warm lighting.",
      "color_palette": ["Ivory", "Sage", "Terracotta"],
      "key_elements": ["Candlelit tables", "Wildflowers"]
    }
  ],
  "model_used": "gemini-2.5-flash",
  "generated_at": "2026-10-27T10:00:00Z",
  "fallback_used": false
}
```
---
## 🛠️ Tech Stack
- **AI Core:** Google Gemini API (`google-genai` SDK)
- **Backend:** Python 3.12, FastAPI, Uvicorn
- **Data Validation:** Pydantic v2 (Strict JSON Schema Enforcement)
- **Frontend:** HTML5, Vanilla JS, Tailwind CSS, Chart.js (for the budget donut chart)
- **Deployment:** Render (Backend), Netlify (Frontend)