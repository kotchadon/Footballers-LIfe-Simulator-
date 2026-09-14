import {formationAnchors} from "./formations.js";
import {integrateMovement} from "./movement.js";
import {sampleSeed} from "./prng.js";
import {createRenderer} from "./renderer.js";

const root = document.getElementById("match-stage");
const stage = document.getElementById("match-visual-stage");
const canvas = document.getElementById("match-canvas");
const visualStatus = document.getElementById("match-visual-status");
const fallback = document.getElementById("match-visual-fallback");

if (root && stage && canvas) {
  boot().catch((error) => {
    console.error("Match visual bootstrap failed:", error);
    if (fallback) fallback.hidden = false;
    if (visualStatus) visualStatus.textContent = "Commentary-only fallback";
  });
}

async function boot() {
  const endpoint = root.dataset.visualEndpoint;
  if (!endpoint) throw new Error("Missing visual plan endpoint.");

  const response = await fetch(endpoint, {
    method: "GET",
    cache: "no-store",
    headers: {"Accept": "application/json", "Cache-Control": "no-cache"},
  });
  const payload = await response.json();
  if (!response.ok || !payload.ok || !payload.visual) throw new Error(payload.message || "Visual plan unavailable.");

  const plan = payload.visual;
  const actors = buildRuntimeActors(plan);
  const ball = {...plan.initial_ball};
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let visualEnabled = true;

  const renderer = createRenderer({
    canvas,
    stage,
    reducedMotion,
    onError(error) {
      visualEnabled = false;
      console.error("Match renderer disabled:", error);
      if (fallback) fallback.hidden = false;
    },
  });

  const observer = new ResizeObserver(() => renderer.resize());
  observer.observe(stage);

  if (visualStatus) visualStatus.textContent = `${plan.home.formation} · ${plan.away.formation} · 22 players`;

  let last = performance.now();
  let elapsed = 0;

  function frame(now) {
    const dt = Math.min(.04, Math.max(0, (now - last) / 1000));
    last = now;
    elapsed += dt;

    for (const actor of actors) {
      const seed = sampleSeed(plan.seed, actor.actorId);
      const frequency = .18 + (seed % 7) * .012;
      const amplitudeX = actor.role === "GK" ? .6 : 1.5;
      const amplitudeY = actor.role === "GK" ? 1.0 : 2.1;
      const target = {
        x: actor.anchorX + Math.sin(elapsed * frequency + seed * .001) * amplitudeX,
        y: actor.anchorY + Math.cos(elapsed * frequency * .83 + seed * .002) * amplitudeY,
      };
      integrateMovement(actor, target, dt, {
        maxSpeed: actor.maxSpeed,
        acceleration: actor.acceleration,
        deceleration: actor.deceleration,
      });
    }

    if (visualEnabled) renderer.render({actors, ball, animationPhase: (elapsed * .72) % 1});
    requestAnimationFrame(frame);
  }

  window.addEventListener("beforeunload", () => {
    observer.disconnect();
    renderer.destroy();
  }, {once: true});

  requestAnimationFrame(frame);
}

function buildRuntimeActors(plan) {
  const byTeam = {
    home: formationAnchors(plan.home.formation, plan.home.attacking_direction),
    away: formationAnchors(plan.away.formation, plan.away.attacking_direction),
  };

  return plan.actors.map((actor, index) => {
    const anchor = byTeam[actor.team][actor.role] || [actor.team === "home" ? 35 : 65, 15 + (index % 10) * 7];
    const pace = Number(actor.attributes?.pace || 60);
    const acceleration = Number(actor.attributes?.acceleration || pace);
    return {
      actorId: actor.actor_id,
      displayName: actor.display_name,
      shirtNumber: actor.shirt_number,
      role: actor.role,
      team: actor.team,
      isUser: actor.actor_id === plan.user_actor_id,
      x: anchor[0],
      y: anchor[1],
      anchorX: anchor[0],
      anchorY: anchor[1],
      vx: 0,
      vy: 0,
      heading: actor.team === "home" ? 0 : Math.PI,
      maxSpeed: 7 + pace * .09,
      acceleration: 18 + acceleration * .25,
      deceleration: 28 + acceleration * .24,
      animationState: actor.role === "GK" ? "GK_SET" : null,
    };
  });
}
