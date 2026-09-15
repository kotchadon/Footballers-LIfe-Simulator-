import {createRenderer} from "./renderer.js";
import {createTacticalEngine} from "./tactical-engine.js";
import {createMatchEngine} from "./match-engine.js";
import {createEventChoreography} from "./event-choreography.js";

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

  if (!response.ok || !payload.ok || !payload.visual) {
    throw new Error(payload.message || "Visual plan unavailable.");
  }

  const plan = payload.visual;
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

  const tactical = createTacticalEngine(plan);

  const engine = createMatchEngine({
    tactical,
    renderer: {
      render(state) {
        if (visualEnabled) renderer.render(state);
      },
    },
    getMatchContext,
    onStatus(status) {
      if (!visualStatus) return;
      const possession = status.possessionTeam === "home"
        ? plan.home.name
        : plan.away.name;
      const phase = status.phase.replaceAll("_", " ");
      visualStatus.textContent = `${phase} - ${possession} possession`;
    },
  });


  const choreography =
    createEventChoreography({
      tactical,
      onOverlay(message) {
        if (visualStatus) {
          visualStatus.textContent = message;
        }
      },
    });

  window.FootyMatchVisuals = {
    async playEvent(item) {
      if (!item?.visual) return;
      await choreography.playEvent(item);
    },
  };

  const observer = new ResizeObserver(() => renderer.resize());
  observer.observe(stage);

  for (const button of document.querySelectorAll("[data-match-speed]")) {
    button.addEventListener("click", () => {
      engine.setSpeed(Number(button.dataset.matchSpeed || 1));
    });
  }

  const pauseButton = document.getElementById("pause-replay");
  if (pauseButton) {
    pauseButton.addEventListener("click", () => {
      if (engine.isPaused()) engine.resume();
      else engine.pause();
    });
  }

  window.addEventListener("keydown", (event) => {
    if (event.repeat) return;
    const tag = document.activeElement?.tagName || "";
    if (
      event.code === "Space"
      && !["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(tag)
    ) {
      if (engine.isPaused()) engine.resume();
      else engine.pause();
    }
  });

  window.addEventListener("beforeunload", () => {
    delete window.FootyMatchVisuals;
    observer.disconnect();
    engine.destroy();
    renderer.destroy();
  }, {once: true});

  engine.start();
}

function getMatchContext() {
  const minuteText = document.getElementById("match-minute")?.textContent || "0";
  const minute = Number.parseInt(minuteText, 10) || 0;
  const homeScore = Number.parseInt(
    document.getElementById("home-live-score")?.textContent || "0",
    10,
  ) || 0;
  const awayScore = Number.parseInt(
    document.getElementById("away-live-score")?.textContent || "0",
    10,
  ) || 0;

  return {minute, homeScore, awayScore};
}
