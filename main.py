"""
Module 2: Proposal-Funding Matching MVP
Uses CrewAI + llama/(via Groq)
"""

import csv
import json
import os
import re
import sqlite3
import uuid
from crewai import Agent, Task, Crew, Process
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
os.environ["GROQ_API_KEY"] = GROQ_API_KEY  # ensure LiteLLM picks it up
LLM_MODEL = "groq/qwen/qwen3-32b"

# ── Sample Funding Database (replace with real data later) ──────────────────
FUNDING_DB = [
    {
        "funding_id": "F001",
        "funding_name": "Wellcome Trust Metabolic Research Fund",
        "description": "Supports research into metabolic regulation, obesity, and related disorders. Welcomes Phase 1 clinical trials.",
        "domains": ["metabolic research", "obesity", "clinical trials"],
        "budget_range": "£200,000 - £500,000",
        "timeline": "Phase 1-2",
        "eligibility": ["UK universities", "NHS trusts"]
    },
    {
        "funding_id": "F002",
        "funding_name": "UKRI Circadian Biology Grant",
        "description": "Funds research into circadian rhythms and their impact on human health, including sleep-wake cycles.",
        "domains": ["circadian biology", "sleep research", "chronotherapy"],
        "budget_range": "£100,000 - £300,000",
        "timeline": "Phase 1",
        "eligibility": ["UK universities"]
    },
    {
        "funding_id": "F003",
        "funding_name": "MRC Drug Discovery Initiative",
        "description": "Supports early-stage drug discovery and development, particularly novel small molecules.",
        "domains": ["drug discovery", "pharmacology", "clinical development"],
        "budget_range": "£300,000 - £800,000",
        "timeline": "Phase 1-3",
        "eligibility": ["UK universities", "biotech companies"]
    },
    {
        "funding_id": "F004",
        "funding_name": "EU Horizon Digital Health Fund",
        "description": "Funds digital health solutions and AI-driven healthcare research.",
        "domains": ["digital health", "AI", "data science"],
        "budget_range": "£500,000 - £2,000,000",
        "timeline": "Phase 2-3",
        "eligibility": ["EU/UK universities"]
    },
    {
        "funding_id": "F005",
        "funding_name": "NIHR Clinical Research Network",
        "description": "Supports clinical trials focused on weight management and metabolic disorders.",
        "domains": ["clinical trials", "weight management", "metabolic disorders"],
        "budget_range": "£150,000 - £400,000",
        "timeline": "Phase 1-2",
        "eligibility": ["NHS trusts", "UK universities"]
    }
]


# ── Helper: Clean Module 1 JSON ─────────────────────────────────────────────
def clean_text(text):
    """Remove \n\n artifacts from Module 1 output."""
    if isinstance(text, str):
        return text.replace("\n\n", " ").replace("\n", " ").strip()
    if isinstance(text, list):
        return [clean_text(t) for t in text]
    return text


def load_proposal(module1_json: dict) -> dict:
    """Map Module 1 output to Proposal Schema."""
    fields = module1_json.get("extracted_fields", {})
    return {
        "proposal_id":        module1_json["doc"]["doc_id"],
        "title":              clean_text(fields.get("title", {}).get("value", "")),
        "core_problem":       clean_text(fields.get("objectives", {}).get("value", "")),
        "solution_approach":  clean_text(fields.get("methods", {}).get("value", "")),
        "domains":            clean_text(fields.get("domain_area", {}).get("value", "")),
        "technical_reqs":     clean_text(fields.get("methods", {}).get("value", "")),
        "readiness_level":    clean_text(fields.get("timeline", {}).get("value", "")),
        "budget":             clean_text(fields.get("budget_summary", {}).get("value", "unknown")),
        "applicant_org":      clean_text(fields.get("applicant_org", {}).get("value", "")),
        "risks":              module1_json.get("risks_and_red_flags", []),
        "questions_for_human":module1_json.get("questions_for_human", []),
    }


