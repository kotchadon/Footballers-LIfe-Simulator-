# Player Progression V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace global career XP/random attribute upgrades with persistent per-attribute development meters driven by training and actual match performance, while preserving sealed-match/idempotent settlement.

**Architecture:** Add a focused `app/progression.py` domain module for all progression math: upgrade costs, training allocation, match-action XP, rating multiplier, 75-XP cap, and conversion of XP meters into integer attributes. Persist six XP meters on `player_attributes`. `app/services.py` remains the orchestration layer: it feeds authoritative match metrics/training context into progression functions, stores the planned result in the sealed snapshot, and commits it once during settlement.

**Tech Stack:** Python 3, Flask, SQLite, pytest, Jinja, vanilla JavaScript/CSS.

**Spec:** `docs/superpowers/specs/2026-09-20-player-progression-v2-design.md`

## Global Constraints

- Property-market work is out of scope.
- Six persistent meters: `pace_xp`, `shooting_xp`, `passing_xp`, `dribbling_xp`, `defending_xp`, `physical_xp`.
- No random attribute roulette.
- OVR itself never earns XP; OVR is recalculated from attributes.
- No match-by-match attribute decreases.
- Non-selection and unused bench produce zero match XP, never negative XP.
- Injury never removes XP earned from the match performance before the injury.
- Recovery focus awards zero attribute XP.
- Match-action XP total is capped at 75 after the rating multiplier.
- Existing match settlement remains idempotent.
- Existing security protections remain unchanged.
- Existing saves migrate legacy `careers.xp` once and only once.
- Use `.venv/bin/python -m pytest -q`, never bare `pytest`.
- Every production behavior change follows RED → confirm expected fail → minimal GREEN.
- Do not modify `main`; work only on `feat/player-progression-v2`.

## Review Focus

1. **Existing-save migration repeated on startup** — legacy XP must move once, never duplicate.
2. **Match completion retried/refreshed** — progression must settle exactly once with no duplicate XP/attribute upgrades.
3. **75-XP scaling with fractional categories** — final distribution must be deterministic and sum to at most 75.
4. **Potential reached mid-conversion** — upgrades stop immediately without discarding remaining XP meters.
5. **Non-selection/injury/recovery combinations** — no negative XP and no accidental training award while unavailable.

---

### Task 1: Persistent attribute XP schema + save migration

**Files:**
- Modify: `app/schema.sql`
- Modify: `app/db.py`
- Modify: `app/services.py`
- Test: `tests/test_player_progression.py`

**Interfaces:**
- Produces persistent columns on `player_attributes`:
  - `pace_xp INTEGER NOT NULL DEFAULT 0`
  - `shooting_xp INTEGER NOT NULL DEFAULT 0`
  - `passing_xp INTEGER NOT NULL DEFAULT 0`
  - `dribbling_xp INTEGER NOT NULL DEFAULT 0`
  - `defending_xp INTEGER NOT NULL DEFAULT 0`
  - `physical_xp INTEGER NOT NULL DEFAULT 0`
  - `legacy_xp_migrated INTEGER NOT NULL DEFAULT 0`
- `get_active_career()` must expose all six `*_xp` fields.

- [ ] **Step 1: Write failing migration tests**

Add `tests/test_player_progression.py` with tests that:
- create an old-style career with legacy `careers.xp=47`;
- set training focus to `passing`;
- run save migration;
- assert `passing_xp == 47`, other XP meters are `0`, `careers.xp == 0`, and `legacy_xp_migrated == 1`;
- run migration again and assert the same values remain unchanged;
- verify balanced/recovery fallback migrates the full remainder to the highest-weight positional attribute.

- [ ] **Step 2: Verify RED**

