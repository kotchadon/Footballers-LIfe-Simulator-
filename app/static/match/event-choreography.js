function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function kindOf(item) {
  return String(item?.visual?.kind || item?.kind || "moment").toUpperCase();
}

export function createEventChoreography({
  tactical,
  matchEngine = null,
  onOverlay = () => {},
}) {
  let halftimeShown = false;

  async function maybeHalftime(item) {
    const minute = Number(item?.minute || 0);
    if (halftimeShown || minute <= 45 || minute >= 90) return;
    if (!matchEngine?.handleHalftime?.()) return;
    halftimeShown = true;
    onOverlay("HALF TIME");
    await sleep(620);
  }

  async function playEvent(item) {
    const visual = item?.visual;
    if (!visual) return;

    await maybeHalftime(item);
    const kind = kindOf(item);

    if (kind === "SUBSTITUTION_ON" || kind === "SUBSTITUTION_OFF") {
      matchEngine?.handleSubstitution?.(item);
      onOverlay(
        kind === "SUBSTITUTION_ON"
          ? "SUBSTITUTION · ON"
          : "SUBSTITUTION · OFF",
      );
      await sleep(360);
      return;
    }

    if (["GOAL", "SAVE", "MISS"].includes(kind)) {
      await playShotFamily(visual, kind);
      return;
    }

    if (kind === "YELLOW_CARD" || kind === "RED_CARD") {
      matchEngine?.handleCard?.(item);
      onOverlay(kind === "RED_CARD" ? "RED CARD" : "YELLOW CARD");
      await sleep(kind === "RED_CARD" ? 430 : 260);
      return;
    }

    if (
      ["SET_PIECE", "CORNER", "PENALTY", "THROW_IN", "FREE_KICK"].includes(kind)
    ) {
      await playSetPiece(item, kind);
      return;
    }

    if (kind === "INJURY") {
      onOverlay("INJURY STOPPAGE");
      await sleep(260);
      return;
    }

    await sleep(40);
  }

  async function playSetPiece(item, kind) {
    const subtype = String(item?.visual?.set_piece_type || kind).toLowerCase();
    let duration = .3;

    if (subtype === "penalty") {
      duration = Number(matchEngine?.handlePenalty?.(item) || .45);
      onOverlay("PENALTY");
    } else if (subtype === "corner") {
      duration = Number(matchEngine?.handleCorner?.(item) || .68);
      onOverlay("CORNER");
    } else if (subtype === "throw_in") {
      duration = Number(matchEngine?.handleThrowIn?.(item) || .48);
      onOverlay("THROW IN");
    } else if (subtype === "free_kick") {
      duration = Number(matchEngine?.handleFreeKick?.(item) || .64);
      onOverlay("FREE KICK");
    } else {
      duration = Number(tactical.prepareSetPiece("restart", item?.visual || {}) || .44);
      onOverlay("SET PIECE");
    }

    await sleep(Math.max(260, Math.min(800, duration * 1000)));
  }

  async function playShotFamily(visual, kind) {
    onOverlay("SHOT");

    const duration = tactical.beginAuthoritativeEvent({
      kind: "SHOT",
      outcome: kind,
      side: visual.side,
      actorId: visual.actor_id,
      ballStart: visual.ball_start,
      ballTarget: visual.ball_target,
    });

    await sleep(Math.max(180, duration * 430));

    if (kind === "GOAL") {
      onOverlay("GOAL");
      await sleep(520);
      return;
    }

    if (kind === "SAVE") {
      tactical.playKeeperAction("GK_DIVE", visual.side);
      await sleep(230);
      tactical.playKeeperAction("GK_CATCH", visual.side);
      onOverlay("SAVE");
      await sleep(280);
      return;
    }

    if (kind === "MISS") {
      onOverlay("OFF TARGET");
      await sleep(240);
    }
  }

  return {playEvent};
}
