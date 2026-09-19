import {createRenderer} from "./renderer.js";
import {createTacticalEngine} from "./tactical-engine.js";
import {createMatchEngine} from "./match-engine.js";
import {createCameraController} from "./camera.js";
import {createAudioController} from "./audio.js";
import {createEventChoreography} from "./event-choreography.js";

const root = document.getElementById("match-stage");
const stage = document.getElementById("match-visual-stage");
const canvas = document.getElementById("match-canvas");
const pitch = document.getElementById("match-pitch-svg");
const visualStatus = document.getElementById("match-visual-status");
const fallback = document.getElementById("match-visual-fallback");
const matchTransitionOverlay = document.getElementById("match-transition-overlay");
const matchTransitionText = document.getElementById("match-transition-text");
const matchPressure = document.getElementById("match-pressure");
const matchTerritory = document.getElementById("match-territory");
const audioToggle = document.getElementById("match-audio-toggle");
let transitionTimer = null;

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
  function readAudioPreference() {
    try {
      return localStorage.getItem("footy-match-audio") === "1";
    } catch (error) {
      return false;
    }
  }

  function storeAudioPreference(enabled) {
    try {
      localStorage.setItem(
        "footy-match-audio",
        enabled ? "1" : "0",
      );
    } catch (error) {
      console.debug(
        "Match audio preference not persisted:",
        error,
      );
    }
  }

  const audio = createAudioController({
    enabled: readAudioPreference(),
  });

  function syncAudioToggle() {
    if (!audioToggle) return;
    const enabled = audio.isEnabled();
    audioToggle.textContent = enabled
      ? "Audio on"
      : "Audio off";
    audioToggle.setAttribute(
      "aria-pressed",
      enabled ? "true" : "false",
    );
    audioToggle.classList.toggle(
      "is-active",
      enabled,
    );
  }

  if (audioToggle) {
    audioToggle.addEventListener("click", () => {
      const enabled = !audio.isEnabled();
      audio.setEnabled(enabled);
      storeAudioPreference(enabled);
      syncAudioToggle();
    });
    syncAudioToggle();
  }

  const camera = createCameraController({reducedMotion});
  let visualEnabled = true;

  const renderer = createRenderer({
    canvas,
    stage,
    pitch,
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
    camera,
    renderer: {
      render(state) {
        if (visualEnabled) renderer.render(state);
      },
    },
    getMatchContext,
    onStatus(status) {
      const possession = status.possessionTeam === "home"
        ? plan.home.name
        : plan.away.name;
      const phase = String(
        status.phase || "reset",
      ).replaceAll("_", " ");

      if (visualStatus) {
        visualStatus.textContent = (
          `${phase} - ${possession} possession`
        );
      }

      updatePresentationIndicators(status);
    },
  });


  function showTransition(message) {
    if (visualStatus) visualStatus.textContent = message;
    if (!matchTransitionOverlay || !matchTransitionText) return;

    matchTransitionText.textContent = message;
    matchTransitionOverlay.hidden = false;

    if (transitionTimer !== null) window.clearTimeout(transitionTimer);
    transitionTimer = window.setTimeout(() => {
      matchTransitionOverlay.hidden = true;
      transitionTimer = null;
    }, 900);
  }

  const choreography = createEventChoreography({
    tactical,
    matchEngine: engine,
    onOverlay: showTransition,
  });

  window.FootyMatchVisuals = {
    async playEvent(item) {
      if (!item?.visual) return;

      const kind = String(
        item.visual.kind
        || item.kind
        || "",
      ).toLowerCase();

      if (kind === "goal") {
        audio.play("goal");
        audio.play("crowd");
      } else if (
        ["save", "miss", "corner", "penalty", "free_kick"].includes(kind)
      ) {
        audio.play("kick");
      } else if (kind === "full_time") {
        audio.play("whistle");
      }

      engine.emphasizeEvent?.(
        item.visual.kind || item.kind,
        item.visual,
      );

      await choreography.playEvent(item);
    },
  };

  function updatePresentationIndicators(status) {
    const phase = String(
      status?.phase || "RESET",
    ).toUpperCase();

    if (matchPressure) {
      const pressure = (
        phase === "FINAL_THIRD"
          ? "High"
          : phase === "PROGRESSION"
            ? "Building"
            : phase === "DEFENSIVE_BLOCK"
              ? "Under pressure"
              : "Balanced"
      );

      matchPressure.textContent = pressure;
    }

    if (matchTerritory) {
      const ballX = Number(status?.ball?.x ?? 50);
      matchTerritory.textContent = (
        ballX < 36
          ? "HOME HALF"
          : ballX > 64
            ? "AWAY HALF"
            : "CENTRAL"
      );
    }
  }

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
    audio.destroy();
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
