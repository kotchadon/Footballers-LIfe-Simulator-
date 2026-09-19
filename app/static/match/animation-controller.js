export const ACTION_STATES = Object.freeze({
  RECEIVE: "RECEIVE",
  DRIBBLE: "DRIBBLE",
  PASS: "PASS",
  LONG_PASS: "LONG_PASS",
  CROSS: "CROSS",
  SHOOT: "SHOOT",
  GK_DIVE: "GK_DIVE",
});

export function createAnimationController() {
  const active = new Map();

  function play(actorId, state, options = {}) {
    if (!actorId) return;
    active.set(actorId, {
      actorId,
      state,
      elapsed: 0,
      duration: Math.max(.08, Number(options.duration || .34)),
      priority: Number(options.priority || 1),
    });
  }

  function getState(actorId) {
    return active.get(actorId)?.state || null;
  }

  function update(dtSeconds) {
    const dt = Math.max(0, Number(dtSeconds) || 0);
    for (const [actorId, action] of active.entries()) {
      action.elapsed += dt;
      if (action.elapsed >= action.duration) {
        active.delete(actorId);
      }
    }
  }

  function clear(actorId) {
    active.delete(actorId);
  }

  function cancelActor(actorId) {
    active.delete(actorId);
  }

  return {
    play,
    getState,
    update,
    clear,
    cancelActor,
  };
}
