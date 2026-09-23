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


  if ("scrollRestoration" in history) history.scrollRestoration = "manual";
  const scrollStorageKey = `footy:scroll:${window.location.pathname}`;

  function saveScroll() {
    try { sessionStorage.setItem(scrollStorageKey, String(window.scrollY || 0)); } catch (_error) {}
  }

  function restoreScroll() {
    let value = null;
    try { value = sessionStorage.getItem(scrollStorageKey); } catch (_error) {}
    if (value === null) return;
    const y = Number(value);
    if (!Number.isFinite(y)) return;
    const apply = () => window.scrollTo({top: y, left: 0, behavior: "auto"});
    requestAnimationFrame(apply);
    setTimeout(apply, 40);
    setTimeout(apply, 180);
    try { sessionStorage.removeItem(scrollStorageKey); } catch (_error) {}
  }

  function hashNumber(value) {
    return Array.from(String(value || "FC")).reduce((hash, char) => ((hash << 5) - hash + char.charCodeAt(0)) | 0, 0);
  }

  function decorateCrests(root = document) {
    root.querySelectorAll("[data-crest]").forEach((node) => {
      const hash = Math.abs(hashNumber(node.dataset.crest));
      const hueA = hash % 360;
      const hueB = (hueA + 48 + (hash % 64)) % 360;
      node.style.background = `linear-gradient(145deg, hsl(${hueA} 68% 46%), hsl(${hueB} 72% 34%))`;
    });
    root.querySelectorAll(".sponsor-logo[data-logo-text]").forEach((node) => {
      const hash = Math.abs(hashNumber(node.dataset.logoText));
      node.style.background = `linear-gradient(145deg, hsl(${hash % 360} 65% 42%), hsl(${(hash + 75) % 360} 70% 30%))`;
    });
  }

  function countryFlag(code) {
    const map = {ENG:"🇬🇧", ESP:"🇪🇸", ITA:"🇮🇹", GER:"🇩🇪", FRA:"🇫🇷", POR:"🇵🇹", NED:"🇳🇱", SCO:"🏴󠁧󠁢󠁳󠁣󠁴󠁿", IRL:"🇮🇪", USA:"🇺🇸", BRA:"🇧🇷", ARG:"🇦🇷", SAU:"🇸🇦", JPN:"🇯🇵", AUS:"🇦🇺", IND:"🇮🇳", LGC:"⚽"};
    return map[String(code || "").toUpperCase()] || "🌐";
  }

  function decorateFlags(root = document) {
    root.querySelectorAll("[data-country-flag]").forEach((node) => { node.textContent = countryFlag(node.dataset.countryFlag); });
  }


  function assetManifest() {
    return window.FOOTY_ASSETS || {clubs:{}, leaguesByCode:{}, leaguesByName:{}, nationalsByCode:{}, nationalsByName:{}, competitions:{}, sponsors:{}};
  }

  function logoPath(relative) {
    if (!relative) return "";
    if (/^(https?:)?\//.test(relative)) return relative;
    return `/static/assets/real/${relative.replace(/^\/+/, "")}`;
  }

  function applyRealLogos(root = document) {
    const manifest = assetManifest();
    root.querySelectorAll("img[data-logo-kind]").forEach((img) => {
      if (img.dataset.assetBound === "true") return;
      img.dataset.assetBound = "true";
      const kind = img.dataset.logoKind;
      const name = img.dataset.logoName || "";
      const code = img.dataset.logoCode || "";
      let relative = "";
      if (kind === "club") relative = manifest.clubs?.[name];
      else if (kind === "league-code") relative = manifest.leaguesByCode?.[code] || manifest.leaguesByName?.[name];
      else if (kind === "league-name") relative = manifest.leaguesByName?.[name];
      else if (kind === "national") relative = manifest.nationalsByCode?.[code] || manifest.nationalsByName?.[name];
      else if (kind === "competition") relative = manifest.competitions?.[code];
      const frame = img.closest(".real-logo-frame, .national-badge, .mini-real-logo");
      if (!relative) {
        img.hidden = true;
        frame?.classList.add("logo-fallback");
        return;
      }
      img.addEventListener("load", () => {
        img.hidden = false;
        frame?.classList.add("logo-loaded");
        frame?.classList.remove("logo-fallback");
      }, {once:true});
      img.addEventListener("error", () => {
        img.hidden = true;
        frame?.classList.add("logo-fallback");
      }, {once:true});
      img.src = logoPath(relative);
    });

    root.querySelectorAll("img[data-sponsor-logo]").forEach((img) => {
      if (img.dataset.assetBound === "true") return;
      img.dataset.assetBound = "true";
      const relative = manifest.sponsors?.[img.dataset.sponsorLogo];
      if (!relative) { img.hidden = true; return; }
      img.src = relative.startsWith("/") ? relative : `/static/${relative}`;
      img.addEventListener("load", () => img.closest(".sponsor-visual")?.classList.add("logo-loaded"), {once:true});
      img.addEventListener("error", () => { img.hidden = true; }, {once:true});
    });
  }

  function drawDetailedChart(canvas) {
    let values = [];
    try { values = JSON.parse(canvas.dataset.series || "[]").map(Number).filter(Number.isFinite); } catch (_error) { values = []; }
    if (!values.length) return;
    while (values.length < 6) values.unshift(values[0]);
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const width = Math.max(320, rect.width || 560);
    const height = Math.max(220, rect.height || 240);
    canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d"); ctx.setTransform(dpr,0,0,dpr,0,0);
    const pad = {left:46,right:18,top:22,bottom:34};
    const iw=width-pad.left-pad.right, ih=height-pad.top-pad.bottom;
    const min=Math.min(...values), max=Math.max(...values), range=Math.max(.5,max-min);
    const points=values.map((v,i)=>({x:pad.left+(i/Math.max(1,values.length-1))*iw,y:pad.top+(1-(v-min)/range)*ih,value:v,index:i}));
    const positive=canvas.dataset.positive === "true";
    const line=positive?"#63a8ff":"#ff5f7f";
    let progress=0;
    function paint(p){
      ctx.clearRect(0,0,width,height);
      ctx.font="11px ui-sans-serif, system-ui"; ctx.fillStyle="rgba(185,199,225,.62)"; ctx.strokeStyle="rgba(142,159,190,.16)"; ctx.lineWidth=1;
      for(let i=0;i<5;i++){const y=pad.top+(i/4)*ih;ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(width-pad.right,y);ctx.stroke();const val=max-(i/4)*range;ctx.fillText(`$${val.toFixed(1)}`,4,y+4);}
      const visible=Math.max(2,Math.ceil(points.length*p)); const active=points.slice(0,visible); const last=active[active.length-1];
      const grad=ctx.createLinearGradient(0,pad.top,0,height-pad.bottom);grad.addColorStop(0,positive?"rgba(99,168,255,.36)":"rgba(255,95,127,.34)");grad.addColorStop(1,"rgba(12,24,47,0)");
      ctx.beginPath();active.forEach((pt,i)=>i?ctx.lineTo(pt.x,pt.y):ctx.moveTo(pt.x,pt.y));ctx.lineTo(last.x,height-pad.bottom);ctx.lineTo(active[0].x,height-pad.bottom);ctx.closePath();ctx.fillStyle=grad;ctx.fill();
      ctx.beginPath();active.forEach((pt,i)=>i?ctx.lineTo(pt.x,pt.y):ctx.moveTo(pt.x,pt.y));ctx.strokeStyle=line;ctx.lineWidth=3;ctx.lineCap="round";ctx.lineJoin="round";ctx.stroke();
      ctx.beginPath();ctx.arc(last.x,last.y,5,0,Math.PI*2);ctx.fillStyle=line;ctx.fill();ctx.strokeStyle="#fff";ctx.lineWidth=2;ctx.stroke();
      ctx.fillStyle="rgba(185,199,225,.7)";ctx.fillText("12 weeks ago",pad.left,height-10);ctx.textAlign="right";ctx.fillText("current",width-pad.right,height-10);ctx.textAlign="left";
    }
    const start=performance.now();
    function frame(now){progress=Math.min(1,(now-start)/900);paint(1-Math.pow(1-progress,3));if(progress<1)requestAnimationFrame(frame);}
    requestAnimationFrame(frame);

    const tooltip=canvas.parentElement?.querySelector(".chart-tooltip");
    canvas.addEventListener("mousemove",(event)=>{if(!tooltip)return;const box=canvas.getBoundingClientRect();const x=event.clientX-box.left;let nearest=points.reduce((best,pt)=>Math.abs(pt.x-x)<Math.abs(best.x-x)?pt:best,points[0]);tooltip.hidden=false;tooltip.textContent=`Week -${values.length-1-nearest.index}: $${nearest.value.toFixed(2)}`;tooltip.style.left=`${nearest.x}px`;tooltip.style.top=`${nearest.y}px`;});
    canvas.addEventListener("mouseleave",()=>{if(tooltip)tooltip.hidden=true;});
  }

  function drawCashflowDonuts(root = document) {
    root.querySelectorAll(".cashflow-rings").forEach((wrap)=>{
      const canvas=wrap.querySelector("canvas"); if(!canvas)return;
      const income=Math.max(0,Number(wrap.dataset.income||0)), expenses=Math.max(0,Number(wrap.dataset.expenses||0)); const total=Math.max(1,income+expenses);
      const dpr=Math.max(1,Math.min(2,window.devicePixelRatio||1)); const size=260; canvas.width=size*dpr;canvas.height=size*dpr;const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);
      const start=-Math.PI/2; let progress=0;
      function paint(p){ctx.clearRect(0,0,size,size);ctx.lineWidth=22;ctx.lineCap="round";ctx.strokeStyle="rgba(124,145,183,.15)";ctx.beginPath();ctx.arc(130,130,88,0,Math.PI*2);ctx.stroke();const incomeAngle=(income/total)*Math.PI*2*p;ctx.strokeStyle="#5fa8ff";ctx.beginPath();ctx.arc(130,130,88,start,start+incomeAngle);ctx.stroke();ctx.strokeStyle="#ff5f7f";ctx.beginPath();ctx.arc(130,130,88,start+incomeAngle,start+Math.PI*2*p);ctx.stroke();}
      const t0=performance.now();function frame(now){progress=Math.min(1,(now-t0)/850);paint(1-Math.pow(1-progress,3));if(progress<1)requestAnimationFrame(frame);}requestAnimationFrame(frame);
    });
  }

  function drawReportRadar(canvas) {
    let values=[];try{values=JSON.parse(canvas.dataset.values||"[]").map(Number);}catch(_error){return;}if(values.length<5)return;
    const labels=["Finishing","Creation","Passing","Duels","Discipline"];const dpr=Math.max(1,Math.min(2,window.devicePixelRatio||1));const size=320;canvas.width=size*dpr;canvas.height=size*dpr;const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);const cx=160,cy=158,r=112;
    function point(i,scale){const a=-Math.PI/2+i*Math.PI*2/5;return{x:cx+Math.cos(a)*r*scale,y:cy+Math.sin(a)*r*scale};}
    function paint(p){ctx.clearRect(0,0,size,size);for(let ring=1;ring<=4;ring++){ctx.beginPath();for(let i=0;i<5;i++){const q=point(i,ring/4);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y);}ctx.closePath();ctx.strokeStyle="rgba(137,159,198,.22)";ctx.stroke();}for(let i=0;i<5;i++){const q=point(i,1);ctx.beginPath();ctx.moveTo(cx,cy);ctx.lineTo(q.x,q.y);ctx.strokeStyle="rgba(137,159,198,.16)";ctx.stroke();ctx.font="12px ui-sans-serif,system-ui";ctx.fillStyle="#8fa2c5";ctx.textAlign=q.x<cx-10?"right":q.x>cx+10?"left":"center";ctx.fillText(labels[i],q.x,q.y+(q.y<cy?-8:16));}ctx.beginPath();values.forEach((v,i)=>{const q=point(i,Math.max(.08,Math.min(1,v/100))*p);i?ctx.lineTo(q.x,q.y):ctx.moveTo(q.x,q.y);});ctx.closePath();ctx.fillStyle="rgba(99,168,255,.22)";ctx.fill();ctx.strokeStyle="#63a8ff";ctx.lineWidth=3;ctx.stroke();}
    const t0=performance.now();function frame(now){const p=Math.min(1,(now-t0)/760);paint(1-Math.pow(1-p,3));if(p<1)requestAnimationFrame(frame);}requestAnimationFrame(frame);
  }

  function drawReportVisuals(root = document) {
    root.querySelectorAll("canvas.performance-radar").forEach(drawReportRadar);
  }

  function drawChart(canvas) {
    let values = [];
    try { values = JSON.parse(canvas.dataset.series || "[]").map(Number).filter(Number.isFinite); } catch (_error) { values = []; }
    if (!values.length) return;
    while (values.length < 4) values.unshift(values[0]);
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    const width = Math.max(280, rect.width || 520);
    const height = Math.max(150, rect.height || 160);
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    const pad = {left: 18, right: 18, top: 16, bottom: 20};
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = Math.max(0.5, max - min);
    const points = values.map((value, index) => ({
      x: pad.left + (index / Math.max(1, values.length - 1)) * innerW,
      y: pad.top + (1 - (value - min) / range) * innerH,
    }));
    const positive = canvas.dataset.positive === "true";
    const line = positive ? "#667dff" : "#e34863";
    const fillTop = positive ? "rgba(102,125,255,.30)" : "rgba(227,72,99,.27)";
    const fillBottom = positive ? "rgba(102,125,255,0)" : "rgba(227,72,99,0)";

    function paint(progress) {
      ctx.clearRect(0, 0, width, height);
      ctx.strokeStyle = "rgba(86,102,133,.12)";
      ctx.lineWidth = 1;
      for (let i=0; i<4; i+=1) {
        const y = pad.top + (i / 3) * innerH;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(width-pad.right, y); ctx.stroke();
      }
      const visible = Math.max(2, Math.ceil(points.length * progress));
      const active = points.slice(0, visible);
      const gradient = ctx.createLinearGradient(0, pad.top, 0, height-pad.bottom);
      gradient.addColorStop(0, fillTop); gradient.addColorStop(1, fillBottom);
      ctx.beginPath();
      active.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
      const last = active[active.length-1];
      ctx.lineTo(last.x, height-pad.bottom); ctx.lineTo(active[0].x, height-pad.bottom); ctx.closePath();
      ctx.fillStyle = gradient; ctx.fill();
      ctx.beginPath();
      active.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
      ctx.strokeStyle = line; ctx.lineWidth = 3; ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.stroke();
      ctx.beginPath(); ctx.arc(last.x, last.y, 4.5, 0, Math.PI*2); ctx.fillStyle=line; ctx.fill();
    }
    const start = performance.now();
    function frame(now) {
      const progress = Math.min(1, (now-start)/720);
      paint(1 - Math.pow(1-progress, 3));
      if (progress < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  function drawCharts(root = document) {
    root.querySelectorAll("canvas.market-chart").forEach(drawChart);
    root.querySelectorAll("canvas.market-chart-pro").forEach(drawDetailedChart);
    drawCashflowDonuts(root);
    drawReportVisuals(root);
  }

  function extractFlash(doc) {
    const flash = doc.querySelector(".flash");
    return flash?.textContent?.trim() || "Action completed.";
  }

  function replaceCareerChrome(doc) {
    [["career-hud", "[data-career-hud]"], ["career-sidebar-card", "[data-career-sidebar]"]].forEach(([id, selector]) => {
      const current = document.getElementById(id);
      const next = doc.querySelector(selector);
      if (current && next) current.replaceWith(next);
    });
  }

  function showActionReceipt(message, isError = false) {
    showToast(message, isError);
    const hud = document.querySelector("[data-career-hud]");
    if (!hud || !message) return;
    let receipt = hud.querySelector(".career-action-receipt");
    if (!receipt) {
      receipt = document.createElement("div");
      receipt.className = "career-action-receipt";
      hud.append(receipt);
    }
    receipt.classList.toggle("error", isError);
    receipt.textContent = message;
    window.clearTimeout(showActionReceipt.timer);
    showActionReceipt.timer = window.setTimeout(() => receipt.classList.add("settled"), 2400);
  }

  function initialiseLiveForms(root = document) {
    root.querySelectorAll("form[data-live-form]").forEach((form) => {
      if (form.dataset.liveBound === "true") return;
      form.dataset.liveBound = "true";
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const scope = form.closest("[data-live-scope]");
        if (!scope) { saveScroll(); form.submit(); return; }
        const submitter = event.submitter || form.querySelector("button[type='submit'], button:not([type])");
        const originalLabel = submitter?.textContent;
        if (submitter) { submitter.disabled = true; submitter.dataset.originalLabel = originalLabel || ""; submitter.textContent = "Working…"; }
        form.setAttribute("aria-busy", "true");
        const y = window.scrollY;
        const scopeId = scope.id;
        try {
          const response = await fetch(form.action, {
            method: (form.method || "POST").toUpperCase(),
            body: new FormData(form),
            headers: {"X-Requested-With":"fetch", "Accept":"text/html"},
            redirect: "follow",
          });
          const html = await response.text();
          if (!response.ok) throw new Error("The action failed.");
          const doc = new DOMParser().parseFromString(html, "text/html");
          const replacement = doc.querySelector(`#${CSS.escape(scopeId)}`);
          if (!replacement) throw new Error("The action completed, but the updated screen did not match this page.");
          const message = extractFlash(doc);
          scope.replaceWith(replacement);
          replaceCareerChrome(doc);
          initialiseVisualUI(replacement);
          window.scrollTo({top:y, behavior:"auto"});
          showActionReceipt(message);
        } catch (error) {
          form.removeAttribute("aria-busy");
          if (submitter) { submitter.disabled = false; submitter.textContent = originalLabel || "Try again"; }
          showActionReceipt(error.message || "Action failed.", true);
        }
      });
    });
  }

  function initialiseVisualUI(root = document) {
    decorateCrests(root);
    decorateFlags(root);
    applyRealLogos(root);
    drawCharts(root);
    initialiseLiveForms(root);
    root.querySelectorAll(".surface, .property-listing, .investment-terminal, .club-card-v64").forEach((node,index)=>{node.style.setProperty("--reveal-delay",`${Math.min(index,12)*35}ms`);node.classList.add("reveal-ready");});
    requestAnimationFrame(()=>root.querySelectorAll(".reveal-ready").forEach(node=>node.classList.add("revealed")));
  }

  const shortcutDialog = document.getElementById("shortcut-dialog");
  document.querySelectorAll("[data-open-shortcuts]").forEach((button) => {
    button.addEventListener("click", () => shortcutDialog?.showModal());
  });
  document.querySelectorAll("[data-close-shortcuts]").forEach((button) => {
    button.addEventListener("click", () => shortcutDialog?.close());
  });
  document.querySelectorAll("[data-toggle-nav]").forEach((button) => {
    button.addEventListener("click", () => document.body.classList.toggle("nav-open"));
  });
  document.querySelectorAll(".side-nav a").forEach((link) => {
    const current = window.location.pathname;
    const path = new URL(link.href, window.location.origin).pathname;
    if (current === path || (path !== "/" && current.startsWith(path))) link.classList.add("active");
    link.addEventListener("click", saveScroll);
  });

  function navigateShortcut(key) {
    const destinations = {
      h: "/",
      k: "/calendar",
      m: "/market",
      f: "/finances",
      y: "/career-history",
      w: "/world",
    };
    if (destinations[key]) { saveScroll(); window.location.href = destinations[key]; }
  }

  async function setTrainingFocus(button) {
    const panel = document.getElementById("development");
    if (!panel || !button) return;
    const endpoint = panel.dataset.trainingEndpoint;
    const focus = button.dataset.trainingFocus;
    if (!endpoint || !focus || button.disabled || panel.dataset.trainingLocked === "true") return;

    document.querySelectorAll("[data-training-focus]").forEach((item) => item.disabled = true);
    button.classList.add("loading");

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({focus}),
      });
      const data = await response.json();
      if (data.plan?.locked) panel.dataset.trainingLocked = "true";
      if (!response.ok || !data.ok) throw new Error(data.message || "Could not update training plan.");

      document.querySelectorAll("[data-training-focus]").forEach((item) => {
        const selected = item.dataset.trainingFocus === data.plan.focus;
        item.classList.toggle("selected", selected);
        item.setAttribute("aria-pressed", String(selected));
      });
      document.getElementById("training-plan-label").textContent = data.plan.label;
      document.getElementById("training-plan-title").textContent = data.plan.label;
      document.getElementById("training-plan-description").textContent = data.plan.description;
      document.getElementById("hero-training-pill").textContent = data.plan.label;
      panel.querySelectorAll("[data-training-preview]").forEach((item) => {
        item.textContent = `+${data.plan.weekly_preview[item.dataset.trainingPreview]} XP`;
      });
      document.getElementById("training-preview-note").textContent = data.plan.preview_note;
      showToast(data.message);
    } catch (error) {
      showToast(error.message || "Training plan failed.", true);
    } finally {
      button.classList.remove("loading");
      document.querySelectorAll("[data-training-focus]").forEach((item) => item.disabled = panel.dataset.trainingLocked === "true");
    }
  }

  document.querySelectorAll("[data-training-focus]").forEach((button) => {
    button.addEventListener("click", () => setTrainingFocus(button));
  });

  function submitContinue() {
    const control = document.querySelector(".keyboard-continue");
    if (!control || control.disabled) return;
    if (control.tagName === "A") {
      window.location.href = control.href;
      return;
    }
    const form = control.closest("form");
    if (form) form.requestSubmit(control);
    else control.click();
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
    const nextEventButton = document.getElementById("skip-next-event");
    const livePlayerFocus = document.getElementById("player-briefing");
    const livePlayerState = document.getElementById("live-player-state");
    const livePlayerGoals = document.getElementById("live-player-goals");
    const livePlayerAssists = document.getElementById("live-player-assists");
    const livePlayerCards = document.getElementById("live-player-cards");
    const homeRevealedShots = document.getElementById("home-revealed-shots");
    const awayRevealedShots = document.getElementById("away-revealed-shots");
    const reportLock = document.getElementById("report-lock");
    const reportMount = document.getElementById("post-match-mount");
    const playerTeamHome = stage.dataset.playerTeamHome === "true";
    const advanceEndpoint = stage.dataset.advanceEndpoint;
    const completeEndpoint = stage.dataset.completeEndpoint;
    const totalEvents = Number(stage.dataset.eventCount || 0);
    const alreadyCompleted = stage.dataset.sessionStatus === "completed";
    const pitchBall = document.getElementById("pitch-ball");
    const pitchLabel = document.getElementById("pitch-action-label");
    const goalFlash = document.getElementById("goal-flash");
    const pitch = document.getElementById("live-pitch");

    let cursor = 0;
    let paused = false;
    let speed = 1;
    let timer = null;
    let finalising = false;
    let reportShown = false;
    let skipInProgress = false;
    const livePresentationSeen = new Set();
    const livePlayerStats = {
      goals: 0,
      assists: 0,
      yellow: 0,
      red: 0,
    };
    const revealedShots = {
      home: 0,
      away: 0,
    };
    const REAL_SECONDS_PER_MATCH_MINUTE = 2;
    const BASE_MATCH_DURATION_MS = 90 * REAL_SECONDS_PER_MATCH_MINUTE * 1000;


    function interval() {
      const eventSlots = Math.max(1, totalEvents);
      return Math.max(
        260,
        BASE_MATCH_DURATION_MS / eventSlots / speed,
      );
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

    function pulseLivePlayerFocus() {
      if (!livePlayerFocus) return;

      livePlayerFocus.classList.remove("is-live-event");
      void livePlayerFocus.offsetWidth;
      livePlayerFocus.classList.add("is-live-event");

      window.setTimeout(() => {
        livePlayerFocus.classList.remove("is-live-event");
      }, 620);
    }

    function updateLivePresentation(item) {
      if (!item) return;

      const key = String(
        item.sequence
        ?? `${item.minute || 0}:${item.kind || "moment"}:${item.text || ""}`,
      );

      if (livePresentationSeen.has(key)) return;
      livePresentationSeen.add(key);

      const visual = item?.visual || {};
      const sourceKind = String(
        visual.source_kind
        || item.kind
        || "",
      ).toLowerCase();
      const visualKind = String(
        visual.kind
        || "",
      ).toLowerCase();
      const contribution = String(
        item?.metadata?.contribution
        || "",
      ).toLowerCase();
      const careerEvent = (
        visual.actor_id === "career_player"
        || contribution === "goal"
        || contribution === "assist"
      );

      let playerChanged = false;

      if (
        sourceKind === "goal_for"
        && contribution === "goal"
      ) {
        livePlayerStats.goals += 1;
        playerChanged = true;
      }

      if (
        sourceKind === "goal_for"
        && contribution === "assist"
      ) {
        livePlayerStats.assists += 1;
        playerChanged = true;
      }

      if (
        careerEvent
        && visualKind === "yellow_card"
      ) {
        livePlayerStats.yellow += 1;
        playerChanged = true;
      }

      if (
        careerEvent
        && visualKind === "red_card"
      ) {
        livePlayerStats.red += 1;
        playerChanged = true;
      }

      if (
        visual.actor_id === "career_player"
        && visualKind === "substitution_on"
        && livePlayerState
      ) {
        livePlayerState.textContent = "ON PITCH";
        playerChanged = true;
      }

      if (
        visual.actor_id === "career_player"
        && visualKind === "substitution_off"
        && livePlayerState
      ) {
        livePlayerState.textContent = "SUBBED OFF";
        playerChanged = true;
      }

      if (livePlayerGoals) {
        livePlayerGoals.textContent = String(
          livePlayerStats.goals,
        );
      }

      if (livePlayerAssists) {
        livePlayerAssists.textContent = String(
          livePlayerStats.assists,
        );
      }

      if (livePlayerCards) {
        livePlayerCards.textContent = (
          `${livePlayerStats.yellow}Y / `
          + `${livePlayerStats.red}R`
        );
      }

      if (
        ["goal", "save", "miss"].includes(visualKind)
        && visual.side === "home"
      ) {
        revealedShots.home += 1;
      }

      if (
        ["goal", "save", "miss"].includes(visualKind)
        && visual.side === "away"
      ) {
        revealedShots.away += 1;
      }

      if (homeRevealedShots) {
        homeRevealedShots.textContent = String(
          revealedShots.home,
        );
      }

      if (awayRevealedShots) {
        awayRevealedShots.textContent = String(
          revealedShots.away,
        );
      }

      if (playerChanged) {
        pulseLivePlayerFocus();
      }
    }

    function addEventImmediate(item, instant = false) {
      if (!item) return;
      updateLivePresentation(item);
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
      timeline.scrollTo({top: timeline.scrollHeight, behavior: instant || speed === 4 ? "auto" : "smooth"});

      const mapped = mapScore(item.score);
      homeScore.textContent = mapped.home;
      awayScore.textContent = mapped.away;
      minute.textContent = item.kind === "full_time" ? "FT" : `${String(item.minute).padStart(2, "0")}'`;
      eventCount.textContent = `${Math.min(cursor + 1, totalEvents)} / ${totalEvents}`;
    }

    async function addEvent(item, instant = false) {
      if (!item) return;
      if (
        timeline.querySelector(
          `[data-sequence="${item.sequence}"]`,
        )
      ) return;

      if (instant || !item.visual) {
        addEventImmediate(item, instant);
        return;
      }

      const visualPlayer =
        window.FootyMatchVisuals?.playEvent;

      if (typeof visualPlayer !== "function") {
        addEventImmediate(item, instant);
        return;
      }

      const VISUAL_TIMEOUT_MS = 1600;
      let timeoutId = null;

      try {
        const timeout = new Promise((resolve) => {
          timeoutId = window.setTimeout(
            resolve,
            VISUAL_TIMEOUT_MS,
          );
        });

        await Promise.race([
          Promise.resolve(visualPlayer(item)),
          timeout,
        ]);
      } catch (error) {
        console.error(
          "Match event visualization failed:",
          error,
        );
      } finally {
        if (timeoutId !== null) {
          window.clearTimeout(timeoutId);
        }
      }

      addEventImmediate(item, false);
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
      const summaryChips = el("div", "offer-chips");
      [["Final score", `${finalScore.home}–${finalScore.away}`], ["Minutes", report.minutes], ["Output", `${report.goals}G · ${report.assists}A`]].forEach(([label, value]) => {
        const chip = el("span", ""); chip.textContent = `${label}: ${value}`; summaryChips.append(chip);
      });
      heroCopy.append(summaryChips);
      const rating = el("div", "report-rating");
      rating.append(el("small", "", "RATING"), el("strong", "", report.rating ? Number(report.rating).toFixed(1) : "—"));
      hero.append(heroCopy, rating);
      root.append(hero);

      const visualGrid = el("div", "report-visual-grid-v64");
      const radarPanel = el("section", "panel report-radar-panel");
      radarPanel.append(el("p", "eyebrow", "PERFORMANCE SHAPE"), el("h2", "", "Match influence radar"));
      const radar = el("canvas", "performance-radar");
      const shotAccuracy = report.metrics.shots ? (report.metrics.shots_on_target / report.metrics.shots) * 100 : 50;
      const creativeScore = Math.min(100, Number(report.metrics.key_passes || 0) * 18 + Number(report.assists || 0) * 28);
      const passingScore = Math.max(0, Math.min(100, Number(report.metrics.pass_accuracy || 0)));
      const duelScore = report.metrics.duels ? (report.metrics.duels_won / report.metrics.duels) * 100 : 50;
      const disciplineScore = Math.max(0, 100 - Number(report.yellow_cards || 0) * 24 - Number(report.red_cards || 0) * 70 - Number(report.metrics.fouls_committed || 0) * 7);
      radar.dataset.values = JSON.stringify([shotAccuracy, creativeScore, passingScore, duelScore, disciplineScore]);
      radarPanel.append(radar);
      const mapPanel = el("section", "panel report-activity-panel");
      mapPanel.append(el("p", "eyebrow", "ACTIVITY MAP"), el("h2", "", "Where your influence landed"));
      const map = el("div", "report-pitch-map");
      const markerCount = Math.min(12, Math.max(3, Number(report.metrics.shots || 0) + Number(report.metrics.key_passes || 0) + Number(report.metrics.dribbles_completed || 0)));
      for (let index=0; index<markerCount; index+=1) { const dot=el("i", index < Number(report.metrics.shots || 0) ? "shot-dot" : "action-dot"); dot.style.left=`${18 + ((index*29 + Number(report.minutes||0))%68)}%`; dot.style.top=`${14 + ((index*37 + Number(report.rating||0)*10)%72)}%`; map.append(dot); }
      mapPanel.append(map, el("p", "muted", "Visual activity estimate derived from recorded shots, chances and successful actions."));
      visualGrid.append(radarPanel, mapPanel);
      root.append(visualGrid);

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
      [["POSITIVE IMPACT", analysis.strengths, false], ["PERFORMANCE REVIEW", analysis.gaps, false], ["NEXT TRAINING BLOCK", analysis.coaching_actions, true]].forEach(([heading, items, includeFocus]) => {
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
      initialiseVisualUI(reportMount);
      reportMount.scrollIntoView({behavior: speed === 4 ? "auto" : "smooth", block: "start"});
      pauseButton.textContent = "Replay complete";
      pauseButton.disabled = true;
      finishButton.disabled = true;
      if (nextEventButton) nextEventButton.disabled = true;
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
          await addEvent(events[index], skip);
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
        await addEvent(payload.event);
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

    const MAJOR_EVENT_KINDS = new Set([
      "goal_for",
      "goal_against",
      "player_shot_saved",
      "player_shot_off_target",
      "yellow_card",
      "red_card",
      "injury",
      "player_on",
      "player_off",
      "set_piece",
      "corner",
      "penalty",
      "free_kick",
      "full_time",
    ]);

    function isMajorEvent(item) {
      if (!item) return false;
      const sourceKind = String(
        item.visual?.source_kind || item.kind || "",
      ).toLowerCase();
      const visualKind = String(
        item.visual?.kind || "",
      ).toLowerCase();

      return (
        MAJOR_EVENT_KINDS.has(sourceKind)
        || ["goal", "save", "miss"].includes(visualKind)
      );
    }

    async function skipToNextMajorEvent() {
      if (finalising || reportShown || skipInProgress) return;

      skipInProgress = true;
      window.clearTimeout(timer);

      if (nextEventButton) nextEventButton.disabled = true;
      status.textContent = "Skipping to next major event";

      try {
        for (let guard = 0; guard < 64; guard += 1) {
          const payload = await postJson(advanceEndpoint, {cursor});

          if (payload.completed) {
            await finalise(false);
            return;
          }

          const major = isMajorEvent(payload.event);
          await addEvent(payload.event, !major);
          cursor = payload.cursor;

          if (
            payload.event?.kind === "full_time"
            || !payload.has_more
          ) {
            await finalise(false);
            return;
          }

          if (major) break;
        }

        status.textContent = paused ? "Paused" : "Playing";

        if (!paused && !reportShown && !finalising) {
          timer = window.setTimeout(tick, interval());
        }
      } catch (error) {
        paused = true;
        status.textContent = "Replay paused · connection error";
        showToast(
          error.message || "Could not skip to next event.",
          true,
        );
      } finally {
        skipInProgress = false;
        if (nextEventButton && !reportShown) {
          nextEventButton.disabled = false;
        }
      }
    }

    if (nextEventButton) {
      nextEventButton.addEventListener(
        "click",
        skipToNextMajorEvent,
      );
    }

    function handleNextEventShortcut(event) {
      if (
        event.defaultPrevented
        || event.repeat
        || event.metaKey
        || event.ctrlKey
        || event.altKey
      ) return;

      const target = event.target;
      if (
        target instanceof HTMLElement
        && (
          target.isContentEditable
          || target.matches("input, textarea, select")
        )
      ) return;

      if (event.key.toLowerCase() !== "n") return;

      event.preventDefault();
      skipToNextMajorEvent();
    }

    document.addEventListener(
      "keydown",
      handleNextEventShortcut,
    );

    function togglePause() {
      if (finalising || reportShown) return;
      paused = !paused;
      status.textContent = paused ? "Paused" : "Playing";
      pauseButton.innerHTML = paused ? "Resume <kbd>Space</kbd>" : "Pause <kbd>Space</kbd>";
      window.clearTimeout(timer);
      if (!paused) tick();
    }

    function setSpeed(nextSpeed) {
      const next = Number(nextSpeed);
      speed = [1, 2, 4].includes(next) ? next : 1;
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

  initialiseVisualUI(document);
  restoreScroll();
  window.addEventListener("resize", () => { window.clearTimeout(window.__footyResize); window.__footyResize = window.setTimeout(() => drawCharts(document), 120); });
  document.addEventListener("submit", (event) => { if (!event.target.matches("form[data-live-form]")) saveScroll(); });

  const replay = page === "match" ? setupMatchReplay() : null;

  document.addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey || event.repeat || isTypingTarget(event.target)) return;
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

    if (key === "c" && document.querySelector(".keyboard-continue")) {
      event.preventDefault();
      submitContinue();
      return;
    }

    if (page === "dashboard" && setupDashboardShortcuts(event)) return;
    if (page === "match" && replay) {
      if (event.code === "Space") {
        event.preventDefault();
        replay.togglePause();
        return;
      }
      if (["1", "2", "4"].includes(key)) {
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
