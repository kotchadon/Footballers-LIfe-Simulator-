function approach(current, target, maxDelta) {
  return current + Math.max(-maxDelta, Math.min(maxDelta, target - current));
}

export function integrateMovement(actor, target, dtSeconds, limits = {}) {
  const maxSpeed = Number(limits.maxSpeed ?? actor.maxSpeed ?? 20);
  const acceleration = Number(limits.acceleration ?? actor.acceleration ?? 45);
  const deceleration = Number(limits.deceleration ?? actor.deceleration ?? 55);
  const dx = Number(target.x) - Number(actor.x);
  const dy = Number(target.y) - Number(actor.y);
  const distance = Math.hypot(dx, dy);
  const desiredSpeed = Math.min(maxSpeed, distance * 2.4);
  const currentSpeed = Math.hypot(actor.vx || 0, actor.vy || 0);
  const desiredVx = distance > 0.001 ? dx / distance * desiredSpeed : 0;
  const desiredVy = distance > 0.001 ? dy / distance * desiredSpeed : 0;
  const rate = desiredSpeed >= currentSpeed ? acceleration : deceleration;
  const maxDelta = rate * Math.max(0, Number(dtSeconds) || 0);

  actor.vx = approach(Number(actor.vx) || 0, desiredVx, maxDelta);
  actor.vy = approach(Number(actor.vy) || 0, desiredVy, maxDelta);
  actor.x = Math.max(0, Math.min(100, Number(actor.x) + actor.vx * dtSeconds));
  actor.y = Math.max(0, Math.min(100, Number(actor.y) + actor.vy * dtSeconds));

  if (Math.hypot(actor.vx, actor.vy) > 0.05) actor.heading = Math.atan2(actor.vy, actor.vx);
  return actor;
}
