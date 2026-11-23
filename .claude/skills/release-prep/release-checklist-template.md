# Release Checklist: <Title> v<version-name> (<version-code>)
Tick an item only after verifying it. Add `- evidence: <command output / file:line / URL>` under each ticked item.

## Build
- [ ] QA verdict is PASS for this exact code (`qa/qa-report.md`, commit hash)
- [ ] All tests pass (`python scripts/studio.py test <slug>`)
- [ ] Debug export succeeds (`python scripts/studio.py build <slug>`), or BLOCKED is documented with the environment reason
- [ ] `version/code` incremented and `version/name` set in `project/export_presets.cfg`
- [ ] Package name final and correct (`package/unique_name`)
- [ ] Target SDK meets the current Google Play requirement (cite the source URL)
- [ ] arm64-v8a included; no debug-only features or logging enabled
- [ ] Permissions minimal and justified

## Store compliance
- [ ] Privacy policy drafted (`release/privacy-policy.md`) and matches actual data use
- [ ] Data safety answers prepared (`release/data-safety.md`)
- [ ] Content rating answers prepared (`release/content-rating.md`)
- [ ] Ads/IAP disclosures consistent with the build (or none present)
- [ ] Store listing complete (`marketing/store-listing.md`), claims match the build
- [ ] No third-party IP or trademarks in the build or listing

## Release content
- [ ] Release notes written (`release/release-notes.md`)
- [ ] Icon and feature-graphic sources exist, or a human asset task is listed below

## Human actions (not tracked by the checklist)
- Approve the gate: `python scripts/studio.py approve <slug> release`
- Build the signed AAB with the release keystore: `python scripts/studio.py build <slug> --release --aab`
- Host the privacy policy at a public URL; create the Play Console app; upload to the internal testing track; fill in the forms; roll out.