Run:

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "migration"
```

Expected: FAIL because the new columns/migration behavior do not exist.

- [ ] **Step 3: Add schema columns**

Extend `player_attributes` in `app/schema.sql`:

```sql
pace_xp INTEGER NOT NULL DEFAULT 0,
shooting_xp INTEGER NOT NULL DEFAULT 0,
passing_xp INTEGER NOT NULL DEFAULT 0,
dribbling_xp INTEGER NOT NULL DEFAULT 0,
defending_xp INTEGER NOT NULL DEFAULT 0,
physical_xp INTEGER NOT NULL DEFAULT 0,
legacy_xp_migrated INTEGER NOT NULL DEFAULT 0,
```

- [ ] **Step 4: Add idempotent migration support**

In `app/db.py`, introduce `PLAYER_ATTRIBUTE_COLUMNS` and call `_add_missing_columns(db, "player_attributes", PLAYER_ATTRIBUTE_COLUMNS)` before iterating careers.

During `migrate_existing_save(db)`:
- skip rows where `legacy_xp_migrated = 1`;
- read legacy `careers.xp`;
- choose target:
  - direct focus if one of six attributes;
  - otherwise highest `POSITION_WEIGHTS[position]`;
- add the legacy remainder once to `<target>_xp`;
- set `legacy_xp_migrated=1`;
- set `careers.xp=0`.

Use only deterministic selection; no RNG.

- [ ] **Step 5: Expose XP meters from active career**

Extend the `get_active_career()` SELECT in `app/services.py` with:

```sql
pa.pace_xp, pa.shooting_xp, pa.passing_xp,
pa.dribbling_xp, pa.defending_xp, pa.physical_xp
```

- [ ] **Step 6: Verify GREEN**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "migration"
```

- [ ] **Step 7: Run regression suite**

```bash
.venv/bin/python -m pytest -q
```

- [ ] **Step 8: Commit**

```bash
git add app/schema.sql app/db.py app/services.py tests/test_player_progression.py
git commit -m "feat: persist attribute development xp"
```

---

### Task 2: Pure progression engine — costs, conversion, deterministic allocation

**Files:**
- Create: `app/progression.py`
- Modify: `tests/test_player_progression.py`

**Interfaces:**
- Produces:
  - `ATTRIBUTES: tuple[str, ...]`
  - `upgrade_cost(attribute_value: int, overall: int, potential: int) -> int`
  - `largest_remainder_scale(values: dict[str, float], target_total: int) -> dict[str, int]`
  - `apply_attribute_xp(*, attributes: dict[str,int], meters: dict[str,int], gains: dict[str,int], position: str, potential: int) -> dict`
- Return shape from `apply_attribute_xp`:

```python
{
    "attributes": {...},
    "meters": {...},
    "overall": 64,
    "upgrades": [
        {"attribute": "passing", "from": 61, "to": 62},
    ],
}
```

- [ ] **Step 1: Write failing cost tests**

Tests must assert:

```python
assert upgrade_cost(55, 58, 88) == 48
assert upgrade_cost(65, 65, 88) == 68
assert upgrade_cost(75, 75, 88) == 105
assert upgrade_cost(82, 82, 88) == 174
assert upgrade_cost(86, 86, 88) == 300
```

These values follow the spec's base-cost bands and potential-gap multipliers with Python `round()`.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "upgrade_cost"
```

Expected: import/function missing.

- [ ] **Step 3: Implement `upgrade_cost` minimally**

Implement exact bands:

```python
def _base_cost(value):
    if value < 60:
        return 60
    if value < 70:
        return 75
    if value < 80:
        return 105
    if value < 85:
        return 145
    if value < 90:
        return 200
    return 280
