# Player Visual Identity V4 — Full Football Hero Revamp

Date: 2026-09-11
Status: Design approved in chat; implementation not started
Branch: `feat/player-visual-identity`

## 1. Objective

Replace the current weak procedural-avatar presentation with a cohesive, production-quality football career identity system.

V4 is not a cosmetic patch to V3. It is a deliberate visual reset of the portrait and Dashboard hero while preserving the safe deterministic identity architecture already implemented.

The end result must feel like a football career game, not a web dashboard with an avatar bolted onto it.

## 2. What survives from previous work

The following architecture remains authoritative:

- `app/player_visuals.py`
- deterministic identity derived from career id
- separate player identity and club-kit identity
- authoritative state projection from fitness, morale, stress, injury and selection
- read-only rendering
- no database migration for visual identity
- no gameplay writes
- no external image service
- no unsafe SVG/HTML input
- existing save and match-settlement integrity rules

The committed deterministic identity engine is retained.

## 3. What is discarded

The V2/V3 art direction is rejected.

Do not preserve or imitate:

- long narrow head silhouettes
- oversized cartoon eyes
- long thin necks
- white clip-art outlines
- large empty portrait frames
- oversized torso blocks
- debug identity text inside the portrait
- "CAREER PLAYER" labels inside artwork
- purple 3D OVR cube/card treatment
- idle breathing/bobbing
- generic gradient-avatar aesthetics
- repeated CSS patches layered over rejected visual versions

Before V4 production work begins, uncommitted V2/V3 visual experiments are reset to the last clean committed feature-branch checkpoint. V4 then replaces the renderer and Dashboard hero deliberately.

## 4. Visual direction

V4 uses the modular-avatar concept common to life/career simulators, but all visual assets and geometry are original.

The player is presented as a curated football profile portrait:

- adult male proportions
- head and upper shoulders only
- tight crop
- broad athletic neck/shoulder relationship
- realistic-cartoon eye scale
- stronger brow structure
- controlled jaw/chin shapes
- serious, neutral or confident default expression
- football-specific hairstyles
- subtle facial hair
- proper football shirt collar and shoulder seams
- restrained two/three-tone shading
- dark stadium/profile background
- club colour used as an accent, not a full-screen fill

The still frame must look good before any reaction or animation is added.

## 5. Curated modular portrait system

V4 avoids arbitrary geometry generation.

Instead it uses a small curated catalogue whose combinations are deterministic.

Initial quality-first catalogue:

- 5 head/jaw presets
- 6 football hairstyles
- 4 eye sets
- 4 brow sets
- 4 nose sets
- 4 mouth/expression base sets
- 4 facial-hair states
- 4 shoulder/build silhouettes
- existing skin palettes
- existing deterministic club-kit palettes

The renderer may expose thousands of combinations, but every building block must be intentionally designed.

No trait list is expanded merely to increase quantity.

## 6. Renderer architecture

Keep the public macro interface stable:

```jinja
player_visual(visual, size='hero', show_status=True)
```

Recommended implementation boundary:

```text
app/player_visuals.py
    deterministic identity + state projection
            ↓
app/templates/_player_visual.html
    composition macro / rendering contract
            ↓
curated face, hair, expression, jersey geometry
            ↓
Dashboard / Match Centre / future new-career preview
```

If the single template becomes hard to reason about, split internal rendering macros under:

```text
app/templates/player_visual/
```

but preserve `_player_visual.html` as the public integration entry point.

## 7. Dashboard hero redesign

The existing hero is fully redesigned.

The new hero should behave as one coherent football-profile surface rather than three unrelated cards.

Desktop composition:

```text
┌────────────────────────────────────────────────────────────────────┐
│  PORTRAIT        PLAYER IDENTITY                         RATING     │
│  tight bust      Advay Katoch                           52 OVR     │
│                  LW · Melbourne City                    POT 88     │
│                  A-League Men                                      │
│                                                                    │
│                  FITNESS 82   MORALE 61   TRUST 19                 │
│                  Explosive Pace · Reserve Bridge                   │
└────────────────────────────────────────────────────────────────────┘
```

Requirements:

- portrait occupies approximately 25–32% of hero width
- no large standalone frame around the portrait
- player name remains prominent but not absurdly oversized
- OVR/POT becomes a restrained football rating block
- status pills are reduced and reorganised
- key state metrics become part of the hero hierarchy
- responsive layout collapses cleanly on tablet/mobile
- hero background uses subtle stadium/profile treatment, not SaaS gradients

