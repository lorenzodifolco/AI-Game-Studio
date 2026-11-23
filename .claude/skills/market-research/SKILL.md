---
name: market-research
description: Research the Android mobile games market and identify commercial opportunities for the studio, using parallel market-analyst subagents. Produces studio/research/<date>-<focus>/report.md. Use when research is missing or stale, or when asked for market or competitor analysis.
argument-hint: "[focus, e.g. broad | puzzle | idle | 'cozy games']"
---

# Market research

Focus: `$ARGUMENTS` (empty = `broad`: scan all genres compatible with `studio/brief.md`).
Today: !`date +%F`

## Steps
1. Set `DIR = studio/research/<today>-<focus-slug>/`. Read `studio/brief.md`. List earlier reports (`ls studio/research`) so the briefs can say what is already known.
2. **In parallel** (one message), dispatch three `market-analyst` subagents. Each brief gives the focus, the constraints from the brief, the date, and its output file:
   - **A: Trends and genres** → `DIR/trends.md`: growing, stable and declining subgenres on Google Play (last 12–18 months); new mechanics and hybrids; seasonal or cultural themes; what's breaking out organically.
   - **B: Competitive landscape** → `DIR/competitors.md`: for 4–6 promising subgenres, the top titles and their hooks, store-page tactics, rating complaints (unmet needs in 1–3★ reviews), supply quality and saturation.
   - **C: Economics** → `DIR/economics.md`: monetization models per subgenre (rewarded and interstitial ads, IAP, premium), benchmark D1/D7/D30 retention, ARPDAU/eCPM ranges, organic discoverability, and what's realistic for a zero-UA-budget studio.
3. When all three return, dispatch one `market-analyst` to synthesize `DIR/report.md` from the A–C files using [report-template.md](report-template.md). The opportunity table must be ranked and must respect `studio/brief.md`.
4. **Verify** yourself: `DIR/report.md` exists, contains the `## Opportunities` table with at least 3 rows, and every quantitative claim has a source or a `~` estimate marker. If not, send it back once with the specific gaps.
5. Checkpoint: `python scripts/studio.py checkpoint studio -m "research: <focus>"`.
6. Report: the top 3 opportunities (one line each) and the report path. The next step is usually `/ideate`.
