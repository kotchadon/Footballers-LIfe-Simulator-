# Player Progression V2 — Performance-Led Attribute Development Design

**Date:** 2026-09-20
**Status:** Approved design, awaiting written-spec review
**Scope:** Player development only. Property-market work is explicitly out of scope.

## Goal

Replace the current slow global-XP/random-attribute progression model with a deterministic, attribute-specific development system where:

- training provides reliable baseline growth;
- match actions develop the attributes actually used in the match;
- non-selection never reduces attributes;
- an injury never deletes development already earned before the injury;
- a low-OVR, high-potential player can escape a selection trap through training;
- a 22-year-old player at 58 OVR / 88 potential can reach roughly 65–68 after a genuinely strong full season;
- progression slows naturally as the player approaches potential.

## Existing Problem

The current system pools development into a single career XP value. At 100 XP it raises one attribute by +1, with the target attribute chosen by training focus and positional weighting. Match XP is mostly rating + goals + assists, despite the simulation already recording detailed passing, shooting, dribbling, tackling, duel and progressive-action metrics.

This makes development feel both too slow and too disconnected from actual play.

## Core Model

### Six persistent attribute-development meters

Each attribute receives its own persistent XP balance:

- `pace_xp`
- `shooting_xp`
- `passing_xp`
- `dribbling_xp`
- `defending_xp`
- `physical_xp`

These live alongside the six existing integer attributes in `player_attributes`.

A meter is allowed to exceed its current threshold. When enough XP exists for a +1:

1. spend the current upgrade cost;
2. increase only that attribute by +1;
3. recalculate OVR;
4. repeat while enough XP remains and OVR is below potential.

Excess XP always carries over. No earned XP is discarded.

`careers.xp` becomes legacy compatibility data and is no longer the progression driver after migration.

## Upgrade Costs

Base +1 cost is determined by the current attribute value:

| Current attribute | Base XP cost |
| --- | ---: |
| 0–59 | 60 |
| 60–69 | 75 |
| 70–79 | 105 |
| 80–84 | 145 |
| 85–89 | 200 |
| 90–99 | 280 |

The player's potential gap modifies the cost:

| `potential - overall` | Cost multiplier |
| --- | ---: |
| 25+ | 0.80 |
| 15–24 | 0.90 |
| 8–14 | 1.00 |
| 3–7 | 1.20 |
| 0–2 | 1.50 |

Final cost is `round(base_cost * potential_multiplier)` with a minimum of 1 XP.

When recalculated OVR has reached potential, no further attribute upgrades occur. XP meters may retain their remainder but cannot convert into more attribute points until the cap logic permits it.

## Age

V2 does not add age-based decline or negative progression.

For ages through the normal growth window, age does not reduce earned XP. The potential-gap cost already governs the speed of development. Late-career decline is a separate future system and must not be mixed into this change.

## Training XP

Training happens automatically through calendar progression; changing the focus does not itself award XP.

### Healthy player workload

A full training week produces:

- focused attribute: `+20`
- support attribute A: `+5`
- support attribute B: `+5`

Total: **30 attribute XP**.

Support attributes are deterministic and position-aware. Each focus has a fixed support pair:

- Pace → Dribbling + Physical
- Shooting → Dribbling + Physical
- Passing → Dribbling + Physical
- Dribbling → Pace + Passing
- Defending → Physical + Passing
- Physical → Pace + Defending
- Balanced → distribute 30 XP by existing position weights, deterministic with largest-remainder allocation

### Match-week workload

If the player appeared in the week's competitive match, training load is reduced because match load replaces some training volume:

- 60+ minutes: 70% of full training allocation
- 30–59 minutes: 80%
- 1–29 minutes: 90%
- unused bench / not selected: 100%

The allocation is rounded deterministically while preserving the intended total.

### Preseason

Preseason training allocation receives `1.25x`.

### Injury

During a week in which the player is already unavailable through injury, attribute-training XP is zero. Recovery continues through the existing fitness/injury system.

If the player becomes injured during a match, all match-development XP earned from the performance generated for the minutes played is retained.

### Recovery focus

Recovery awards **zero attribute XP** and continues to prioritize fitness, morale and stress.

## Match Development XP

Only players with actual match minutes receive match-development XP.

No selection or unused bench:
- zero match XP;
- no attribute loss.

A substitute receives development only from the minutes and actions generated for that appearance.

### Passing XP

Raw Passing XP:

- `passes_completed * 0.20`
- `key_passes * 3`
- `assists * 8`
- `+5` if `passes_attempted >= 20` and `pass_accuracy >= 85`
- additional `+3` if `passes_attempted >= 20` and `pass_accuracy >= 92`

Per-match Passing cap: **28 XP** before rating multiplier.

### Shooting XP

Raw Shooting XP:

- `shots * 1`
- `shots_on_target * 2`
- `goals * 10`
- `+3` if `shots >= 2` and `shot_accuracy >= 50`

Per-match Shooting cap: **24 XP** before rating multiplier.