## 8. Rating presentation

Remove the purple pseudo-3D `player-card-mark` treatment.

Replace it with a compact rating module:

- OVR primary
- POT secondary
- optional role/squad indicator
- club accent line or badge-like geometry
- high contrast
- no neon cube
- no fake 3D transform

The rating module remains semantic HTML, not baked into the portrait SVG.

## 9. Reactive identity

V4 is not permanently static.

However, reactions are introduced only after the base portrait passes visual QA.

Authoritative reactions:

### Fitness
- fresh: alert eyes, upright shoulders
- normal: neutral
- tired: slightly lower eyelids, mild shoulder drop
- exhausted: heavier eye treatment, subtle facial shadow, more subdued posture

### Morale
- confident: firmer brow/mouth presentation
- neutral: baseline
- subdued: flatter mouth, softer posture

### Stress
- calm: baseline
- tense: brow convergence and tighter mouth

### Injury
- no injury: clean portrait
- injury: subtle treatment/tape and guarded expression

### Selection
- starting: full-presence presentation
- substitute: slightly reduced emphasis
- not selected: muted treatment without greying out the entire UI

Reaction logic must never write gameplay state.

## 10. Motion

No generic idle loop.

No continuous breathing, bobbing, wobbling or blinking during the initial V4 rollout.

After the still portrait and reactive states are approved, micro-motion may be added only where meaningful.

Permitted future examples:

- one short expression transition after a state change
- brief highlight after a goal or major career event
- controlled eye/brow transition
- subtle shoulder settling

Motion must be event/state driven and respect `prefers-reduced-motion`.

## 11. New-career and other surfaces

The renderer is reusable beyond Dashboard.

Rollout order:

1. Dashboard hero
2. Match Centre compact identity
3. New-career visual preview
4. Training/development context
5. other profile surfaces only if useful

The new-career preview must reuse the same curated rendering vocabulary. It must not create a second avatar implementation.

## 12. Security

Preserve all existing security controls.

V4 must not introduce:

- `|safe` for user-controlled data
- user-generated SVG fragments
- external image hosts
- remote fonts/assets required for portrait rendering
- `innerHTML`
- new write endpoints
- dynamic code execution
- CSP relaxations
- CSRF relaxations

All player-provided text remains escaped.

## 13. Save integrity

The visual system remains a read-only projection.

V4 must not change:

- match simulation
- match settlement
- XP
- salary
- goals
- assists
- appearances
- finances
- transfer resolution
- save schema

Visual failure must never block career loading or match completion.

## 14. Engineering quality requirements

Implementation follows:

OBSERVE → RED TEST → MINIMAL CHANGE → FOCUSED GREEN → FULL GREEN → DIFF CHECK → BROWSER QA.

No direct edits to `main`.

No merge before browser approval.

Tests must cover:

- stable identity contract
- curated trait mapping
- template safety
- renderer reuse
- Dashboard context integration
- rejected V2/V3 debug/animation artifacts absent
- responsive CSS hooks
- reaction-state mapping
- reduced-motion behavior
- escaping of hostile player names

Avoid brittle full-SVG snapshots as the only protection. Prefer structural/invariant tests plus manual browser review.

## 15. Visual QA gate

A renderer is not accepted because pytest is green.

Dashboard must be manually reviewed for:

- adult proportions
- eye scale
- jaw/chin
- neck width/length
- ears
- hairstyle silhouette
- facial hair
- jersey collar
- shoulder crop
- colour balance
- portrait-to-hero scale
- typography hierarchy
- rating hierarchy
- mobile/tablet behavior

If the portrait still looks like clip-art, web-avatar art or a children's game, it is rejected and iterated before Match Centre work.

## 16. Definition of done

V4 is complete only when:

- a still portrait is visually approved
- player identity remains deterministic
- Dashboard feels like a football career interface
- rejected V2/V3 visual language is removed
- OVR/POT presentation is rebuilt coherently
- reactive states are visually meaningful
- Match Centre reuses the same player identity
- new-career preview reuses the same rendering system
- no gameplay or save logic is affected
- focused tests pass
- full test suite passes
- `git diff --check` passes
- browser QA passes
- feature branch is committed and reviewed
- only then is it merged into `main`
