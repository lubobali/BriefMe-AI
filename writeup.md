# BriefMe-AI — Token Efficiency Optimization Writeup

## 1. Before/After Spec

### Original (Inefficient) Behavior

On every heartbeat the agent:

1. Searches inbox **3 times** with overlapping filters ("last 24h", "unread", "from sender") — returns duplicate emails
2. Fetches up to **50 emails** regardless of relevance
3. For each email (including duplicates), generates **3 separate summaries**: full paraphrase, executive summary, risk assessment
4. **Repeats the full security policy** (~500 tokens) with every email processed
5. **Re-checks inbox** after handling each email (N extra API calls)
6. Outputs **verbose reasoning** before every tool call
7. **No dedup** — the same meeting email creates 3 calendar events

Result: 19 tool calls, 2,477 estimated tokens for 3 emails.

### Updated (Optimized) Behavior

See `homework/HEARTBEAT_OPTIMIZED.md` for the full prompt.

1. **1 search** combining all filters → `from:{sender}`, limit 10
2. **Batch process** — no re-checking inbox between emails
3. **1 classification per email** — no separate paraphrase/executive/risk
4. **Security policy once** at init, not repeated per email
5. **Dedup via processed_ids** — each email handled exactly once
6. **No verbose reasoning** — direct tool calls
7. **Better FYI detection** — checks "no action" before "action" keyword

Result: 4 tool calls, 102 estimated tokens for 3 emails.

---

## 2. Optimization Rationale

| Change | What | Why it reduces overhead |
|--------|------|----------------------|
| 1 search → 1 | Combined 3 overlapping queries into 1 | 3 API calls → 1. Eliminates duplicate emails in results. |
| No re-check | Removed inbox scan after each email | N extra API calls → 0. New emails caught on next heartbeat. |
| No 3 summaries | Removed paraphrase + executive + risk | 3 LLM calls per email → 0 (keyword) or 1 (LLM classifier). |
| Policy once | Security text at init, not per email | ~500 tokens x N → 0 tokens per email. |
| Dedup | Track processed IDs in a set | 9 duplicate actions → 3 unique actions. |
| No verbose reasoning | Direct tool calls | ~30 tokens x 12 blocks → 0. |
| FYI-first classification | Check "fyi"/"no action" before "action" | Fixes misclassification of FYI emails containing "action" keyword. |

---

## 3. Evidence

### Tool-Call Count

| | Before | After | Reduction |
|---|---|---|---|
| Total tool calls | 19 | 4 | **78.9%** |
| Gmail searches | 11 | 1 | **90.9%** |

### Token Estimate

| | Before | After | Reduction |
|---|---|---|---|
| Estimated tokens | 2,477 | 102 | **95.9%** |

### Test Outcomes

| Test Case | Input | Expected | Result |
|-----------|-------|----------|--------|
| Meeting request | "Schedule 30 min next Tuesday at 2pm" | Calendar event created | PASSED — 1 event created (not 3) |
| Action item | "Please remind me to submit expense report by Friday" | Action Required email sent | PASSED — 1 email sent |
| FYI message | "No action needed, just sharing context" | FYI email sent | PASSED — correctly classified as FYI (not action) |
| No new email | Empty inbox | HEARTBEAT_OK | PASSED — returned HEARTBEAT_OK |

### All Tests (44 total)

- Schema validation: 10 tests (Pydantic accept/reject)
- PII redaction: 8 tests (email, phone, IP, API key, prompt injection)
- LLM client: 1 test (real DataExpert API call)
- LLM classifier: 4 tests (real API — meeting, action, FYI, prompt injection)
- Heartbeat workflow: 8 tests (all 4 cases + efficiency metrics)
- FastAPI API: 4 tests (health, mock heartbeat, metrics, compare endpoint)
- Edge cases: 6 tests (non-approved sender, rate limit, mixed intent, FYI regression, security policy)
- E2E: 3 tests (classifier → calendar with real LLM, ambiguous date, real token usage capture)

Run: `python -m pytest briefme/test_briefme.py -v` → 44 passed in 7.84s

See `homework/test_run_output.log` for full captured test output.

---

## 4. Edge-Case Handling

| Edge Case | Handling |
|-----------|---------|
| Ambiguous date ("next week") | LLM classifier extracts what it can, flags low confidence. Calendar event created with placeholder. |
| Malformed email (empty body) | Classifier works from subject alone. Falls through to FYI if no keywords match. |
| Duplicate emails | `_processed_ids` set tracks handled IDs. Duplicates silently skipped. |
| Mixed intent (meeting + action) | Meeting keywords checked first — meetings take priority per prompt instructions. |
| Prompt injection | `check_prompt_injection()` scans for injection patterns. Flagged emails classified as `skip` with `risk_level: high`. No LLM call made. |
| Non-approved sender | Search query filters by `from:{approved_sender}`. Unknown senders never enter pipeline. |

---

## 5. Safety Posture

| Control | Before | After | Change |
|---------|--------|-------|--------|
| Policy enforcement | Repeated per email (wasteful but present) | Checked once at init | Unchanged — same rules, less token waste |
| PII redaction | Not present | Added — redacts email, phone, IP, API keys | **Improved** |
| Prompt injection defense | Not present | Added — pattern detection before LLM | **Improved** |
| Duplicate prevention | Not present | Added — processed_ids tracking | **Improved** |
| Rate limiting | Fetch 50 | Fetch 10 max | **Improved** |

Safety posture is **improved**, not weakened.