### Dribbling XP

Raw Dribbling XP:

- `dribbles_completed * 2.5`
- `+4` if `dribbles_attempted >= 3` and `dribble_success >= 60`
- `progressive_actions * 0.35`

Per-match Dribbling cap: **20 XP** before rating multiplier.

### Defending XP

Raw Defending XP:

- `tackles_won * 3`
- `duels_won * 1`
- `+4` if `tackles_attempted >= 2` and `tackle_success >= 70`

Per-match Defending cap: **22 XP** before rating multiplier.

### Physical XP

Raw Physical XP:

- `floor(minutes / 10)`
- `duels_won * 0.6`
- `+2` for 90 minutes

Per-match Physical cap: **15 XP** before rating multiplier.

### Pace XP

The current match simulation does not record sprint distance or top speed, so V2 uses only evidence already available:

- `progressive_actions * 1`
- `dribbles_completed * 0.5`
- `+2` if `minutes >= 60`

Per-match Pace cap: **12 XP** before rating multiplier.

Pace therefore remains more training-led than other attributes until sprint metrics exist.

## Match Rating Multiplier

Rating modifies only XP that was already earned from actual actions:

| Rating | Multiplier |
| --- | ---: |
| below 6.5 | 0.90 |
| 6.5–7.49 | 1.00 |
| 7.5–8.49 | 1.10 |
| 8.5+ | 1.20 |

A high rating cannot create XP in an attribute with zero raw XP.

After multiplying and rounding each attribute, total match-development XP is capped at **75 XP**.

If the six multiplied values exceed 75, scale all six proportionally to sum to 75 using deterministic largest-remainder allocation. This preserves the attribute mix while enforcing the cap.

There is no negative match XP.

## Example

A winger plays 78 minutes and records:

- 28/32 passes
- 2 key passes
- 1 assist
- 4/6 dribbles
- 1 goal
- 2 shots on target
- 5 progressive actions
- 8.1 rating

The match awards a strong mix led by Passing, Shooting and Dribbling, with smaller Physical and Pace development. Rating applies a 1.10 multiplier. The final total cannot exceed 75 XP.

The player therefore improves because of what he actually did, not because the game selected a random attribute.

## Migration of Existing Saves

`player_attributes` gains six non-negative integer XP columns with default 0.

For an existing career:

1. read legacy `careers.xp`;
2. if it is zero, initialize all six meters to zero;
3. if `training_focus` is one of the six attributes, move the full legacy remainder into that attribute's meter;
4. if focus is `balanced` or `recovery`, move the full legacy remainder into the highest-weight attribute for the player's position;
5. set legacy `careers.xp` to zero after successful migration.

Migration must be idempotent. Re-running app initialization must not duplicate migrated XP.

New careers start all six meters at zero.

## Persistence and Sealed Match Integrity

Match development must be calculated inside the authoritative sealed match snapshot using the same performance metrics that produced the report.

The snapshot stores the exact attribute-XP award and resulting planned attribute state.

Completing a match commits that planned state once, within the existing idempotent match-settlement transaction.

Browser replay never computes or decides development.

Refreshing, replaying, skipping to full time, or retrying completion must never double-award XP or attributes.

## Dashboard / Player Development UI

The development panel stops showing one global `x/100 XP` bar.

Each attribute card shows:

- current integer attribute;
- XP toward the next +1;
- required XP for the next +1;
- percentage progress;
- selected training focus.

Example:

`PAS 61`
`34 / 75 XP to 62`

The side console explains the selected focus and the current week's expected training distribution.

After a match, the post-match report shows only the development earned by that settled match, for example:

`PAS +18 XP · DRI +11 XP · SHO +7 XP · PHY +5 XP`

If one or more attributes crossed a threshold, the report also shows:

`PAS 61 → 62`

No future/unsettled development is exposed before full time.

## Season Balance Targets

For a 22-year-old, 58 OVR, 88-potential player:

- almost no competitive minutes, consistent healthy training: **about 61–62 OVR**
- mixed season: **about 63–65 OVR**
- strong regular-starter season: **about 65–68 OVR**
- exceptional breakout season: **up to about 68–69 OVR**

These are balance targets, not forced outcomes. Position, training focus, match volume and actual performance determine the exact result.

As OVR approaches potential, higher attribute costs and the potential-gap multiplier naturally reduce the rate of improvement.

## Non-Negotiable Rules

- No match-by-match attribute decreases.
- No penalty for not being selected.
- No penalty for being an unused substitute.
- Injury never removes XP earned before the injury event.
- Recovery focus does not secretly award attribute XP.
- Match actions determine match-development distribution.
- Rating only multiplies earned action XP.
- Maximum match-development award is 75 XP.
- No random attribute roulette.
- OVR is recalculated from attributes; OVR itself does not receive XP.
- Potential remains a cap on long-term OVR growth.
- Existing sealed-match settlement remains idempotent.
- Existing security protections remain unchanged.
