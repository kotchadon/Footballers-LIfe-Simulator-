export const REAL_SECONDS_PER_MATCH_MINUTE = 2;
const STEP = 1 / 60;

export function createMatchEngine({
  tactical, renderer, camera = null,
  getMatchContext = () => ({}), onStatus = () => {},
}) {
  let frameId = 0;
  let running = false;
  let started = false;
  let paused = false;
  let manualPause = false;
  let hiddenPause = Boolean(document.hidden);
  let finished = false;
  let destroyed = false;
  let speed = 1;
  let lastTimestamp = 0;
  let animationElapsed = 0;
  let accumulator = 0;
  let visualEnabled = true;
  let visualMinute = 0;
  let halftimeHandled = false;
  let lastFrame = null;
  const waiters = new Set();
  const active = () => !finished && !destroyed;

  function cancelFrame() {
    if (frameId) cancelAnimationFrame(frameId);
    frameId = 0;
  }
  function schedule() {
    paused = manualPause || hiddenPause;
    if (active() && running && !paused && !frameId) frameId = requestAnimationFrame(tick);
  }
  function draw(frame) {
    if (!visualEnabled || destroyed) return;
    try { renderer.render(frame); }
    catch (error) {
      visualEnabled = false;
      console.error("Match visual renderer disabled:", error);
    }
  }
  function capture(state, cameraState) {
    lastFrame = structuredClone({
      actors: state.actors, ball: state.ball, camera: cameraState,
      animationPhase: (animationElapsed * .72) % 1,
      elapsed: animationElapsed, visualMinute,
    });
    draw(lastFrame);
  }
  function repaint() {
    if (destroyed) return false;
    if (!lastFrame) {
      const state = tactical.getState();
      capture(state, camera?.update?.(0, state) || null);
    } else draw(lastFrame);
    return true;
  }
  function refresh() {
    if (!active()) return false;
    const state = tactical.getState();
    capture(state, lastFrame?.camera || camera?.update?.(0, state) || null);
    return true;
  }
  function handleHalftime() {
    if (!active() || halftimeHandled) return false;
    halftimeHandled = true;
    tactical.switchEnds();
    lastTimestamp = performance.now();
    accumulator = 0;
    return true;
  }
  function handleSubstitution(event) {
    if (!active()) return null;
    const visual = event?.visual || {};
    const kind = String(visual.kind || event?.kind || "").toLowerCase();
    if (kind === "substitution_on") return tactical.activateActor(visual.actor || null);
    if (kind === "substitution_off") return tactical.removeActor(visual.actor_id || null);
    return null;
  }
  function handleCard(event) {
    if (!active()) return null;
    const visual = event?.visual || {};
    const kind = String(visual.kind || event?.kind || "").toLowerCase();
    if (kind !== "red_card") return null;
    return tactical.reshapeForRedCard(visual.side, visual.actor_id || null);
  }
  function handlePenalty(event) {
    return active() ? tactical.prepareSetPiece("penalty", event?.visual || {}) : 0;
  }
  function handleCorner(event) {
    return active() ? tactical.prepareSetPiece("corner", event?.visual || {}) : 0;
  }
  function handleThrowIn(event) {
    return active() ? tactical.prepareSetPiece("throw_in", event?.visual || {}) : 0;
  }
  function handleFreeKick(event) {
    return active() ? tactical.prepareSetPiece("free_kick", event?.visual || {}) : 0;
  }
  function setSpeed(multiplier) {
    if (!active()) return speed;
    const next = Number(multiplier);
    speed = [1, 2, 4].includes(next) ? next : 1;
    return speed;
  }
  function pause(reason = "manual") {
    if (!active()) return false;
    if (reason === "hidden") hiddenPause = true;
    else manualPause = true;
    paused = true;
    cancelFrame();
    return true;
  }
  function resume(reason = "manual") {
    if (!active()) return false;
    if (reason === "hidden") hiddenPause = false;
    else manualPause = false;
    paused = manualPause || hiddenPause;
    lastTimestamp = performance.now();
    accumulator = 0;
    schedule();
    return !paused;
  }
  function settleWaiters(cancelled = false) {
    for (const waiter of waiters) {
      if (cancelled || animationElapsed + 1e-9 >= waiter.until) {
        waiters.delete(waiter);
        waiter.resolve(!cancelled);
      }
    }
  }
  function waitForSimulation(seconds) {
    if (!active()) return Promise.resolve(false);
    const duration = Math.max(0, Number(seconds) || 0);
    if (!duration) return Promise.resolve(true);
    return new Promise(resolve => waiters.add({until: animationElapsed + duration, resolve}));
  }
  function tick(timestamp) {
    frameId = 0;
    if (!active() || !running || paused) return;
    const rawDt = Math.max(0, (timestamp - lastTimestamp) / 1000);
    lastTimestamp = timestamp;
    accumulator += Math.min(.1, rawDt) * speed;
    let state = tactical.getState();
    let cameraState = lastFrame?.camera || null;
    let steps = 0;
    while (accumulator + 1e-9 >= STEP && steps < 24 && active()) {
      animationElapsed += STEP;
      visualMinute = Math.min(90, animationElapsed / REAL_SECONDS_PER_MATCH_MINUTE);
      state = tactical.update(STEP, {...getMatchContext(), visualMinute});
      cameraState = camera?.update?.(STEP, state) || null;
      accumulator = Math.max(0, accumulator - STEP);
      steps++;
    }
    if (steps) {
      capture(state, cameraState);
      onStatus({
        phase: state.phase, possessionTeam: state.possessionTeam,
        home: state.teams.home, away: state.teams.away,
        ball: state.ball, visualMinute,
      });
      settleWaiters();
    }
    schedule();
  }
  function emphasizeEvent(kind, payload = {}) {
    if (active()) camera?.emphasize?.(kind, payload);
  }
  function skipToNextMajorEvent() {
    if (active()) window.dispatchEvent(new CustomEvent("footy:skip-next-major-event"));
  }
  function start() {
    if (!active() || started) return false;
    started = true;
    running = true;
    lastTimestamp = performance.now();
    repaint();
    schedule();
    return true;
  }
  function finish() {
    if (!active()) return false;
    finished = true;
    running = false;
    paused = true;
    cancelFrame();
    settleWaiters(true);
    const state = tactical.getState();
    capture(state, lastFrame?.camera || camera?.update?.(0, state) || null);
    return true;
  }
  function destroy() {
    if (destroyed) return;
    destroyed = true;
    running = false;
    cancelFrame();
    settleWaiters(true);
    document.removeEventListener("visibilitychange", onVisibilityChange);
  }
  function onVisibilityChange() {
    if (document.hidden) pause("hidden");
    else resume("hidden");
  }
  document.addEventListener("visibilitychange", onVisibilityChange);
  return {
    start, destroy, pause, resume, finish, repaint, refresh, waitForSimulation,
    setSpeed, emphasizeEvent, skipToNextMajorEvent,
    handleHalftime, handleSubstitution, handleCard,
    handlePenalty, handleCorner, handleThrowIn, handleFreeKick,
    isPaused: () => paused, isFinished: () => finished,
    isDestroyed: () => destroyed, getSpeed: () => speed,
  };
}
