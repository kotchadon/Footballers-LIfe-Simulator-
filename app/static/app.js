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
    if (key === "w") window.location.href = "/world";
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
    const stage = document.getElementById("match-stage");
    const timeline = document.getElementById("match-timeline");
    if (!stage || !timeline) return null;

    const minute = document.getElementById("match-minute");
    const status = document.getElementById("match-status");
    const eventCount = document.getElementById("event-count");
    const homeScore = document.getElementById("home-live-score");
    const awayScore = document.getElementById("away-live-score");
    const scoreCaption = document.getElementById("score-caption");
    const pauseButton = document.getElementById("pause-replay");
    const finishButton = document.getElementById("finish-replay");
    const reportLock = document.getElementById("report-lock");
    const reportMount = document.getElementById("post-match-mount");
    const playerTeamHome = stage.dataset.playerTeamHome === "true";
    const advanceEndpoint = stage.dataset.advanceEndpoint;
    const completeEndpoint = stage.dataset.completeEndpoint;
    const totalEvents = Number(stage.dataset.eventCount || 0);
    const alreadyCompleted = stage.dataset.sessionStatus === "completed";

    let cursor = 0;
    let paused = false;
    let speed = 1;
    let timer = null;
    let finalising = false;
    let reportShown = false;

    function interval() {
      return Math.max(170, 920 / speed);
    }

    function updateSpeedButtons() {
      document.querySelectorAll("[data-match-speed]").forEach((button) => {
        button.classList.toggle("active", Number(button.dataset.matchSpeed) === speed);
      });
    }

    function mapScore(score) {
      const player = Number(score?.player || 0);
      const opponent = Number(score?.opponent || 0);
      return playerTeamHome ? {home: player, away: opponent} : {home: opponent, away: player};
    }

    function addEvent(item, instant = false) {
      if (!item) return;
      if (timeline.querySelector(`[data-sequence="${item.sequence}"]`)) return;
      const row = document.createElement("article");
      row.className = `timeline-event ${item.kind || "moment"}`;
      row.dataset.sequence = String(item.sequence);
      const stamp = document.createElement("strong");
      stamp.textContent = `${String(item.minute).padStart(2, "0")}'`;
      const copy = document.createElement("p");
      copy.textContent = item.text;
      row.append(stamp, copy);
      if (instant) row.style.animationDuration = "0s";
      timeline.append(row);
      timeline.scrollTo({top: timeline.scrollHeight, behavior: instant || speed === 3 ? "auto" : "smooth"});

      const mapped = mapScore(item.score);
      homeScore.textContent = mapped.home;
      awayScore.textContent = mapped.away;
      minute.textContent = item.kind === "full_time" ? "FT" : `${String(item.minute).padStart(2, "0")}'`;
      eventCount.textContent = `${Math.min(cursor + 1, totalEvents)} / ${totalEvents}`;
    }

    async function postJson(endpoint, payload) {
      const response = await fetch(endpoint, {
        method: "POST",
        cache: "no-store",
        headers: {"Content-Type": "application/json", "Accept": "application/json", "Cache-Control": "no-cache"},
        body: JSON.stringify(payload || {}),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.message || "Match request failed.");
      return data;
    }

    function el(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined && text !== null) node.textContent = String(text);
      return node;
    }

    function reportItem(item, includeFocus = false) {
      const article = el("article", "analysis-item");
      article.append(el("h3", "", item.title || "Analysis"), el("p", "", item.detail || ""));
      if (includeFocus && item.focus) article.append(el("span", "analysis-focus", item.focus.toUpperCase()));
      if (Array.isArray(item.evidence) && item.evidence.length) {
        article.append(el("small", "", item.evidence.map((entry) => `${entry.label}: ${entry.value}`).join(" · ")));
      }
      return article;
    }

    function buildReport(payload) {
      const report = payload.report;
      const analysis = report.analysis;
      const finalScore = payload.final_score;
      const root = el("section", "post-match-report");

      const hero = el("div", "report-hero panel");
      const heroCopy = el("div");
      heroCopy.append(el("p", "eyebrow", "FULL-TIME ANALYSIS"), el("h2", "", analysis.headline), el("p", "", analysis.verdict));
      const rating = el("div", "report-rating");
      rating.append(el("small", "", "RATING"), el("strong", "", report.rating ? Number(report.rating).toFixed(1) : "—"));
      hero.append(heroCopy, rating);
      root.append(hero);

      const storyGrid = el("div", "report-grid");
      const story = el("section", "panel");
      story.append(el("p", "eyebrow", "MATCH STORY"), el("p", "", analysis.result_context));
      const turning = el("div", "report-list");
      (analysis.turning_points || []).forEach((item) => {
        const article = el("article", "analysis-item compact");
        article.append(el("h3", "", `${item.minute}'`), el("p", "", item.text));
        turning.append(article);
      });
      story.append(turning);

      const output = el("section", "panel");
      output.append(el("p", "eyebrow", "PLAYER OUTPUT"));
      const stats = el("div", "match-stat-grid");
      [
        ["Minutes", report.minutes], ["Goals", report.goals], ["Assists", report.assists],
        ["Shots", report.metrics.shots], ["Key passes", report.metrics.key_passes],
        ["Pass accuracy", `${Math.round(report.metrics.pass_accuracy)}%`],
        ["Duels", `${report.metrics.duels_won}/${report.metrics.duels}`],
        ["Cards", `${report.yellow_cards}Y / ${report.red_cards}R`],
      ].forEach(([label, value]) => {
        const box = el("div");
        box.append(el("span", "", label), el("strong", "", value));
        stats.append(box);
      });
      output.append(stats);
      const fitness = el("div", "fitness-shift");
      fitness.append(el("span", "", "Fitness"), el("strong", "", `${report.fitness_before}% → ${report.fitness_after}%`));
      const development = el("div", "development-note");
      development.append(el("span", "", "DEVELOPMENT"), el("p", "", report.development_summary));
      output.append(fitness, development);
      storyGrid.append(story, output);
      root.append(storyGrid);

      const insightGrid = el("div", "report-grid three-column");
      [["WHAT WORKED", analysis.strengths, false], ["PERFORMANCE GAPS", analysis.gaps, false], ["COACHING ACTIONS", analysis.coaching_actions, true]].forEach(([heading, items, includeFocus]) => {
        const panel = el("section", "panel");
        panel.append(el("p", "eyebrow", heading));
        const list = el("div", "report-list");
        list.replaceChildren(...(items || []).map((item) => reportItem(item, includeFocus)));
        panel.append(list);
        insightGrid.append(panel);
      });
      root.append(insightGrid);

      const otherPanel = el("section", "panel");
      const heading = el("div", "panel-heading");
      const headingCopy = el("div");
      headingCopy.append(el("p", "eyebrow", "MATCHWEEK"), el("h2", "", "Other results"));
      heading.append(headingCopy);
      const otherResults = el("div", "other-results");
      (payload.week_results || []).forEach((result) => {
        const row = el("p", "result-row");
        row.append(el("span", "", result.home_name), el("strong", "", `${result.home_goals}–${result.away_goals}`), el("span", "", result.away_name));
        otherResults.append(row);
      });
      otherPanel.append(heading, otherResults);
      root.append(otherPanel);

      const link = el("a", "button primary continue-button", "Return to dashboard");
      link.href = payload.dashboard_url || "/";
      root.append(link);
      return root;
    }

    function renderReport(payload) {
      if (reportShown) return;
      reportShown = true;
      const finalScore = payload.final_score;
      homeScore.textContent = finalScore.home;
      awayScore.textContent = finalScore.away;
      minute.textContent = "FT";
      status.textContent = "Full time";
      scoreCaption.textContent = "FINAL SCORE";
      reportLock.remove();
      reportMount.replaceChildren(buildReport(payload));
      reportMount.scrollIntoView({behavior: speed === 3 ? "auto" : "smooth", block: "start"});
      pauseButton.textContent = "Replay complete";
      pauseButton.disabled = true;
      finishButton.disabled = true;
      finalising = false;
    }

    async function finalise(skip = false) {
      if (finalising || reportShown) return;
      finalising = true;
      window.clearTimeout(timer);
      status.textContent = skip ? "Skipping to full time" : "Finalising";
      pauseButton.disabled = true;
      finishButton.disabled = true;
      try {
        const payload = await postJson(completeEndpoint, {skip});
        const events = payload.remaining_events || [];
        for (let index = cursor; index < events.length; index += 1) {
          addEvent(events[index], skip);
          cursor = index + 1;
        }
        renderReport(payload);
      } catch (error) {
        finalising = false;
        paused = true;
        status.textContent = "Completion failed";
        pauseButton.disabled = false;
        finishButton.disabled = false;
        showToast(error.message || "Could not finalise match.", true);
      }
    }

    async function tick() {
      if (paused || finalising || reportShown) return;
      try {
        const payload = await postJson(advanceEndpoint, {cursor});
        if (payload.completed) {
          await finalise(false);
          return;
        }
        addEvent(payload.event);
        cursor = payload.cursor;
        if (payload.event?.kind === "full_time" || !payload.has_more) {
          await finalise(false);
          return;
        }
        timer = window.setTimeout(tick, interval());
      } catch (error) {
        paused = true;
        status.textContent = "Replay paused · connection error";
        pauseButton.innerHTML = "Retry <kbd>Space</kbd>";
        showToast(error.message || "Replay request failed.", true);
      }
    }

    function togglePause() {
      if (finalising || reportShown) return;
      paused = !paused;
      status.textContent = paused ? "Paused" : "Playing";
      pauseButton.innerHTML = paused ? "Resume <kbd>Space</kbd>" : "Pause <kbd>Space</kbd>";
      window.clearTimeout(timer);
      if (!paused) tick();
    }

    function setSpeed(nextSpeed) {
      speed = Math.max(1, Math.min(3, Number(nextSpeed)));
      updateSpeedButtons();
      if (!paused && !finalising && !reportShown) {
        window.clearTimeout(timer);
        timer = window.setTimeout(tick, 60);
      }
    }

    function finish() {
      if (reportShown) return;
      finalise(true);
    }

    pauseButton?.addEventListener("click", togglePause);
    finishButton?.addEventListener("click", finish);
    document.querySelectorAll("[data-match-speed]").forEach((button) => {
      button.addEventListener("click", () => setSpeed(button.dataset.matchSpeed));
    });

    status.textContent = alreadyCompleted ? "Loading final report" : "Playing";
    if (alreadyCompleted) finalise(false);
    else timer = window.setTimeout(tick, 450);
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
