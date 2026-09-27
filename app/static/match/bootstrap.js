import {createRenderer} from "./renderer.js";
import {createTacticalEngine} from "./tactical-engine.js";
import {createMatchEngine} from "./match-engine.js";
import {createCameraController} from "./camera.js";
import {createAudioController} from "./audio.js";
import {createEventChoreography} from "./event-choreography.js";

import {createRendererBridge} from "./renderer-bridge.js";

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

  const canvasRenderer = createRenderer({
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

  const shell3d = document.getElementById("match-3d-shell");
  const shell2d = document.getElementById("match-2d-shell");
  const switcher = document.getElementById("match-view-switcher");
  const status3d = document.getElementById("match-3d-status");
  const controls = new AbortController();
  const renderer = createRendererBridge({
    fallback: canvasRenderer,
    async load() {
      const {createThreeRenderer} = await import("./three-renderer.js");
      return createThreeRenderer({canvas: document.getElementById("match-3d-canvas"),
        modelUrl: shell3d.dataset.modelSrc, plan, reducedMotion,
        onError: error => { renderer.fail(error); engine.repaint(); }});
    },
    onMode(mode, available) {
      shell3d.hidden = mode !== "3d";
      shell3d.setAttribute("aria-hidden", String(mode !== "3d"));
      shell2d.hidden = mode !== "2d";
      switcher.hidden = false;
      for (const button of switcher.querySelectorAll("[data-match-view-target]")) {
        const selected = button.dataset.matchViewTarget === mode;
        button.disabled = button.dataset.matchViewTarget === "3d" && !available;
        button.classList.toggle("active", selected);
        button.setAttribute("aria-pressed", String(selected));
      }
      if (available) status3d.textContent = "Live match · your player marked in gold";
    },
    onError(error) {
      console.warn("3D unavailable; tactical view active:", error);
      status3d.textContent = "Tactical view · 3D unavailable";
    },
  });
  switcher.hidden = false;
  switcher.addEventListener("click", event => {
    const button = event.target.closest("[data-match-view-target]");
    if (button) renderer.select(button.dataset.matchViewTarget);
  }, {signal: controls.signal});
  document.getElementById("match-camera-mode")?.addEventListener("change", event => {
    renderer.setCameraMode(event.target.value);
  }, {signal: controls.signal});
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
    pause: () => engine.pause(), resume: () => engine.resume(),
    setSpeed: value => engine.setSpeed(value),
    finish() { choreography.cancel(); engine.finish(); },
    cancelEvent: () => choreography.cancel(),
    waitForSimulation: seconds => engine.waitForSimulation(seconds),
    // A ceiling, not a delay: most sequences finish in 1–3 seconds. Normal events
    // retain their original watchdog; connected attacks may finish a live pass.
    eventBudget: item => ['GOAL','SAVE','MISS'].includes(String(item?.visual?.kind||item?.kind).toUpperCase()) ? 7 : 1.6,
    applyInstantEvent: item => choreography.applyInstantEvent(item),
    async playEvent(item) {
      if (!item?.visual || engine.isFinished()) return;

      const kind = String(
        item.visual.kind
        || item.kind
        || "",
      ).toLowerCase();

      if (
        ["save", "miss", "corner", "penalty", "free_kick"].includes(kind)
      ) {
        audio.play("kick");
      } else if (kind === "full_time") {
        audio.play("whistle");
      }

      const presented=await choreography.playEvent(item);
      if(presented&&!engine.isFinished()) {
        engine.emphasizeEvent?.(presented);
        if(presented==='GOAL'){audio.play("goal");audio.play("crowd");}
      }
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
  observer.observe(root.querySelector(".match-broadcast"));

  window.addEventListener("beforeunload", () => {
    controls.abort();
    choreography.cancel();
    window.clearTimeout(transitionTimer);
    delete window.FootyMatchVisuals;
    observer.disconnect();
    audio.destroy();
    engine.destroy();
    renderer.destroy();
  }, {once: true});

  for (const item of (window.FootyRevealedEvents || [])) choreography.applyInstantEvent(item);
  engine.setSpeed(Number(root.dataset.replaySpeed || 1));
  if (root.dataset.replayPaused === "true") engine.pause();
  if (root.dataset.replayFinished === "true") engine.finish();
  else if (root.dataset.sessionStatus === "completed") { engine.pause(); engine.repaint(); }
  else engine.start();
  renderer.init();
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
