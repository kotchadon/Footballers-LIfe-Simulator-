import {drawPlayerRig, poseForState} from "./player-rig.js";

export function broadcastProjection(width, height) {
  return (x, y, visualHeight = 0) => {
    const depth = Math.max(0, Math.min(1, Number(y) / 100));
    const left = width * (.035 - .025 * depth);
    const right = width * (.965 + .025 * depth);
    const px = left + (right - left) * (Number(x) / 100);
    const py = height * (.145 + .775 * depth) - Number(visualHeight) * height * .012;
    return {x: px, y: py, scale: .68 + depth * .48};
  };
}

export function createRenderer({canvas, stage, reducedMotion = false, onError = () => {}}) {
  const ctx = canvas.getContext("2d", {alpha: true});
  let width = 1;
  let height = 1;
  let destroyed = false;

  function resize() {
    if (destroyed) return;
    const rect = stage.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawBall(ball, projection) {
    if (!ball) return;
    const p = projection(ball.x, ball.y, ball.height || 0);
    const ground = projection(ball.x, ball.y, 0);
    ctx.save();
    ctx.fillStyle = "rgba(0,0,0,.32)";
    ctx.beginPath();
    ctx.ellipse(ground.x, ground.y + 5 * ground.scale, 4.5 * ground.scale, 2.2 * ground.scale, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f7f4e8";
    ctx.strokeStyle = "#111827";
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 4.4 * p.scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  function render(state) {
    if (destroyed || !ctx) return;
    try {
      ctx.clearRect(0, 0, width, height);
      const projection = broadcastProjection(width, height);
      const actors = [...(state.actors || [])].sort((a, b) => Number(a.y) - Number(b.y));
      for (const actor of actors) {
        const speed = Math.hypot(actor.vx || 0, actor.vy || 0);
        let animationState = actor.animationState || "IDLE";
        if (!actor.animationState) animationState = speed > 10 ? "SPRINT" : speed > 5 ? "RUN" : speed > .5 ? "JOG" : "IDLE";
        const pose = poseForState(animationState, state.animationPhase || 0, speed);
        drawPlayerRig(ctx, actor, pose, projection);
      }
      drawBall(state.ball, projection);
    } catch (error) {
      onError(error);
    }
  }

  function destroy() {
    destroyed = true;
  }

  resize();
  return {resize, render, destroy};
}
