const TAU = Math.PI * 2;

function limb(ctx, x1, y1, length, angle, width) {
  const x2 = x1 + Math.cos(angle) * length;
  const y2 = y1 + Math.sin(angle) * length;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  return [x2, y2];
}

export function poseForState(state = "IDLE", phase = 0, speed = 0) {
  const cycle = Math.sin(phase * TAU);
  const opposite = Math.sin(phase * TAU + Math.PI);
  const lean = Math.min(0.22, Math.max(0, speed) * 0.012);

  const poses = {
    IDLE: {lean: 0, leftLeg: 1.55, rightLeg: 1.59, leftArm: 1.72, rightArm: 1.42},
    JOG: {lean, leftLeg: 1.57 + cycle * .45, rightLeg: 1.57 + opposite * .45, leftArm: 1.57 + opposite * .34, rightArm: 1.57 + cycle * .34},
    RUN: {lean: lean + .06, leftLeg: 1.57 + cycle * .62, rightLeg: 1.57 + opposite * .62, leftArm: 1.57 + opposite * .48, rightArm: 1.57 + cycle * .48},
    SPRINT: {lean: lean + .14, leftLeg: 1.57 + cycle * .82, rightLeg: 1.57 + opposite * .82, leftArm: 1.57 + opposite * .60, rightArm: 1.57 + cycle * .60},
    RECEIVE: {lean: .04, leftLeg: 1.74, rightLeg: 1.40, leftArm: 1.88, rightArm: 1.26},
    DRIBBLE: {lean: lean + .05, leftLeg: 1.57 + cycle * .42, rightLeg: 1.57 + opposite * .42, leftArm: 1.57 + opposite * .30, rightArm: 1.57 + cycle * .30},
    PASS: {lean: .08, leftLeg: 1.48, rightLeg: .88, leftArm: 1.90, rightArm: 1.20},
    LONG_PASS: {lean: .13, leftLeg: 1.66, rightLeg: .48, leftArm: 2.18, rightArm: .98},
    CROSS: {lean: .16, leftLeg: 1.72, rightLeg: .42, leftArm: 2.28, rightArm: .86},
    SHOOT: {lean: .18, leftLeg: 1.68, rightLeg: .35, leftArm: 2.05, rightArm: 1.05},
    GK_SET: {lean: 0, leftLeg: 1.90, rightLeg: 1.24, leftArm: 2.55, rightArm: .60},
    GK_DIVE: {lean: .55, leftLeg: 2.0, rightLeg: 1.7, leftArm: 3.05, rightArm: .10},
  };
  return poses[state] || poses.IDLE;
}

export function drawPlayerRig(ctx, actor, pose, projection) {
  const p = projection(actor.x, actor.y, actor.visualHeight || 0);
  const scale = p.scale;
  const isUser = Boolean(actor.isUser);

  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.scale(scale, scale);
  ctx.rotate((actor.bodyLean || pose.lean || 0) * .25);

  ctx.fillStyle = "rgba(0,0,0,.28)";
  ctx.beginPath();
  ctx.ellipse(0, 8, 8.5, 3.2, 0, 0, TAU);
  ctx.fill();

  if (isUser) {
    ctx.strokeStyle = "#ffd34d";
    ctx.lineWidth = 2.6;
    ctx.beginPath();
    ctx.ellipse(0, 4, 12, 7, 0, 0, TAU);
    ctx.stroke();
  }

  const shirt = actor.team === "home" ? "#4ca6ff" : "#ef5b62";
  const shorts = actor.team === "home" ? "#0b2447" : "#4d1118";
  const skin = "#d7a47d";

  ctx.strokeStyle = skin;
  const shoulderY = -18;
  limb(ctx, -5, shoulderY, 10, pose.leftArm, 3.3);
  limb(ctx, 5, shoulderY, 10, pose.rightArm, 3.3);

  ctx.fillStyle = shirt;
  ctx.beginPath();
  ctx.moveTo(-7, -22);
  ctx.lineTo(7, -22);
  ctx.lineTo(6, -5);
  ctx.lineTo(-6, -5);
  ctx.closePath();
  ctx.fill();

  ctx.fillStyle = shorts;
  ctx.fillRect(-6, -6, 12, 6);

  ctx.strokeStyle = shorts;
  const leftKnee = limb(ctx, -3, -1, 9, pose.leftLeg, 4);
  const rightKnee = limb(ctx, 3, -1, 9, pose.rightLeg, 4);

  ctx.strokeStyle = skin;
  limb(ctx, leftKnee[0], leftKnee[1], 8, 1.57 + (pose.leftLeg - 1.57) * .25, 3);
  limb(ctx, rightKnee[0], rightKnee[1], 8, 1.57 + (pose.rightLeg - 1.57) * .25, 3);

  ctx.fillStyle = skin;
  ctx.beginPath();
  ctx.arc(0, -27, 4.7, 0, TAU);
  ctx.fill();

  ctx.fillStyle = "#071322";
  ctx.font = "700 7px Arial Narrow, Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(String(actor.shirtNumber || ""), 0, -13);

  ctx.restore();

  ctx.save();
  ctx.font = `${Math.max(8, 9 * scale)}px Arial Narrow, Arial, sans-serif`;
  ctx.textAlign = "center";
  ctx.fillStyle = isUser ? "#ffe37a" : "rgba(236,244,255,.88)";
  ctx.fillText(String(actor.shirtNumber || ""), p.x, p.y - 31 * scale);
  if (isUser) {
    ctx.font = `700 ${Math.max(9, 10 * scale)}px Arial Narrow, Arial, sans-serif`;
    ctx.fillText(actor.displayName || "PLAYER", p.x, p.y - 43 * scale);
  }
  ctx.restore();
}
