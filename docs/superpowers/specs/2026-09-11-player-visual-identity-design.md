# Player Visual Identity — Design Specification

## Goal
Build a deterministic, reusable, production-quality visual identity system for the career player.

## Architecture
- Permanent identity is a read-only projection of immutable career id.
- Club kit is derived independently from club id.
- Dynamic state is derived only from authoritative career/match fields.
- Renderer never mutates gameplay or save state.
- V1 requires no database migration and no external services.

## Authoritative V1 state
- fitness
- morale
- stress
- injured_weeks
- suspended_matches
- position
- overall
- club
- Match Centre selection_status

## Security and reliability
- No user-supplied SVG/HTML.
- No `|safe` for player text.
- No network calls or external asset dependency.
- No CSP/CSRF relaxation.
- No write endpoint.
- No use of Python built-in hash() for identity.
- No global random state.
- Existing settlement logic remains untouched.

## Rendering target
A reusable procedural SVG footballer with stable facial/body identity, separate club kit, state-driven expression/posture, reduced-motion support and accessible textual context.

## Definition of done
Targeted tests, full regression suite, diff check, Dashboard/Match/Training browser QA, feature-branch commit, then merge only after verification.