```

Potential multiplier:
- gap >=25 → `.80`
- gap >=15 → `.90`
- gap >=8 → `1.00`
- gap >=3 → `1.20`
- otherwise `1.50`

- [ ] **Step 4: Add deterministic largest-remainder tests**

Test values that require rounding:

```python
scaled = largest_remainder_scale(
    {"passing": 30.4, "shooting": 20.2, "dribbling": 15.1, "physical": 9.3},
    75,
)
assert sum(scaled.values()) == 75
assert scaled == {
    "passing": 30,
    "shooting": 20,
    "dribbling": 15,
    "physical": 10,
}
```

Also test an input sum below cap returns rounded deterministic values without inflating to target.

- [ ] **Step 5: Implement `largest_remainder_scale`**

Requirements:
- never creates negative values;
- if raw total <= target, round each value deterministically and do not pad to target;
- if raw total > target, scale proportionally;
- floor scaled values;
- distribute remaining integer points by descending fractional remainder, breaking ties by `ATTRIBUTES` order.

- [ ] **Step 6: Add conversion tests**

Cover:
- meter crossing one threshold;
- remainder carry-over;
- one large gain crossing multiple thresholds with changing costs;
- exact stop when recalculated OVR reaches potential;
- meter remainder retained when capped.

- [ ] **Step 7: Implement `apply_attribute_xp`**

Implementation rules:
- copy input dicts;
- add non-negative gains to meters;
- process attributes in stable `ATTRIBUTES` order;
- before every +1, recalculate overall and stop all conversion if OVR >= potential;
- compute the current cost using the latest attribute value and latest overall;
- cap integer attributes at 99;
- recalculate final overall with existing `calculate_overall`.

To avoid a circular import, move `calculate_overall` into `app/progression.py` or import a lower-level pure implementation from `app/engine.py`. Prefer one canonical calculation only; do not duplicate formulas.

- [ ] **Step 8: Verify focused GREEN**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "upgrade_cost or remainder or attribute_xp"
```

- [ ] **Step 9: Full suite + commit**

```bash
.venv/bin/python -m pytest -q
git add app/progression.py app/engine.py tests/test_player_progression.py
git commit -m "feat: add deterministic attribute progression engine"
```

---

### Task 3: Match-action XP calculation

**Files:**
- Modify: `app/progression.py`
- Modify: `tests/test_player_progression.py`

**Interfaces:**
- Produces:
  - `match_development_xp(performance: dict) -> dict[str,int]`
  - `rating_multiplier(rating: float) -> float`

- [ ] **Step 1: Write failing passing/shooting tests**

Passing formula:
- completed pass `0.20`
- key pass `3`
- assist `8`
- 20+ attempts + 85% accuracy `+5`
- 20+ attempts + 92% accuracy additional `+3`
- pre-rating cap `28`

Shooting formula:
- shot `1`
- shot on target `2`
- goal `10`
- 2+ shots + 50% accuracy `+3`
- pre-rating cap `24`

Use real performance dictionaries shaped like `simulate_player_performance()` output.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "match_passing or match_shooting"
```

- [ ] **Step 3: Implement Passing and Shooting**

Read metrics from `performance["metrics"]`; read goals, assists, rating, minutes from top-level performance.

No XP for zero-minute appearances.

- [ ] **Step 4: Add failing Dribbling/Defending/Physical/Pace tests**

Dribbling:
- completed dribble `2.5`
- 3+ attempts and >=60% success `+4`
- progressive action `0.35`
- cap `20`

Defending:
- tackle won `3`
- duel won `1`
- 2+ tackles and >=70% tackle success `+4`
- cap `22`

Physical:
- `floor(minutes/10)`
- duel won `0.6`
- +2 for 90 minutes
- cap `15`

Pace:
- progressive action `1`
- completed dribble `0.5`
- +2 for 60+ minutes
- cap `12`

- [ ] **Step 5: Implement remaining categories**

Keep calculations pure and side-effect free.

- [ ] **Step 6: Add rating/cap tests**

Assert:
- rating <6.5 → `.90`
- 6.5–7.49 → `1.00`
- 7.5–8.49 → `1.10`
- 8.5+ → `1.20`
- high rating does not create XP for a zero raw category;
- after multiplier, total is <=75;
- a deliberately huge performance is deterministically scaled to exactly 75.

- [ ] **Step 7: Implement rating + 75 cap**

Apply multiplier to each category's already-earned raw XP, then use deterministic scaling if total exceeds 75.

- [ ] **Step 8: Add non-selection/injury tests**

Assert:
- `minutes == 0` returns six zeros;
- `performance["injured"] == True` with minutes/actions still returns earned XP;
- bad rating never produces negative XP.

- [ ] **Step 9: Verify + commit**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py
.venv/bin/python -m pytest -q
git add app/progression.py tests/test_player_progression.py
git commit -m "feat: derive development xp from match performance"
```

