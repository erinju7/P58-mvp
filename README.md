**Architecture**
```text
┌─────────────────────────────────────────┐
                          │               CLI (cli.py)              │
                          │   p58 match --input proposal.pdf        │
                          └──────────────────┬──────────────────────┘
                                             │
                                             ▼
                          ┌─────────────────────────────────────────┐
                          │         Pipeline (pipeline.py)          │
                          │           Orchestrator                  │
                          └──────────────────┬──────────────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               │                             │                             │
               ▼                             ▼                             ▼
  ┌────────────────────┐    ┌───────────────────────┐    ┌─────────────────────────┐
  │  ProposalAgent     │    │    MatchingAgent       │    │  ValidationAgent        │
  │ (proposal_agent.py)│    │  (matching_agent.py)   │    │ (validation_agent.py)   │
  │                    │    │                        │    │                         │
  │  • Load PDF/DOCX/  │    │  • Eligibility filter  │    │  • LLM consistency      │
  │    TXT/MD          │──▶ │  • Embedding retrieval │──▶ │    check (run twice →   │
  │  • Extract keywords│    │  • Top-K candidates    │    │    uncertainty score)   │
  │  • LLM → semantic  │    │  • Score per dimension │    │  • LLM soft constraint  │
  │    fields          │    │    (thematic/technical │    │    recheck              │
  │  • Normalize text  │    │    feasibility/timeline│    │  • LLM explanation      │
  │                    │    │    /budget) by LLM     │    │    generation           │
  │                    │    │  • Weighted re-rank    │    │  • Flag for human       │
  │                    │    │                        │    │    review               │
  └────────┬───────────┘    └───────────┬────────────┘    └────────────┬────────────┘
           │                            │                              │
           ▼                            └──────────────────────────────┘
  ┌─────────────────────┐                              │
  │  Proposal Schema:   │                              ▼
  │                     │               ┌──────────────────────────────┐     ┌─────────────────────────┐
  │  • proposal_id      │               │      MatchOutput JSON        │────▶│   Registry (SQLite)     │
  │  • core_problem     │               │        (schemas.py)          │     │     (registry.py)       │
  │  • solution_approach│               │                              │     └─────────────────────────┘
  │  • domains          │               │  • proposal_id               │
  │  • technical_reqs   │               │  • ranked_matches            │
  │  • readiness_level  │               │  • alignment_score           │
  └─────────────────────┘               │  • dimensions {}             │
                                        │  • decision_status           │
                                        │  • requires_human_review     │
                                        │  • explanation               │
                                        └──────────────────────────────┘
```
**Output Schema**
```text
json{
  "proposal_id": "P001",
  "ranked_matches": [
    {
      "funding_id": "F204",
      "funding_name": "Sustainable Materials Innovation Call",
      "alignment_score": 87,
      "dimensions": {
        "thematic": 90,
        "technical": 85,
        "feasibility": 85,
        "timeline": 80,
        "budget": 90
      },
      "decision_status": "VALID",
      "requires_human_review": true,
      "explanation": "This funding opportunity strongly aligns with the proposal's focus on biomaterials and polymer synthesis. The thematic and budget scores are high, though the project timeline slightly exceeds the funding window."
    }
  ]
}
```
