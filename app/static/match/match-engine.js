export function createMatchEngine({
  tactical,
  renderer,
  getMatchContext = () => ({}),
  onStatus = () => {},
}) {
  let frameId = 0;
  let running = false;
  let paused = false;
  let speed = 1;
  let lastTimestamp = 0;
  let animationElapsed = 0;
  let hiddenPause = false;


  let halftimeHandled = false;

  function handleHalftime() {
    if (halftimeHandled) return false;
    halftimeHandled = true;
    tactical.switchEnds();
    animationElapsed = 0;
    lastTimestamp = performance.now();
    return true;
  }

  function handleSubstitution(event) {
    const visual = event?.visual || {};
    const kind = String(visual.kind || event?.kind || "").toLowerCase();
    if (kind === "substitution_on") return tactical.activateActor(visual.actor || null);
    if (kind === "substitution_off") return tactical.removeActor(visual.actor_id || null);
    return null;
  }

  function handleCard(event) {
    const visual = event?.visual || {};
    const kind = String(visual.kind || event?.kind || "").toLowerCase();
    if (kind !== "red_card") return null;
    return tactical.reshapeForRedCard(visual.side, visual.actor_id || null);
  }

  function handlePenalty(event) {
    return tactical.prepareSetPiece("penalty", event?.visual || {});
  }

  function handleCorner(event) {
    return tactical.prepareSetPiece("corner", event?.visual || {});
  }

  function handleThrowIn(event) {
    return tactical.prepareSetPiece("throw_in", event?.visual || {});
  }

  function handleFreeKick(event) {
    return tactical.prepareSetPiece("free_kick", event?.visual || {});
  }

  function setSpeed(multiplier) {
    const next = Number(multiplier);
    speed = [1, 2, 4].includes(next) ? next : 1;
    return speed;
  }

  function pause(reason = "manual") {
    paused = true;
    if (reason === "hidden") hiddenPause = true;
  }

  function resume(reason = "manual") {
    if (reason === "hidden") hiddenPause = false;
    if (!hiddenPause) {
      paused = false;
      lastTimestamp = performance.now();
    }
  }

  function tick(timestamp) {
    if (!running) return;

    const rawDt = lastTimestamp ? (timestamp - lastTimestamp) / 1000 : 0;
    lastTimestamp = timestamp;

    if (!paused) {
      const dt = Math.min(.04, Math.max(0, rawDt)) * speed;
      animationElapsed += dt;

      const context = getMatchContext();
      const state = tactical.update(dt, context);

      renderer.render({
        actors: state.actors,
        ball: state.ball,
        animationPhase: (animationElapsed * .72) % 1,
      });

      onStatus({
        phase: state.phase,
        possessionTeam: state.possessionTeam,
        home: state.teams.home,
        away: state.teams.away,
      });
    }

    frameId = requestAnimationFrame(tick);
  }

  function start() {
    if (running) return;
    running = true;
    lastTimestamp = performance.now();
    frameId = requestAnimationFrame(tick);
  }

  function destroy() {
    running = false;
    cancelAnimationFrame(frameId);
    document.removeEventListener("visibilitychange", onVisibilityChange);
  }

  function onVisibilityChange() {
    if (document.hidden) {
      pause("hidden");
    } else {
      resume("hidden");
    }
  }

  document.addEventListener("visibilitychange", onVisibilityChange);

  return {
    start,
    destroy,
    pause,
    resume,
    setSpeed,
    handleHalftime,
    handleSubstitution,
    handleCard,
    handlePenalty,
    handleCorner,
    handleThrowIn,
    handleFreeKick,
    isPaused: () => paused,
    getSpeed: () => speed,
  };
}