---

### Task 4: Training XP allocation and calendar integration

**Files:**
- Modify: `app/progression.py`
- Modify: `app/services.py`
- Modify: `tests/test_player_progression.py`
- Modify: `tests/test_calendar_economy.py`

**Interfaces:**
- Produces:
  - `training_development_xp(*, focus: str, position: str, season_phase: str, minutes: int, unavailable_injured: bool) -> dict[str,int]`

- [ ] **Step 1: Write failing training-allocation tests**

Assert normal healthy full week:
- selected focus gets 20;
- two support stats get 5 each;
- total 30.

Assert workload totals:
- >=60 minutes → 21 total;
- 30–59 → 24 total;
- 1–29 → 27 total;
- zero minutes → 30 total.

Assert preseason multiplies total by 1.25:
- unused player = deterministic total 38 after rounding.

Assert:
- recovery = all zeros;
- player unavailable through injury = all zeros.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "training"
```

- [ ] **Step 3: Implement training allocation**

Use the fixed support pairs from the spec. For balanced focus:
- read `POSITION_WEIGHTS[position]`;
- allocate exactly the target total using `largest_remainder_scale`.

- [ ] **Step 4: Replace free-week global XP**

Refactor `_apply_free_week_development()`:
- query current attributes + six XP meters;
- call `training_development_xp(..., minutes=0, unavailable_injured=...)`;
- call `apply_attribute_xp`;
- persist all six attributes and meters in one UPDATE;
- set `careers.overall` from progression result;
- leave legacy `careers.xp=0`;
- preserve existing fitness/morale/stress effects.

- [ ] **Step 5: Verify free-week behavior**

Tests:
- non-selected healthy week actually advances the focused meter;
- threshold crossing raises the focused stat;
- recovery never changes meters;
- injured unavailable week never changes meters;
- repeated calendar calls remain protected by existing week advancement rules.

- [ ] **Step 6: Run regressions + commit**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py tests/test_calendar_economy.py
.venv/bin/python -m pytest -q
git add app/progression.py app/services.py tests/test_player_progression.py tests/test_calendar_economy.py
git commit -m "feat: make training drive attribute progression"
```

---

### Task 5: Sealed match snapshot + idempotent progression settlement

**Files:**
- Modify: `app/services.py`
- Modify: `tests/test_match_integrity.py`
- Modify: `tests/test_player_progression.py`

**Interfaces:**
- Match snapshot `post_match["development"]` changes from generic XP to:

```python
{
    "match_xp": {
        "pace": 5,
        "shooting": 14,
        "passing": 18,
        "dribbling": 11,
        "defending": 0,
        "physical": 7,
    },
    "training_xp": {...},
    "total_xp": {...},
    "meters_before": {...},
    "meters_after": {...},
    "attributes_before": {...},
    "attributes": {...},
    "overall_before": 58,
    "overall": 59,
    "upgrades": [...],
}
```

- [ ] **Step 1: Write failing snapshot tests**

For a starter:
- build sealed snapshot;
- verify `match_xp` equals `match_development_xp(performance)`;
- verify training load uses actual generated minutes;
- verify total gain is per-attribute sum;
- verify development is deterministic for the same sealed seed/performance.

For bench/not-selected:
- `match_xp` all zero;
- training still exists if healthy.

