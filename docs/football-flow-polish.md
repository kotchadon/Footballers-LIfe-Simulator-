# Football-flow polish candidate

Scope: presentation only. Backend events, scorers, results, progression, saves,
models, local Three.js dependencies and renderer switching are unchanged.

## Changes

- Ordinary possession retains its carrier through phase changes. Phases progress
  through midfield before final-third play; turnovers require a nearby challenge.
- Local receivers are preferred. Ground, driven, lofted, switch and cross flights
  have distinct trajectories. Flight endpoints are committed, not magnetic.
- A cross needs an advanced wide origin and an actual box receiver, including
  a short backward cutback. Opposite-wing diagonals remain switches.
- An authorized shot finishes any current flight, links actual receivers to the
  named shooter, then launches from the live ball position. Shot staging no
  longer moves players or the ball to event coordinates. Only explicit football
  restarts can reposition actors. Supporting actions never create official stats.
- Ball radius is 0.135 m, with brighter material, stronger contact shadow and a
  restrained airborne ground cue. No new textures or rendering passes.
- Both cameras use bounded current-action anticipation. Unreached event targets
  cannot pull the camera away from live play. Frozen snapshots retain the cue.

## Timing and limits

The fixed-step clock still owns all action waits, pause, visibility and speed.
The old 1.6-second watchdog could cancel a physically continuous linking pass.
Major shots now have a seven-simulation-second safety ceiling (not a fixed delay);
normal events retain 1.6 seconds. Longer sequences consume the existing replay
gap rather than append another full gap. Official match minutes are unchanged.
An unusually long sequence can still exceed a short event slot; it is bounded,
not accelerated by teleporting actors. This is a deliberate presentation tradeoff.

The presentation is deterministic illustrative football, not a replacement for
the authoritative simulation. Routes are short receiver chains, not a new
strategic AI or physics engine. Browser visual acceptance remains necessary.

## Verification

- Full Node suite: 55 tests passed, including continuity, contextual crossing,
  mirrored outcomes, pause/cancellation, marker ownership, frozen snapshots,
  renderer fallback, resize, speed and replay-gap compensation.
- Python full run: 360 passed; two bootstrap wiring checks initially failed.
  After the wiring correction, all 39 tests in `test_match_visual_replay.py`
  passed. The full suite was not repeated, per the no-loop brief.
- Affected choreography: all 9 tests passed after that correction.
- Python compileall (`app tools`), bootstrap syntax and diff whitespace passed.
- Browser visual QA was not run here. No claim of on-device visual approval.

## Local visual acceptance

Run `./start.sh`, open a new match and inspect:

1. Buildup: continuous midfield/final-third development, including a turnover.
2. Passing: grounded short play versus driven, lofted and opposite-wing switches.
3. Crossing: wide advanced delivery to a real box receiver, not a midfield diagonal.
4. Ball visibility: readable on the turf and in flight, without an oversized ball.
5. Goal sequence: reception, actual shooter, connected shot, correct save/miss/goal.
6. Camera: current attack remains readable without jumping to the next event.

Also check both halves, the career-player marker after substitution, 1x/2x/4x,
pause/resume, narrow window, 2D/3D switching, skip and completed-match reload.
