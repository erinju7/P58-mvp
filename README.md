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
  │  • Load PDF/DOCX/  │    │  • Eligibility filter  │    │  • Validate score       │
  │    TXT/MD          │──▶ │  • Embedding retrieval │──▶ │    stability            │
  │  • Extract keywords│    │  • Top-K candidates    │    │  • Constraint recheck   │
  │  • LLM → semantic  │    │  • Score per dimension │    │  • Flag for human       │
  │    fields          │    │    (thematic/technical │    │    review               │
  │  • Normalize text  │    │    feasibility/timeline│    │                         │
  │                    │    │    /budget)            │    │                         │
  │                    │    │  • Weighted re-rank    │    │                         │
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
                                        └──────────────────────────────┘
