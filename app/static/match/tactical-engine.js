import {formationAnchors} from "./formations.js";
import {integrateMovement} from "./movement.js";
import {createPrng, sampleSeed} from "./prng.js";
import {createBallController} from "./ball.js";
import {createAnimationController} from "./animation-controller.js";
import {nextFlowPhase, selectPassProfile, planAuthoritativeAttack, currentPresentationFocus} from "./football-flow.js";

export const TACTICAL_PHASES = Object.freeze([
  "BUILDUP",
  "PROGRESSION",
  "FINAL_THIRD",
  "TRANSITION_ATTACK",
  "TRANSITION_DEFENCE",
  "DEFENSIVE_BLOCK",
]);

const ATTACK_ROLES = new Set(["LW", "RW", "LM", "RM", "ST", "LST", "RST", "CAM"]);
const MIDFIELD_ROLES = new Set(["DM", "LDM", "RDM", "CM", "LCM", "RCM", "CAM"]);
const WIDE_ROLES = new Set(["LB", "RB", "LWB", "RWB", "LW", "RW", "LM", "RM"]);
const DEFENDER_ROLES = new Set(["LB", "RB", "LWB", "RWB", "CB", "LCB", "RCB"]);

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function distance(a, b) {
  return Math.hypot(Number(a.x) - Number(b.x), Number(a.y) - Number(b.y));
}

function teamPlan(plan, team) {
  return team === "home" ? plan.home : plan.away;
}

function scoreContext(team, context) {
  const home = Number(context.homeScore || 0);
  const away = Number(context.awayScore || 0);
  if (team === "home") {
    return {trailing: home < away, leading: home > away};
  }
  return {trailing: away < home, leading: away > home};
}

function baseTeamState(plan, team) {
  const side = teamPlan(plan, team);
  return {
    team,
    formation: side.formation,
    direction: Number(side.attacking_direction || (team === "home" ? 1 : -1)),
    possession: team === "home",
    phase: team === "home" ? "BUILDUP" : "DEFENSIVE_BLOCK",
    width: 1,
    compactness: 1,
    lineHeight: 0,
    pressIntensity: .55,
    tempo: 1,
    primaryPresserId: null,
    coverActorId: null,
  };
}

function initialActor(actor, plan) {
  const side = teamPlan(plan, actor.team);
  const anchors = formationAnchors(side.formation, side.attacking_direction);
  const anchor = anchors[actor.role] || [actor.team === "home" ? 35 : 65, 50];
  const pace = Number(actor.attributes?.pace || 60);
  const acceleration = Number(actor.attributes?.acceleration || pace);

  return {
    actorId: actor.actor_id,
    displayName: actor.display_name,
    shirtNumber: actor.shirt_number,
    role: actor.role,
    team: actor.team,
    isUser:
      actor.actor_id === plan.user_actor_id
      || actor.actor_id === plan.career_player?.actor_id
      || actor.visual_profile?.is_user === true,
    x: anchor[0],
    y: anchor[1],
    anchorX: anchor[0],
    anchorY: anchor[1],
    targetX: anchor[0],
    targetY: anchor[1],
    vx: 0,
    vy: 0,
    heading: actor.team === "home" ? 0 : Math.PI,
    maxSpeed: 5.8 + pace * .033,
    acceleration: 4 + acceleration * .035,
    deceleration: 7 + acceleration * .035,
    staminaFactor: clamp(Number(actor.attributes?.stamina || 72) / 100, .45, 1),
    animationState: actor.role === "GK" ? "GK_SET" : null,
    tacticalIntent: "holdShape",
    markingTarget: null,
    supportTarget: null,
  };
}

function nearestOutfieldActors(actors, team, point, count = 2) {
  return actors
    .filter((actor) => actor.team === team && actor.role !== "GK")
    .map((actor) => ({actor, d: distance(actor, point)}))
    .sort((a, b) => a.d - b.d)
    .slice(0, count)
    .map((item) => item.actor);
}

