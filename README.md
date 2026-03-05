# P58 Proposal-Funding Matching Pipeline

Matches research proposals (ingested by Module 1) against a funding database using a 3-agent CrewAI pipeline powered by Groq (Qwen3-32B).

## Quickstart

```bash
# Activate environment
source venv/bin/activate

# Set API key
export GROQ_API_KEY="your-key-here"

# Run
python main.py
```

---

## Architecture

```text
registry.sqlite (documents table)
        │
        ▼
  load_proposal()          ← maps Module 1 JSON → compact proposal schema
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                  CrewAI Sequential Pipeline            │
│                                                       │
│  Task 1: ProposalAgent                                │
│  • Step-by-step CoT analysis of the proposal          │
│  • Summarises domains, methods, phase, funding needs  │
│                         │                             │
│  Task 2: MatchingAgent                                │
│  • Scores each funding opportunity across 5 dims      │
│    thematic (30%) · technical (20%) · feasibility     │
│    (20%) · timeline (15%) · budget (15%)              │
│  • Returns ranked JSON                                │
│                         │                             │
│  Task 3: ValidationAgent                              │
│  • Checks soft constraints & eligibility              │
│  • Assigns decision_status: VALID / REVIEW / INVALID  │
│  • Generates human-readable explanation               │
└───────────────────────────────────────────────────────┘
        │
        ▼
  save_analysis()
  ├── registry.sqlite  → analyses table
  └── registry_analyses.csv  → one row per funding match
```

---

## Output Schema

```json
{
  "proposal_id": "doc_ff615c3dc79f",
  "timestamp": "2026-03-05T17:48:35",
  "ranked_matches": [
    {
      "funding_id": "F002",
      "funding_name": "UKRI Circadian Biology Grant",
      "alignment_score": 92.5,
      "dimensions": {
        "thematic": 95,
        "technical": 95,
        "feasibility": 95,
        "timeline": 90,
        "budget": 85
      },
      "decision_status": "VALID",
      "uncertainty": 2,
      "requires_human_review": false,
      "explanation": "Strong thematic/technical alignment with circadian biology..."
    }
  ]
}
```

---

## Database Tables

| Table | Description |
|-------|-------------|
| `documents` | Raw Module 1 output per ingested PDF |
| `analyses` | Matching results per pipeline run |

### `analyses` columns
`analysis_id` · `doc_id` · `proposal_id` · `ran_at` · `model` · `top_match_id` · `top_match_name` · `top_score` · `ranked_matches` (JSON) · `full_output`

---

## CSV Output

`registry_analyses.csv` — one row per funding match, appended after each run.

Columns: `analysis_id`, `proposal_id`, `ran_at`, `model`, `funding_id`, `funding_name`, `alignment_score`, `thematic`, `technical`, `feasibility`, `timeline`, `budget`, `decision_status`, `uncertainty`, `requires_human_review`, `explanation`

---

## Decision Status

| Status | Meaning |
|--------|---------|
| `VALID` | Strong match: recommended to apply |
| `REVIEW` | Good match but requires human verification |
| `INVALID` | Fundamental mismatch: not worth applying |

---

## Rate Limits

The free Groq tier has a 6,000 TPM limit. `max_rpm=1` is set on the Crew to stay within limits (~6–8 minutes per proposal).
