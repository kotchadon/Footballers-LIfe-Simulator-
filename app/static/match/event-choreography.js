function kindOf(item) { return String(item?.visual?.kind || item?.kind || 'moment').toUpperCase(); }
export function createEventChoreography({tactical, matchEngine, onOverlay = () => {}}) {
  let generation = 0, halftimeShown = false;
  const seen = new Set();
  function cancel() { generation++; tactical.cancelAuthoritativeBuildup?.(); }
  function applyInstantEvent(item) {
    if (!item?.visual || matchEngine.isFinished()) return;
    const key = item.sequence ?? item;
    if (seen.has(key)) return;
    seen.add(key);
    if (!halftimeShown && Number(item.minute) > 45) {
      halftimeShown = Boolean(matchEngine.handleHalftime());
    }
    const kind = kindOf(item);
    if (kind.startsWith('SUBSTITUTION_')) matchEngine.handleSubstitution(item);
    if (kind === 'RED_CARD') matchEngine.handleCard(item);
    matchEngine.refresh();
  }
  async function playEvent(item) {
    if (!item?.visual || matchEngine.isFinished()) return;
    const token = ++generation;
    const alive = () => token === generation && !matchEngine.isFinished() && !matchEngine.isDestroyed();
    const wait = async seconds => (await matchEngine.waitForSimulation(seconds)) && alive();
    const half = !halftimeShown && Number(item.minute) > 45;
    applyInstantEvent(item);
    if (half) onOverlay('SECOND HALF');
    const visual = item.visual, kind = kindOf(item);
    if (kind.startsWith('SUBSTITUTION_')) { onOverlay(kind.endsWith('_ON') ? 'SUBSTITUTION · ON' : 'SUBSTITUTION · OFF'); return; }
    if (kind.endsWith('_CARD')) { onOverlay(kind === 'RED_CARD' ? 'RED CARD' : 'YELLOW CARD'); return; }
    if (['GOAL', 'SAVE', 'MISS'].includes(kind)) {
      onOverlay('BUILDUP');
      const buildupDuration=tactical.beginAuthoritativeBuildup({side:visual.side,actorId:visual.actor_id});
      // This is the existing fixed-step presentation clock, never a wall timer.
      let elapsed=0;
      while(!tactical.isAuthoritativeBuildupReady() && elapsed<buildupDuration+.5) {
        if(!(await wait(.05)))return;
        elapsed+=.05;
      }
      if(!tactical.isAuthoritativeBuildupReady()){tactical.cancelAuthoritativeBuildup();return;}
      onOverlay('SHOT');
      const duration = tactical.beginAuthoritativeEvent({kind:'SHOT',outcome:kind,side:visual.side,actorId:visual.actor_id,ballStart:visual.ball_start,ballTarget:visual.ball_target});
      if (!(await wait(duration))) return;
      if (kind === 'GOAL') { tactical.celebrate?.(visual.side); onOverlay('GOAL'); }
      if (kind === 'SAVE') { tactical.playKeeperAction('GK_CATCH',visual.side); onOverlay('SAVE'); }
      if (kind === 'MISS') onOverlay('OFF TARGET');
      await wait(.35);
      return alive()?kind:null;
    }
    if (['SET_PIECE','CORNER','PENALTY','THROW_IN','FREE_KICK'].includes(kind)) {
      const type = String(visual.set_piece_type || kind).toLowerCase();
      onOverlay(type.replaceAll('_',' ').toUpperCase());
      const handlers = {penalty:'handlePenalty',corner:'handleCorner',throw_in:'handleThrowIn',free_kick:'handleFreeKick'};
      const duration = handlers[type] ? matchEngine[handlers[type]](item) : tactical.prepareSetPiece('restart',visual);
      await wait(duration || .4);
    }
    if (kind === 'INJURY') onOverlay('INJURY STOPPAGE');
    if (kind === 'FULL_TIME') { onOverlay('FULL TIME'); matchEngine.finish(); }
  }
  return {playEvent,applyInstantEvent,cancel};
}
