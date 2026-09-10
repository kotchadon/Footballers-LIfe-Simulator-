# Player Visual Identity Implementation Plan

> **For agentic workers:** Execute task-by-task with TDD and reviewer checkpoints.

**Goal:** Add a persistent procedural footballer visual shared across career surfaces without affecting simulation or saves.

**Architecture:** `app/player_visuals.py` creates a pure normalized visual model. `_player_visual.html` renders only that model. Dashboard, Match Centre and Training reuse the same component with context-specific sizing/state.

**Tech Stack:** Python, Flask, SQLite row mappings, Jinja, inline SVG, CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-player-visual-identity-design.md`

## Global Constraints
- Work only on `feat/player-visual-identity`.
- No database migration in V1.
- No external asset/API dependency.
- No gameplay mutation.
- TDD before each production slice.
- Run `.venv/bin/python -m pytest -q`.
- Browser verification required before completion.

---

### Task 1: Deterministic visual model
**Files:** create `app/player_visuals.py`, create `tests/test_player_visuals.py`.
**Produces:** `build_player_visual(career, *, selection_status=None, context="default") -> dict`.
- RED: deterministic identity/state tests fail because module is absent.
- GREEN: implement BLAKE2-based identity, kit projection, normalized state and safe defaults.
- Verify focused tests, full suite and `git diff --check`.
- Commit as `feat: add deterministic player visual model`.

### Task 2: Reusable SVG renderer
**Files:** create `app/templates/_player_visual.html`, create `tests/test_player_visual_templates.py`, modify `app/static/style.css`.
- RED: template integration/security/accessibility tests.
- GREEN: layered procedural SVG with trait-specific geometry and no unsafe markup.
- Add reduced-motion handling.
- Verify focused/full tests and diff check.
- Commit as `feat: add procedural footballer renderer`.

### Task 3: Dashboard integration
**Files:** modify `app/routes.py`, `app/templates/dashboard.html`, integration tests.
- RED: Dashboard must receive/render visual model.
- GREEN: add large portrait to existing player hero; preserve existing controls/metrics.
- Browser verify normal + low-fitness/injury state.
- Commit as `feat: integrate player identity on dashboard`.

### Task 4: Match Centre integration
**Files:** modify `app/routes.py`, `app/templates/match.html`, integration tests.
- RED: Match Centre must reuse same identity and normalize authoritative selection status.
- GREEN: compact match portrait; no replay or settlement coupling.
- Browser verify starter/substitute/not-selected where reproducible.
- Commit as `feat: integrate player identity in match centre`.

### Task 5: Training context and final hardening
**Files:** reuse Dashboard training region or training surface, CSS/tests as required.
- RED: state/context coverage.
- GREEN: context-specific presentation without duplicating renderer.
- Verify targeted suite, full suite, `git diff --check`, hard refresh and responsive QA.
- Run completion verification before merge.

