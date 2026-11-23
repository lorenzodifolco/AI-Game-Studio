# QA Report: <Title> (<YYYY-MM-DD>, cycle <n>)

Verdict: PASS | FAIL
(FAIL if any P0/P1 bug is open, tests fail, or the build fails for a reason in the game itself.)

## Summary
Build, test result line, and the overall quality impression in 3 bullets.

## Automated Results
- Tests: `RESULT: x passed, y failed`
- Debug build: OK | FAILED | BLOCKED (environment: reason)

## Spec Compliance
| Backlog item | Acceptance criterion met? | Evidence (test or file:line) |
|---|---|---|

## Bugs
| ID | Sev | Title | Repro steps | Expected | Actual | Location |
|---|---|---|---|---|---|---|

## Android Readiness
- [ ] Portrait layout at 16:9 and 20:9 · [ ] touch targets ≥ 48 px · [ ] back button · [ ] pause on focus loss · [ ] save on exit · [ ] no unneeded permissions

## Code Health
Debug prints, TODOs, hard-coded tunables, per-frame allocations, GDScript 3 leftovers.

## Deferred
P2/P3 items accepted for post-launch, with reasons.
