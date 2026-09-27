export const BALL_STATES = Object.freeze({
  CONTROLLED: "CONTROLLED",
  PASS: "PASS",
  LONG_BALL: "LONG_BALL",
  CROSS: "CROSS",
  SHOT: "SHOT",
  DEFLECTION: "DEFLECTION",
  LOOSE: "LOOSE",
  KEEPER_HELD: "KEEPER_HELD",
});

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function createBallController(initialBall = {}) {
  const state = {
    x: Number(initialBall.x ?? 50),
    y: Number(initialBall.y ?? 50),
    height: Number(initialBall.height ?? 0),
    ownerActorId: initialBall.ownerActorId ?? initialBall.owner_actor_id ?? null,
    state: initialBall.state || BALL_STATES.LOOSE,
    targetActorId: null,
    action: null,
  };

  function control(actorId) {
    state.ownerActorId = actorId || null;
    state.targetActorId = null;
    state.state = actorId ? BALL_STATES.CONTROLLED : BALL_STATES.LOOSE;
    state.height = 0;
    state.action = null;
  }

  function launch(kind, from, to, options = {}) {
    state.ownerActorId = null;
    state.targetActorId = options.targetActorId || null;
    state.state = kind;
    state.x = Number(from.x);
    state.y = Number(from.y);
    state.height = Number(from.height || 0);
    state.action = {
      kind,
      from: {x: Number(from.x), y: Number(from.y)},
      to: {x: Number(to.x), y: Number(to.y)},
      elapsed: 0,
      duration: Math.max(.18, Number(options.duration || .7)),
      maxHeight: Math.max(0, Number(options.maxHeight || 0)),
      targetActorId: options.targetActorId || null,
      settleToOwner: options.settleToOwner !== false,
    };
  }

  function pass(from, to, options = {}) {
    launch(BALL_STATES.PASS, from, to, {
      ...options,
      duration: options.duration || .62,
      maxHeight: options.maxHeight || .22,
    });
  }

  function longBall(from, to, options = {}) {
    launch(BALL_STATES.LONG_BALL, from, to, {
      ...options,
      duration: options.duration || .95,
      maxHeight: options.maxHeight || 4.6,
    });
  }

  function cross(from, to, options = {}) {
    launch(BALL_STATES.CROSS, from, to, {
      ...options,
      duration: options.duration || .82,
      maxHeight: options.maxHeight || 3.8,
    });
  }

  function shoot(from, to, options = {}) {
    launch(BALL_STATES.SHOT, from, to, {
      ...options,
      duration: options.duration || .44,
      maxHeight: options.maxHeight || 1.1,
      settleToOwner: false,
    });
  }

  function deflect(from, to, options = {}) {
    launch(BALL_STATES.DEFLECTION, from, to, {
      ...options,
      duration: options.duration || .38,
      maxHeight: options.maxHeight || 1.4,
      settleToOwner: options.settleToOwner ?? false,
    });
  }

  function keeperHold(actorId) {
    state.ownerActorId = actorId || null;
    state.targetActorId = null;
    state.state = BALL_STATES.KEEPER_HELD;
    state.action = null;
    state.height = 1.2;
  }

  function updateControlled(dtSeconds, actorMap) {
    const owner = actorMap.get(state.ownerActorId);
    if (!owner) {
      control(null);
      return;
    }

    const speed = Math.hypot(owner.vx || 0, owner.vy || 0);
    const heading = Number(owner.heading || 0);
    const touchLength = owner.role === "GK" ? .22 : clamp(.55 + speed * .025, .55, .82);
    const targetX = owner.x + Math.cos(heading) * touchLength / 1.05;
    const targetY = owner.y + Math.sin(heading) * touchLength / .68;
    const response = clamp(dtSeconds * 12, 0, 1);

    state.x = lerp(state.x, targetX, response);
    state.y = lerp(state.y, targetY, response);
    state.height = state.state === BALL_STATES.KEEPER_HELD ? 1.2 : 0;
  }

  function updateAction(dtSeconds, actorMap) {
    const action = state.action;
    if (!action) return;

    action.elapsed += Math.max(0, dtSeconds);
    const progress = clamp(action.elapsed / action.duration, 0, 1);
    const eased = progress * progress * (3 - 2 * progress);

    const liveTarget = action.targetActorId
      ? actorMap.get(action.targetActorId)
      : null;

    const targetX = liveTarget?.x ?? action.to.x;
    const targetY = liveTarget?.y ?? action.to.y;

    state.x = lerp(action.from.x, targetX, eased);
    state.y = lerp(action.from.y, targetY, eased);
    state.height = 4 * action.maxHeight * progress * (1 - progress);

    if (progress >= 1) {
      const targetActorId = action.targetActorId;
      const settle = action.settleToOwner && targetActorId;
      state.action = null;

      if (settle) {
        control(targetActorId);
      } else {
        state.ownerActorId = null;
        state.targetActorId = null;
        state.state = BALL_STATES.LOOSE;
        state.height = 0;
      }
    }
  }

  function update(dtSeconds, actors = []) {
    const actorMap = actors instanceof Map
      ? actors
      : new Map(actors.map((actor) => [actor.actorId, actor]));

    if (state.action) {
      updateAction(dtSeconds, actorMap);
    } else if (
      state.state === BALL_STATES.CONTROLLED
      || state.state === BALL_STATES.KEEPER_HELD
    ) {
      updateControlled(dtSeconds, actorMap);
    }

    return state;
  }

  return {
    state,
    control,
    pass,
    longBall,
    cross,
    shoot,
    deflect,
    keeperHold,
    update,
  };
}
