import json
import struct
from pathlib import Path

MATCH_TEMPLATE = Path("app/templates/match.html")
STATIC = Path("app/static")


def _glb_json(path: Path) -> dict:
    data = path.read_bytes()
    assert data[:4] == b"glTF"
    version = struct.unpack("<I", data[4:8])[0]
    declared_length = struct.unpack("<I", data[8:12])[0]
    assert version == 2
    assert declared_length == len(data)

    chunk_length, chunk_type = struct.unpack("<II", data[12:20])
    assert chunk_type == 0x4E4F534A
    return json.loads(data[20:20 + chunk_length].decode("utf-8").rstrip("\x00 "))


def test_stage1_files_are_local_and_present():
    expected = (
        STATIC / "vendor/model-viewer/model-viewer.min.js",
        STATIC / "vendor/model-viewer/config.js",
        STATIC / "match/stadium-3d-poc.js",
        STATIC / "match/stadium-3d-poc.css",
        STATIC / "match/assets/footy-match-stadium-v1.glb",
    )
    for path in expected:
        assert path.is_file(), path


def test_match_template_keeps_2d_and_adds_opt_in_3d_shell():
    source = MATCH_TEMPLATE.read_text()

    assert 'id="match-canvas"' in source
    assert 'id="match-visual-stage"' in source
    assert 'id="match-2d-shell"' in source

    assert 'id="match-view-switcher"' in source
    assert 'id="match-3d-shell"' in source
    assert 'id="match-3d-viewer"' in source
    assert 'data-model-src=' in source

    assert "vendor/model-viewer/config.js" in source
    assert "vendor/model-viewer/model-viewer.min.js" in source
    assert "match/stadium-3d-poc.js" in source
    assert "match/stadium-3d-poc.css" in source

    # Static viewer only: no animation loop is auto-started in Stage 1.
    viewer_start = source.index('id="match-3d-viewer"')
    viewer_end = source.index("</model-viewer>", viewer_start)
    viewer_markup = source[viewer_start:viewer_end]
    assert "autoplay" not in viewer_markup
    assert "auto-rotate" not in viewer_markup


def test_stage1_bootstrap_is_presentation_only_and_fail_open():
    source = (STATIC / "match/stadium-3d-poc.js").read_text()

    assert 'getContext("webgl2"' in source
    assert 'getContext("webgl"' in source
    assert '"error"' in source
    assert "MODEL_LOAD_TIMEOUT_MS" in source
    assert 'setView("2d")' in source
    assert "button3d.disabled = true" in source

    forbidden = (
        "fetch(",
        "XMLHttpRequest",
        "advance_match",
        "complete_match",
        "visualEndpoint",
        "data-complete-endpoint",
        "data-advance-endpoint",
        "localStorage",
        "sessionStorage",
    )
    for token in forbidden:
        assert token not in source


def test_stage1_runtime_configuration_never_points_to_third_party_hosts():
    source = (STATIC / "vendor/model-viewer/config.js").read_text()
    assert "https://" not in source
    assert "http://" not in source
    assert "/static/vendor/model-viewer/draco/" in source
    assert "/static/vendor/model-viewer/basis/" in source
    assert "/static/vendor/model-viewer/lottie/" in source


def test_stadium_glb_is_self_contained_and_does_not_need_optional_decoders():
    doc = _glb_json(STATIC / "match/assets/footy-match-stadium-v1.glb")

    assert "KHR_draco_mesh_compression" not in doc.get("extensionsUsed", [])
    assert "KHR_texture_basisu" not in doc.get("extensionsUsed", [])

    external_uris = [
        item["uri"]
        for group in ("buffers", "images")
        for item in doc.get(group, [])
        if item.get("uri")
    ]
    assert external_uris == []

    names = {node.get("name") for node in doc.get("nodes", [])}
    assert "MatchBall" in names
    for side in ("home", "away"):
        for number in range(1, 12):
            assert f"{side}_{number:02d}" in names

def test_stage1_hidden_viewer_forces_eager_model_loading():
    source = Path("app/templates/match.html").read_text()

    start = source.index('id="match-3d-viewer"')
    end = source.index("</model-viewer>", start)
    viewer_markup = source[start:end]

    # The 3D shell intentionally starts hidden so the existing 2D renderer is
    # always the safe first paint. model-viewer lazy-loads by default, so hidden
    # preload must explicitly opt into eager loading or `load` can never fire.
    assert 'loading="eager"' in viewer_markup