function roleMovementOffset(actor, teamState, phase, ball, phaseIndex) {
  const direction = teamState.direction;
  const attacking = teamState.possession;
  const seed = sampleSeed(phaseIndex + 1, actor.actorId, phase);
  const pulse = ((seed % 1000) / 999) * 2 - 1;

  let x = 0;
  let y = 0;
  let intent = attacking ? "supportRun" : "holdShape";

  if (actor.role === "GK") {
    return {
      x: direction * (attacking ? 2.2 : .5),
      y: (ball.y - 50) * .05,
      intent: "keeperAngle",
    };
  }

  if (WIDE_ROLES.has(actor.role)) {
    y += actor.anchorY < 50 ? -3.4 * teamState.width : 3.4 * teamState.width;
  }

  if (attacking && ["LB", "RB", "LWB", "RWB"].includes(actor.role)) {
    x += direction * (phase === "FINAL_THIRD" ? 10 : 6);
    intent = "overlap";
  }

  if (attacking && ATTACK_ROLES.has(actor.role)) {
    if (phase === "PROGRESSION") {
      x += direction * (4 + Math.abs(pulse) * 3);
      intent = "supportRun";
    }
    if (phase === "FINAL_THIRD") {
      x += direction * (8 + Math.abs(pulse) * 5);
      y += pulse * 3;
      intent = "runBehind";
    }
    if (phase === "TRANSITION_ATTACK") {
      x += direction * (10 + Math.abs(pulse) * 4);
      intent = "runBehind";
    }
  }

  if (attacking && MIDFIELD_ROLES.has(actor.role)) {
    x += direction * (phase === "BUILDUP" ? 1.5 : phase === "FINAL_THIRD" ? 5 : 3);
    y += (ball.y - actor.anchorY) * .10;
    intent = "supportRun";
  }

  if (!attacking && DEFENDER_ROLES.has(actor.role)) {
    x -= direction * (phase === "DEFENSIVE_BLOCK" ? 3 : 1);
    intent = "recover";
  }

  return {x, y, intent};
}

function phaseShapeSettings(teamState, context) {
  const {trailing, leading} = scoreContext(teamState.team, context);
  const late = Number(context.minute || 0) >= 70;

  let width = teamState.possession ? 1.12 : .84;
  let compactness = teamState.possession ? .92 : 1.18;
  let lineHeight = 0;
  let pressIntensity = teamState.possession ? .38 : .62;
  let tempo = 1;

  if (teamState.phase === "FINAL_THIRD") {
    width += .10;
    lineHeight += 3;
  }
  if (teamState.phase === "TRANSITION_ATTACK") {
    lineHeight += 5;
    tempo += .16;
  }
  if (teamState.phase === "DEFENSIVE_BLOCK") {
    width -= .08;
    compactness += .12;
    lineHeight -= 2;
  }

  if (late && trailing) {
    lineHeight += 5;
    width += .08;
    pressIntensity += .18;
    tempo += .18;
  }
  if (late && leading) {
    lineHeight -= 4;
    width -= .05;
    compactness += .08;
    pressIntensity -= .08;
    tempo -= .08;
  }

  return {
    width: clamp(width, .72, 1.32),
    compactness: clamp(compactness, .78, 1.38),
    lineHeight,
    pressIntensity: clamp(pressIntensity, .28, .92),
    tempo: clamp(tempo, .82, 1.32),
  };
}

function suitableCarrier(actor, phase) {
  if (actor.role === "GK") return phase === "BUILDUP" ? .3 : 0;

  if (phase === "BUILDUP") {
    return DEFENDER_ROLES.has(actor.role) || ["DM", "LDM", "RDM"].includes(actor.role) ? 1 : .2;
  }
  if (phase === "PROGRESSION") {
    return MIDFIELD_ROLES.has(actor.role) || WIDE_ROLES.has(actor.role) ? 1 : .35;
  }
  if (phase === "FINAL_THIRD") {
    return ATTACK_ROLES.has(actor.role) ? 1 : .25;
  }
  if (phase === "TRANSITION_ATTACK") {
    return ATTACK_ROLES.has(actor.role) || MIDFIELD_ROLES.has(actor.role) ? 1 : .25;
  }
  return .5;
}

function selectCarrier(actors, team, phase, seed) {
  const candidates = actors
    .filter((actor) => actor.team === team)
    .map((actor) => ({actor, weight: suitableCarrier(actor, phase)}))
    .filter((item) => item.weight > 0);

  if (!candidates.length) return null;

  const rng = createPrng(seed);
  const total = candidates.reduce((sum, item) => sum + item.weight, 0);
  let roll = rng() * total;

  for (const item of candidates) {
    roll -= item.weight;
    if (roll <= 0) return item.actor;
  }
  return candidates[candidates.length - 1].actor;
}

function nextAttackingPhase(currentPhase, rng) {
  return nextFlowPhase(currentPhase);
}

const TEN_MAN_SHAPES = Object.freeze({
  compact: Object.freeze([
    [20,18],[17,40],[17,60],[20,82],
    [42,24],[39,50],[42,76],[65,36],[68,64],
  ]),
});

