---
name: qa
description: Full QA pass for a game with the qa-tester subagent (tests, build, spec compliance, code review, Android readiness), followed by a bounded fix loop with the godot-engineer subagent until the verdict is PASS. Use when a game is in the qa stage.
argument-hint: "<slug>"
---

# QA stage

Game: `$ARGUMENTS`

## Steps
1. `python scripts/studio.py check <slug> --fast`. The stage must be `qa`.
2. Dispatch the `qa-tester` subagent in **full mode**. Brief: slug; the report goes to `qa/qa-report.md` using [qa-report-template.md](qa-report-template.md). Severity: P0 = crash or data loss or blocker, P1 = core feature broken or spec violated, P2 = minor, P3 = cosmetic.
3. If the verdict is `FAIL`, run a fix loop (at most **3 cycles**):
   - Dispatch the `godot-engineer` subagent with the P0/P1 bug list (ids and repro steps). Each fix needs a regression test.
   - Verify that `python scripts/studio.py test <slug>` passes, then checkpoint `"qa: fix cycle <n>"`.
   - Re-dispatch the `qa-tester` subagent to re-verify the bug ids and re-issue the verdict.
   - If it still fails after 3 cycles, stop and report to the user with the remaining bugs.
4. **Verify:** `python scripts/studio.py check <slug>` shows every criterion PASS (tests pass and the report says `Verdict: PASS`).
5. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "qa: PASS"`, then `python scripts/studio.py advance <slug>`.
6. Report: the verdict, bug counts, and any P2/P3 bugs deferred to post-launch.
