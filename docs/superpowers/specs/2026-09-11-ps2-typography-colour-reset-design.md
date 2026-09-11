# PS2 / PSP Typography and Colour Reset — Design

Date: 2026-09-11
Status: Approved
Branch: `ui/ps2-typography-colour-reset`

## Objective

Replace the remaining generic SaaS / AI-dashboard visual language with a cohesive early-2000s console sports-game presentation while preserving modern readability and the approved V5 player portrait.

The app should feel closer to a PS2 / PSP football career menu and sports broadcast package than a contemporary analytics dashboard.

## Scope

Dashboard, Match Centre, Training, Transfer Market, Finance, World, Calendar, post-match reports, and navigation.

No gameplay, save, match-settlement, API, database, security, or JavaScript behavior changes.

## Typography

Reading/body:

`"Iowan Old Style", "Palatino Linotype", "Book Antiqua", Palatino, Georgia, serif`

Display/headings:

`Impact, Haettenschweiler, "Arial Narrow Bold", "Arial Black", sans-serif`

Dense UI/data:

`"Trebuchet MS", "Arial Narrow", Arial, sans-serif`

No external fonts, font CDN, or `@font-face` dependency.

## Palette

- Canvas `#07101b`
- Canvas deep `#050a11`
- Surface `#0d1928`
- Surface raised `#122237`
- Steel `#26384e`
- Steel light `#3b506a`
- Strong text `#edf2f8`
- Body text `#cbd5e1`
- Muted `#8fa0b5`
- Reading cream `#ddd4c2`
- Accent blue `#5f7faa`
- Cold accent `#8aa4c7`
- Success `#6f9c82`
- Warning `#c4a35e`
- Danger `#b86161`

Purple is not part of the new core theme. Large paper-white dashboard cards are removed from the visual language.

## Architecture

Add `app/static/theme-ps2.css` and load it after `style.css` from `base.html`.

This file is the canonical final presentation layer for the showcase sprint. Legacy CSS remains responsible for structure; the new layer owns typography, palette, surfaces, navigation, controls, tables, reports, and cross-page compatibility styling.

## V5 protection

Do not modify:

- `app/player_visuals.py`
- `app/templates/_player_visual.html`
- `app/templates/player_portrait_v5/`

The new theme must not redefine `.football-portrait-v5` or `.fp5-*` internal portrait selectors.

## Accessibility

Maintain visible focus, strong contrast, semantic statuses, existing reduced-motion behavior, readable body sizes, and clear interactive controls.

## Acceptance criteria

- App no longer looks like a generic SaaS/AI dashboard.
- Major headings feel like PS2/PSP sports-game UI.
- Prose/reports use readable serif typography.
- Data/UI copy uses compact sans-serif typography.
- Dark navy/black/steel palette is consistent.
- Purple/white card clashes are materially reduced.
- V5 portrait remains intact.
- No external fonts or CSP changes.
- No gameplay/save/security behavior changes.
- Full pytest suite passes.
- `git diff --check` passes.
- Browser QA covers all scoped screens before commit/merge.