# ── Define Agents ───────────────────────────────────────────────────────────
def build_crew(proposal_schema: dict, funding_db: list):

    funding_db_str = json.dumps(funding_db, indent=2)

    # Compact proposal: only key matching fields (avoids TPM rate limits)
    compact = {
        "proposal_id":       proposal_schema["proposal_id"],
        "title":             proposal_schema["title"],
        "domains":           proposal_schema["domains"],
        "core_problem":      proposal_schema["core_problem"],
        "solution_approach": proposal_schema["solution_approach"],
        "readiness_level":   proposal_schema["readiness_level"],
        "budget":            proposal_schema["budget"],
        "applicant_org":     proposal_schema["applicant_org"],
    }
    proposal_str = json.dumps(compact, indent=2)

    # Slim risk summary for task 3
    risk_summary = "; ".join(
        f"[{r['severity'].upper()}] {r['risk']}"
        for r in proposal_schema.get("risks", [])
    )
    questions_summary = "; ".join(
        q["question"] for q in proposal_schema.get("questions_for_human", [])
    )

    # Agent 1: ProposalAgent
    proposal_agent = Agent(
        role="Proposal Analyst",
        goal="Understand and summarise the research proposal clearly for matching.",
        backstory=(
            "You are an expert at reading research proposals and extracting "
            "the key information needed for funding matching. You always reason "
            "step by step (Chain of Thought) before drawing conclusions."
        ),
        llm=LLM_MODEL,
        verbose=True
    )

    # Agent 2: MatchingAgent
    matching_agent = Agent(
        role="Funding Matcher",
        goal="Match the proposal to the most suitable funding opportunities using structured scoring.",
        backstory=(
            "You are an expert at evaluating research proposals against funding criteria. "
            "You score matches across 5 dimensions: thematic, technical, feasibility, "
            "timeline, and budget. You reason step by step before scoring, and always "
            "explain your reasoning transparently."
        ),
        llm=LLM_MODEL,
        verbose=True
    )

    # Agent 3: ValidationAgent
    validation_agent = Agent(
        role="Validator",
        goal="Validate match scores, check soft constraints, and generate human-readable explanations.",
        backstory=(
            "You are a critical reviewer who ensures match quality. You check for "
            "consistency, flag uncertain results, identify soft constraint violations, "
            "and generate clear explanations for each recommendation."
        ),
        llm=LLM_MODEL,
        verbose=True
    )

    # Task 1: Proposal Understanding (CoT)
    task1 = Task(
        description=f"""
        Analyse this research proposal step by step:

        {proposal_str}

        Step 1: What is the core research problem?
        Step 2: What methods/approaches are used?
        Step 3: What research domains does this belong to?
        Step 4: What is the readiness level (Phase 1/2/3)?
        Step 5: What are the key technical requirements?
        Step 6: Summarise in 2-3 sentences what kind of funding this proposal needs.

        Output a clear summary that will help the Funding Matcher.
        """,
        agent=proposal_agent,
        expected_output="A structured step-by-step analysis and summary of the proposal."
    )

    # Task 2: Matching & Scoring (CoT per dimension)
    task2 = Task(
        description=f"""
        Using the proposal analysis from Task 1, score each funding opportunity.

        Funding Database:
        {funding_db_str}

        For EACH funding opportunity, reason step by step:
        Step 1: Thematic match (0-100) - Do the research domains align?
        Step 2: Technical match (0-100) - Do the methods/approaches fit?
        Step 3: Feasibility (0-100) - Is the proposal realistic for this fund?
        Step 4: Timeline match (0-100) - Does the phase/timeline align?
        Step 5: Budget match (0-100) - Does the budget range fit?
        Step 6: Weighted overall score = (thematic*0.3 + technical*0.2 + feasibility*0.2 + timeline*0.15 + budget*0.15)

        Return results as JSON:
        {{
            "ranked_matches": [
                {{
                    "funding_id": "",
                    "funding_name": "",
                    "dimensions": {{
                        "thematic": 0,
                        "technical": 0,
                        "feasibility": 0,
                        "timeline": 0,
                        "budget": 0
                    }},
                    "alignment_score": 0,
                    "reasoning": "brief explanation of scores"
                }}
            ]
        }}

        Sort by alignment_score descending.
        """,
        agent=matching_agent,
        expected_output="JSON with ranked funding matches and dimension scores."
    )

    # Task 3: Validation & Explanation
    task3 = Task(
        description=f"""
        Review the ranked matches from Task 2 and validate them.

        Original proposal:
        {proposal_str}

        Known risks: {risk_summary}

        Questions flagged for human review: {questions_summary}

        For each match:
        1. Check soft constraints (e.g. eligibility, ethics considerations)
        2. Assess uncertainty - would you give a different score on a second pass?
        3. Generate a 2-3 sentence human-readable explanation

        Determine:
        - decision_status: "VALID", "REVIEW", or "INVALID"
        - requires_human_review: true if uncertainty is high or constraints are unclear
        - uncertainty score (0-10, where 10 = very uncertain)

        Return final MatchOutput JSON:
        {{
            "proposal_id": "{proposal_schema['proposal_id']}",
            "timestamp": "{datetime.now().isoformat()}",
            "ranked_matches": [
                {{
                    "funding_id": "",
                    "funding_name": "",
                    "alignment_score": 0,
                    "dimensions": {{}},
                    "decision_status": "VALID",
                    "uncertainty": 0,
                    "requires_human_review": false,
                    "explanation": ""
                }}
            ]
        }}
        """,
        agent=validation_agent,
        expected_output="Final validated MatchOutput JSON with explanations."
    )

    # Build Crew (sequential pipeline)
    crew = Crew(
        agents=[proposal_agent, matching_agent, validation_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential,
        verbose=True,
        max_rpm=1  # stay within Groq free tier 6000 TPM limit
    )

    return crew


# ── Save to Registry ────────────────────────────────────────────────────────
def save_analysis(proposal_schema: dict, result_str: str, db_path: str = "registry.sqlite"):
    # Try to extract ranked_matches JSON from the result string
    ranked_matches = []
    top_match_id = top_match_name = None
    top_score = None

    match = re.search(r'"ranked_matches"\s*:\s*(\[.*?\])', result_str, re.DOTALL)
    if match:
        try:
            ranked_matches = json.loads(match.group(1))
            if ranked_matches:
                ranked_matches.sort(key=lambda x: x.get("alignment_score", 0), reverse=True)
                top = ranked_matches[0]
                top_match_id   = top.get("funding_id")
                top_match_name = top.get("funding_name")
                top_score      = top.get("alignment_score")
        except json.JSONDecodeError:
            pass

    analysis_id = "ana_" + uuid.uuid4().hex[:12]
    ran_at = datetime.now().isoformat()

    con = sqlite3.connect(db_path)
    con.execute(
        """INSERT INTO analyses
           (analysis_id, doc_id, proposal_id, ran_at, model,
            top_match_id, top_match_name, top_score, ranked_matches, full_output)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            analysis_id,
            proposal_schema["proposal_id"],
            proposal_schema["proposal_id"],
            ran_at,
            LLM_MODEL,
            top_match_id,
            top_match_name,
            top_score,
            json.dumps(ranked_matches),
            result_str,
        ),
    )
    con.commit()
    con.close()

    # Write CSV alongside the DB
    csv_path = db_path.replace(".sqlite", "_analyses.csv")
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "analysis_id", "proposal_id", "ran_at", "model",
                "funding_id", "funding_name", "alignment_score",
                "thematic", "technical", "feasibility", "timeline", "budget",
                "decision_status", "uncertainty", "requires_human_review", "explanation"
            ])
        for m in ranked_matches:
            dims = m.get("dimensions", {})
            writer.writerow([
                analysis_id,
                proposal_schema["proposal_id"],
                ran_at,
                LLM_MODEL,
                m.get("funding_id"),
                m.get("funding_name"),
                m.get("alignment_score"),
                dims.get("thematic"),
                dims.get("technical"),
                dims.get("feasibility"),
                dims.get("timeline"),
                dims.get("budget"),
                m.get("decision_status"),
                m.get("uncertainty"),
                m.get("requires_human_review"),
                m.get("explanation"),
            ])

    return analysis_id


# ── Main ────────────────────────────────────────────────────────────────────
def run_matching_pipeline(module1_json: dict):
    print("\n" + "="*60)
    print("Module 2: Proposal-Funding Matching Pipeline")
    print("="*60 + "\n")

    # Step 1: Load and clean proposal from Module 1 output
    print("Loading proposal from Module 1 output...")
    proposal_schema = load_proposal(module1_json)
    print(f"Proposal ID: {proposal_schema['proposal_id']}")
    print(f"Title: {proposal_schema['title']}\n")

    # Step 2: Build and run crew
    crew = build_crew(proposal_schema, FUNDING_DB)
    result = crew.kickoff()

    # Step 3: Save output to registry
    analysis_id = save_analysis(proposal_schema, str(result))
    print(f"\nSaved to registry as: {analysis_id}")
    return result


# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    con = sqlite3.connect("registry.sqlite")
    rows = con.execute("SELECT doc_id, filename, json_blob FROM documents").fetchall()
    con.close()

    if not rows:
        print("No proposals found in registry.")
    else:
        for doc_id, filename, json_blob in rows:
            print(f"\nProcessing: {filename} ({doc_id})")
            module1_json = json.loads(json_blob)
            result = run_matching_pipeline(module1_json)
            print("\nFinal Output:")
            print(result)