export function createTacticalEngine(plan) {
  const actors = plan.actors.map((actor) => initialActor(actor, plan));
  const teams = {
    home: baseTeamState(plan, "home"),
    away: baseTeamState(plan, "away"),
  };

  let possessionTeam = "home";
  let phaseIndex = 0;
  let phaseElapsed = 0;
  let phaseDuration = 4.2;
  let attackingPhase = "BUILDUP";
  const rng = createPrng(sampleSeed(plan.seed, "tactical-phases"));

  let carrier = selectCarrier(
    actors,
    possessionTeam,
    attackingPhase,
    sampleSeed(plan.seed, "carrier", phaseIndex),
  );

  const ballController = createBallController({
    x: Number(plan.initial_ball?.x ?? 50),
    y: Number(plan.initial_ball?.y ?? 50),
    height: 0,
    ownerActorId: carrier?.actorId || null,
    state: "CONTROLLED",
  });
  const animationController = createAnimationController();
  const ball = ballController.state;
  // Initial kickoff placement happens before the first presented frame.
  if (carrier) { ball.x=carrier.x; ball.y=carrier.y; }
  ballController.control(carrier?.actorId || null);

  let passClock = 0;
  let nextPassAt = 1.15 + rng() * .75;
  let eventOverrideUntil = 0;
  let eventClock = 0;
  let buildup = null;
  let pendingRestart = null;

  function resetPhase() {
    phaseIndex += 1;
    phaseElapsed = 0;

    const turnoverChance =
      attackingPhase === "FINAL_THIRD"
        ? .42
        : attackingPhase === "TRANSITION_DEFENCE"
          ? .74
          : .16;

    const opponent = possessionTeam === "home" ? "away" : "home";
    const challenger = nearestOutfieldActors(actors, opponent, ball, 1)[0];
    if (rng() < turnoverChance && challenger && distance(challenger,ball)<4) {
      // A visible nearby challenge, not a random remote ownership reassignment.
      animationController.play(ball.ownerActorId,"PASS",{duration:.25,priority:3});
      ballController.deflect({...ball},challenger,{targetActorId:challenger.actorId,duration:.3,maxHeight:.12,settleToOwner:true});
      attackingPhase = "TRANSITION_ATTACK";
    } else {
      const progress=teams[possessionTeam].direction>0?ball.x:100-ball.x;
      if (attackingPhase === "FINAL_THIRD") attackingPhase=progress<55?"PROGRESSION":"FINAL_THIRD";
      else if (attackingPhase !== "PROGRESSION" || progress>=64) attackingPhase = nextAttackingPhase(attackingPhase, rng);
    }

    phaseDuration = 3.4 + rng() * 3.1;
    carrier = actors.find(a=>a.actorId===ball.ownerActorId) || carrier;
    passClock = 0;
    nextPassAt = .85 + rng() * .95;
  }

  function receiverScore(actor, currentCarrier, phase) {
    if (actor.actorId === currentCarrier.actorId) return -999;

    const direction = teams[currentCarrier.team].direction;
    const forwardDelta = (actor.x - currentCarrier.x) * direction;
    const lateralDelta = Math.abs(actor.y - currentCarrier.y);
    let score = -distance(actor,currentCarrier) * .065 - lateralDelta * .01;

    if (phase === "BUILDUP") {
      if (MIDFIELD_ROLES.has(actor.role)) score += 1.3;
      if (DEFENDER_ROLES.has(actor.role)) score += .7;
    }

    if (phase === "PROGRESSION") {
      if (MIDFIELD_ROLES.has(actor.role)) score += 1.1;
      if (WIDE_ROLES.has(actor.role)) score += 1.0;
      if (forwardDelta > 0) score += .8;
    }

    if (phase === "FINAL_THIRD") {
      if (ATTACK_ROLES.has(actor.role)) score += 1.4;
      if (forwardDelta > 0) score += 1.1;
      if (WIDE_ROLES.has(actor.role)) score += .45;
    }

    if (phase === "TRANSITION_ATTACK") {
      if (forwardDelta > 0) score += 1.5;
      if (ATTACK_ROLES.has(actor.role)) score += 1.1;
    }

    return score;
  }

  function selectReceiver(currentCarrier) {
    const candidates = actors
      .filter((actor) => actor.team === currentCarrier.team && actor.role !== "GK" && actor.actorId!==currentCarrier.actorId)
      .map((actor) => ({
        actor,
        score: receiverScore(actor, currentCarrier, attackingPhase),
      }))
      .sort((a, b) => b.score - a.score);

    if (!candidates.length) return null;

    const localRng = createPrng(
      sampleSeed(
        plan.seed,
        "receiver",
        phaseIndex,
        passClock.toFixed(2),
        currentCarrier.actorId,
      ),
    );
    const nearby=candidates.filter(({actor})=>distance(actor,currentCarrier)<30);
    const pool=nearby.length && localRng()<.88 ? nearby : candidates;
    const top=pool.slice(0,3);
    return top[Math.floor(localRng() * top.length)]?.actor || top[0].actor;
  }

  function schedulePass() {
    if (ball.action) return;

    const currentCarrier = actors.find(
      (actor) => actor.actorId === ball.ownerActorId,
    );
    if (!currentCarrier || currentCarrier.team !== possessionTeam) return;

    const receiver = selectReceiver(currentCarrier);
    if (!receiver) return;

    launchPass(receiver);
    receiver.supportTarget = currentCarrier.actorId;
  }

  function launchPass(receiver) {
    const direction=teams[receiver.team].direction;
    const phase=(direction>0?ball.x:100-ball.x)>=72?'FINAL_THIRD':attackingPhase;
    const profile=selectPassProfile(ball,receiver,{direction,phase});
    const owner=actors.find(a=>a.actorId===ball.ownerActorId);
    const methods={GROUND_PASS:'groundPass',DRIVEN_PASS:'drivenPass',LOFTED_PASS:'loftedPass',LONG_SWITCH:'longSwitch',CROSS:'cross'};
    const animation=profile.kind==='CROSS'?'CROSS':['LOFTED_PASS','LONG_SWITCH'].includes(profile.kind)?'LONG_PASS':'PASS';
    if(owner)animationController.play(owner.actorId,animation,{duration:.34,priority:4});
    ballController[methods[profile.kind]]({...ball},profile.target,{...profile,targetActorId:receiver.actorId});
    return profile.duration;
  }

  function beginAuthoritativeBuildup(payload={}) {
    const side=payload.side==='away'?'away':'home',shooter=eventActor(side,payload.actorId);
    if(!shooter)return 0;
    if(pendingRestart){const restart=pendingRestart;pendingRestart=null;prepareSetPiece(restart.kind,{side:restart.side});}
    // Finish a live flight first. The authorized event supplies identity, never staging coordinates.
    const landing=ball.action?{...ball.action.to,ownerActorId:ball.action.targetActorId}:ball;
    const route=planAuthoritativeAttack(landing,actors,{side,direction:teams[side].direction,shooterId:shooter.actorId});
    const flight=ball.action?Math.max(0,ball.action.duration-ball.action.elapsed):0;
    const duration=flight+route.reduce((sum,leg)=>sum+leg.duration+.18,0)+.25;
    buildup={side,shooterId:shooter.actorId,route:route.map(leg=>leg.receiverId),ready:false,dwell:.12};
    eventClock=0;eventOverrideUntil=duration+1;
    if(!ball.action)advanceBuildup(0);
    return duration;
  }

  function advanceBuildup(dt) {
    if(!buildup||buildup.ready||ball.action)return;
    buildup.dwell+=dt;
    if(ball.ownerActorId===buildup.shooterId) { buildup.ready=true; return; }
    if(buildup.dwell<.12&&ball.ownerActorId)return;
    let next;
    do { next=actors.find(a=>a.actorId===buildup.route.shift()); }
    while(next?.actorId===ball.ownerActorId&&buildup.route.length);
    if(!next)next=actors.find(a=>a.actorId===buildup.shooterId);
    if(!next){cancelAuthoritativeBuildup();return;}
    launchPass(next);buildup.dwell=0;
  }

  function cancelAuthoritativeBuildup() {
    buildup=null;
    eventOverrideUntil=eventClock;
  }

  function updateTeamStates(context) {
    for (const team of ["home", "away"]) {
      const state = teams[team];
      state.possession = team === possessionTeam;
      state.phase = state.possession
        ? attackingPhase
        : attackingPhase === "TRANSITION_ATTACK"
          ? "TRANSITION_DEFENCE"
          : "DEFENSIVE_BLOCK";

      Object.assign(state, phaseShapeSettings(state, context));
      state.primaryPresserId = null;
      state.coverActorId = null;
    }
  }


  function keeperForAttackingSide(attackingSide) {
    const defendingTeam =
      attackingSide === "home"
        ? "away"
        : "home";

    return actors.find(
      (actor) =>
        actor.team === defendingTeam
        && actor.role === "GK",
    ) || null;
  }

  function eventActor(
    side,
    preferredActorId,
  ) {
    if (preferredActorId) {
      const exact = actors.find(
        (actor) =>
          actor.actorId === preferredActorId,
      );

      if (exact) return exact;
      return null; // Never substitute another scorer for an unavailable named actor.
    }

    const team =
      side === "away"
        ? "away"
        : "home";

    return actors.find(
      (actor) =>
        actor.team === team
        && ATTACK_ROLES.has(actor.role),
    ) || actors.find(
      (actor) =>
        actor.team === team
        && actor.role !== "GK",
    ) || null;
  }


  function removeActor(actorId) {
    if (!actorId) return null;
    const index = actors.findIndex((actor) => actor.actorId === actorId);
    if (index < 0 || actors[index].role === "GK") return null;
    const [removed] = actors.splice(index, 1);
    animationController.cancelActor?.(actorId);
    if (ball.ownerActorId === actorId) ballController.control(null);
    if (carrier?.actorId === actorId) {
      carrier = selectCarrier(
        actors, possessionTeam, attackingPhase,
        sampleSeed(plan.seed, "carrier-after-removal", phaseIndex, actorId),
      );
      // A removed owner leaves a loose ball for the nearest player to recover.
    }
    return removed;
  }

  function activateActor(payload) {
    if (!payload?.actor_id) return null;
    const existing = actors.find((actor) => actor.actorId === payload.actor_id);
    if (existing) return existing;

    const team = payload.team === "away" ? "away" : "home";
    const role = String(payload.role || "CM").toUpperCase();
    const candidates = actors.filter(
      (actor) => actor.team === team && actor.role !== "GK" && !actor.isUser,
    );
    const hasVacancy = actors.filter(a => a.team === team).length < (teams[team].redCard ? 10 : 11);
    const outgoing = hasVacancy ? null :
      candidates.find((actor) => actor.role === role)
      || candidates.slice().sort(
        (a, b) => Math.abs(b.anchorX - 50) - Math.abs(a.anchorX - 50),
      )[0]
      || null;

    if (outgoing) removeActor(outgoing.actorId);

    const runtime = initialActor(
      {
        ...payload,
        team,
        visual_profile: {
          ...(payload.visual_profile || {}),
          is_user: true,
          kit_slot: team,
        },
      },
      plan,
    );
    runtime.isUser = true;

    if (outgoing) {
      runtime.x = outgoing.x;
      runtime.y = outgoing.y;
      runtime.anchorX = outgoing.anchorX;
      runtime.anchorY = outgoing.anchorY;
      runtime.targetX = outgoing.targetX;
      runtime.targetY = outgoing.targetY;
    }

    actors.push(runtime);
    return runtime;
  }

  function switchEnds() {
    for (const team of ["home", "away"]) teams[team].direction *= -1;
    for (const actor of actors) {
      actor.x = 100 - actor.x;
      actor.anchorX = 100 - actor.anchorX;
      actor.targetX = 100 - actor.targetX;
      actor.heading = Math.PI - actor.heading;
      actor.vx *= -1;
    }
    ball.x = 100 - ball.x;
    if (ball.action) { ball.action.from.x = 100-ball.action.from.x; ball.action.to.x = 100-ball.action.to.x; }
    if (!ball.action && ball.ownerActorId) {
      ballController.control(ball.ownerActorId);
    }
    phaseElapsed = 0;
    attackingPhase = "BUILDUP";
    return true;
  }

  function reshapeForRedCard(team, preferredActorId = null) {
    const side = team === "away" ? "away" : "home";
    if (preferredActorId && !actors.some(a => a.actorId === preferredActorId)) return null;
    let removed = preferredActorId ? removeActor(preferredActorId) : null;

    if (!removed) {
      const fallback = actors
        .filter((actor) => actor.team === side && actor.role !== "GK")
        .sort(
          (a, b) => Math.abs(b.anchorX - 50) - Math.abs(a.anchorX - 50),
        )[0];
      if (fallback) removed = removeActor(fallback.actorId);
    }

    const outfield = actors
      .filter((actor) => actor.team === side && actor.role !== "GK")
      .sort((a, b) => a.anchorX - b.anchorX || a.anchorY - b.anchorY);

    outfield.forEach((actor, index) => {
      const point = TEN_MAN_SHAPES.compact[Math.min(index, 8)];
      const x = teams[side].direction > 0 ? point[0] : 100 - point[0];
      actor.anchorX = x;
      actor.anchorY = point[1];
      actor.targetX = x;
      actor.targetY = point[1];
      actor.tacticalIntent = "tenManShape";
    });

    teams[side].redCard = true;
    return removed;
  }

  function prepareSetPiece(kind, visual = {}) {
    const side =
      visual.side === "away" ? "away"
      : visual.side === "home" ? "home"
      : possessionTeam;

    attackingPhase = "SET_PIECE";
    phaseElapsed = 0;
    possessionTeam = side;

    const direction = teams[side].direction;
    const outfield = actors.filter(
      (actor) => actor.team === side && actor.role !== "GK",
    );
    const kicker = (kind==='goal_kick'?actors.find(a=>a.team===side&&a.role==='GK'):null) || outfield.find(
      (actor) => ATTACK_ROLES.has(actor.role) || WIDE_ROLES.has(actor.role),
    ) || outfield[0] || null;

    if (!kicker) return 0;

    let x = Number(visual.ball_start?.[0] ?? (direction > 0 ? 62 : 38));
    let y = Number(visual.ball_start?.[1] ?? 50);

    if (kind === "restart") {
      x=50;y=50;
    } else if (kind === "goal_kick") {
      x=direction>0?6:94;y=50;
    } else if (kind === "penalty") {
      x = direction > 0 ? 88 : 12;
      y = 50;
    } else if (kind === "corner") {
      x = direction > 0 ? 97 : 3;
      y = y < 50 ? 7 : 93;
    } else if (kind === "throw_in") {
      y = y < 50 ? 5 : 95;
    }

    kicker.x = x - (kind === "penalty" ? direction * 2.4 : 0);
    kicker.y = y;
    kicker.vx = 0;
    kicker.vy = 0;
    ball.x = x;
    ball.y = y;
    ball.height = 0;
    ballController.control(kicker.actorId);

    eventClock = 0;

    if (kind === "penalty") {
      eventOverrideUntil = .55;
      animationController.play(kicker.actorId, "SHOOT", {
        duration: .38,
        priority: 8,
      });
      return .45;
    }

    const receivers = outfield
      .filter((actor) => actor.actorId !== kicker.actorId)
      .sort((a, b) => {
        const attackA = ATTACK_ROLES.has(a.role) ? 0 : 1;
        const attackB = ATTACK_ROLES.has(b.role) ? 0 : 1;
        const goalX = direction > 0 ? 94 : 6;
        return (
          attackA - attackB
          || Math.abs(a.x - goalX) - Math.abs(b.x - goalX)
          || a.actorId.localeCompare(b.actorId)
        );
      });

    const receiver = receivers[0] || null;
    if (!receiver) return .3;

    if (kind === "corner") {
      const boxX = direction > 0 ? 88 : 12;
      const boxY = y < 50 ? 42 : 58;
      receiver.x = boxX;
      receiver.y = boxY;
      receiver.vx = 0;
      receiver.vy = 0;

      const support = receivers.slice(1, 3);
      support.forEach((actor, index) => {
        actor.x = boxX - direction * (3 + index * 2);
        actor.y = index === 0 ? 50 : (y < 50 ? 62 : 38);
        actor.vx = 0;
        actor.vy = 0;
      });

      animationController.play(kicker.actorId, "CROSS", {
        duration: .42,
        priority: 8,
      });
      animationController.play(receiver.actorId, "RECEIVE", {
        duration: .74,
        priority: 6,
      });
      ballController.cross(
        {x, y},
        {x: receiver.x, y: receiver.y},
        {
          targetActorId: receiver.actorId,
          duration: .68,
          maxHeight: 3.8,
        },
      );
      eventOverrideUntil = .78;
      return .68;
    }

    if (kind === "throw_in") {
      receiver.x = clamp(x + direction * 8, 8, 92);
      receiver.y = clamp(y + (y < 50 ? 8 : -8), 8, 92);
      animationController.play(receiver.actorId, "RECEIVE", {
        duration: .52,
        priority: 5,
      });
      ballController.pass(
        {x, y},
        {x: receiver.x, y: receiver.y},
        {
          targetActorId: receiver.actorId,
          duration: .48,
          maxHeight: 1.1,
        },
      );
      eventOverrideUntil = .58;
      return .48;
    }

    if (kind === "free_kick") {
      const targetX = clamp(x + direction * 18, 8, 92);
      const targetY = clamp(50 + (receiver.y - 50) * .45, 12, 88);
      receiver.x = targetX;
      receiver.y = targetY;
      animationController.play(kicker.actorId, "LONG_PASS", {
        duration: .44,
        priority: 7,
      });
      animationController.play(receiver.actorId, "RECEIVE", {
        duration: .68,
        priority: 5,
      });
      ballController.longBall(
        {x, y},
        {x: targetX, y: targetY},
        {
          targetActorId: receiver.actorId,
          duration: .64,
          maxHeight: 3.2,
        },
      );
      eventOverrideUntil = .74;
      return .64;
    }

    animationController.play(kicker.actorId, "PASS", {
      duration: .32,
      priority: 5,
    });
    animationController.play(receiver.actorId, "RECEIVE", {
      duration: .48,
      priority: 5,
    });
    const duration=launchPass(receiver);
    eventOverrideUntil = duration+.1;
    return duration;
  }

  function beginAuthoritativeEvent(
    payload = {},
  ) {
    const side =
      payload.side === "away"
        ? "away"
        : "home";

    const actor = eventActor(
      side,
      payload.actorId,
    );

    if (!actor) return .42;

    possessionTeam = side;

    const start = {...ball};
    buildup = null;

    const target =
      Array.isArray(payload.ballTarget)
        ? {
            x: Number(payload.ballTarget[0]),
            y: Number(payload.ballTarget[1]),
          }
        : {
            x:
              teams[side].direction > 0
                ? 98
                : 2,
            y: 50,
          };

    // Only the outcome/identity are authoritative; never relocate the live scene.
    const direction = teams[side].direction;
    if (payload.outcome === "GOAL") { target.x = direction > 0 ? 101 : -1; target.y = clamp(target.y,46,54); }
    if (payload.outcome === "MISS") { target.x = direction > 0 ? 103 : -3; target.y = target.y < 50 ? 42 : 58; }
    if (payload.outcome === "SAVE") {
      const goalie = keeperForAttackingSide(side);
      if (goalie) { target.x = goalie.x; target.y = goalie.y; }
    }
    actor.heading = Math.atan2(target.y-start.y,target.x-start.x);
    actor.vx = 0;
    actor.vy = 0;

    animationController.play(
      actor.actorId,
      "SHOOT",
      {
        duration: .42,
        priority: 10,
      },
    );

    const keeper =
      keeperForAttackingSide(side);

    if (
      keeper
      && payload.outcome !== "MISS"
    ) {
      animationController.play(
        keeper.actorId,
        "GK_DIVE",
        {
          duration: .55,
          priority: 10,
        },
      );
    }

    const duration =
      payload.outcome === "GOAL"
        ? .52
        : .46;

    ballController.shoot(
      start,
      target,
      {
        duration,
        maxHeight:
          payload.outcome === "GOAL"
            ? 1.2
            : .85,
        settleToOwner: false,
      },
    );

    eventClock = 0;

    eventOverrideUntil =
      payload.outcome === "GOAL"
        ? 1.2
        : .9;
    pendingRestart = payload.outcome === 'GOAL' ? {kind:'restart',side:side==='home'?'away':'home'}
      : payload.outcome === 'MISS' ? {kind:'goal_kick',side:side==='home'?'away':'home'} : null;

    return duration;
  }

  function playKeeperAction(
    action,
    attackingSide,
  ) {
    const keeper =
      keeperForAttackingSide(
        attackingSide === "away"
          ? "away"
          : "home",
      );

    if (!keeper) return;

    if (action === "GK_CATCH") {
      animationController.play(
        keeper.actorId,
        "GK_CATCH",
        {
          duration: .6,
          priority: 10,
        },
      );

      ballController.keeperHold(
        keeper.actorId,
      );

      return;
    }

    if (action === "GK_PARRY") {
      animationController.play(
        keeper.actorId,
        "GK_DIVE",
        {
          duration: .36,
          priority: 10,
        },
      );

      ballController.deflect(
        {
          x: ball.x,
          y: ball.y,
        },
        {
          x:
            keeper.x
            + teams[keeper.team].direction * 5,
          y: keeper.y + 6,
        },
        {
          duration: .34,
          maxHeight: 1.1,
          settleToOwner: false,
        },
      );

      return;
    }

    animationController.play(
      keeper.actorId,
      "GK_DIVE",
      {
        duration: .52,
        priority: 10,
      },
    );
  }

  function updatePressing() {
    const defendingTeam = possessionTeam === "home" ? "away" : "home";
    const defending = teams[defendingTeam];
    const nearest = nearestOutfieldActors(actors, defendingTeam, ball, 2);

    defending.primaryPresserId = nearest[0]?.actorId || null;
    defending.coverActorId = nearest[1]?.actorId || null;
  }

  function baseTarget(actor) {
    const state = teams[actor.team];
    // Receivers meet the committed flight endpoint; ready shooters retain their touch.
    if(ball.action?.targetActorId===actor.actorId)return ball.action.to;
    if(buildup?.ready&&buildup.shooterId===actor.actorId)return {x:actor.x,y:actor.y};
    if(!ball.action&&!ball.ownerActorId&&!pendingRestart&&!buildup){
      const nearest=actors.filter(a=>a.role!=='GK').sort((a,b)=>distance(a,ball)-distance(b,ball))[0];
      if(nearest===actor)return {x:ball.x,y:ball.y};
    }

    const possessionXShift = state.direction * (
      state.possession
        ? state.phase === "FINAL_THIRD"
          ? 8
          : state.phase === "TRANSITION_ATTACK"
            ? 10
            : 4
        : -2
    );

    const ballSideShift = (ball.y - 50) * (state.possession ? .25 : .32);
    const widthDelta = (actor.anchorY - 50) * (state.width - 1);
    const compactY = 50 + (actor.anchorY - 50) / state.compactness;
    const role = roleMovementOffset(actor, state, state.phase, ball, phaseIndex);

    let x = actor.anchorX + possessionXShift + state.direction * state.lineHeight + role.x;
    let y = compactY + ballSideShift + widthDelta + role.y;
    let intent = role.intent;

    if (state.primaryPresserId === actor.actorId) {
      const pressureDistance = 2.2 + (1 - state.pressIntensity) * 3.2;
      x = ball.x - state.direction * pressureDistance;
      y = ball.y;
      intent = "press";
    } else if (state.coverActorId === actor.actorId) {
      x = (actor.anchorX + ball.x) * .5;
      y = (actor.anchorY + ball.y) * .5;
      intent = "cover";
    }

    if (actor.role === "GK") {
      const ownGoalX = state.direction > 0 ? 5 : 95;
      x = ownGoalX + state.direction * clamp(Math.abs(ball.x - ownGoalX) * .06, 1, 7);
      y = 50 + (ball.y - 50) * .16;
    } else if(ball.ownerActorId===actor.actorId && state.possession && !buildup) {
      x=actor.x+state.direction*5;
      y=actor.y+(50-actor.y)*.08;
      intent="carry";
    }

    actor.tacticalIntent = intent;

    return {
      x: clamp(x, actor.role === "GK" ? 2 : 4, actor.role === "GK" ? 98 : 96),
      y: clamp(y, 6, 94),
    };
  }

  function updateBall(dt) {
    const oldOwner=ball.ownerActorId;
    ballController.update(dt, actors);
    if(!ball.action&&!ball.ownerActorId&&!pendingRestart&&!buildup&&eventClock>=eventOverrideUntil){
      const recovery=actors.find(a=>distance(a,ball)<1.1);
      if(recovery)ballController.control(recovery.actorId);
    }

    const newOwner = ball.ownerActorId
      ? actors.find((actor) => actor.actorId === ball.ownerActorId)
      : null;

    if (newOwner) {
      if(newOwner.team!==possessionTeam){possessionTeam=newOwner.team;attackingPhase="TRANSITION_ATTACK";phaseElapsed=0;}
      carrier = newOwner;
      if(oldOwner!==newOwner.actorId)animationController.play(newOwner.actorId,"RECEIVE",{duration:.2,priority:2});
    }
  }

  function update(dtSeconds, context = {}) {
    const dt = clamp(Number(dtSeconds) || 0, 0, .05);
    phaseElapsed += dt * teams[possessionTeam].tempo;
    passClock += dt * teams[possessionTeam].tempo;
    eventClock += dt;
    animationController.update(dt);

    if (pendingRestart && eventClock>=eventOverrideUntil && !ball.action) {
      const restart=pendingRestart;pendingRestart=null;
      prepareSetPiece(restart.kind,{side:restart.side});
    }
    if (phaseElapsed >= phaseDuration && eventClock >= eventOverrideUntil && !ball.action && !buildup) {
      resetPhase();
    }

    if (
      eventClock >= eventOverrideUntil
      && !buildup
      && passClock >= nextPassAt
      && !ball.action
      && ball.ownerActorId
    ) {
      schedulePass();
      passClock = 0;
      nextPassAt = .85 + rng() * 1.15;
    }

    updateTeamStates(context);
    updatePressing();

    for (const actor of actors) {
      const target = baseTarget(actor);
      actor.targetX = target.x;
      actor.targetY = target.y;

      const teamTempo = teams[actor.team].tempo;
      const staminaPenalty =
        Number(context.minute || 0) >= 70
          ? .86 + actor.staminaFactor * .14
          : 1;

      const actionAnimation = animationController.getState(actor.actorId);
      if (!["SHOOT", "GK_DIVE", "CELEBRATE"].includes(actionAnimation)) integrateMovement(
        actor,
        target,
        dt,
        {
          maxSpeed: actor.maxSpeed * teamTempo * staminaPenalty,
          acceleration: actor.acceleration * staminaPenalty,
          deceleration: actor.deceleration,
        },
      );

      actor.animationProgress = animationController.getProgress(actor.actorId);

      if (actionAnimation) {
        actor.animationState = actionAnimation;
      } else if (actor.role === "GK") {
        actor.animationState = "GK_SET";
      } else if (
        actor.tacticalIntent === "press"
        && Math.hypot(actor.vx, actor.vy) > 5
      ) {
        actor.animationState = "SPRINT";
      } else if (ball.ownerActorId === actor.actorId) {
        actor.animationState = "DRIBBLE";
      } else {
        actor.animationState = null;
      }
    }

    // Resolve body overlap gently in metres, without deciding fouls or possession.
    for (let i=0;i<actors.length;i++) for (let j=i+1;j<actors.length;j++) {
      const a=actors[i],b=actors[j];
      if ([a.animationState,b.animationState].some(state=>["SHOOT","GK_DIVE"].includes(state))) continue;
      let dx=(b.x-a.x)*1.05,dy=(b.y-a.y)*.68,d=Math.hypot(dx,dy);
      if (d>=.52) continue;
      if (d<.001) {dx=(i+j)%2?1:-1;dy=0;d=1;}
      const push=Math.min(.04,(.52-Math.hypot((b.x-a.x)*1.05,(b.y-a.y)*.68))/2);
      a.x=clamp(a.x-dx/d*push/1.05,0,100);a.y=clamp(a.y-dy/d*push/.68,0,100);
      b.x=clamp(b.x+dx/d*push/1.05,0,100);b.y=clamp(b.y+dy/d*push/.68,0,100);
    }
    updateBall(dt);
    advanceBuildup(dt);

    return {
      actors,
      ball,
      teams,
      possessionTeam,
      phase: attackingPhase,
      phaseIndex,
      presentationFocus: currentPresentationFocus(ball,actors),
    };
  }

  return {
    update,
    removeActor,
    activateActor,
    switchEnds,
    reshapeForRedCard,
    prepareSetPiece,
    beginAuthoritativeEvent,
    beginAuthoritativeBuildup,
    isAuthoritativeBuildupReady: () => Boolean(buildup?.ready),
    cancelAuthoritativeBuildup,
    playKeeperAction,
    celebrate(side) {
      for (const actor of actors.filter(a=>a.team===side&&a.role!=="GK")) animationController.play(actor.actorId,"CELEBRATE",{duration:.7,priority:10});
    },
    getState() {
      return {
        actors,
        ball,
        teams,
        possessionTeam,
        phase: attackingPhase,
        phaseIndex,
        presentationFocus: currentPresentationFocus(ball,actors),
      };
    },
  };
}
