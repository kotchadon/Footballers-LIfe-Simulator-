// Stage 1 runtime policy: keep optional model-viewer helpers same-origin.
// The current stadium GLB is self-contained and uncompressed, so none of these
// helpers should be requested. If a future asset needs them before they are
// vendored, that asset must fail locally and the match page must remain on 2D.
self.ModelViewerElement = self.ModelViewerElement || {};
self.ModelViewerElement.dracoDecoderLocation = "/static/vendor/model-viewer/draco/";
self.ModelViewerElement.ktx2TranscoderLocation = "/static/vendor/model-viewer/basis/";
self.ModelViewerElement.lottieLoaderLocation = "/static/vendor/model-viewer/lottie/LottieLoader.js";
