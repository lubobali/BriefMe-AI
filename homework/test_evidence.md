# Test Evidence

All 35 tests pass. Run with: `python -m pytest briefme/test_briefme.py -v`

## Test Case 1: Meeting Request → Calendar Event

**Input:** "Can you schedule a 30-minute meeting next Tuesday at 2pm?"

**Mock heartbeat result:**
```
[TOOL] Google Calendar:Create Detailed Event:
  title='Meeting: Schedule a meeting'
  start=next Tuesday 2:00 PM
  end=next Tuesday 2:30 PM
  attendee=owner@example.com
```

**LLM classifier result (real API call):**
```json
{
  "category": "meeting",
  "extracted_date": "next Tuesday at 2:00 PM",
  "confidence": 0.95
}
```

**Tests:**
- `test_meeting_creates_calendar_event` — PASSED (1 calendar event created)
- `test_classify_meeting` — PASSED (category=meeting, date extracted, confidence >= 0.7)

---

## Test Case 2: Action Item → Summary Email

**Input:** "Please remind me to submit the expense report by Friday."

**Mock heartbeat result:**
```
[TOOL] Gmail:Send Email:
  to=owner@example.com
  subject='Action Required'
  body='Action needed: Quick reminder — Please remind me to submit the expense report by Friday.'
```

**LLM classifier result (real API call):**
```json
{
  "category": "action",
  "extracted_action": "Submit the expense report by Friday",
  "confidence": 0.92
}
```

**Tests:**
- `test_action_sends_email` — PASSED (1 action email sent)
- `test_classify_action` — PASSED (category=action, action extracted, confidence >= 0.7)

---

## Test Case 3: FYI → Brief Notification

**Input:** "No action needed, just sharing context."

**Mock heartbeat result:**
```
[TOOL] Gmail:Send Email:
  to=owner@example.com
  subject='FYI'
  body='FYI: FYI budget note — No action needed, just sharing context.'
```

**LLM classifier result (real API call):**
```json
{
  "category": "fyi",
  "risk_level": "none",
  "confidence": 0.90
}
```

**Tests:**
- `test_fyi_sends_email` — PASSED (1 FYI email sent)
- `test_classify_fyi` — PASSED (category=fyi, risk_level=none/low, confidence >= 0.7)

---

## Test Case 4: Empty Inbox → HEARTBEAT_OK

**Input:** No emails in inbox.

**Mock heartbeat result:**
```
Status: HEARTBEAT_OK
Tool calls: 1 (just the search)
Actions: []
```

**Tests:**
- `test_empty_inbox_returns_heartbeat_ok` — PASSED (returns "HEARTBEAT_OK")

---

## Efficiency Tests

- `test_single_inbox_search` — PASSED (exactly 1 Gmail search, not 3)
- `test_no_duplicate_processing` — PASSED (3 action tools for 3 emails, not 9)
- `test_total_tool_calls_reduced` — PASSED (4 tool calls, not 19)
- `test_token_usage_reduced` — PASSED (102 tokens, not 2,477)

---

## Full Test Output

```
35 passed in 7.56s

TestSchemaValidation (10 tests) — Pydantic model validation
TestGuardrails (8 tests) — PII redaction + prompt injection detection
TestLLMClient (1 test) — Real DataExpert API call
TestClassifier (4 tests) — Real LLM classification for all 4 email types
TestHeartbeat (8 tests) — Optimized workflow with mock tools
TestAPI (4 tests) — FastAPI endpoint responses
```
