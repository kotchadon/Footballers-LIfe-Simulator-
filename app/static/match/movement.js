// Velocities remain normalized pitch units; physical limits are metres/second.
export function integrateMovement(actor, target, dtSeconds, limits = {}) {
  const dt = Math.max(0, Number(dtSeconds) || 0);
  const maxSpeed = Math.min(10.5, Number(limits.maxSpeed ?? actor.maxSpeed ?? 8));
  const acceleration = Number(limits.acceleration ?? actor.acceleration ?? 6);
  const deceleration = Number(limits.deceleration ?? actor.deceleration ?? 9);
  const dx = (Number(target.x)-actor.x)*1.05, dy = (Number(target.y)-actor.y)*.68;
  const distance = Math.hypot(dx,dy), desiredSpeed = Math.min(maxSpeed,distance*2.4);
  let vx = (actor.vx||0)*1.05, vy = (actor.vy||0)*.68;
  const desiredX = distance>.001 ? dx/distance*desiredSpeed : 0;
  const desiredY = distance>.001 ? dy/distance*desiredSpeed : 0;
  const deltaX=desiredX-vx,deltaY=desiredY-vy,delta=Math.hypot(deltaX,deltaY);
  const rate=desiredSpeed>=Math.hypot(vx,vy)?acceleration:deceleration;
  const scale=delta>0?Math.min(1,rate*dt/delta):0;
  vx+=deltaX*scale;vy+=deltaY*scale;
  actor.vx=vx/1.05;actor.vy=vy/.68;
  actor.x = Math.max(0,Math.min(100,actor.x+actor.vx*dt));
  actor.y = Math.max(0,Math.min(100,actor.y+actor.vy*dt));
  if(Math.hypot(vx,vy)>.05){
    const desiredHeading=Math.atan2(actor.vy,actor.vx);
    const turn=Math.atan2(Math.sin(desiredHeading-(actor.heading||0)),Math.cos(desiredHeading-(actor.heading||0)));
    actor.heading=(actor.heading||0)+Math.max(-9*dt,Math.min(9*dt,turn));
  }
  return actor;
}
