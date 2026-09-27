import * as THREE from '../vendor/three/three.module.js';
import {GLTFLoader} from '../vendor/three/GLTFLoader.js';
import {createMatchScene} from './match-scene.js';

// The shared match engine owns the only animation loop.
export async function createThreeRenderer({canvas, modelUrl, plan, reducedMotion, onError}) {
  const abort = new AbortController();
  const timeout = setTimeout(() => abort.abort(), 12000);
  let webgl, model, disposed = false;
  let width = 0, height = 0;
  const lost = event => { event.preventDefault(); onError(new Error('3D context lost')); };
  function destroy() {
    if (disposed) return;
    disposed = true;
    abort.abort();
    clearTimeout(timeout);
    canvas.removeEventListener('webglcontextlost', lost);
    model?.dispose();
    webgl?.dispose();
  }
  try {
    webgl = new THREE.WebGLRenderer({canvas, antialias: true, alpha: false, powerPreference: 'high-performance'});
    webgl.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    webgl.shadowMap.enabled = true;
    webgl.shadowMap.type = THREE.PCFSoftShadowMap;
    webgl.outputColorSpace = THREE.SRGBColorSpace;
    webgl.toneMapping = THREE.ACESFilmicToneMapping;
    webgl.toneMappingExposure = 1.15;
    const response = await fetch(modelUrl, {signal: abort.signal, credentials: 'same-origin'});
    if (!response.ok) throw new Error('Stadium unavailable');
    const asset = await new GLTFLoader().parseAsync(await response.arrayBuffer(), '');
    model = createMatchScene(asset.scene, plan, {reducedMotion});
    clearTimeout(timeout);
    canvas.addEventListener('webglcontextlost', lost);
    function resize() {
      const w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight);
      if (w !== width || h !== height) { width = w; height = h; webgl.setSize(w, h, false); }
    }
    return {
      render(frame) {
        if (disposed) return;
        resize();
        model.sync(frame, width / height);
        webgl.render(model.scene, model.camera);
      },
      resize, destroy,
      setCameraMode(mode) { model.setCameraMode(mode); },
    };
  } catch (error) { destroy(); throw error; }
}
