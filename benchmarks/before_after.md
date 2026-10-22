# Before/After Comparison

## Metrics (3-email inbox: 1 meeting, 1 action, 1 FYI)

| Metric | Before (Inefficient) | After (Optimized) | Reduction |
|--------|---------------------|-------------------|-----------|
| Total tool calls | 19 | 4 | 78.9% |
| Estimated tokens | 2,477 | 102 | 95.9% |
| Gmail searches | 11 | 1 | 90.9% |
| Emails processed | 9 (duplicates) | 3 (unique) | 66.7% |
| Calendar events created | 3 (same meeting 3x) | 1 | 66.7% |
| Policy blocks repeated | 9 | 0 | 100% |
| Verbose reasoning blocks | 12 | 0 | 100% |

## Tool Call Breakdown

### Before (19 tool calls)
```
[TOOL] Gmail:Find Email: query='last 24h', limit=50           # search 1
[TOOL] Gmail:Find Email: query='unread', limit=50             # search 2
[TOOL] Gmail:Find Email: query='from:owner@example.com'       # search 3
[TOOL] Google Calendar:Create Detailed Event                   # meeting (1st time)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 1
[TOOL] Gmail:Send Email: Action Required                       # action (1st time)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 2
[TOOL] Gmail:Send Email: Action Required                       # FYI misclassified
[TOOL] Gmail:Find Email: re-check after email                 # re-check 3
[TOOL] Google Calendar:Create Detailed Event                   # meeting (2nd time - DUPLICATE)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 4
[TOOL] Gmail:Send Email: Action Required                       # action (2nd time - DUPLICATE)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 5
[TOOL] Google Calendar:Create Detailed Event                   # meeting (3rd time - DUPLICATE)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 6
[TOOL] Gmail:Send Email: Action Required                       # action (3rd time - DUPLICATE)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 7
[TOOL] Gmail:Send Email: Action Required                       # FYI misclassified (DUPLICATE)
[TOOL] Gmail:Find Email: re-check after email                 # re-check 8
```

### After (4 tool calls)
```
[TOOL] Gmail:Find Email: query='from:owner@example.com'       # single search
[TOOL] Google Calendar:Create Detailed Event                   # meeting (once)
[TOOL] Gmail:Send Email: Action Required                       # action (once)
[TOOL] Gmail:Send Email: FYI                                   # FYI (once, correctly classified)
```

## Why It's Faster

1. **1 search instead of 3** — combined filters into single query
2. **No re-checking** — process the batch, don't re-scan after each email
3. **No duplicates** — track processed IDs, each email handled exactly once
4. **No policy repetition** — security policy checked once at init, not per email
5. **No verbose reasoning** — direct tool calls, no narration
6. **Better classification** — FYI detection prevents misclassification ("no action needed" ≠ action item)
