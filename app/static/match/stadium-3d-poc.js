const matchStage = document.getElementById("match-stage");
const switcher = document.getElementById("match-view-switcher");
const shell3d = document.getElementById("match-3d-shell");
const shell2d = document.getElementById("match-2d-shell");
const viewer = document.getElementById("match-3d-viewer");
const status = document.getElementById("match-3d-status");
const button3d = document.querySelector('[data-match-view-target="3d"]');
const button2d = document.querySelector('[data-match-view-target="2d"]');

const CUSTOM_ELEMENT_TIMEOUT_MS = 5000;
const MODEL_LOAD_TIMEOUT_MS = 10000;

if (
  matchStage
  && switcher
  && shell3d
  && shell2d
  && viewer
  && status
  && button3d
  && button2d
) {
  bootStage1ThreeD();
}

async function bootStage1ThreeD() {
  // Architectural boundary: this module is presentation-only. It never fetches
  // match APIs, writes match state, completes a match, or derives sealed results.
  switcher.hidden = false;
  setView("2d");
  setStatus("Checking 3D support…");

  button2d.addEventListener("click", () => setView("2d"));
  button3d.addEventListener("click", () => {
    if (!button3d.disabled) setView("3d");
  });

  if (!supportsWebGL()) {
    disableThreeD("3D unavailable — WebGL is disabled. Tactical 2D is active.");
    return;
  }

  try {
    await waitForCustomElement("model-viewer", CUSTOM_ELEMENT_TIMEOUT_MS);
  } catch (error) {
    console.warn("3D stadium runtime unavailable:", error);
    disableThreeD("3D runtime unavailable. Tactical 2D is active.");
    return;
  }

  const modelSrc = shell3d.dataset.modelSrc;
  if (!modelSrc) {
    disableThreeD("3D asset path is missing. Tactical 2D is active.");
    return;
  }

  let settled = false;
  const timeoutId = window.setTimeout(() => {
    if (settled) return;
    settled = true;
    disableThreeD("3D stadium timed out. Tactical 2D is active.");
  }, MODEL_LOAD_TIMEOUT_MS);

  viewer.addEventListener(
    "load",
    () => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      button3d.disabled = false;
      setStatus("3D stadium ready");
      setView("3d");
    },
    {once: true},
  );

  viewer.addEventListener(
    "error",
    (event) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      console.warn("3D stadium asset failed to load:", event);
      disableThreeD("3D stadium failed to load. Tactical 2D is active.");
    },
    {once: true},
  );

  // Deliberately set src only after runtime + WebGL checks. Unsupported browsers
  // therefore never download the GLB and simply keep the existing 2D renderer.
  viewer.src = modelSrc;
}

function setView(view) {
  const useThreeD = view === "3d" && !button3d.disabled;

  shell3d.hidden = !useThreeD;
  shell3d.setAttribute("aria-hidden", String(!useThreeD));

  shell2d.hidden = useThreeD;
  shell2d.setAttribute("aria-hidden", String(useThreeD));

  button3d.classList.toggle("active", useThreeD);
  button3d.setAttribute("aria-pressed", String(useThreeD));

  button2d.classList.toggle("active", !useThreeD);
  button2d.setAttribute("aria-pressed", String(!useThreeD));
}

function disableThreeD(message) {
  button3d.disabled = true;
  setStatus(message);
  setView("2d");
}

function setStatus(message) {
  status.textContent = message;
}

function supportsWebGL() {
  try {
    const canvas = document.createElement("canvas");
    const gl = (
      canvas.getContext("webgl2", {failIfMajorPerformanceCaveat: true})
      || canvas.getContext("webgl", {failIfMajorPerformanceCaveat: true})
      || canvas.getContext("experimental-webgl")
    );

    if (!gl) return false;

    const loseContext = gl.getExtension("WEBGL_lose_context");
    if (loseContext) loseContext.loseContext();
    return true;
  } catch (error) {
    console.warn("WebGL feature detection failed:", error);
    return false;
  }
}

function waitForCustomElement(name, timeoutMs) {
  if (!window.customElements) {
    return Promise.reject(new Error("Custom Elements are unsupported."));
  }

  if (customElements.get(name)) {
    return Promise.resolve();
  }

  return Promise.race([
    customElements.whenDefined(name),
    new Promise((_, reject) => {
      window.setTimeout(
        () => reject(new Error(`${name} registration timed out.`)),
        timeoutMs,
      );
    }),
  ]);
}
