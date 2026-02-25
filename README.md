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
  │  • Read from       │    │  • Eligibility filter  │    │  • LLM consistency      │
  │    Module 1        │──▶ │  • Embedding retrieval │──▶ │    check (run twice →   │
  │    Registry        │    │  • Top-K candidates    │    │    uncertainty score)   │
  │  • Clean \n\n      │    │  • Score per dimension │    │  • LLM soft constraint  │
  │    artifacts       │    │    (thematic/technical │    │    recheck              │
  │  • Map fields to   │    │    feasibility/timeline│    │  • LLM explanation      │
  │    proposal schema │    │    /budget) by LLM     │    │    generation           │
  │                    │    │  • Weighted re-rank    │    │  • Flag for human       │
  │                    │    │                        │    │    review               │
  └────────┬───────────┘    └───────────┬────────────┘    └────────────┬────────────┘
           │                            │                              │
           ▼                            └──────────────────────────────┘
  ┌─────────────────────┐                              │
  │  Proposal Schema:   │                              ▼
  │                     │               ┌──────────────────────────────┐     ┌─────────────────────────┐
  │  • proposal_id      │               │      MatchOutput JSON        │────▶│   Registry (SQLite)     │
  │    (doc.doc_id)     │               │        (schemas.py)          │     │     (registry.py)       │
  │  • core_problem     │               │                              │     └─────────────────────────┘
  │    (objectives)     │               │  • proposal_id               │
  │  • solution_approach│               │  • ranked_matches            │
  │    (methods)        │               │  • alignment_score           │
  │  • domains          │               │  • dimensions {}             │
  │    (domain_area)    │               │  • decision_status           │
  │  • technical_reqs   │               │  • requires_human_review     │
  │    (methods)        │               │  • explanation               │
  │  • readiness_level  │               └──────────────────────────────┘
  │    (timeline)       │
  └─────────────────────┘
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
