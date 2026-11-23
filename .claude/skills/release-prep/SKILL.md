---
name: release-prep
description: Prepare a game for Google Play release with the release-manager subagent - evidence-backed release checklist, versioning, policy compliance (target API, data safety, content rating, privacy policy), release notes and debug-build verification. Ends at the human release gate. Use in the launch stage (can run in parallel with marketing-kit).
argument-hint: "<slug>"
---

# Release preparation

Game: `$ARGUMENTS`

## Steps
1. `python scripts/studio.py check <slug> --fast`. The stage must be `launch`.
2. Dispatch the `release-manager` subagent. Brief: slug, the template [release-checklist-template.md](release-checklist-template.md), and outputs under `release/` (checklist, privacy-policy, data-safety, content-rating, release-notes). Remind it that release signing and upload are human-only.
3. **Verify:** `python scripts/studio.py check <slug>`. Read the checklist: every ticked item has an `evidence:` line. If items remain unticked, decide whether the studio can fix them (dispatch the right subagent) or whether they need the human (report them).
4. Checkpoint: `python scripts/studio.py checkpoint <slug> -m "release-prep: checklist x/y"`, then `python scripts/studio.py advance <slug>`. This stops at the human release gate.
5. Report: checklist status, and the human release procedure:
   1. Review `release/` and `marketing/`.
   2. `python scripts/studio.py approve <slug> release`
   3. With the release keystore env vars set: `python scripts/studio.py build <slug> --release --aab`
   4. Upload to the Play Console (internal testing track first), then complete the Data safety and content-rating forms using the prepared answers.
