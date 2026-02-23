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
