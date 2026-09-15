
function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function kindOf(item) {
  return String(
    item?.visual?.kind
    || item?.kind
    || "moment",
  ).toUpperCase();
}

export function createEventChoreography({
  tactical,
  onOverlay = () => {},
}) {
  async function playEvent(item) {
    const visual = item?.visual;
    if (!visual) return;

    const kind = kindOf(item);

    if (["GOAL", "SAVE", "MISS"].includes(kind)) {
      await playShotFamily(visual, kind);
      return;
    }

    if (kind === "YELLOW_CARD") {
      onOverlay("YELLOW CARD");
      await sleep(220);
      return;
    }

    if (kind === "RED_CARD") {
      onOverlay("RED CARD");
      await sleep(300);
      return;
    }

    if (kind === "INJURY") {
      onOverlay("INJURY STOPPAGE");
      await sleep(260);
      return;
    }

    await sleep(40);
  }

  async function playShotFamily(visual, kind) {
    onOverlay("SHOT");

    const duration =
      tactical.beginAuthoritativeEvent({
        kind: "SHOT",
        outcome: kind,
        side: visual.side,
        actorId: visual.actor_id,
        ballStart: visual.ball_start,
        ballTarget: visual.ball_target,
      });

    await sleep(
      Math.max(
        180,
        duration * 430,
      ),
    );

    if (kind === "GOAL") {
      onOverlay("GOAL");
      await sleep(520);
      return;
    }

    if (kind === "SAVE") {
      tactical.playKeeperAction(
        "GK_DIVE",
        visual.side,
      );

      await sleep(230);

      tactical.playKeeperAction(
        "GK_CATCH",
        visual.side,
      );

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
