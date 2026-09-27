// Optional 3D never owns the match clock or outcome. Both renderers receive the
// same captured presentation frame, including while paused or at full time.
export function createRendererBridge({fallback, load, onMode = () => {}, onError = () => {}, timeoutMs = 15000}) {
  let three = null;
  let selected = "2d";
  let requested = "3d";
  let latest = null;
  let disposed = false;
  let failed = false;
  let pending = null;
  let timer = null;
  const notify = () => onMode(selected, Boolean(three) && !failed);
  function fail(error) {
    if (disposed || failed) return;
    failed = true;
    selected = "2d";
    const old = three;
    three = null;
    old?.destroy();
    notify();
    onError(error);
  }
  function render(frame) {
    if (disposed) return;
    latest = frame;
    if (selected === "3d" && three) {
      try { three.render(frame); return; }
      catch (error) { fail(error); }
    }
    fallback.render(frame);
  }
  function select(mode) {
    if (disposed) return selected;
    requested = mode === "3d" ? "3d" : "2d";
    selected = requested === "3d" && three && !failed ? "3d" : "2d";
    notify();
    if (latest) render(latest);
    return selected;
  }
  function init() {
    if (pending) return pending;
    if (disposed) return Promise.resolve(false);
    let expired = false;
    pending = new Promise(resolve => {
      timer = setTimeout(() => {
        expired = true;
        fail(new Error("3D loading timed out"));
        if (latest) fallback.render(latest);
        resolve(false);
      }, timeoutMs);
      // load() is deliberately inside a Promise boundary: missing modules,
      // unavailable WebGL, and malformed models all preserve Canvas boot.
      let loading;
      try { loading = load(); } catch (error) { loading = Promise.reject(error); }
      Promise.resolve(loading).then(runtime => {
        clearTimeout(timer);
        if (disposed || expired || failed) { runtime.destroy(); resolve(false); return; }
        three = runtime;
        select(requested);
        resolve(!failed);
      }).catch(error => {
        clearTimeout(timer);
        if (!disposed && !expired) { fail(error); if (latest) fallback.render(latest); }
        resolve(false);
      });
    });
    return pending;
  }
  function resize() {
    if (disposed) return;
    fallback.resize();
    if (three) {
      try { three.resize(); } catch (error) { fail(error); }
    }
    if (latest) render(latest);
  }
  function setCameraMode(mode) {
    three?.setCameraMode?.(mode);
    if (latest) render(latest);
  }
  function destroy() {
    if (disposed) return;
    disposed = true;
    clearTimeout(timer);
    three?.destroy();
    three = null;
    fallback.destroy();
  }
  return {init, render, select, resize, destroy, fail, setCameraMode, mode: () => selected};
}
