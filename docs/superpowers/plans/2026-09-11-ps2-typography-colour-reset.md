# PS2 / PSP Typography and Colour Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply one cohesive early-2000s console sports-game typography and colour system across the application without changing gameplay or V5 portrait internals.

**Architecture:** Keep `style.css` as the legacy structural layer and add `theme-ps2.css` as the final presentation layer loaded after it by `base.html`. The new file centralizes typography roles, palette, navigation, surfaces, controls, tables, reports, page compatibility, responsive behavior, and accessibility.

**Tech Stack:** Flask/Jinja, CSS, pytest.

**Spec:** `docs/superpowers/specs/2026-09-11-ps2-typography-colour-reset-design.md`

## Global Constraints

- Work only on `ui/ps2-typography-colour-reset`.
- Never patch `main` directly.
- No external fonts or remote CSS.
- No gameplay, save, API, DB, JS, or security behavior changes.
- Do not modify `app/player_visuals.py`, `_player_visual.html`, or `player_portrait_v5/`.
- Use `.venv/bin/python -m pytest -q`.
- Run `git diff --check`.
- Browser QA is mandatory before committing production theme changes.

---

### Task 1: Add visual-system regression tests

**Files:**
- Create: `tests/test_ps2_visual_system.py`

**Interfaces:**
- Consumes: `base.html`, V5 renderer, static CSS.
- Produces: tests covering loading order, local font stacks, palette, cross-page scope, V5 isolation, and accessibility.

- [ ] Write the regression test file.
- [ ] Run `.venv/bin/python -m pytest -q tests/test_ps2_visual_system.py`.
- [ ] Confirm RED because `theme-ps2.css` is not installed yet.

### Task 2: Install canonical theme layer

**Files:**
- Create: `app/static/theme-ps2.css`
- Modify: `app/templates/base.html`

**Interfaces:**
- Consumes: existing DOM/classes.
- Produces: a single final presentation layer loaded after legacy `style.css`.

- [ ] Create palette/font tokens.
- [ ] Apply body, heading, UI, navigation, panel, control, table, report, and page compatibility styling.
- [ ] Load the stylesheet immediately after `style.css` in `base.html`.
- [ ] Keep V5 portrait internal selectors untouched.

### Task 3: Verify

**Files:**
- No extra production files.

**Interfaces:**
- Consumes: complete theme layer.
- Produces: browser-QA-ready branch.

- [ ] Run `.venv/bin/python -m pytest -q tests/test_ps2_visual_system.py` and confirm GREEN.
- [ ] Run `.venv/bin/python -m pytest -q` and confirm the full suite passes.
- [ ] Run `git diff --check`.
- [ ] Confirm `git diff --quiet HEAD -- app/player_visuals.py app/templates/_player_visual.html app/templates/player_portrait_v5`.
- [ ] Browser-QA Dashboard, Match Centre, Training, Market, Finance, World, Calendar, reports, and navigation.
- [ ] Commit only after visual approval.
