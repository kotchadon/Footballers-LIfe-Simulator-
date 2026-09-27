function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value) || 0));
}

function smooth(current, target, dt, response) {
  const alpha = 1 - Math.exp(-Math.max(0, dt) * response);
  return current + (target - current) * alpha;
}

const MIN_ZOOM = .955;
const MAX_ZOOM = .995;
const MAX_PAN_PERCENT = 1.6;

export function createCameraController({reducedMotion = false} = {}) {
  const state = {
    panX: 0,
    panY: 0,
    zoom: reducedMotion ? .972 : .965,
    shakeX: 0,
    shakeY: 0,
    eventFocusX: 50,
    emphasis: null,
  };

  let elapsed = 0;
  let emphasisTime = 0;
  let emphasisDuration = 0;
  let emphasisStrength = 0;

  function emphasize(kind, payload = {}) {
    const eventKind = String(kind || "").toUpperCase();
    const target = Array.isArray(payload.ball_target)
      ? payload.ball_target
      : Array.isArray(payload.ballTarget)
        ? payload.ballTarget
        : null;

    // Emphasis affects zoom, never the location of an unreached event target.
    state.emphasis = eventKind || null;

    if (eventKind === "GOAL") {
      emphasisDuration = reducedMotion ? .42 : .72;
      emphasisStrength = reducedMotion ? .24 : 1;
    } else if (["SAVE", "MISS", "SHOT"].includes(eventKind)) {
      emphasisDuration = reducedMotion ? .28 : .46;
      emphasisStrength = reducedMotion ? .16 : .55;
    } else {
      emphasisDuration = .24;
      emphasisStrength = reducedMotion ? .08 : .24;
    }

    emphasisTime = emphasisDuration;
  }

  function update(dtSeconds, tacticalState = {}) {
    const dt = clamp(dtSeconds, 0, .05);
    elapsed += dt;
    emphasisTime = Math.max(0, emphasisTime - dt);

    const ballX = clamp(tacticalState?.ball?.x ?? 50, 0, 100);
    const liveFocusX = clamp(tacticalState.presentationFocus?.x ?? ballX,ballX-7,ballX+7);
    const normalized = (liveFocusX - 50) / 50;
    const targetPanX = clamp(
      normalized * MAX_PAN_PERCENT,
      -MAX_PAN_PERCENT,
      MAX_PAN_PERCENT,
    );

    const pulse = emphasisDuration > 0
      ? emphasisTime / emphasisDuration
      : 0;

    const targetZoom = clamp(
      (reducedMotion ? .974 : .968)
        + pulse * (reducedMotion ? .006 : .022),
      MIN_ZOOM,
      MAX_ZOOM,
    );

    state.panX = smooth(
      state.panX,
      targetPanX,
      dt,
      reducedMotion ? 2.4 : 3.8,
    );
    state.panY = smooth(state.panY, 0, dt, reducedMotion ? 2.4 : 4.2);
    state.zoom = smooth(
      state.zoom,
      targetZoom,
      dt,
      reducedMotion ? 2.0 : 4.0,
    );

    if (!reducedMotion && emphasisTime > 0 && state.emphasis === "GOAL") {
      const envelope = pulse * emphasisStrength;
      state.shakeX = Math.sin(elapsed * 46) * .16 * envelope;
      state.shakeY = Math.sin(elapsed * 61 + .8) * .08 * envelope;
    } else {
      state.shakeX = smooth(state.shakeX, 0, dt, 12);
      state.shakeY = smooth(state.shakeY, 0, dt, 12);
    }

    if (emphasisTime <= 0) state.emphasis = null;
    return {...state};
  }

  return {
    update,
    emphasize,
    getState: () => ({...state}),
  };
}
