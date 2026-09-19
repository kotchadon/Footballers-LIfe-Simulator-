# Match Visual System V1 — Design Specification

Date: 2026-09-15
Status: Approved
Branch: `feat/match-visual-system-v1`

Core requirements:
- sealed server-side result remains authoritative;
- visual layer is read-only for gameplay settlement;
- broadcast side-on full-pitch presentation;
- Canvas 2D animated actors + ball, SVG pitch geometry, DOM commentary/controls;
- 22 continuously moving tactical actors;
- articulated 2D player rigs;
- deterministic seeded visual movement;
- approximately 3 real minutes per 90-minute match at 1x;
- 1x / 2x / 4x playback;
- future persistent squad players must fit the same actor contract;
- renderer failure must never block commentary or settlement;
- browser QA is mandatory before merge.
