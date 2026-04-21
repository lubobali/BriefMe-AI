# BriefMe-AI

AI-powered email chief of staff. Checks your inbox, classifies emails (meeting/action/FYI), creates calendar events, and sends you summaries — all optimized for minimal token usage.

Built as a homework submission for DataExpert.io AI Engineering Bootcamp (Week 3) and as a real tool for personal use with OpenClaw + WhatsApp.

## Token Efficiency — Before vs After

| Metric | Before (Inefficient) | After (Optimized) | Reduction |
|--------|---------------------|-------------------|-----------|
| Tool calls | 19 | 4 | **78.9%** |
| Estimated tokens | 2,477 | 102 | **95.9%** |
| Gmail searches | 11 | 1 | **90.9%** |
| Duplicate processing | 9 emails | 0 | **100%** |

## What Was Wrong (Inefficient Version)

1. **3 overlapping inbox searches** — "last 24h", "unread", "from sender" all return the same emails
2. **50 emails fetched** regardless of actual count
3. **3 summaries per email** — paraphrase + executive + risk (should be 1)
4. **Policy block repeated** with every email (~500 tokens x 9 = wasted)
5. **Re-checks inbox** after processing each email
6. **Verbose reasoning** before every tool call
7. **No dedup** — same meeting email creates 3 calendar events

## What Was Fixed (Optimized Version)

1. **1 search** combining all filters
2. **Limit 10** — fetch only what's needed
3. **1 classification per email** — combined classify + summarize
4. **Policy once** at init, not per email
5. **Batch processing** — no re-checking
6. **No verbose output** — direct tool calls
7. **Dedup via processed_ids** — each email handled exactly once
8. **Better classification** — FYI patterns checked first ("no action needed" ≠ action item)

## Architecture

```
briefme/
  schemas.py        — Pydantic v2 models (Email, EmailClassification, Action, HeartbeatResult)
  guardrails.py     — PII redaction + prompt injection detection
  client.py         — LLM client (DataExpert Anthropic proxy + NVIDIA NIM fallback)
  classifier.py     — LLM email classification (1 call per email)
  heartbeat.py      — Optimized heartbeat workflow + mock tools
  api.py            — FastAPI endpoints (/health, /heartbeat/mock, /compare)
  test_briefme.py   — 45 tests across 8 classes

claude_skills/
  email_classifier.md — Combined classify + summarize prompt

homework/
  before_after.md      — Metrics comparison table
  optimized_workflow.md — What changed and why
  test_evidence.md     — Test results for all 4 cases
  edge_cases.md        — Ambiguous dates, duplicates, prompt injection
```

## Setup

```bash
git clone https://github.com/lubobali/BriefMe-AI.git
cd BriefMe-AI
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Run Tests

```bash
# All 45 tests (~13 sec, includes real LLM API calls)
python -m pytest briefme/test_briefme.py -v

# Fast tests only (~0.2 sec, no API calls)
python -m pytest briefme/test_briefme.py -v -k "Schema or Guardrails or Heartbeat or API or EdgeCases"
```

## Run the API

```bash
uvicorn briefme.api:app --port 8098
```

Then:
- `curl http://localhost:8098/health` — health check
- `curl http://localhost:8098/heartbeat/mock` — run optimized heartbeat
- `curl http://localhost:8098/compare` — before vs after metrics

## Sender/Recipient Configuration

The agent only processes emails from an approved sender and forwards summaries to a configured recipient. Set these in your code or via environment variables:

```python
agent = EfficientChiefOfStaffAgent(
    tools=tools,
    approved_sender="boss@company.com",    # only emails FROM this sender are processed
    approved_recipient="you@company.com",  # summaries/actions sent TO this address
)
```

For the real app, configure via `.env`:
```
GMAIL_APPROVED_SENDER=boss@company.com
GMAIL_RECIPIENT=you@company.com
```

Security policy enforces that `approved_sender` must be set — the agent will not run without it.

## Before/After Evidence (saved output)

See `homework/compare_output.json` for a saved `/compare` endpoint result:
```json
{
  "before": { "tool_calls": 19, "estimated_tokens": 2477, "gmail_searches": 11 },
  "after": { "tool_calls": 4, "estimated_tokens": 102, "gmail_searches": 1 },
  "reduction": { "tool_calls_pct": 78.9, "tokens_pct": 95.9 }
}
```

## Mock vs Real Flow

BriefMe-AI has two processing paths:

- **Mock path** (`heartbeat.py`): Uses keyword classification for the homework before/after comparison. No LLM calls, no guardrails needed — classification is deterministic. This is what `/heartbeat/mock` and `/compare` use.
- **Real path** (`classifier.py`): Uses LLM (Claude Sonnet / NVIDIA NIM) for classification + summarization. PII redaction and prompt injection detection run **before** the LLM call. This is what the `TestClassifier` and `TestE2E` tests exercise.

Both paths share the same schemas, dedup logic, rate limiting, and sender scoping. The guardrails (PII redaction, injection detection) apply only in the real path because the mock path never sends content to an LLM.

## Safety Controls

- PII redaction on all email content before LLM (email, phone, IP, API keys)
- Prompt injection detection — flagged emails skip LLM, classified as `skip` with `risk_level: high`
- Duplicate prevention via processed ID tracking
- Rate limiting: max 10 emails per heartbeat
- No destructive email operations (no delete, no archive)
- Security policy enforced at init — agent won't start without approved sender
- Sender scoping via `from:{approved_sender}` query — unknown senders never enter pipeline

## Built With

- Python 3.13, Pydantic v2, pytest, FastAPI
- Claude Sonnet 4.6 via DataExpert proxy (primary)
- NVIDIA NIM Nemotron Ultra 253B (fallback)
