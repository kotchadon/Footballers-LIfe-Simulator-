const CUES = new Set([
  "whistle",
  "kick",
  "crowd",
  "goal",
]);

export function createAudioController({enabled = false} = {}) {
  let isEnabled = Boolean(enabled);
  let context = null;

  function ensureContext() {
    if (context) return context;

    const AudioContextClass =
      window.AudioContext
      || window.webkitAudioContext;

    if (!AudioContextClass) return null;

    context = new AudioContextClass();
    return context;
  }

  function resumeSafely(ctx) {
    if (!ctx || ctx.state !== "suspended") return;
    const resumed = ctx.resume();
    if (resumed?.catch) resumed.catch(() => {});
  }

  function tone(
    ctx,
    frequency,
    duration,
    gainValue,
    {
      delay = 0,
      type = "sine",
      endFrequency = null,
    } = {},
  ) {
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = ctx.currentTime + delay;
    const end = start + duration;

    oscillator.type = type;
    oscillator.frequency.setValueAtTime(
      frequency,
      start,
    );

    if (endFrequency !== null) {
      oscillator.frequency.exponentialRampToValueAtTime(
        Math.max(1, endFrequency),
        end,
      );
    }

    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(
      Math.max(0.0001, gainValue),
      start + Math.min(.025, duration / 3),
    );
    gain.gain.exponentialRampToValueAtTime(
      0.0001,
      end,
    );

    oscillator.connect(gain);
    gain.connect(ctx.destination);
    oscillator.start(start);
    oscillator.stop(end + .02);
  }

  function setEnabled(value) {
    isEnabled = Boolean(value);

    if (isEnabled) {
      try {
        resumeSafely(ensureContext());
      } catch (error) {
        console.debug(
          "Match audio unavailable:",
          error,
        );
      }
    }

    return isEnabled;
  }

  function play(name) {
    const cue = String(name || "").toLowerCase();

    if (!isEnabled || !CUES.has(cue)) {
      return false;
    }

    try {
      const ctx = ensureContext();
      if (!ctx) return false;
      resumeSafely(ctx);

      if (cue === "kick") {
        tone(
          ctx,
          120,
          .07,
          .055,
          {
            type: "triangle",
            endFrequency: 72,
          },
        );
      } else if (cue === "whistle") {
        tone(
          ctx,
          1760,
          .11,
          .028,
          {
            type: "square",
            endFrequency: 2240,
          },
        );
        tone(
          ctx,
          1980,
          .10,
          .022,
          {
            delay: .12,
            type: "square",
            endFrequency: 1680,
          },
        );
      } else if (cue === "goal") {
        tone(ctx, 392, .18, .035);
        tone(
          ctx,
          523.25,
          .24,
          .032,
          {delay: .09},
        );
        tone(
          ctx,
          659.25,
          .34,
          .028,
          {delay: .18},
        );
      } else if (cue === "crowd") {
        tone(
          ctx,
          196,
          .34,
          .018,
          {type: "triangle"},
        );
        tone(
          ctx,
          246.94,
          .42,
          .015,
          {
            delay: .04,
            type: "triangle",
          },
        );
        tone(
          ctx,
          293.66,
          .48,
          .012,
          {
            delay: .08,
            type: "triangle",
          },
        );
      }

      return true;
    } catch (error) {
      console.debug(
        "Match audio cue skipped:",
        error,
      );
      return false;
    }
  }

  function destroy() {
    if (!context || context.state === "closed") {
      return;
    }

    const closed = context.close();
    if (closed?.catch) closed.catch(() => {});
    context = null;
  }

  return {
    setEnabled,
    play,
    isEnabled: () => isEnabled,
    destroy,
  };
}
