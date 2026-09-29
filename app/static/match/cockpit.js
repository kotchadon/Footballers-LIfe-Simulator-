/* Presentation only: called after the shared visual clock reveals an event. */
(() => {
  'use strict';
  const kindOf = item => String(item?.visual?.kind || item?.kind || 'moment').toLowerCase();
  function createPlayerState(selection) {
    return {status: selection === 'starter' ? 'ON PITCH' : ['bench', 'substitute'].includes(selection) ? 'BENCH' : 'UNAVAILABLE',
      enter: selection === 'starter' ? 0 : null, exit: null, minutes: 0, finished: false, seen: new Set()};
  }
  function advancePlayer(state, item) {
    const key = item.sequence ?? `${item.minute}:${item.kind}:${item.text}`;
    if (state.finished || state.seen.has(key)) return state;
    state.seen.add(key);
    const minute = Math.max(0, Number(item.minute) || 0), kind = kindOf(item);
    if (item.visual?.actor_id === 'career_player') {
      if (kind === 'substitution_on' && state.enter === null) {
        state.enter = minute; state.status = 'ON PITCH';
      }
      if (['substitution_off', 'red_card'].includes(kind) && state.enter !== null && state.exit === null) {
        state.exit = minute; state.status = kind === 'red_card' ? 'SENT OFF' : 'SUBBED OFF';
      }
    }
    if (state.enter !== null) state.minutes = Math.max(state.minutes, (state.exit ?? minute) - state.enter);
    if (kind === 'full_time' || item.kind === 'full_time') state.finished = true;
    return state;
  }
  function eventType(item) {
    const kind = kindOf(item);
    if (kind.includes('goal') && !kind.includes('kick')) return 'GOAL';
    const labels = {moment: 'PLAY', substitution_on: 'SUB ON', substitution_off: 'SUB OFF',
      yellow_card: 'YELLOW CARD', red_card: 'RED CARD', half_time: 'HALF TIME', full_time: 'FULL TIME',
      kick_off: 'KICK OFF', injury: 'INJURY', shot: 'SHOT', save: 'SAVE'};
    return labels[kind] || kind.replaceAll('_', ' ').toUpperCase();
  }
  function createFollowState() {
    return {following: true, unread: 0,
      scroll(top, height, total) { this.following = total - top - height <= 36; if (this.following) this.unread = 0; },
      append() { if (!this.following) this.unread += 1; return this.following; },
      resume() { this.following = true; this.unread = 0; }};
  }
  function mount() {
    const byId = id => document.getElementById(id);
    const data = JSON.parse(byId('cockpit-data').textContent);
    const state = createPlayerState(data.selection);
    const feed = byId('match-timeline'), jump = byId('jump-to-live'), follow = createFollowState();
    const dialog = byId('match-report-dialog'), reportButton = byId('open-match-report');
    const ownSide = data.player.team || 'home';
    const text = (id, value) => { const node = byId(id); if (node) node.textContent = value; };
    function renderPlayer() {
      text('live-player-state', state.finished && state.status === 'ON PITCH' ? 'FULL TIME' : state.status);
      text('live-player-minutes', `${state.minutes}′`);
      text('live-player-timing', `${data.selection === 'starter' ? 'Starter' : 'Bench / unavailable'}${state.enter !== null && state.enter > 0 ? ` · On ${state.enter}′` : ''}${state.exit !== null ? ` · Off ${state.exit}′` : ''}`);
      document.querySelectorAll('[data-career-status]').forEach(node => { node.textContent = state.status; });
    }
    function renderSquad(panelId, actors) {
      const list = byId(panelId).querySelector('ul');
      actors.forEach(actor => {
        const row = document.createElement('li');
        const number = document.createElement('span'), name = document.createElement('strong'), role = document.createElement('span');
        number.textContent = actor.shirt_number ?? '—'; name.textContent = actor.display_name || 'Unknown player'; role.textContent = actor.role || '—';
        row.append(number, name, role);
        if (actor.actor_id === 'career_player') {
          row.classList.add('is-career-player');
          const status = document.createElement('small'); status.dataset.careerStatus = ''; row.append(status);
        }
        list.append(row);
      });
    }
    renderSquad('squad-own', data.squads[ownSide]);
    renderSquad('squad-opponent', data.squads[ownSide === 'home' ? 'away' : 'home']);
    renderSquad('squad-bench', ['substitute', 'bench'].includes(data.selection) ? [data.player] : []);
    const tabs = [...byId('squad-tabs').querySelectorAll('[role=tab]')];
    function selectTab(tab) {
      tabs.forEach(button => {
        const active = button === tab;
        button.setAttribute('aria-selected', String(active)); button.tabIndex = active ? 0 : -1;
        byId(button.getAttribute('aria-controls')).hidden = !active;
      });
    }
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => selectTab(tab));
      tab.addEventListener('keydown', event => {
        const targets = {ArrowRight: (index + 1) % tabs.length, ArrowLeft: (index + tabs.length - 1) % tabs.length, Home: 0, End: tabs.length - 1};
        if (!(event.key in targets)) return;
        event.preventDefault(); const target = tabs[targets[event.key]]; selectTab(target); target.focus();
      });
    });
    const updateJump = () => { jump.hidden = follow.following; jump.textContent = `Jump to live${follow.unread ? ` · ${follow.unread} new` : ''}`; };
    feed.addEventListener('scroll', () => { follow.scroll(feed.scrollTop, feed.clientHeight, feed.scrollHeight); updateJump(); }, {passive: true});
    jump.addEventListener('click', () => { follow.resume(); feed.scrollTop = feed.scrollHeight; updateJump(); });
    reportButton.addEventListener('click', () => dialog.showModal());
    byId('close-match-report').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => reportButton.focus());
    renderPlayer();
    return {
      event(item, row) {
        advancePlayer(state, item); renderPlayer();
        const type = document.createElement('span'); type.className = 'commentary-type'; type.textContent = eventType(item);
        row.querySelector('p').prepend(type);
        if (item.visual?.actor_id === 'career_player' || ['goal', 'assist'].includes(item.metadata?.contribution)) row.classList.add('is-career-event');
        text('cockpit-latest-type', `${item.minute}′ · ${eventType(item)}`);
        text('cockpit-latest-text', item.text || 'Play continues.');
        if (follow.append()) feed.scrollTop = feed.scrollHeight;
        updateJump();
      },
      finish(payload) {
        state.finished = true;
        const report = payload.report || {};
        if (Number.isFinite(Number(report.minutes))) state.minutes = Number(report.minutes);
        renderPlayer();
        text('live-player-goals', report.goals ?? 0); text('live-player-assists', report.assists ?? 0);
        text('live-player-cards', `${report.yellow_cards ?? 0}Y / ${report.red_cards ?? 0}R`);
        if (report.fitness_after !== undefined) text('live-player-fitness', `${report.fitness_after}%`);
        text('live-player-rating', report.rating ?? '—');
        text('cockpit-latest-type', 'FULL TIME · FINAL');
        reportButton.disabled = false; reportButton.textContent = 'Match report ↗';
        document.querySelectorAll('[data-match-speed]').forEach(button => { button.disabled = true; });
        byId('player-briefing').dataset.finished = 'true';
      },
    };
  }
  globalThis.FootyCockpit = {createPlayerState, advancePlayer, eventType, createFollowState, mount};
})();