For in-match injury:
- earned match XP remains non-zero when actions/minutes exist.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py -k "snapshot"
```

- [ ] **Step 3: Replace `_plan_development` usage in `_build_match_snapshot`**

Remove global `match_xp + training_xp` flow.

Instead:
1. compute `match_gains = match_development_xp(performance)`;
2. compute `training_gains = training_development_xp(...)`;
3. sum by attribute;
4. call `apply_attribute_xp`;
5. seal exact before/after states into snapshot.

Do not mutate database during snapshot creation.

- [ ] **Step 4: Write failing settlement-idempotency tests**

In `tests/test_match_integrity.py`:
- prepare match;
- capture six meters/attributes;
- complete once;
- assert DB equals sealed `development` final state;
- complete same session again/retry completion;
- assert attributes and meters unchanged after second completion.

Also verify skip-to-full-time uses the exact same settlement.

- [ ] **Step 5: Update settlement UPDATE**

At existing match commit:
- set all six integer attributes;
- set all six XP meter columns;
- set career `overall`;
- force legacy `xp=0`;
- do this within existing transaction guarded by prepared/completed session state.

- [ ] **Step 6: Preserve report summary**

Generate development summary from actual XP:
- list earned non-zero categories;
- append upgrade transitions if any.

Examples:

```text
Match development: PAS +18 XP · DRI +11 XP · SHO +7 XP.
Breakthrough: PAS 61 → 62.
```

- [ ] **Step 7: Verify settlement + full suite**

```bash
.venv/bin/python -m pytest -q tests/test_match_integrity.py tests/test_player_progression.py
.venv/bin/python -m pytest -q
```

- [ ] **Step 8: Commit**

```bash
git add app/services.py tests/test_match_integrity.py tests/test_player_progression.py
git commit -m "feat: settle performance-led match development"
```

---

### Task 6: Training plan API + dashboard progress UI

**Files:**
- Modify: `app/services.py`
- Modify: `app/templates/dashboard.html`
- Modify: `app/static/app.js`
- Modify: `app/static/style.css`
- Modify: `tests/test_career_flow.py`
- Modify: `tests/test_player_progression.py`

**Interfaces:**
- `get_training_plan(career_id)` returns:

```python
{
    "focus": "passing",
    "label": "Passing craft",
    "description": "...",
    "attributes": {
        "pace": {"value": 58, "xp": 14, "cost": 48, "percent": 29},
        ...
    },
    "weekly_preview": {
        "pace": 0,
        "shooting": 0,
        "passing": 20,
        "dribbling": 5,
        "defending": 0,
        "physical": 5,
    },
}
```

- [ ] **Step 1: Write failing service/UI tests**

Assert:
- service exposes all six value/xp/cost/percent values;
- dashboard no longer contains global `{{ training_plan.xp }}/100 XP`;
- each attribute card has meter/progress markup;
- selected focus remains keyboard/click selectable;
- recovery card remains available;
- no form/action awards XP immediately.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_player_progression.py tests/test_career_flow.py -k "training_plan or development"
```

- [ ] **Step 3: Update `get_training_plan`**

Query `careers` joined with `player_attributes`; compute current cost/percent using pure progression helpers.

Do not expose hidden future match development.

- [ ] **Step 4: Update dashboard**

Replace the single global XP track with per-attribute progress bars.

Each card should show:

```text
PAS 61
34 / 75 XP to 62
```

Side console shows a weekly training preview for current focus.

- [ ] **Step 5: Update live training-focus UI**

When focus changes via existing API:
- update selected state;
- update focus description;
- update weekly preview;
- do not fake-change XP meter/value until calendar progression actually happens.

- [ ] **Step 6: Browser QA**

Verify:
- six XP meters render;
- selecting each focus changes preview only;
- Recovery shows zero development allocation;
- existing keyboard shortcuts still work;
- mobile layout remains readable.

