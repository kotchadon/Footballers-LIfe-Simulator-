# Match Cockpit V2

Baseline: supplied clean archive of `50200071fa9d3cec6e98dd293ffac2e0fc9fc681`
on `feat/3d-match-flow-polish`. The football-flow engine, choreography, stadium
asset, renderer, shared clock, fallback and career-player marker are unchanged.

The match page is now a viewport workspace: compact home/away scorebar and clock,
playback/view/camera toolbar, flexible pitch, commentary rail, persistent career
player strip and internally scrolling squad tabs. Full-time opens no dialog and
moves no page; the report button explicitly opens the existing full report.
Escape closes it and restores focus. The existing career portrait is reused.

## Data contract

- `match_cockpit.cockpit_context` projects only initial actor identity, side,
  shirt number, role and selection from the existing visual plan. Sealed events,
  attributes and outcomes are not embedded in this projection.
- The same revealed-event callback that already waits for goal choreography
  updates commentary and player state. Goals, assists and cards retain the
  existing live counters; final values come from the settlement response.
- Minutes are elapsed revealed match minutes between introduction and removal.
  Substitution, sending off and final settlement stop accumulation. Treatment
  alone does not imply removal. Rating remains a dash until settlement.
- Squad tabs are explicitly **starting** match XIs. The source only records the
  career player's bench selection, not a complete substitutes roster. The bench
  panel says so; it does not fabricate identities or outgoing substitutions.
- Live pressure/territory remain presentation cues. No live passing/possession
  percentages or invented performance ratings are introduced.
- Commentary follows within 36px of the bottom. Reading older events suspends
  following; a new-event count and Jump to live restore it. Only the latest-event
  region announces changes, avoiding replaying the entire history to readers.

## Validation

Python route/privacy tests, Node state and mounted-interaction tests cover
minutes, substitution, dismissal, duplicate events, injury, unavailable players,
feed following, squad keyboard navigation, final stats and explicit report focus.
Existing Python and Node regressions remain mandatory in the installer.

`node tools/check_match_cockpit.cjs` is optional browser acceptance using an
existing Playwright installation and Chromium. It starts a disposable database,
checks all four requested desktop sizes and 390x844, both renderers, keyboard
tabs, full time, report focus, reload and missing-model fallback. Screenshots and
results go to `.upgrade-backups/cockpit-browser-qa`. It never opens the real save.

Chromium could not start in the build environment, so browser screenshots,
pixel quality and real M3 Air performance are **not verified** here. Desktop
layout is designed for the requested sizes; narrow landscape/very short windows
allow page scrolling rather than clipping controls. Portrait mobile keeps the
pitch, player strip and smaller internally scrolling rails in the viewport.

No application dependencies, database migrations, external assets, media jobs
or paid Higgsfield generation were added. No GitHub access is needed to install.

## Design references

- W3C APG tabs: https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
  Roving focus, arrow/Home/End navigation and associated panels.
- Three.js responsive manual: https://threejs.org/manual/pages/responsive.html
  CSS owns the viewport; the existing ResizeObserver keeps canvas dimensions
  and camera aspect synchronized.
- Football Manager UI overview:
  https://www.footballmanager.com/fm26/features/fm26s-reimagined-user-interface
  Compact persistent summaries with detail available without leaving the match.

## Installation and recovery

Run the supplied installer from the repository using `.venv/bin/python`.
It requires the exact baseline HEAD, original branch, a clean tree and matching
source hashes. It creates `feat/match-cockpit-v2`, backs up every changed file in
the Git directory, applies the bundle, runs Python/Node checks and commits only
the bundle paths. It neither pushes nor touches career databases or 3D assets.
If validation fails before commit, it restores its own files and returns to the
original branch when safe. If unrelated concurrent edits appear, it stops and
retains the backups instead of overwriting them. After success, switching back
to `feat/3d-match-flow-polish` restores the baseline UI without losing this work.
