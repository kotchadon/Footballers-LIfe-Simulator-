(() => {
  "use strict";

  const body = document.body;
  const page = body.dataset.page || "default";
  const toast = document.getElementById("toast");

  function showToast(message, isError = false) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle("error", isError);
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2400);
  }

  function isTypingTarget(target) {
    return target instanceof HTMLElement && (
      target.matches("input, textarea, select, [contenteditable='true']") ||
      target.closest("input, textarea, select, [contenteditable='true']")
    );
  }

  const shortcutDialog = document.getElementById("shortcut-dialog");
  document.querySelectorAll("[data-open-shortcuts]").forEach((button) => {
    button.addEventListener("click", () => shortcutDialog?.showModal());
  });
  document.querySelectorAll("[data-close-shortcuts]").forEach((button) => {
    button.addEventListener("click", () => shortcutDialog?.close());
  });

  function navigateShortcut(key) {
    if (key === "h") window.location.href = "/";
    if (key === "y") window.location.href = "/career-history";
  }

  async function setTrainingFocus(button) {
    const panel = document.getElementById("development");
    if (!panel || !button) return;
    const endpoint = panel.dataset.trainingEndpoint;
    const focus = button.dataset.trainingFocus;
    if (!endpoint || !focus || button.disabled) return;

    document.querySelectorAll("[data-training-focus]").forEach((item) => item.disabled = true);
    button.classList.add("loading");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({focus}),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || "Could not update training plan.");

      document.querySelectorAll("[data-training-focus]").forEach((item) => {
        item.classList.toggle("selected", item.dataset.trainingFocus === data.plan.focus);
      });
      document.getElementById("training-plan-label").textContent = data.plan.label;
      document.getElementById("training-plan-title").textContent = data.plan.label;
      document.getElementById("training-plan-description").textContent = data.plan.description;
      document.getElementById("hero-training-pill").textContent = `Plan · ${data.plan.label}`;
      document.getElementById("xp-progress").textContent = `${data.plan.xp}/100 XP`;
      document.getElementById("xp-track-fill").style.width = `${data.plan.xp}%`;
      showToast(data.message);
    } catch (error) {
      showToast(error.message || "Training plan failed.", true);
    } finally {
      button.classList.remove("loading");
      document.querySelectorAll("[data-training-focus]").forEach((item) => item.disabled = false);
    }
  }

  document.querySelectorAll("[data-training-focus]").forEach((button) => {
    button.addEventListener("click", () => setTrainingFocus(button));
  });

  function submitContinue() {
    const form = document.getElementById("play-form");
    if (form) form.requestSubmit();
  }

  function setupDashboardShortcuts(event) {
    const key = event.key.toLowerCase();
    const mappings = {
      "1": "pace",
      "2": "shooting",
      "3": "passing",
      "4": "dribbling",
      "5": "defending",
      "6": "physical",
      "r": "recovery",
    };
    if (mappings[key]) {
      event.preventDefault();
      setTrainingFocus(document.querySelector(`[data-training-focus="${mappings[key]}"]`));
      return true;
    }
    if (key === "c") {
      event.preventDefault();
      submitContinue();
      return true;
    }
    return false;
  }

  function setupMatchReplay() {
    const dataNode = document.getElementById("match-events");
    const stage = document.getElementById("match-stage");
    const timeline = document.getElementById("match-timeline");
    if (!dataNode || !stage || !timeline) return null;

    const events = JSON.parse(dataNode.textContent || "[]");
    const minute = document.getElementById("match-minute");
    const status = document.getElementById("match-status");
    const eventCount = document.getElementById("event-count");
    const homeScore = document.getElementById("home-live-score");
    const awayScore = document.getElementById("away-live-score");
    const pauseButton = document.getElementById("pause-replay");
    const finishButton = document.getElementById("finish-replay");
    const playerTeamHome = stage.dataset.playerTeamHome === "true";
    const finalHome = Number(stage.dataset.finalHome || 0);
    const finalAway = Number(stage.dataset.finalAway || 0);

    let index = 0;
    let paused = false;
    let speed = 1;
    let timer = null;
    let liveHome = 0;
    let liveAway = 0;

    function interval() {
      return Math.max(170, 920 / speed);
    }

    function updateSpeedButtons() {
      document.querySelectorAll("[data-match-speed]").forEach((button) => {
        button.classList.toggle("active", Number(button.dataset.matchSpeed) === speed);
      });
    }

    function addEvent(item) {
      const row = document.createElement("article");
      row.className = `timeline-event ${item.kind || "moment"}`;
      const stamp = document.createElement("strong");
      stamp.textContent = `${String(item.minute).padStart(2, "0")}'`;
      const copy = document.createElement("p");
      copy.textContent = item.text;
      row.append(stamp, copy);
      timeline.append(row);
      timeline.scrollTo({top: timeline.scrollHeight, behavior: speed === 3 ? "auto" : "smooth"});

      if (item.kind === "goal_for") {
        if (playerTeamHome) liveHome += 1; else liveAway += 1;
      } else if (item.kind === "goal_against") {
        if (playerTeamHome) liveAway += 1; else liveHome += 1;
      }
      homeScore.textContent = liveHome;
      awayScore.textContent = liveAway;
      minute.textContent = `${String(item.minute).padStart(2, "0")}'`;
      eventCount.textContent = `${Math.min(index + 1, events.length)} / ${events.length}`;
    }

    function completeReplay() {
      window.clearTimeout(timer);
      liveHome = finalHome;
      liveAway = finalAway;
      homeScore.textContent = finalHome;
      awayScore.textContent = finalAway;
      minute.textContent = "FT";
      status.textContent = "Full time";
      paused = true;
      pauseButton.textContent = "Replay complete";
      pauseButton.disabled = true;
      finishButton.disabled = true;
    }

    function tick() {
      if (paused) return;
      if (index >= events.length) {
        completeReplay();
        return;
      }
      addEvent(events[index]);
      index += 1;
      timer = window.setTimeout(tick, interval());
    }

    function togglePause() {
      if (index >= events.length) return;
      paused = !paused;
      status.textContent = paused ? "Paused" : "Playing";
      pauseButton.innerHTML = paused ? "Resume <kbd>Space</kbd>" : "Pause <kbd>Space</kbd>";
      window.clearTimeout(timer);
      if (!paused) tick();
    }

    function setSpeed(nextSpeed) {
      speed = Math.max(1, Math.min(3, Number(nextSpeed)));
      updateSpeedButtons();
      if (!paused) {
        window.clearTimeout(timer);
        timer = window.setTimeout(tick, 80);
      }
    }

    function finish() {
      window.clearTimeout(timer);
      paused = true;
      while (index < events.length) {
        addEvent(events[index]);
        index += 1;
      }
      completeReplay();
    }

    pauseButton?.addEventListener("click", togglePause);
    finishButton?.addEventListener("click", finish);
    document.querySelectorAll("[data-match-speed]").forEach((button) => {
      button.addEventListener("click", () => setSpeed(button.dataset.matchSpeed));
    });

    window.setTimeout(tick, 450);
    return {togglePause, setSpeed, finish};
  }

  const replay = page === "match" ? setupMatchReplay() : null;

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || isTypingTarget(event.target)) return;
    const key = event.key.toLowerCase();

    if (key === "?" || (key === "/" && event.shiftKey)) {
      event.preventDefault();
      shortcutDialog?.showModal();
      return;
    }
    if (shortcutDialog?.open) {
      if (key === "escape") shortcutDialog.close();
      return;
    }

    if (page === "dashboard" && setupDashboardShortcuts(event)) return;
    if (page === "match" && replay) {
      if (event.code === "Space") {
        event.preventDefault();
        replay.togglePause();
        return;
      }
      if (["1", "2", "3"].includes(key)) {
        event.preventDefault();
        replay.setSpeed(Number(key));
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        replay.finish();
        return;
      }
    }
    navigateShortcut(key);
  });
})();