- [ ] **Step 7: Full suite + commit**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app
git diff --check
git add app/services.py app/templates/dashboard.html app/static/app.js app/static/style.css tests/test_career_flow.py tests/test_player_progression.py
git commit -m "feat: show attribute development progress"
```

---

### Task 7: Post-match development display

**Files:**
- Modify: `app/static/app.js`
- Modify: `app/templates/match.html` only if a stable mount is required
- Modify: `tests/test_match_visual_replay.py`
- Modify: `tests/test_match_integrity.py`

**Interfaces:**
- Completed report payload already contains sealed `development_summary`; extend the report data with safe settled development detail only after completion.

- [ ] **Step 1: Write failing no-spoiler/report tests**

Assert:
- live/pre-FT HTML contains no future `match_xp`, meter-after state or attribute upgrade result;
- completion payload includes settled `development`;
- post-match report renders earned XP categories and upgrade transitions.

- [ ] **Step 2: Verify RED**

```bash
.venv/bin/python -m pytest -q tests/test_match_visual_replay.py tests/test_match_integrity.py -k "development"
```

- [ ] **Step 3: Expose settled development in completion payload**

Only completion response may include:
- match XP per attribute;
- training XP per attribute;
- upgrades;
- final meter progress.

Do not add this to `/advance` or the visual-plan endpoint.

- [ ] **Step 4: Render report**

Add a development section to `buildReport(payload)` with text-safe DOM construction only.

No `innerHTML` using server strings.

- [ ] **Step 5: Verify + browser QA**

Test:
- goal-heavy match shows shooting XP;
- passing-heavy match shows passing XP;
- injury match still shows earned XP;
- not-selected match shows no match XP;
- refresh after completion shows one settled report, no duplicate change.

- [ ] **Step 6: Full suite + commit**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app
git diff --check
git add app/services.py app/static/app.js app/templates/match.html tests/test_match_visual_replay.py tests/test_match_integrity.py
git commit -m "feat: explain post-match development gains"
```

---

### Task 8: Balance simulation against approved season targets

**Files:**
- Create: `tests/test_progression_balance.py`
- Modify: `app/progression.py` only if test evidence shows tuning is required
- Modify: `docs/superpowers/specs/2026-09-20-player-progression-v2-design.md` only if an approved numerical formula must change

**Interfaces:**
- No new production interface.

- [ ] **Step 1: Write deterministic season-simulation tests**

Use pure progression functions, not Flask/browser flows.

Scenarios for a 22-year-old 58 OVR / 88 potential player:
1. **Training-only:** 52 healthy zero-minute weeks with realistic season phases and a fixed focus rotation.
2. **Mixed season:** 25 appearances with mid-range performance fixtures + training.
3. **Strong starter:** 32 appearances with good but plausible metrics + training.
4. **Exceptional:** 36 high-level appearances + training.

Tests should assert approved ranges:
- training-only → 61–62;
- mixed → 63–65;
- strong → 65–68;
- exceptional <=69.

Also assert `overall <= potential`.

- [ ] **Step 2: Verify RED or range evidence**

```bash
.venv/bin/python -m pytest -q tests/test_progression_balance.py -vv
```

If ranges fail, inspect whether formula implementation differs from the spec or the agreed formula itself is mistuned.

- [ ] **Step 3: Tune only constants necessary to hit targets**

Do not introduce hidden catch-up bonuses.

Allowed tuning:
- training amounts;
- category coefficients/caps;
- potential cost multipliers;
- base-cost bands.

Any changed constant must stay explicit in `app/progression.py` and be reflected in the spec.

- [ ] **Step 4: Run full verification**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app
git diff --check
git status --short
```

- [ ] **Step 5: Final browser acceptance**

Manual matrix:
- existing 58 OVR career migrates without losing save;
- dashboard shows six meters;
- training focus changes preview but not XP instantly;
- non-selected week grows training only;
- starter match grows action-relevant stats;
- substitute receives smaller minutes-dependent development;
- injury match keeps earned XP;
- recovery week gives no attribute XP;
- match completion retry does not duplicate progression;
- no final development result leaks before full time.

- [ ] **Step 6: Commit final balance**

```bash
git add app/progression.py tests/test_progression_balance.py docs/superpowers/specs/2026-09-20-player-progression-v2-design.md
git commit -m "test: lock player progression season balance"
```

---

## Final Verification

Before claiming Player Progression V2 complete:

```bash
git branch --show-current
git status --short
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app
git diff --check
git log --oneline --decorate -12
```

Expected branch: `feat/player-progression-v2`.

Do not merge until:
- full pytest suite is green;
- browser acceptance matrix is green;
- working tree is clean;
- whole-branch code review finds no Critical/Important blockers.
